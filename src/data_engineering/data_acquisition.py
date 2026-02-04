"""
Data Acquisition Module for OLPA Project
Handles downloading and generating datasets for predictive maintenance
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataAcquisitionError(Exception):
    """Custom exception for data acquisition errors"""
    pass


class DatasetGenerator:
    """
    Generate synthetic aeronautical maintenance datasets
    Simulates NASA Turbofan-style degradation patterns
    """

    def __init__(self, seed=42):
        self.seed = seed
        np.random.seed(seed)

    def generate_sensor_data(
        self,
        n_aircraft=50,
        n_days=365,
        sensors=['temperature', 'vibration', 'pressure', 'rpm'],
        failure_rate=0.15
    ):
        """
        Generate synthetic sensor data with degradation patterns

        Args:
            n_aircraft: Number of aircraft to simulate
            n_days: Number of days of data
            sensors: List of sensor types
            failure_rate: Proportion of aircraft that will fail

        Returns:
            DataFrame with sensor readings and failure labels
        """
        logger.info(f"Generating sensor data for {n_aircraft} aircraft over {n_days} days")

        data = []
        start_date = datetime(2023, 1, 1)

        for aircraft_id in range(1, n_aircraft + 1):
            # Determine if this aircraft will fail
            will_fail = np.random.random() < failure_rate

            # If failing, determine when (between day 100 and day 365)
            if will_fail:
                failure_day = np.random.randint(100, n_days)
            else:
                failure_day = None

            # Generate daily readings
            for day in range(n_days):
                current_date = start_date + timedelta(days=day)

                # Calculate degradation factor (increases as failure approaches)
                if will_fail and day > failure_day - 90:
                    degradation = (failure_day - day) / 90.0
                    degradation = max(0, degradation)  # 1.0 at 90 days before, 0.0 at failure
                    degradation = 1 - degradation  # Invert: 0.0 at 90 days before, 1.0 at failure
                else:
                    degradation = 0.0

                # Generate sensor readings with degradation effects
                readings = {
                    'aircraft_id': f'AC{aircraft_id:03d}',
                    'date': current_date,
                    'cycle': day,
                }

                # Temperature: increases with degradation
                temp_base = np.random.normal(400, 10)
                readings['temperature'] = temp_base + degradation * 50 + np.random.normal(0, 5)

                # Vibration: increases with degradation
                vib_base = np.random.normal(0.5, 0.1)
                readings['vibration'] = vib_base + degradation * 0.8 + np.random.normal(0, 0.05)

                # Pressure: decreases with degradation
                press_base = np.random.normal(100, 5)
                readings['pressure'] = press_base - degradation * 20 + np.random.normal(0, 2)

                # RPM: becomes more variable with degradation
                rpm_base = np.random.normal(3000, 100)
                rpm_noise = np.random.normal(0, 50 * (1 + degradation * 2))
                readings['rpm'] = rpm_base + rpm_noise

                # Operating conditions (additional features)
                readings['altitude'] = np.random.uniform(0, 40000)
                readings['ambient_temp'] = np.random.normal(15, 10)
                readings['flight_hours'] = day * np.random.uniform(8, 12)

                # Failure labels
                readings['failed'] = 1 if (will_fail and day >= failure_day) else 0
                readings['days_to_failure'] = failure_day - day if will_fail and day < failure_day else None
                readings['will_fail_7days'] = 1 if (will_fail and 0 <= failure_day - day <= 7) else 0

                data.append(readings)

        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} records")
        logger.info(f"Failures: {df['failed'].sum()} events across {df[df['failed']==1]['aircraft_id'].nunique()} aircraft")

        return df

    def generate_maintenance_records(self, sensor_df):
        """
        Generate maintenance records based on failures

        Args:
            sensor_df: DataFrame with sensor data and failure labels

        Returns:
            DataFrame with maintenance records
        """
        logger.info("Generating maintenance records")

        # Get all failure events
        failures = sensor_df[sensor_df['failed'] == 1].copy()

        maintenance_records = []

        for _, failure in failures.iterrows():
            # Record the failure
            record = {
                'aircraft_id': failure['aircraft_id'],
                'maintenance_date': failure['date'],
                'maintenance_type': 'corrective',
                'issue_detected': np.random.choice([
                    'engine_overheating',
                    'bearing_failure',
                    'blade_damage',
                    'seal_leak',
                    'compressor_stall'
                ]),
                'downtime_hours': np.random.uniform(24, 120),
                'cost_usd': np.random.uniform(50000, 200000),
                'parts_replaced': np.random.choice([
                    'turbine_blade',
                    'bearing_assembly',
                    'seal_kit',
                    'compressor_blade',
                    'fuel_nozzle'
                ])
            }
            maintenance_records.append(record)

        # Add some preventive maintenance records
        aircraft_ids = sensor_df['aircraft_id'].unique()
        for aircraft_id in aircraft_ids:
            # 2-3 preventive maintenance per aircraft per year
            n_preventive = np.random.randint(2, 4)
            aircraft_dates = sensor_df[sensor_df['aircraft_id'] == aircraft_id]['date']

            for _ in range(n_preventive):
                date = np.random.choice(aircraft_dates)
                record = {
                    'aircraft_id': aircraft_id,
                    'maintenance_date': date,
                    'maintenance_type': 'preventive',
                    'issue_detected': 'scheduled_inspection',
                    'downtime_hours': np.random.uniform(4, 12),
                    'cost_usd': np.random.uniform(5000, 15000),
                    'parts_replaced': 'none'
                }
                maintenance_records.append(record)

        df_maintenance = pd.DataFrame(maintenance_records)
        logger.info(f"Generated {len(df_maintenance)} maintenance records")

        return df_maintenance.sort_values('maintenance_date')

    def generate_inventory_data(self, maintenance_df):
        """
        Generate inventory/logistics data based on maintenance needs

        Args:
            maintenance_df: DataFrame with maintenance records

        Returns:
            DataFrame with inventory data
        """
        logger.info("Generating inventory data")

        # Critical parts inventory
        critical_parts = [
            'turbine_blade',
            'bearing_assembly',
            'seal_kit',
            'compressor_blade',
            'fuel_nozzle'
        ]

        inventory_records = []
        start_date = maintenance_df['maintenance_date'].min()
        end_date = maintenance_df['maintenance_date'].max()

        current_date = start_date
        while current_date <= end_date:
            for part in critical_parts:
                record = {
                    'date': current_date,
                    'part_name': part,
                    'stock_level': np.random.randint(5, 30),
                    'reorder_point': 10,
                    'lead_time_days': np.random.randint(7, 21),
                    'unit_cost_usd': np.random.uniform(5000, 50000),
                    'supplier': np.random.choice(['SupplierA', 'SupplierB', 'SupplierC'])
                }
                inventory_records.append(record)

            current_date += timedelta(days=7)  # Weekly snapshots

        df_inventory = pd.DataFrame(inventory_records)
        logger.info(f"Generated {len(df_inventory)} inventory records")

        return df_inventory

    def generate_aircraft_metadata(self, n_aircraft=50):
        """
        Generate aircraft metadata

        Args:
            n_aircraft: Number of aircraft

        Returns:
            DataFrame with aircraft metadata
        """
        logger.info(f"Generating metadata for {n_aircraft} aircraft")

        metadata = []
        for aircraft_id in range(1, n_aircraft + 1):
            record = {
                'aircraft_id': f'AC{aircraft_id:03d}',
                'model': np.random.choice(['A320', 'B737', 'A350', 'B787']),
                'manufacture_year': np.random.randint(2010, 2023),
                'total_flight_hours': np.random.uniform(10000, 50000),
                'total_cycles': np.random.randint(5000, 25000),
                'location': np.random.choice(['Paris', 'London', 'New York', 'Tokyo', 'Dubai']),
                'status': 'active'
            }
            metadata.append(record)

        df_metadata = pd.DataFrame(metadata)
        logger.info(f"Generated {len(df_metadata)} aircraft metadata records")

        return df_metadata


class DataAcquisition:
    """Main class for data acquisition orchestration"""

    def __init__(self, data_dir='data/raw'):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.generator = DatasetGenerator()

    def acquire_all_datasets(self, n_aircraft=50, n_days=365):
        """
        Generate and save all required datasets

        Args:
            n_aircraft: Number of aircraft to simulate
            n_days: Number of days of sensor data

        Returns:
            Dictionary with paths to all generated datasets
        """
        logger.info("Starting full dataset acquisition")

        try:
            # Generate sensor data
            logger.info("Step 1/4: Generating sensor data")
            sensor_df = self.generator.generate_sensor_data(
                n_aircraft=n_aircraft,
                n_days=n_days
            )
            sensor_path = self.data_dir / 'sensor_data.csv'
            sensor_df.to_csv(sensor_path, index=False)
            logger.info(f"Saved sensor data to {sensor_path}")

            # Generate maintenance records
            logger.info("Step 2/4: Generating maintenance records")
            maintenance_df = self.generator.generate_maintenance_records(sensor_df)
            maintenance_path = self.data_dir / 'maintenance_records.csv'
            maintenance_df.to_csv(maintenance_path, index=False)
            logger.info(f"Saved maintenance records to {maintenance_path}")

            # Generate inventory data
            logger.info("Step 3/4: Generating inventory data")
            inventory_df = self.generator.generate_inventory_data(maintenance_df)
            inventory_path = self.data_dir / 'inventory_data.csv'
            inventory_df.to_csv(inventory_path, index=False)
            logger.info(f"Saved inventory data to {inventory_path}")

            # Generate aircraft metadata
            logger.info("Step 4/4: Generating aircraft metadata")
            metadata_df = self.generator.generate_aircraft_metadata(n_aircraft)
            metadata_path = self.data_dir / 'aircraft_metadata.csv'
            metadata_df.to_csv(metadata_path, index=False)
            logger.info(f"Saved aircraft metadata to {metadata_path}")

            # Create data dictionary
            self._create_data_dictionary()

            logger.info("Dataset acquisition completed successfully")

            return {
                'sensor_data': sensor_path,
                'maintenance_records': maintenance_path,
                'inventory_data': inventory_path,
                'aircraft_metadata': metadata_path
            }

        except Exception as e:
            logger.error(f"Error during data acquisition: {str(e)}")
            raise DataAcquisitionError(f"Failed to acquire datasets: {str(e)}")

    def _create_data_dictionary(self):
        """Create comprehensive data dictionary documentation"""

        data_dict_content = """# OLPA Data Dictionary

## 1. Sensor Data (`sensor_data.csv`)

Real-time sensor readings from aircraft engines with degradation patterns.

| Column | Type | Description | Range/Values |
|--------|------|-------------|--------------|
| `aircraft_id` | string | Unique aircraft identifier | AC001-AC050 |
| `date` | datetime | Date of sensor reading | 2023-01-01 to 2023-12-31 |
| `cycle` | integer | Operating cycle number | 0-364 |
| `temperature` | float | Engine temperature (°C) | 350-500 |
| `vibration` | float | Vibration amplitude (mm/s) | 0.3-1.5 |
| `pressure` | float | Engine pressure (PSI) | 75-110 |
| `rpm` | float | Rotations per minute | 2500-3500 |
| `altitude` | float | Flight altitude (feet) | 0-40000 |
| `ambient_temp` | float | Ambient temperature (°C) | -20 to 40 |
| `flight_hours` | float | Cumulative flight hours | Increasing |
| `failed` | binary | Failure indicator (0=operational, 1=failed) | 0, 1 |
| `days_to_failure` | integer | Days until failure (null if no failure) | 0-365 or null |
| `will_fail_7days` | binary | **Target variable**: Will fail in next 7 days | 0, 1 |

**Key Notes:**
- Total records: ~18,250 (50 aircraft × 365 days)
- Failure rate: ~15% of aircraft
- Degradation patterns visible 60-90 days before failure
- Target variable (`will_fail_7days`) is used for ML model training

## 2. Maintenance Records (`maintenance_records.csv`)

Historical maintenance events including corrective and preventive actions.

| Column | Type | Description | Range/Values |
|--------|------|-------------|--------------|
| `aircraft_id` | string | Unique aircraft identifier | AC001-AC050 |
| `maintenance_date` | datetime | Date of maintenance event | 2023-01-01 to 2023-12-31 |
| `maintenance_type` | string | Type of maintenance | corrective, preventive |
| `issue_detected` | string | Issue or inspection type | See issue types below |
| `downtime_hours` | float | Aircraft downtime duration | 4-120 hours |
| `cost_usd` | float | Maintenance cost in USD | $5,000-$200,000 |
| `parts_replaced` | string | Parts replaced during maintenance | See parts list below |

**Issue Types:**
- `engine_overheating`: Critical temperature exceedance
- `bearing_failure`: Bearing assembly failure
- `blade_damage`: Turbine/compressor blade damage
- `seal_leak`: Seal integrity failure
- `compressor_stall`: Compressor performance issue
- `scheduled_inspection`: Routine preventive check

**Parts List:**
- `turbine_blade`: Turbine blade assembly
- `bearing_assembly`: Engine bearing components
- `seal_kit`: Seal replacement kit
- `compressor_blade`: Compressor blade assembly
- `fuel_nozzle`: Fuel injection nozzle
- `none`: No parts replaced (inspection only)

**Key Notes:**
- Corrective maintenance: Triggered by failures
- Preventive maintenance: 2-3 per aircraft per year
- Average corrective cost: $125,000
- Average preventive cost: $10,000

## 3. Inventory Data (`inventory_data.csv`)

Weekly inventory snapshots for critical spare parts.

| Column | Type | Description | Range/Values |
|--------|------|-------------|--------------|
| `date` | datetime | Inventory snapshot date | Weekly intervals |
| `part_name` | string | Part identifier | See parts list above |
| `stock_level` | integer | Current stock quantity | 5-30 units |
| `reorder_point` | integer | Reorder threshold | 10 units |
| `lead_time_days` | integer | Supplier lead time | 7-21 days |
| `unit_cost_usd` | float | Cost per unit | $5,000-$50,000 |
| `supplier` | string | Parts supplier | SupplierA, SupplierB, SupplierC |

**Key Notes:**
- Stock-out risk when `stock_level < reorder_point`
- Lead time variability impacts ordering strategy
- Total records: ~260 (52 weeks × 5 parts)

## 4. Aircraft Metadata (`aircraft_metadata.csv`)

Static information about each aircraft in the fleet.

| Column | Type | Description | Range/Values |
|--------|------|-------------|--------------|
| `aircraft_id` | string | Unique aircraft identifier | AC001-AC050 |
| `model` | string | Aircraft model | A320, B737, A350, B787 |
| `manufacture_year` | integer | Year manufactured | 2010-2023 |
| `total_flight_hours` | float | Cumulative flight hours | 10,000-50,000 |
| `total_cycles` | integer | Cumulative flight cycles | 5,000-25,000 |
| `location` | string | Primary base location | Paris, London, New York, Tokyo, Dubai |
| `status` | string | Operational status | active |

**Key Notes:**
- Fleet size: 50 aircraft
- Mixed fleet with 4 different models
- Geographic distribution across 5 major hubs

## Data Relationships

```
aircraft_metadata (1) ──→ (N) sensor_data
aircraft_metadata (1) ──→ (N) maintenance_records
maintenance_records (N) ──→ (M) inventory_data
```

## Target Variable for ML

**Primary Target**: `will_fail_7days` in `sensor_data.csv`
- Binary classification problem
- Objective: Predict failures 7 days in advance
- Success metric: F1-Score > 85%, Recall > 85%

## Data Quality Notes

- **Missing Values**: Minimal (<1%) in sensor readings
- **Outliers**: Present by design (degradation signals)
- **Class Imbalance**: ~2-3% positive class for `will_fail_7days`
- **Temporal Ordering**: Critical for time-series splits
- **Data Freshness**: Daily sensor readings, weekly inventory snapshots

## Usage in ML Pipeline

1. **Bronze Layer**: Raw CSV files loaded as-is
2. **Silver Layer**: Cleaned data with quality validation
3. **Gold Layer**: Feature-engineered dataset with:
   - Rolling statistics (7-day, 14-day, 30-day windows)
   - Trend indicators (slopes, volatility)
   - Anomaly scores
   - Maintenance history features
   - Inventory availability flags

## References

- Dataset inspired by NASA Turbofan Engine Degradation Simulation
- AI4I 2020 Predictive Maintenance Dataset patterns
- Domain knowledge from aeronautical engineering best practices
"""

        dict_path = Path('docs') / 'data_dictionary.md'
        dict_path.parent.mkdir(parents=True, exist_ok=True)

        with open(dict_path, 'w') as f:
            f.write(data_dict_content)

        logger.info(f"Created data dictionary at {dict_path}")


if __name__ == "__main__":
    # Example usage
    acquisition = DataAcquisition()
    paths = acquisition.acquire_all_datasets(n_aircraft=50, n_days=365)

    print("\nDataset acquisition completed!")
    print("\nGenerated files:")
    for name, path in paths.items():
        print(f"  - {name}: {path}")

    print("\nNext steps:")
    print("  1. Review data in notebooks/01_exploratory_data_analysis.ipynb")
    print("  2. Load data into database using src/data_engineering/database.py")
    print("  3. Run data quality checks")
