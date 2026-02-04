"""
OLPA Database Utility Module
==============================
Purpose: Database connection management, table creation, and CRUD operations
for the OLPA data warehouse.

This module provides:
- Database connection utilities with connection pooling
- Schema initialization and table creation
- Data ingestion functions (batch and streaming)
- Query utilities for ETL pipelines
- Transaction management
- Error handling and logging

Author: OLPA Data Engineering Team
Version: 1.0
Last Updated: 2025-10-21
"""

import os
import logging
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from datetime import datetime
import yaml

import pandas as pd
import psycopg2
from psycopg2 import pool, sql, extras
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseConfig:
    """
    Database configuration management.
    Loads configuration from environment variables or config file.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize database configuration.

        Args:
            config_path: Path to YAML configuration file
        """
        if config_path and os.path.exists(config_path):
            self._load_from_file(config_path)
        else:
            self._load_from_env()

    def _load_from_file(self, config_path: str):
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        db_config = config.get('database', {}).get('warehouse', {}).get('connection', {})

        self.host = self._resolve_env_var(db_config.get('host', 'localhost'))
        self.port = int(self._resolve_env_var(db_config.get('port', '5432')))
        self.database = self._resolve_env_var(db_config.get('database', 'olpa_warehouse'))
        self.username = self._resolve_env_var(db_config.get('username', 'olpa_user'))
        self.password = self._resolve_env_var(db_config.get('password', 'changeme'))

        # Pool settings
        pool_config = config.get('database', {}).get('warehouse', {}).get('pool', {})
        self.pool_min_size = pool_config.get('min_size', 2)
        self.pool_max_size = pool_config.get('max_size', 10)

    def _load_from_env(self):
        """Load configuration from environment variables."""
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = int(os.getenv('DB_PORT', '5432'))
        self.database = os.getenv('DB_NAME', 'olpa_warehouse')
        self.username = os.getenv('DB_USER', 'olpa_user')
        self.password = os.getenv('DB_PASSWORD', 'changeme')
        self.pool_min_size = int(os.getenv('DB_POOL_MIN', '2'))
        self.pool_max_size = int(os.getenv('DB_POOL_MAX', '10'))

    @staticmethod
    def _resolve_env_var(value: str) -> str:
        """
        Resolve environment variable placeholders like ${VAR_NAME:-default}.

        Args:
            value: String that may contain env var placeholder

        Returns:
            Resolved string value
        """
        if not isinstance(value, str):
            return value

        if value.startswith('${') and value.endswith('}'):
            # Extract variable name and default value
            var_content = value[2:-1]
            if ':-' in var_content:
                var_name, default = var_content.split(':-', 1)
                return os.getenv(var_name, default)
            else:
                return os.getenv(var_content, value)
        return value

    def get_connection_string(self) -> str:
        """
        Get database connection string.

        Returns:
            PostgreSQL connection string
        """
        return (
            f"host={self.host} "
            f"port={self.port} "
            f"dbname={self.database} "
            f"user={self.username} "
            f"password={self.password}"
        )


class DatabaseConnection:
    """
    Database connection manager with connection pooling.
    Supports both single connections and connection pools for production use.
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize database connection manager.

        Args:
            config: DatabaseConfig instance (creates default if None)
        """
        self.config = config or DatabaseConfig()
        self._pool: Optional[pool.SimpleConnectionPool] = None
        self._standalone_conn: Optional[psycopg2.extensions.connection] = None

        logger.info(
            f"Database connection initialized for {self.config.database} "
            f"at {self.config.host}:{self.config.port}"
        )

    def initialize_pool(self):
        """
        Initialize connection pool for production use.
        Call this method to enable connection pooling.
        """
        if self._pool is not None:
            logger.warning("Connection pool already initialized")
            return

        try:
            self._pool = pool.SimpleConnectionPool(
                self.config.pool_min_size,
                self.config.pool_max_size,
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password
            )
            logger.info(
                f"Connection pool initialized "
                f"(min={self.config.pool_min_size}, max={self.config.pool_max_size})"
            )
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise

    def close_pool(self):
        """Close all connections in the pool."""
        if self._pool:
            self._pool.closeall()
            self._pool = None
            logger.info("Connection pool closed")

    @contextmanager
    def get_connection(self):
        """
        Get database connection (from pool or standalone).

        Yields:
            psycopg2 connection object

        Usage:
            with db.get_connection() as conn:
                # Use connection
                pass
        """
        conn = None
        from_pool = False

        try:
            if self._pool:
                conn = self._pool.getconn()
                from_pool = True
            else:
                conn = psycopg2.connect(self.config.get_connection_string())

            yield conn

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                if from_pool and self._pool:
                    self._pool.putconn(conn)
                elif not from_pool:
                    conn.close()

    @contextmanager
    def get_cursor(self, cursor_factory=None):
        """
        Get database cursor with automatic connection management.

        Args:
            cursor_factory: Optional cursor factory (e.g., RealDictCursor)

        Yields:
            psycopg2 cursor object

        Usage:
            with db.get_cursor() as cur:
                cur.execute("SELECT * FROM table")
                results = cur.fetchall()
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Cursor operation error: {e}")
                raise
            finally:
                cursor.close()

    def test_connection(self) -> bool:
        """
        Test database connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                logger.info("Database connection test successful")
                return result[0] == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False


class SchemaManager:
    """
    Manage database schema creation and updates.
    """

    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize schema manager.

        Args:
            db_connection: DatabaseConnection instance
        """
        self.db = db_connection

    def create_schema_from_file(self, schema_file_path: str):
        """
        Create database schema from SQL file.

        Args:
            schema_file_path: Path to schema.sql file
        """
        logger.info(f"Creating schema from file: {schema_file_path}")

        try:
            with open(schema_file_path, 'r') as f:
                schema_sql = f.read()

            with self.db.get_cursor() as cur:
                cur.execute(schema_sql)

            logger.info("Schema created successfully")
        except Exception as e:
            logger.error(f"Failed to create schema: {e}")
            raise

    def table_exists(self, table_name: str, schema: str = 'public') -> bool:
        """
        Check if table exists in database.

        Args:
            table_name: Name of the table
            schema: Schema name (default: public)

        Returns:
            True if table exists, False otherwise
        """
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = %s
                AND table_name = %s
            );
        """

        try:
            with self.db.get_cursor() as cur:
                cur.execute(query, (schema, table_name))
                return cur.fetchone()[0]
        except Exception as e:
            logger.error(f"Error checking table existence: {e}")
            return False

    def get_table_row_count(self, table_name: str) -> int:
        """
        Get row count for a table.

        Args:
            table_name: Name of the table

        Returns:
            Number of rows in table
        """
        query = sql.SQL("SELECT COUNT(*) FROM {}").format(
            sql.Identifier(table_name)
        )

        try:
            with self.db.get_cursor() as cur:
                cur.execute(query)
                return cur.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting row count: {e}")
            return -1

    def truncate_table(self, table_name: str, cascade: bool = False):
        """
        Truncate a table.

        Args:
            table_name: Name of the table to truncate
            cascade: Whether to cascade truncate to dependent tables
        """
        cascade_clause = " CASCADE" if cascade else ""
        query = sql.SQL("TRUNCATE TABLE {} {}").format(
            sql.Identifier(table_name),
            sql.SQL(cascade_clause)
        )

        try:
            with self.db.get_cursor() as cur:
                cur.execute(query)
            logger.info(f"Table {table_name} truncated successfully")
        except Exception as e:
            logger.error(f"Error truncating table: {e}")
            raise


class DataIngestion:
    """
    Handle data ingestion operations with optimized batch loading.
    """

    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize data ingestion manager.

        Args:
            db_connection: DatabaseConnection instance
        """
        self.db = db_connection

    def insert_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        batch_size: int = 5000,
        conflict_action: str = 'error'
    ) -> int:
        """
        Insert pandas DataFrame into database table using batch insertion.

        Args:
            df: Pandas DataFrame to insert
            table_name: Target table name
            batch_size: Number of rows per batch
            conflict_action: Action on conflict ('error', 'ignore', 'update')

        Returns:
            Number of rows inserted
        """
        if df.empty:
            logger.warning("DataFrame is empty, skipping insertion")
            return 0

        logger.info(f"Inserting {len(df)} rows into {table_name}")

        # Prepare data
        columns = list(df.columns)
        values = [tuple(row) for row in df.itertuples(index=False, name=None)]

        # Build insert query
        insert_query = self._build_insert_query(
            table_name, columns, conflict_action
        )

        rows_inserted = 0

        try:
            with self.db.get_cursor() as cur:
                # Batch insertion
                for i in range(0, len(values), batch_size):
                    batch = values[i:i + batch_size]
                    extras.execute_batch(cur, insert_query, batch, page_size=batch_size)
                    rows_inserted += len(batch)

                    if (i + batch_size) % (batch_size * 10) == 0:
                        logger.info(f"Inserted {rows_inserted}/{len(values)} rows")

            logger.info(f"Successfully inserted {rows_inserted} rows into {table_name}")
            return rows_inserted

        except Exception as e:
            logger.error(f"Error inserting data into {table_name}: {e}")
            raise

    def _build_insert_query(
        self,
        table_name: str,
        columns: List[str],
        conflict_action: str
    ) -> str:
        """
        Build parameterized INSERT query.

        Args:
            table_name: Target table name
            columns: List of column names
            conflict_action: Action on conflict

        Returns:
            SQL INSERT query string
        """
        columns_str = ', '.join([f'"{col}"' for col in columns])
        placeholders = ', '.join(['%s'] * len(columns))

        query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"

        if conflict_action == 'ignore':
            query += " ON CONFLICT DO NOTHING"
        # Add more conflict handling as needed

        return query

    def bulk_copy_from_file(
        self,
        file_path: str,
        table_name: str,
        delimiter: str = ',',
        columns: Optional[List[str]] = None
    ) -> int:
        """
        Fast bulk load from CSV file using COPY command.

        Args:
            file_path: Path to CSV file
            table_name: Target table name
            delimiter: CSV delimiter (default: comma)
            columns: Optional list of column names

        Returns:
            Number of rows loaded
        """
        logger.info(f"Bulk loading data from {file_path} to {table_name}")

        try:
            with open(file_path, 'r') as f:
                with self.db.get_cursor() as cur:
                    if columns:
                        cur.copy_expert(
                            f"COPY {table_name} ({','.join(columns)}) "
                            f"FROM STDIN WITH CSV HEADER DELIMITER '{delimiter}'",
                            f
                        )
                    else:
                        cur.copy_expert(
                            f"COPY {table_name} FROM STDIN WITH CSV HEADER DELIMITER '{delimiter}'",
                            f
                        )

                    # Get row count
                    row_count = cur.rowcount

            logger.info(f"Bulk loaded {row_count} rows into {table_name}")
            return row_count

        except Exception as e:
            logger.error(f"Error bulk loading data: {e}")
            raise

    def upsert_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        conflict_columns: List[str],
        update_columns: Optional[List[str]] = None,
        batch_size: int = 5000
    ) -> int:
        """
        Upsert DataFrame (INSERT with ON CONFLICT UPDATE).

        Args:
            df: Pandas DataFrame to upsert
            table_name: Target table name
            conflict_columns: Columns to check for conflicts (unique constraint)
            update_columns: Columns to update on conflict (default: all except conflict columns)
            batch_size: Number of rows per batch

        Returns:
            Number of rows upserted
        """
        if df.empty:
            logger.warning("DataFrame is empty, skipping upsert")
            return 0

        logger.info(f"Upserting {len(df)} rows into {table_name}")

        columns = list(df.columns)
        values = [tuple(row) for row in df.itertuples(index=False, name=None)]

        # Determine update columns
        if update_columns is None:
            update_columns = [col for col in columns if col not in conflict_columns]

        # Build upsert query
        columns_str = ', '.join([f'"{col}"' for col in columns])
        placeholders = ', '.join(['%s'] * len(columns))
        conflict_str = ', '.join([f'"{col}"' for col in conflict_columns])
        update_str = ', '.join([f'"{col}" = EXCLUDED."{col}"' for col in update_columns])

        query = (
            f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders}) "
            f"ON CONFLICT ({conflict_str}) DO UPDATE SET {update_str}"
        )

        rows_upserted = 0

        try:
            with self.db.get_cursor() as cur:
                for i in range(0, len(values), batch_size):
                    batch = values[i:i + batch_size]
                    extras.execute_batch(cur, query, batch, page_size=batch_size)
                    rows_upserted += len(batch)

            logger.info(f"Successfully upserted {rows_upserted} rows into {table_name}")
            return rows_upserted

        except Exception as e:
            logger.error(f"Error upserting data: {e}")
            raise


class DataQuery:
    """
    Utility functions for querying data.
    """

    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize data query manager.

        Args:
            db_connection: DatabaseConnection instance
        """
        self.db = db_connection

    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch: str = 'all'
    ) -> Any:
        """
        Execute SQL query and return results.

        Args:
            query: SQL query string
            params: Query parameters (for parameterized queries)
            fetch: Fetch mode ('all', 'one', 'none')

        Returns:
            Query results based on fetch mode
        """
        try:
            with self.db.get_cursor() as cur:
                cur.execute(query, params)

                if fetch == 'all':
                    return cur.fetchall()
                elif fetch == 'one':
                    return cur.fetchone()
                else:
                    return None

        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise

    def query_to_dataframe(
        self,
        query: str,
        params: Optional[Tuple] = None
    ) -> pd.DataFrame:
        """
        Execute query and return results as pandas DataFrame.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Pandas DataFrame with query results
        """
        try:
            with self.db.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)

            logger.info(f"Query returned {len(df)} rows")
            return df

        except Exception as e:
            logger.error(f"Error executing query to DataFrame: {e}")
            raise

    def get_table_sample(
        self,
        table_name: str,
        limit: int = 10,
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Get sample rows from a table.

        Args:
            table_name: Name of the table
            limit: Number of rows to return
            columns: Optional list of columns to select

        Returns:
            Pandas DataFrame with sample data
        """
        columns_str = ', '.join([f'"{col}"' for col in columns]) if columns else '*'
        query = f"SELECT {columns_str} FROM {table_name} LIMIT {limit}"

        return self.query_to_dataframe(query)

    def get_date_range(
        self,
        table_name: str,
        date_column: str
    ) -> Tuple[datetime, datetime]:
        """
        Get min and max dates from a table.

        Args:
            table_name: Name of the table
            date_column: Name of the date/timestamp column

        Returns:
            Tuple of (min_date, max_date)
        """
        query = f"""
            SELECT
                MIN("{date_column}") as min_date,
                MAX("{date_column}") as max_date
            FROM {table_name}
        """

        result = self.execute_query(query, fetch='one')
        return result[0], result[1]


# Convenience function for quick database access
def get_database_connection(
    config_path: Optional[str] = None
) -> DatabaseConnection:
    """
    Get a database connection instance.

    Args:
        config_path: Optional path to configuration file

    Returns:
        DatabaseConnection instance
    """
    config = DatabaseConfig(config_path)
    return DatabaseConnection(config)


# Example usage and testing
if __name__ == "__main__":
    # Example: Initialize and test connection
    db = get_database_connection()

    if db.test_connection():
        print("Database connection successful!")

        # Example: Create schema
        schema_manager = SchemaManager(db)
        schema_file = "/home/slim/OLPA/src/data_engineering/schema.sql"

        if os.path.exists(schema_file):
            print(f"Creating schema from {schema_file}")
            # schema_manager.create_schema_from_file(schema_file)
            # Commented out to prevent accidental schema creation

        # Example: Check if table exists
        if schema_manager.table_exists("bronze_sensor_data"):
            print("Table bronze_sensor_data exists")
            row_count = schema_manager.get_table_row_count("bronze_sensor_data")
            print(f"Row count: {row_count}")

        # Example: Insert sample data
        # sample_data = pd.DataFrame({
        #     'aircraft_id': ['AC001', 'AC002'],
        #     'sensor_id': ['S001', 'S002'],
        #     'sensor_type': ['temperature', 'vibration'],
        #     'measurement_timestamp': [datetime.now(), datetime.now()],
        #     'measurement_value': [75.5, 12.3],
        #     'measurement_unit': ['celsius', 'm/s2']
        # })

        # ingestion = DataIngestion(db)
        # ingestion.insert_dataframe(sample_data, 'bronze_sensor_data')

        # Example: Query data
        # query_manager = DataQuery(db)
        # df = query_manager.get_table_sample('bronze_sensor_data', limit=5)
        # print(df)

    else:
        print("Database connection failed!")
