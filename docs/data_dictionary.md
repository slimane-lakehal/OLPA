# OLPA Data Dictionary

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
