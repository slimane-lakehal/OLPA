# OLPA - Optimisation Logistique & Prédictive Aéronautique

## Vision
Data-driven solution for aeronautical predictive maintenance and critical spare parts optimization.

## Objectives
- **Prediction Accuracy:** 85%+ F1-Score for failure prediction 7 days in advance
- **Stock Optimization:** 20% reduction in critical stock-outs
- **Delivery:** Daily refreshed dashboard with maintenance alerts and stock recommendations

## Project Structure
```
OLPA/
├── data/
│   ├── raw/              # Raw sensor and logistics data
│   ├── processed/        # Cleaned and transformed data
│   └── warehouse/        # Data warehouse files
├── src/
│   ├── data_engineering/ # ETL/ELT pipelines
│   ├── ml_models/        # ML model training and evaluation
│   ├── api/              # FastAPI prediction service
│   └── dashboard/        # Dashboard configuration
├── notebooks/            # Jupyter notebooks for EDA
├── config/               # Configuration files
├── tests/                # Unit and integration tests
└── docs/                 # Technical documentation
```

## Tech Stack
- **Data Engineering:** Python, Pandas, Spark
- **ML/DS:** Scikit-learn, TensorFlow/PyTorch, MLflow
- **API:** FastAPI, Docker
- **Dashboard:** Power BI/Tableau
- **Cloud:** Azure Synapse/Snowflake (configurable)

## Development Sprints

### Sprint 1: Infrastructure & Data Exploration
- **Sprint 1.1:** Environment setup and project initialization
- **Sprint 1.2:** Data architecture design (COMPLETE)
  - Architecture documentation with system diagrams
  - Complete database schema (Bronze/Silver/Gold layers)
  - Pipeline configuration template
  - Database utility module
- **Sprint 1.3:** Data acquisition and initial loading (NEXT)

### Sprint 2: Data Engineering & Feature Engineering
### Sprint 3: ML Modeling & Validation
### Sprint 4: API & Dashboard Delivery
### Sprint 5: MLOps & Documentation

## Quick Start

### Database Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=olpa_warehouse
export DB_USER=olpa_user
export DB_PASSWORD=your_password

# Create database schema
psql -h localhost -U olpa_user -d olpa_warehouse -f src/data_engineering/schema.sql
```

### Using the Database Module
```python
from src.data_engineering import get_database_connection, DataIngestion

# Initialize database connection
db = get_database_connection()

# Test connection
if db.test_connection():
    print("Connected successfully!")

# Load data from DataFrame
import pandas as pd
df = pd.read_csv('data/raw/sensor_data.csv')

ingestion = DataIngestion(db)
ingestion.insert_dataframe(df, 'bronze_sensor_data')
```

## Documentation
- [Architecture Documentation](docs/architecture.md) - Complete system architecture and design decisions
- [Sprint 1.2 Summary](docs/sprint_1_2_summary.md) - Data architecture deliverables and decisions
- [Database Schema](src/data_engineering/schema.sql) - Complete SQL schema definition
- [Pipeline Configuration](config/pipeline_config.yaml) - Comprehensive pipeline settings
