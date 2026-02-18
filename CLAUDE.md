# CLAUDE.md — OLPA Codebase Guide

> **OLPA** — *Optimisation Logistique & Prédictive Aéronautique*
> Aeronautical predictive maintenance and spare parts optimization platform.

---

## Project Overview

OLPA predicts aircraft component failures 7 days in advance (target: ≥85% F1-score) and optimizes critical spare parts inventory (target: 20% reduction in stock-outs). The system ingests sensor and maintenance data, processes it through a Bronze→Silver→Gold medallion architecture, trains ML models with full MLflow tracking, and serves predictions via a FastAPI REST API.

**Current sprint**: Sprint 1.3 — Data Acquisition
**License**: MIT (Copyright 2025 Slimane Lakehal)

---

## Repository Structure

```
OLPA/
├── main.py                          # CLI entry point (placeholder)
├── pyproject.toml                   # Project metadata and dependencies (uv)
├── uv.lock                          # Locked dependency versions
├── Dockerfile                       # Multi-stage build (base/development/training/api)
├── docker-compose.yml               # Services: jupyter, mlflow, training, postgres, api
├── .python-version                  # Python 3.12
│
├── src/
│   ├── data_engineering/
│   │   ├── __init__.py              # Public API exports
│   │   ├── database.py              # DB connection, schema, ingestion, query utilities
│   │   ├── etl_pipeline.py          # Bronze→Silver→Gold ETL pipeline
│   │   └── data_acquisition.py      # Synthetic dataset generator
│   │
│   └── ml_models/
│       ├── __init__.py              # Public API exports
│       ├── train.py                 # MaintenancePredictor: training + experiment runner
│       └── utils.py                 # MLflowManager, ModelEvaluator, TimeSeriesSplit
│
├── config/
│   ├── pipeline_config.yaml         # Full pipeline settings (959 lines)
│   └── mlflow_config.yaml           # MLflow experiments, metrics, model registry
│
├── docs/
│   ├── architecture.md              # System architecture with Mermaid diagrams
│   └── data_dictionary.md           # Schema for all 4 data sources
│
└── data/                            # Generated at runtime (gitignored)
    ├── raw/                         # Bronze layer — raw CSVs
    ├── processed/                   # Silver + Gold layer CSVs
    └── warehouse/                   # DB warehouse files
```

**Planned but not yet implemented:**
- `src/api/` — FastAPI prediction service (Sprint 4)
- `src/dashboard/` — Dashboard configuration (Sprint 4)
- `notebooks/` — Jupyter EDA notebooks (Sprint 2)
- `tests/` — Test suite (pytest installed but no tests yet)

---

## Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| Package manager | `uv` (NOT pip/poetry) |
| Data processing | Pandas 2.3, NumPy 2.3, PyArrow 21 |
| ML/DS | Scikit-learn 1.7, XGBoost 3.1, TensorFlow 2.20 (planned) |
| Class balancing | imbalanced-learn (SMOTE) |
| ML ops | MLflow 3.5 |
| API | FastAPI 0.121 + Uvicorn 0.38 |
| Database | PostgreSQL 15 via SQLAlchemy 2.0 + psycopg2 |
| Notebooks | JupyterLab 4.5 |
| Visualization | Matplotlib 3.10, Plotly 6.5, Seaborn 0.13 |
| Config | PyYAML 6.0, Pydantic 2.12 |
| Code quality | Black 25.11, Flake8 7.3 |
| Testing | Pytest 9.0 |
| Containers | Docker (multi-stage) + Docker Compose |

---

## Development Environment Setup

### Prerequisites
- Python 3.12+
- `uv` package manager
- Docker + Docker Compose (for full stack)

### Local setup (Python only)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies from lockfile
uv sync

# Set database environment variables
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=olpa_warehouse
export DB_USER=olpa_user
export DB_PASSWORD=olpa_password
```

### Full stack with Docker

```bash
# Start all services (Jupyter, MLflow, PostgreSQL, training, API)
docker-compose up

# Start specific services only
docker-compose up jupyter mlflow postgres

# Rebuild images after dependency changes
docker-compose build

# Run training container
docker-compose run training
```

**Service endpoints:**
- JupyterLab: http://localhost:8888
- MLflow UI: http://localhost:5000
- FastAPI: http://localhost:8000 (Sprint 4)
- PostgreSQL: localhost:5432 (`olpa_warehouse` db)

### Database initialization

```bash
# PostgreSQL auto-initializes via Docker using schema.sql
# For manual setup:
psql -h localhost -U olpa_user -d olpa_warehouse \
  -f src/data_engineering/schema.sql
```

---

## Data Pipeline

### Medallion Architecture

```
Raw Sources → Bronze (raw CSV/DB) → Silver (cleaned) → Gold (ML-ready features)
```

| Layer | Location | Content |
|---|---|---|
| Bronze | `data/raw/`, `bronze_*` DB tables | Raw ingested data, 2-year retention |
| Silver | `data/processed/silver_sensor_data.csv` | Cleaned, validated, no duplicates |
| Gold | `data/processed/gold_ml_dataset.csv` | Engineered features, ML-ready |

### Running the ETL pipeline

```python
from src.data_engineering.etl_pipeline import ETLPipeline

pipeline = ETLPipeline(
    bronze_path='data/raw/sensor_data.csv',
    silver_path='data/processed/silver_sensor_data.csv',
    gold_path='data/processed/gold_ml_dataset.csv'
)
results = pipeline.run()
```

Or directly:
```bash
python src/data_engineering/etl_pipeline.py
```

### ETL pipeline steps

1. **Extract** — Load Bronze CSV (`parse_dates=['date']`)
2. **Quality check** — `DataQualityChecker`: completeness, validity (range checks), consistency (monotonic flight_hours), timeliness. Threshold: ≥90%. Below threshold logs a warning but does not halt.
3. **Clean** — `DataCleaner`: forward-fill missing values, IQR outlier capping (threshold=3.0), deduplication on `(aircraft_id, date)`
4. **Save Silver** — cleaned CSV
5. **Feature engineering** — `FeatureEngineer`: rolling stats (7/14/30d), trend/slope features, z-score anomaly scores, domain features
6. **Save Gold** — feature-rich CSV for ML

### Sensor validity ranges (used in quality checks)

| Sensor | Min | Max |
|---|---|---|
| temperature | 300 | 600 |
| vibration | 0 | 3 |
| pressure | 50 | 150 |
| rpm | 2000 | 4000 |

### Synthetic data generation

```python
from src.data_engineering.data_acquisition import DatasetGenerator

gen = DatasetGenerator()
sensor_df = gen.generate_sensor_data()   # 50 aircraft × 365 days, 15% failure rate
# Saves to data/raw/sensor_data.csv by default
```

---

## Database Module

Located in `src/data_engineering/database.py`. Config is loaded from `config/pipeline_config.yaml` or environment variables.

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `olpa_warehouse` | Database name |
| `DB_USER` | `olpa_user` | Username |
| `DB_PASSWORD` | `changeme` | Password |
| `DB_POOL_MIN` | `2` | Min pool connections |
| `DB_POOL_MAX` | `10` | Max pool connections |

### Usage pattern

```python
from src.data_engineering import get_database_connection, DataIngestion, DataQuery

db = get_database_connection()  # or get_database_connection('config/pipeline_config.yaml')

# Test connection
db.test_connection()

# Insert a DataFrame
ingestion = DataIngestion(db)
ingestion.insert_dataframe(df, 'bronze_sensor_data', batch_size=5000)

# Upsert (idempotent)
ingestion.upsert_dataframe(df, 'bronze_sensor_data', conflict_columns=['aircraft_id', 'date'])

# Query to DataFrame
query_mgr = DataQuery(db)
df = query_mgr.query_to_dataframe("SELECT * FROM silver_sensor_data WHERE aircraft_id = %s", ('AC001',))

# Always use context managers for connections
with db.get_cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM bronze_sensor_data")
```

---

## ML Training

### Running a training experiment

```bash
# Using defaults (random_forest on gold dataset)
python src/ml_models/train.py

# With options
python src/ml_models/train.py \
  --data_path data/processed/gold_ml_dataset.csv \
  --model_type xgboost \
  --use_smote \
  --use_engineered
```

**Supported model types:** `logistic_regression`, `decision_tree`, `random_forest`, `xgboost`

### Programmatic usage

```python
from src.ml_models.train import MaintenancePredictor

predictor = MaintenancePredictor(data_path='data/processed/gold_ml_dataset.csv')
model, metrics = predictor.run_experiment(
    model_type='xgboost',
    use_smote=True,
    use_engineered=True,
    hyperparams={'n_estimators': 200, 'max_depth': 8, 'learning_rate': 0.05}
)
```

### Training pipeline steps

1. Load Gold CSV
2. Feature preparation — exclude `aircraft_id`, `date`, `cycle`, `failed`, `days_to_failure`; target = `will_fail_7days`
3. Time-series split (70/15/15 by date, 7-day gap between sets to prevent leakage)
4. StandardScaler fit on train, transform on val/test
5. Class imbalance handling: `class_weight` (default) or SMOTE
6. Train model, evaluate on val + test sets
7. Log everything to MLflow (params, metrics, artifacts, model)

### Success thresholds

- F1-score ≥ 0.85
- Recall ≥ 0.85
- Precision ≥ 0.75 (secondary)
- Inference latency < 100ms

### MLflow utilities

```python
from src.ml_models.utils import MLflowManager, ModelEvaluator, TimeSeriesSplit

# MLflow is configured from config/mlflow_config.yaml
# Default tracking URI: sqlite:///mlruns/mlflow.db (local) or http://mlflow:5000 (Docker)
mlflow_mgr = MLflowManager('config/mlflow_config.yaml')

# Evaluate a model
evaluator = ModelEvaluator(y_true, y_pred, y_proba)
metrics = evaluator.compute_metrics()
evaluator.generate_confusion_matrix(save_path='cm.png')
evaluator.generate_roc_curve(save_path='roc.png')

# Time-series split
splitter = TimeSeriesSplit(df, date_column='date', gap_days=7)
train_df, val_df, test_df = splitter.split(0.7, 0.15, 0.15)
X_train, y_train = splitter.get_xy(train_df, feature_cols, 'will_fail_7days')
```

---

## Data Schema

### Primary dataset columns

| Column | Type | Description |
|---|---|---|
| `aircraft_id` | str | Aircraft identifier (AC001–AC050) |
| `date` | datetime | Observation date |
| `cycle` | int | Flight cycle number |
| `temperature` | float | Engine temperature (300–600 range) |
| `vibration` | float | Vibration level (0–3) |
| `pressure` | float | Engine pressure (50–150) |
| `rpm` | float | Engine RPM (2000–4000) |
| `altitude` | float | Flight altitude |
| `ambient_temp` | float | Ambient temperature |
| `flight_hours` | float | Cumulative flight hours (monotonically increasing per aircraft) |
| `failed` | bool | Whether failure occurred |
| `days_to_failure` | int | Days until next failure |
| `will_fail_7days` | int | **TARGET**: 1 if failure within 7 days, else 0 |

Gold layer adds engineered columns: `{col}_rolling_mean/std/min/max_{7,14,30}d`, `{col}_diff_1d`, `{col}_slope_{7,14,30}d`, `{col}_zscore`, `{col}_dist_from_mean`, `temp_vibration_interaction`, `pressure_rpm_ratio`.

---

## Code Quality

```bash
# Format code
black src/

# Lint
flake8 src/

# Run tests (when test suite is added)
pytest tests/
```

**Conventions:**
- Black formatting enforced (line length: default 88)
- Flake8 linting
- All modules use `logging` (not `print`) for operational output
- Docstrings on all public classes and methods
- Type hints on all function signatures
- Context managers for all database connections (never hold raw connections)
- Parameterized SQL queries only — never string interpolation for user inputs

---

## Configuration Files

### `config/pipeline_config.yaml`
Master pipeline configuration (959 lines). Key sections:
- `environment`: dev/staging/prod toggle, cloud provider selection
- `data_sources`: sensor, maintenance, inventory, metadata source definitions
- `database.warehouse`: PostgreSQL connection + pool settings
- `data_quality`: validation thresholds per layer
- `transformations`: Bronze→Silver→Gold rules, outlier methods
- `feature_engineering`: rolling windows, anomaly features
- `model_training`: split ratios, SMOTE, target column, algorithms
- `batch_prediction`: schedule (daily 02:00 UTC), 7-day horizon
- `api`: port 8000, rate limits, caching
- `monitoring`: drift detection, alert thresholds
- `retention`: 2-year Bronze, 5-year Silver/Gold

### `config/mlflow_config.yaml`
MLflow tracking configuration:
- `mlflow.tracking.backend_uri`: SQLite local or remote PostgreSQL
- `mlflow.tracking.default_experiment_name`: `olpa_predictive_maintenance`
- Experiments: `baseline_models`, `random_forest_optimization`, `xgboost_optimization`, `lstm_time_series`
- Model promotion criteria: F1≥0.85, Recall≥0.85, Precision≥0.75, inference<100ms

---

## Docker Architecture

### Stages

| Stage | Base | Purpose | Ports |
|---|---|---|---|
| `base` | python:3.12-slim | Shared foundation with uv + all deps | — |
| `development` | base | JupyterLab + dev tools | 8888, 5000 |
| `training` | base | ML training jobs | — |
| `api` | base | FastAPI service | 8000 |

### docker-compose services

| Service | Image | Purpose |
|---|---|---|
| `jupyter` | development stage | Interactive development |
| `mlflow` | base stage | Experiment tracking UI |
| `training` | training stage | Run model training |
| `postgres` | postgres:15-alpine | Data warehouse |
| `api` | api stage | Prediction REST API (Sprint 4) |

All services share `olpa_network` (bridge). PostgreSQL data persisted in `postgres_data` volume. `mlruns/` is mounted into all ML-related services for artifact sharing.

---

## Development Roadmap

| Sprint | Focus | Status |
|---|---|---|
| 1.1 | Environment setup, project init | Complete |
| 1.2 | Data architecture, DB schema, pipeline config | Complete |
| 1.3 | Data acquisition, initial loading | **Current** |
| 2 | Data engineering, feature engineering | Pending |
| 3 | ML modeling, validation, hyperparameter tuning | Pending |
| 4 | FastAPI service, dashboard (Power BI/Tableau) | Pending |
| 5 | MLOps, CI/CD, documentation | Pending |

---

## Known Gaps and Planned Work

- **No test suite yet** — `tests/` directory and pytest are set up, but no test files exist. Tests should be added during or after Sprint 2.
- **No CI/CD** — No GitHub Actions, GitLab CI, or other pipeline configured. Planned for Sprint 5.
- **API not implemented** — `src/api/` does not exist yet (Dockerfile references `src.api.main:app`). Planned for Sprint 4.
- **Dashboard not implemented** — `src/dashboard/` does not exist yet. Planned for Sprint 4.
- **No Jupyter notebooks** — `notebooks/` directory is referenced but empty. Planned for Sprint 2 EDA.
- **TensorFlow / LSTM disabled** — `tensorflow` is installed but LSTM models are commented out for MVP. Will be enabled in Sprint 3.
- **Synthetic data only** — Real data integration is Sprint 1.3 work.
- **`psycopg2` not in `pyproject.toml`** — `database.py` imports `psycopg2` but the lockfile uses it as a transitive dependency. If issues arise, add `psycopg2-binary` explicitly.
- **`imbalanced-learn` not in `pyproject.toml`** — `train.py` imports SMOTE from `imblearn`. Add `imbalanced-learn` to `pyproject.toml` if not present as a transitive dep.

---

## Scalability Targets

| Phase | Aircraft | Records/day |
|---|---|---|
| MVP | 10–50 | ~1M |
| Production | 500+ | ~100M |

The architecture is designed cloud-agnostic. Current config supports AWS (S3, RDS, SageMaker, Step Functions) and Azure (ADLS Gen2, Azure SQL, Databricks). Cloud provider is toggled in `config/pipeline_config.yaml` under `environment.cloud_provider`.
