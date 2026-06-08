# OLPA Notebooks - Learning Path

This folder contains Jupyter notebooks for learning data engineering and data analysis through the OLPA project.

## 🚀 Quick Start

1. **Start the database**:
```bash
cd /home/slim/OLPA
docker-compose up -d postgres
```

2. **Launch Jupyter**:
```bash
jupyter notebook
# Or for JupyterLab:
jupyter lab
```

3. **Start with notebook 01**, then progress sequentially through the numbered notebooks.

---

## 📚 Notebooks Overview

| # | Notebook | Focus | Duration | Status |
|---|----------|-------|----------|--------|
| 01 | `01_exploratory_data_analysis.ipynb` | Data exploration, visualization, patterns | 2-3 hours | ✅ Complete |
| 02 | `02_database_basics.ipynb` | PostgreSQL, SQL, data loading | 3-4 hours | 🔄 Ready |
| 03 | `03_data_quality_cleaning.ipynb` | Data quality, cleaning, Silver layer | 2-3 hours | ⏳ Coming |
| 04 | `04_feature_engineering.ipynb` | Feature creation, Gold layer | 3-4 hours | ⏳ Coming |
| 05 | `05_model_training_baseline.ipynb` | ML training, evaluation | 3-4 hours | ⏳ Coming |
| 06 | `06_model_evaluation_tuning.ipynb` | Hyperparameter tuning, model selection | 2-3 hours | ⏳ Coming |
| 07 | `07_pipeline_integration.ipynb` | End-to-end pipeline, automation | 2-3 hours | ⏳ Coming |
| 08 | `08_api_prototyping.ipynb` | FastAPI, model serving | 2-3 hours | ⏳ Coming |

**Total Learning Time**: ~20-25 hours

---

## 🎯 What You'll Learn

### Notebook 01: EDA ✅
- Pandas data manipulation
- Data visualization (matplotlib, seaborn)
- Statistical analysis
- Pattern identification
- Target variable analysis

### Notebook 02: Database Basics 🔄
- PostgreSQL setup with Docker
- Database connections (psycopg2, SQLAlchemy)
- SQL fundamentals (DDL, DML)
- Data loading strategies
- Query optimization
- Bronze layer implementation

### Notebook 03: Data Quality (Coming Soon)
- Quality metrics calculation
- Missing value handling
- Outlier detection and treatment
- Data validation rules
- Silver layer creation
- Cleaning documentation

### Notebook 04: Feature Engineering (Coming Soon)
- Time-series features
- Rolling statistics
- Trend indicators
- Domain-specific features
- Feature selection
- Gold layer creation

### Notebook 05-08: Advanced Topics (Coming Soon)
- Machine learning modeling
- Hyperparameter tuning
- Pipeline automation
- API development

---

## 📖 Prerequisites

- Python 3.12+
- Basic Python knowledge (lists, dicts, functions)
- Basic SQL knowledge (helpful but not required)
- Docker installed and running

## 🛠️ Environment Setup

All required packages are in `pyproject.toml`:
```bash
# Install dependencies with uv
uv pip install -e .

# Or with pip
pip install -e .
```

---

## 💡 Learning Tips

1. **Run cells sequentially** - Don't skip ahead
2. **Experiment** - Modify code and see what happens
3. **Add notes** - Use markdown cells for your observations
4. **Save often** - Ctrl+S or Cmd+S
5. **Clear output** - Cell → All Output → Clear before committing
6. **Ask why** - Understand the reasoning behind each step

---

## 📊 Data Files

Located in `../data/`:
- `raw/sensor_data.csv` - Aircraft sensor readings (~32K records)
- `raw/maintenance_records.csv` - Maintenance events (~1.4K records)
- `raw/inventory_data.csv` - Parts inventory (~160 records)
- `raw/aircraft_metadata.csv` - Fleet metadata (~27 aircraft)

---

## 🔗 Additional Resources

- **Full Learning Roadmap**: `../docs/LEARNING_ROADMAP.md`
- **Architecture**: `../docs/architecture.md`
- **Database Schema**: `../src/data_engineering/schema.sql`

---

## 🐛 Troubleshooting

### Database won't connect
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Restart if needed
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

### Jupyter kernel crashes
```bash
# Restart kernel: Kernel → Restart
# Or restart Jupyter server
```

### Missing packages
```bash
# Install in the notebook
!pip install package_name

# Or update pyproject.toml and reinstall
uv pip install -e .
```

---

**Happy Learning! 🚀**

*Start with notebook 01 to understand the data, then move to notebook 02 to learn databases.*
