# OLPA Learning Roadmap
## Notebook-Driven Development for Data Engineering & Data Analysis

This guide helps you learn data engineering, data analysis, Python, and databases through building the OLPA project step-by-step in Jupyter notebooks.

---

## 🎯 Learning Philosophy

**Build → Understand → Refactor → Productionize**

1. **Notebooks First**: Experiment, visualize, and understand each component
2. **Learn by Doing**: Hands-on exercises with real data
3. **Incremental Complexity**: Start simple, add sophistication gradually
4. **Production Mindset**: Learn patterns that scale to production systems

---

## 📚 Learning Path (8 Notebooks)

### **Phase 1: Data Exploration & Infrastructure** (Weeks 1-2)

#### ✅ Notebook 01: Exploratory Data Analysis
**File**: `notebooks/01_exploratory_data_analysis.ipynb`
**Status**: COMPLETE
**Skills**: pandas, matplotlib, seaborn, data profiling

**What you learned**:
- Data loading from CSV files
- Statistical summaries and distributions
- Data visualization (histograms, time series, correlations)
- Identifying patterns and anomalies
- Target variable analysis (class imbalance)

**Key Outputs**:
- Understanding of sensor degradation patterns
- Feature importance insights
- Data quality assessment

---

#### 🔄 Notebook 02: Database Basics
**File**: `notebooks/02_database_basics.ipynb`
**Status**: READY TO RUN
**Skills**: PostgreSQL, psycopg2, SQLAlchemy, SQL fundamentals

**What you'll learn**:
- Database connection management (psycopg2 vs SQLAlchemy)
- DDL operations (CREATE TABLE, CREATE INDEX)
- DML operations (INSERT, SELECT, UPDATE, DELETE)
- Loading CSV data into PostgreSQL
- SQL queries (aggregation, GROUP BY, window functions)
- Database indexes and performance

**Exercises**:
1. Set up PostgreSQL with Docker
2. Create your first table
3. Insert and query data
4. Load sensor data into Bronze layer
5. Practice SQL queries (aggregation, joins, window functions)

**Key Concepts**:
- **Bronze Layer**: Raw data, exactly as ingested
- **Connection Pooling**: Efficient database access
- **Batch Loading**: Faster data ingestion with `to_sql()`
- **Indexing**: Speed up queries

---

### **Phase 2: Data Quality & Transformation** (Weeks 3-4)

#### 📝 Notebook 03: Data Quality & Cleaning
**File**: `notebooks/03_data_quality_cleaning.ipynb`
**Status**: TO BE CREATED
**Skills**: Data validation, outlier detection, missing value imputation

**What you'll learn**:
- Data quality metrics (completeness, validity, consistency, timeliness)
- Missing value strategies (forward fill, interpolation, mean imputation)
- Outlier detection (IQR, Z-score methods)
- Data validation rules
- Silver layer creation

**Exercises**:
1. Calculate data quality scores
2. Handle missing sensor readings
3. Detect and cap outliers
4. Remove duplicates
5. Create cleaned Silver layer tables
6. Document cleaning operations

**Key Concepts**:
- **Data Quality Dimensions**: The 4 Cs (Completeness, Consistency, Conformity, Currentness)
- **Silver Layer**: Cleaned, validated, standardized data
- **Audit Trail**: Logging all transformations

---

#### 🔧 Notebook 04: Feature Engineering
**File**: `notebooks/04_feature_engineering.ipynb`
**Status**: TO BE CREATED
**Skills**: Time-series features, domain knowledge, feature selection

**What you'll learn**:
- Rolling statistics (mean, std, min, max over windows)
- Trend features (slope, rate of change)
- Lag features (previous values)
- Domain-specific features (aeronautical metrics)
- Feature scaling and normalization
- Gold layer creation

**Exercises**:
1. Create rolling window features (7-day, 14-day, 30-day)
2. Calculate trend indicators
3. Build anomaly scores
4. Create interaction features
5. Feature selection (correlation analysis, feature importance)
6. Save to Gold layer

**Key Concepts**:
- **Feature Store**: Centralized feature repository
- **Time-Series Features**: Capturing temporal patterns
- **Gold Layer**: ML-ready features
- **Feature Engineering** > Algorithm Selection

---

### **Phase 3: Machine Learning** (Weeks 5-6)

#### 🤖 Notebook 05: Model Training Baseline
**File**: `notebooks/05_model_training_baseline.ipynb`
**Status**: TO BE CREATED
**Skills**: scikit-learn, model training, cross-validation

**What you'll learn**:
- Train/test split (time-series aware)
- Baseline models (Logistic Regression, Random Forest, XGBoost)
- Cross-validation strategies for time-series
- Handling class imbalance (SMOTE, class weights)
- Evaluation metrics (F1, Recall, Precision, ROC-AUC)
- Model interpretation

**Exercises**:
1. Prepare training dataset from Gold layer
2. Train baseline Random Forest model
3. Evaluate performance on validation set
4. Analyze feature importance
5. Tune hyperparameters
6. Save model with MLflow

**Key Concepts**:
- **Time-Series CV**: No random shuffling, respect temporal order
- **Class Imbalance**: Techniques to handle rare failures
- **Business Metrics**: Cost of false positives vs false negatives
- **Model Versioning**: Track experiments with MLflow

---

#### 📊 Notebook 06: Model Evaluation & Tuning
**File**: `notebooks/06_model_evaluation_tuning.ipynb`
**Status**: TO BE CREATED
**Skills**: Hyperparameter tuning, model comparison, error analysis

**What you'll learn**:
- Hyperparameter tuning (Grid Search, Random Search, Bayesian Optimization)
- Model comparison (Random Forest vs XGBoost vs LSTM)
- Error analysis (confusion matrix, ROC curves)
- Prediction calibration
- Business impact analysis

**Exercises**:
1. Compare multiple algorithms
2. Optimize hyperparameters with GridSearchCV
3. Analyze misclassified examples
4. Create calibration plots
5. Select best model based on business metrics
6. Generate evaluation report

**Key Concepts**:
- **Recall vs Precision Tradeoff**: Minimize missed failures
- **Calibrated Predictions**: Reliable probability estimates
- **Model Selection**: Not just accuracy, consider business impact

---

### **Phase 4: Integration & Deployment** (Weeks 7-8)

#### 🔄 Notebook 07: Pipeline Integration
**File**: `notebooks/07_pipeline_integration.ipynb`
**Status**: TO BE CREATED
**Skills**: ETL orchestration, automated workflows, data lineage

**What you'll learn**:
- End-to-end pipeline execution (Bronze → Silver → Gold → Predictions)
- Batch prediction workflows
- Pipeline monitoring and logging
- Error handling and retry logic
- Data lineage tracking

**Exercises**:
1. Run full ETL pipeline from notebook
2. Generate batch predictions
3. Create maintenance alerts
4. Update inventory recommendations
5. Monitor pipeline execution
6. Handle failures gracefully

**Key Concepts**:
- **Pipeline Orchestration**: Coordinating multiple steps
- **Idempotency**: Safe to re-run
- **Data Lineage**: Track data transformations
- **Monitoring**: Log metrics at each stage

---

#### 🚀 Notebook 08: API Prototyping
**File**: `notebooks/08_api_prototyping.ipynb`
**Status**: TO BE CREATED
**Skills**: FastAPI, REST APIs, model serving

**What you'll learn**:
- FastAPI basics
- Model loading and caching
- Request validation (Pydantic)
- Real-time prediction endpoint
- API testing with requests library
- Swagger/OpenAPI documentation

**Exercises**:
1. Create simple FastAPI app in notebook
2. Load trained model into memory
3. Create prediction endpoint
4. Test API with sample requests
5. Add input validation
6. Prototype frontend integration

**Key Concepts**:
- **Model Serving**: Load once, predict many times
- **API Design**: RESTful patterns
- **Input Validation**: Pydantic models
- **Testing**: Request/response validation

---

## 🛠️ Setup Instructions

### Prerequisites
- Python 3.12+
- Docker & Docker Compose
- Git
- Jupyter (or JupyterLab)

### Quick Start

1. **Start Database & Services**
```bash
cd /home/slim/OLPA

# Start PostgreSQL
docker-compose up -d postgres

# Verify it's running
docker ps
```

2. **Start Jupyter**
```bash
# Option A: Local Jupyter
jupyter notebook notebooks/

# Option B: Docker Jupyter
docker-compose up jupyter
```

3. **Open First Notebook**
- Navigate to `notebooks/01_exploratory_data_analysis.ipynb`
- Run all cells to familiarize yourself with the data

4. **Progress to Database Notebook**
- Open `notebooks/02_database_basics.ipynb`
- Follow the exercises step-by-step

---

## 📖 Learning Resources

### Python & Pandas
- [Pandas Official Documentation](https://pandas.pydata.org/docs/)
- [Python Data Science Handbook](https://jakevdp.github.io/PythonDataScienceHandbook/)

### SQL & Databases
- [PostgreSQL Tutorial](https://www.postgresqltutorial.com/)
- [SQLBolt Interactive Tutorial](https://sqlbolt.com/)
- [Use The Index, Luke](https://use-the-index-luke.com/) - SQL Performance

### Data Engineering
- [The Data Engineering Cookbook](https://github.com/andkret/Cookbook)
- [Designing Data-Intensive Applications](https://dataintensive.net/) (Book)

### Machine Learning
- [Scikit-Learn Documentation](https://scikit-learn.org/stable/)
- [Time Series Forecasting](https://www.tensorflow.org/tutorials/structured_data/time_series)

---

## 🎯 Learning Objectives by Phase

### Phase 1: Foundation
- [ ] Understand the data (distributions, patterns, quality)
- [ ] Set up PostgreSQL database
- [ ] Load data into Bronze layer
- [ ] Write basic SQL queries
- [ ] Understand medallion architecture

### Phase 2: Transformation
- [ ] Assess and improve data quality
- [ ] Clean and standardize data (Silver layer)
- [ ] Engineer time-series features
- [ ] Build feature store (Gold layer)
- [ ] Document transformations

### Phase 3: Modeling
- [ ] Train baseline predictive models
- [ ] Evaluate with appropriate metrics
- [ ] Handle class imbalance
- [ ] Tune hyperparameters
- [ ] Select best model for production

### Phase 4: Integration
- [ ] Build end-to-end pipeline
- [ ] Generate batch predictions
- [ ] Prototype API for real-time predictions
- [ ] Monitor and log pipeline execution
- [ ] Prepare for production deployment

---

## 📝 Progress Tracking

| Notebook | Status | Completed Date | Notes |
|----------|--------|----------------|-------|
| 01_exploratory_data_analysis | ✅ Complete | - | Existing |
| 02_database_basics | 🔄 Ready | - | Start here! |
| 03_data_quality_cleaning | ⏳ Pending | - | - |
| 04_feature_engineering | ⏳ Pending | - | - |
| 05_model_training_baseline | ⏳ Pending | - | - |
| 06_model_evaluation_tuning | ⏳ Pending | - | - |
| 07_pipeline_integration | ⏳ Pending | - | - |
| 08_api_prototyping | ⏳ Pending | - | - |

---

## 💡 Tips for Success

1. **Don't Rush**: Take time to understand each concept
2. **Experiment**: Modify code, break things, fix them
3. **Document**: Add notes about what you learn
4. **Ask Questions**: Why does this work? What if I change X?
5. **Compare**: Notebooks vs production code - what's different and why?
6. **Visualize**: Always plot your data before modeling
7. **Version Control**: Commit notebooks regularly

---

## 🔄 From Notebooks to Production

After completing all notebooks, you'll refactor into production code:

```
Notebook Learning          →    Production Code
─────────────────────────────────────────────────
02_database_basics.ipynb   →    src/data_engineering/database.py
03_data_quality.ipynb      →    src/data_engineering/quality.py
04_feature_engineering.ipynb →  src/data_engineering/features.py
05_model_training.ipynb    →    src/ml_models/train.py
08_api_prototyping.ipynb   →    src/api/main.py
```

**Why notebooks first?**
- Faster iteration and experimentation
- Better visualization and understanding
- Easier to share insights
- Natural documentation

**Why production code?**
- Better testing and error handling
- Automated scheduling
- Performance optimization
- Scalability and maintainability

---

## 🎓 Next Steps After Completion

Once you complete all 8 notebooks, you'll be ready to:

1. **Refactor to Production**: Convert notebook logic to modular Python code
2. **Add Testing**: Unit tests, integration tests
3. **Orchestration**: Airflow or similar for scheduling
4. **Monitoring**: Prometheus, Grafana for observability
5. **CI/CD**: Automated testing and deployment
6. **Cloud Deployment**: AWS/Azure production setup

---

## 📞 Need Help?

- Review the architecture docs: `docs/architecture.md`
- Check the database schema: `src/data_engineering/schema.sql`
- Refer to sprint summaries: `docs/sprint_1_2_summary.md`

---

**Good luck on your learning journey! 🚀**

*Start with `notebooks/02_database_basics.ipynb` and work your way through.*
