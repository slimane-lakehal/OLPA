"""
ETL/ELT Pipeline for OLPA Project
Transforms raw sensor data into ML-ready features
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataQualityChecker:
    """
    Data quality validation and scoring
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.quality_scores = {}

    def check_completeness(self) -> float:
        """Check for missing values"""
        total_cells = self.df.size
        missing_cells = self.df.isnull().sum().sum()
        completeness = 1 - (missing_cells / total_cells)

        logger.info(f"Completeness: {completeness:.2%} ({missing_cells}/{total_cells} missing)")
        self.quality_scores['completeness'] = completeness

        return completeness

    def check_validity(self, column_ranges: Dict[str, Tuple[float, float]]) -> float:
        """
        Check if values are within valid ranges

        Args:
            column_ranges: Dict of {column: (min, max)}
        """
        valid_count = 0
        total_count = 0

        for column, (min_val, max_val) in column_ranges.items():
            if column in self.df.columns:
                col_data = self.df[column].dropna()
                valid = ((col_data >= min_val) & (col_data <= max_val)).sum()
                total = len(col_data)

                valid_count += valid
                total_count += total

                logger.info(f"{column}: {valid}/{total} valid ({valid/total:.2%})")

        validity = valid_count / total_count if total_count > 0 else 1.0
        logger.info(f"Overall Validity: {validity:.2%}")
        self.quality_scores['validity'] = validity

        return validity

    def check_consistency(self) -> float:
        """Check for logical consistency"""
        consistency_checks = []

        # Example: flight_hours should be increasing for each aircraft
        if 'aircraft_id' in self.df.columns and 'flight_hours' in self.df.columns:
            for aircraft in self.df['aircraft_id'].unique():
                aircraft_data = self.df[self.df['aircraft_id'] == aircraft]['flight_hours']
                if len(aircraft_data) > 1:
                    is_increasing = (aircraft_data.diff().dropna() >= 0).all()
                    consistency_checks.append(is_increasing)

        consistency = np.mean(consistency_checks) if consistency_checks else 1.0
        logger.info(f"Consistency: {consistency:.2%}")
        self.quality_scores['consistency'] = consistency

        return consistency

    def check_timeliness(self, date_column='date', expected_frequency='D') -> float:
        """Check if data is up-to-date and has expected frequency"""
        if date_column not in self.df.columns:
            return 1.0

        # Check recency
        max_date = self.df[date_column].max()
        days_old = (datetime.now() - max_date).days

        timeliness = max(0, 1 - (days_old / 365))  # Penalize if > 1 year old

        logger.info(f"Latest data: {max_date} ({days_old} days old)")
        logger.info(f"Timeliness: {timeliness:.2%}")
        self.quality_scores['timeliness'] = timeliness

        return timeliness

    def get_quality_score(self) -> float:
        """Calculate overall quality score"""
        if not self.quality_scores:
            return 0.0

        overall = np.mean(list(self.quality_scores.values()))
        logger.info(f"\nOVERALL DATA QUALITY SCORE: {overall:.2%}")

        return overall

    def generate_report(self) -> Dict:
        """Generate detailed quality report"""
        return {
            'quality_scores': self.quality_scores,
            'overall_score': self.get_quality_score(),
            'record_count': len(self.df),
            'column_count': len(self.df.columns),
            'missing_values': self.df.isnull().sum().to_dict()
        }


class DataCleaner:
    """
    Data cleaning and anomaly handling
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.cleaning_log = []

    def handle_missing_values(self, strategy='forward_fill', columns=None):
        """
        Handle missing values

        Args:
            strategy: 'forward_fill', 'interpolate', 'mean', or 'drop'
            columns: List of columns (None = all numeric columns)
        """
        if columns is None:
            columns = self.df.select_dtypes(include=[np.number]).columns

        initial_missing = self.df[columns].isnull().sum().sum()

        if strategy == 'forward_fill':
            self.df[columns] = self.df[columns].fillna(method='ffill')
            self.df[columns] = self.df[columns].fillna(method='bfill')  # Fill any remaining

        elif strategy == 'interpolate':
            self.df[columns] = self.df[columns].interpolate(method='linear')

        elif strategy == 'mean':
            for col in columns:
                self.df[col].fillna(self.df[col].mean(), inplace=True)

        elif strategy == 'drop':
            self.df.dropna(subset=columns, inplace=True)

        final_missing = self.df[columns].isnull().sum().sum()

        log_entry = {
            'operation': 'handle_missing_values',
            'strategy': strategy,
            'initial_missing': initial_missing,
            'final_missing': final_missing,
            'columns': list(columns)
        }
        self.cleaning_log.append(log_entry)

        logger.info(f"Missing values: {initial_missing} → {final_missing} (strategy: {strategy})")

        return self.df

    def remove_outliers(self, columns, method='iqr', threshold=3.0):
        """
        Remove or cap outliers

        Args:
            columns: List of columns
            method: 'iqr' (Interquartile Range) or 'zscore'
            threshold: Threshold for outlier detection
        """
        initial_count = len(self.df)

        for col in columns:
            if col not in self.df.columns:
                continue

            if method == 'iqr':
                Q1 = self.df[col].quantile(0.25)
                Q3 = self.df[col].quantile(0.75)
                IQR = Q3 - Q1

                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR

                # Cap outliers instead of removing
                self.df[col] = self.df[col].clip(lower=lower_bound, upper=upper_bound)

            elif method == 'zscore':
                z_scores = np.abs((self.df[col] - self.df[col].mean()) / self.df[col].std())
                mean = self.df[col].mean()
                std = self.df[col].std()

                lower_bound = mean - threshold * std
                upper_bound = mean + threshold * std

                self.df[col] = self.df[col].clip(lower=lower_bound, upper=upper_bound)

        final_count = len(self.df)

        log_entry = {
            'operation': 'remove_outliers',
            'method': method,
            'initial_count': initial_count,
            'final_count': final_count,
            'columns': columns
        }
        self.cleaning_log.append(log_entry)

        logger.info(f"Outlier handling: {initial_count} → {final_count} records (method: {method})")

        return self.df

    def deduplicate(self, subset=None):
        """Remove duplicate records"""
        initial_count = len(self.df)

        self.df.drop_duplicates(subset=subset, keep='first', inplace=True)

        final_count = len(self.df)
        removed = initial_count - final_count

        log_entry = {
            'operation': 'deduplicate',
            'initial_count': initial_count,
            'final_count': final_count,
            'removed': removed
        }
        self.cleaning_log.append(log_entry)

        logger.info(f"Deduplication: Removed {removed} duplicates")

        return self.df

    def get_cleaned_data(self):
        """Return cleaned dataframe"""
        return self.df

    def get_cleaning_report(self):
        """Return cleaning operations log"""
        return self.cleaning_log


class FeatureEngineer:
    """
    Feature engineering for predictive maintenance
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.feature_log = []

    def create_rolling_features(self, columns: List[str], windows: List[int] = [7, 14, 30]):
        """
        Create rolling statistics features

        Args:
            columns: List of sensor columns
            windows: List of window sizes in days
        """
        logger.info(f"Creating rolling features for {len(columns)} columns, {len(windows)} windows")

        # Ensure data is sorted by date for each aircraft
        self.df = self.df.sort_values(['aircraft_id', 'date'])

        for col in columns:
            if col not in self.df.columns:
                continue

            for window in windows:
                # Rolling mean
                self.df[f'{col}_rolling_mean_{window}d'] = (
                    self.df.groupby('aircraft_id')[col]
                    .rolling(window=window, min_periods=1)
                    .mean()
                    .reset_index(level=0, drop=True)
                )

                # Rolling std
                self.df[f'{col}_rolling_std_{window}d'] = (
                    self.df.groupby('aircraft_id')[col]
                    .rolling(window=window, min_periods=1)
                    .std()
                    .reset_index(level=0, drop=True)
                )

                # Rolling min/max
                self.df[f'{col}_rolling_min_{window}d'] = (
                    self.df.groupby('aircraft_id')[col]
                    .rolling(window=window, min_periods=1)
                    .min()
                    .reset_index(level=0, drop=True)
                )

                self.df[f'{col}_rolling_max_{window}d'] = (
                    self.df.groupby('aircraft_id')[col]
                    .rolling(window=window, min_periods=1)
                    .max()
                    .reset_index(level=0, drop=True)
                )

        new_features = [col for col in self.df.columns if 'rolling' in col]
        logger.info(f"Created {len(new_features)} rolling features")

        self.feature_log.append({
            'operation': 'create_rolling_features',
            'features_created': len(new_features)
        })

        return self.df

    def create_trend_features(self, columns: List[str], windows: List[int] = [7, 14, 30]):
        """
        Create trend and rate-of-change features

        Args:
            columns: List of sensor columns
            windows: List of window sizes
        """
        logger.info(f"Creating trend features for {len(columns)} columns")

        self.df = self.df.sort_values(['aircraft_id', 'date'])

        for col in columns:
            if col not in self.df.columns:
                continue

            # Rate of change (difference from previous day)
            self.df[f'{col}_diff_1d'] = (
                self.df.groupby('aircraft_id')[col].diff(1)
            )

            # Slope over windows (linear regression coefficient)
            for window in windows:
                # Simple slope approximation: (last - first) / window
                self.df[f'{col}_slope_{window}d'] = (
                    self.df.groupby('aircraft_id')[col]
                    .rolling(window=window, min_periods=2)
                    .apply(lambda x: (x.iloc[-1] - x.iloc[0]) / len(x) if len(x) > 1 else 0)
                    .reset_index(level=0, drop=True)
                )

        new_features = [col for col in self.df.columns if ('diff' in col or 'slope' in col)]
        logger.info(f"Created {len(new_features)} trend features")

        self.feature_log.append({
            'operation': 'create_trend_features',
            'features_created': len(new_features)
        })

        return self.df

    def create_anomaly_scores(self, columns: List[str]):
        """
        Create anomaly detection scores

        Args:
            columns: List of sensor columns
        """
        logger.info(f"Creating anomaly scores for {len(columns)} columns")

        for col in columns:
            if col not in self.df.columns:
                continue

            # Z-score anomaly
            mean = self.df.groupby('aircraft_id')[col].transform('mean')
            std = self.df.groupby('aircraft_id')[col].transform('std')

            self.df[f'{col}_zscore'] = np.abs((self.df[col] - mean) / (std + 1e-6))

            # Distance from historical mean
            self.df[f'{col}_dist_from_mean'] = np.abs(self.df[col] - mean)

        new_features = [col for col in self.df.columns if ('zscore' in col or 'dist_from_mean' in col)]
        logger.info(f"Created {len(new_features)} anomaly features")

        self.feature_log.append({
            'operation': 'create_anomaly_scores',
            'features_created': len(new_features)
        })

        return self.df

    def create_domain_features(self):
        """Create domain-specific aeronautical features"""
        logger.info("Creating domain-specific features")

        # Days since last maintenance (would join with maintenance records in production)
        # For now, create a proxy feature

        # Cumulative metrics
        self.df = self.df.sort_values(['aircraft_id', 'date'])

        # Days in operation (cycle number)
        if 'cycle' not in self.df.columns:
            self.df['days_in_operation'] = (
                self.df.groupby('aircraft_id').cumcount()
            )

        # Interaction features
        if 'temperature' in self.df.columns and 'vibration' in self.df.columns:
            self.df['temp_vibration_interaction'] = self.df['temperature'] * self.df['vibration']

        if 'pressure' in self.df.columns and 'rpm' in self.df.columns:
            self.df['pressure_rpm_ratio'] = self.df['pressure'] / (self.df['rpm'] + 1)

        new_features = ['days_in_operation', 'temp_vibration_interaction', 'pressure_rpm_ratio']
        logger.info(f"Created {len(new_features)} domain features")

        self.feature_log.append({
            'operation': 'create_domain_features',
            'features_created': len(new_features)
        })

        return self.df

    def get_engineered_data(self):
        """Return dataframe with engineered features"""
        return self.df

    def get_feature_report(self):
        """Return feature engineering log"""
        return self.feature_log


class ETLPipeline:
    """
    Main ETL pipeline orchestrator
    """

    def __init__(self, bronze_path: str, silver_path: str = None, gold_path: str = None):
        """
        Initialize pipeline

        Args:
            bronze_path: Path to raw data (Bronze layer)
            silver_path: Path to save cleaned data (Silver layer)
            gold_path: Path to save ML-ready data (Gold layer)
        """
        self.bronze_path = Path(bronze_path)
        self.silver_path = Path(silver_path) if silver_path else Path('data/processed/silver_sensor_data.csv')
        self.gold_path = Path(gold_path) if gold_path else Path('data/processed/gold_ml_dataset.csv')

        self.silver_path.parent.mkdir(parents=True, exist_ok=True)
        self.gold_path.parent.mkdir(parents=True, exist_ok=True)

    def run(self):
        """Execute complete ETL pipeline"""
        logger.info("=" * 60)
        logger.info("STARTING ETL PIPELINE")
        logger.info("=" * 60)

        # 1. Extract - Load Bronze data
        logger.info("\n[EXTRACT] Loading Bronze layer data...")
        df = pd.read_csv(self.bronze_path, parse_dates=['date'])
        logger.info(f"Loaded {len(df)} records from {self.bronze_path}")

        # 2. Transform - Data Quality Check
        logger.info("\n[TRANSFORM] Step 1: Data Quality Assessment...")
        quality_checker = DataQualityChecker(df)
        quality_checker.check_completeness()
        quality_checker.check_validity({
            'temperature': (300, 600),
            'vibration': (0, 3),
            'pressure': (50, 150),
            'rpm': (2000, 4000)
        })
        quality_score = quality_checker.get_quality_score()

        if quality_score < 0.90:
            logger.warning(f"Quality score {quality_score:.2%} below threshold (90%)")

        # 3. Transform - Data Cleaning
        logger.info("\n[TRANSFORM] Step 2: Data Cleaning...")
        cleaner = DataCleaner(df)

        cleaner.handle_missing_values(strategy='forward_fill')
        cleaner.remove_outliers(
            columns=['temperature', 'vibration', 'pressure', 'rpm'],
            method='iqr',
            threshold=3.0
        )
        cleaner.deduplicate(subset=['aircraft_id', 'date'])

        silver_df = cleaner.get_cleaned_data()

        # 4. Load - Save Silver data
        logger.info("\n[LOAD] Saving Silver layer data...")
        silver_df.to_csv(self.silver_path, index=False)
        logger.info(f"Silver data saved to {self.silver_path}")

        # 5. Transform - Feature Engineering
        logger.info("\n[TRANSFORM] Step 3: Feature Engineering...")
        engineer = FeatureEngineer(silver_df)

        sensor_cols = ['temperature', 'vibration', 'pressure', 'rpm']

        engineer.create_rolling_features(sensor_cols, windows=[7, 14, 30])
        engineer.create_trend_features(sensor_cols, windows=[7, 14, 30])
        engineer.create_anomaly_scores(sensor_cols)
        engineer.create_domain_features()

        gold_df = engineer.get_engineered_data()

        # 6. Load - Save Gold data
        logger.info("\n[LOAD] Saving Gold layer data...")
        gold_df.to_csv(self.gold_path, index=False)
        logger.info(f"Gold data saved to {self.gold_path}")

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("ETL PIPELINE COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Bronze → Silver: {len(df)} → {len(silver_df)} records")
        logger.info(f"Silver → Gold: {len(silver_df)} → {len(gold_df)} records")
        logger.info(f"Features: {len(df.columns)} → {len(gold_df.columns)}")
        logger.info(f"Data Quality Score: {quality_score:.2%}")

        return {
            'bronze_records': len(df),
            'silver_records': len(silver_df),
            'gold_records': len(gold_df),
            'bronze_features': len(df.columns),
            'gold_features': len(gold_df.columns),
            'quality_score': quality_score,
            'silver_path': str(self.silver_path),
            'gold_path': str(self.gold_path)
        }


if __name__ == "__main__":
    # Run ETL pipeline
    pipeline = ETLPipeline(
        bronze_path='data/raw/sensor_data.csv',
        silver_path='data/processed/silver_sensor_data.csv',
        gold_path='data/processed/gold_ml_dataset.csv'
    )

    results = pipeline.run()

    print("\nPipeline Results:")
    for key, value in results.items():
        print(f"  {key}: {value}")
