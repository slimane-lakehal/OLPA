"""
OLPA Data Engineering Module
==============================
Data engineering utilities for the OLPA predictive maintenance project.

This module provides:
- Database connection management and CRUD operations
- ETL/ELT pipeline utilities
- Data quality validation
- Schema management

Usage:
    from src.data_engineering import get_database_connection
    from src.data_engineering import DataIngestion, DataQuery

    db = get_database_connection()
    ingestion = DataIngestion(db)
"""

from .database import (
    DatabaseConfig,
    DatabaseConnection,
    SchemaManager,
    DataIngestion,
    DataQuery,
    get_database_connection
)

__all__ = [
    'DatabaseConfig',
    'DatabaseConnection',
    'SchemaManager',
    'DataIngestion',
    'DataQuery',
    'get_database_connection'
]

__version__ = '1.0'
