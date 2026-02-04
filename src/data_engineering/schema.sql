-- =============================================================================
-- OLPA Data Warehouse Schema Definition
-- Optimisation Logistique & Prédictive Aéronautique
-- =============================================================================
-- Purpose: Complete data warehouse schema for aeronautical predictive maintenance
-- Architecture: Medallion (Bronze → Silver → Gold) with star schema for analytics
-- Database: PostgreSQL 13+ (compatible with Azure SQL, AWS RDS)
-- Version: 1.0
-- Last Updated: 05/02/2026
-- =============================================================================

-- =============================================================================
-- BRONZE LAYER - Raw Data Tables
-- Purpose: Store raw data exactly as ingested from source systems
-- Retention: 2 years
-- Partitioning: By ingestion date (recommended for production)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Raw Sensor Data
-- Source: Aircraft sensor systems (daily dumps)
-- Volume: ~1-10M records/day
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bronze_sensor_data (
    id BIGSERIAL PRIMARY KEY,
    aircraft_id VARCHAR(50) NOT NULL,
    sensor_id VARCHAR(100) NOT NULL,
    sensor_type VARCHAR(50) NOT NULL, -- temperature, vibration, pressure, etc.
    measurement_timestamp TIMESTAMP NOT NULL,
    measurement_value NUMERIC(12, 4),
    measurement_unit VARCHAR(20),
    raw_data_json JSONB, -- For additional metadata from source
    ingestion_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_file VARCHAR(500),
    data_quality_flag VARCHAR(20) DEFAULT 'unchecked' -- unchecked, valid, invalid, suspicious
);

CREATE INDEX idx_bronze_sensor_aircraft_time ON bronze_sensor_data(aircraft_id, measurement_timestamp);
CREATE INDEX idx_bronze_sensor_sensor_time ON bronze_sensor_data(sensor_id, measurement_timestamp);
CREATE INDEX idx_bronze_sensor_ingestion ON bronze_sensor_data(ingestion_timestamp);
CREATE INDEX idx_bronze_sensor_quality ON bronze_sensor_data(data_quality_flag);

COMMENT ON TABLE bronze_sensor_data IS 'Raw sensor readings from aircraft systems';

-- -----------------------------------------------------------------------------
-- Raw Maintenance Records
-- Source: Maintenance management system (MRO)
-- Volume: ~100-1K records/day
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bronze_maintenance_records (
    id BIGSERIAL PRIMARY KEY,
    aircraft_id VARCHAR(50) NOT NULL,
    component_id VARCHAR(100),
    maintenance_type VARCHAR(50), -- scheduled, unscheduled, corrective, preventive
    maintenance_action VARCHAR(100), -- inspection, repair, replacement
    failure_occurred BOOLEAN DEFAULT FALSE,
    failure_type VARCHAR(100),
    failure_description TEXT,
    scheduled_date TIMESTAMP,
    actual_start_date TIMESTAMP,
    actual_end_date TIMESTAMP,
    technician_id VARCHAR(50),
    parts_used_json JSONB, -- Array of parts used
    labor_hours NUMERIC(6, 2),
    cost_total NUMERIC(10, 2),
    notes TEXT,
    ingestion_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_system VARCHAR(100)
);

CREATE INDEX idx_bronze_maint_aircraft ON bronze_maintenance_records(aircraft_id);
CREATE INDEX idx_bronze_maint_date ON bronze_maintenance_records(actual_start_date);
CREATE INDEX idx_bronze_maint_failure ON bronze_maintenance_records(failure_occurred);
CREATE INDEX idx_bronze_maint_component ON bronze_maintenance_records(component_id);

COMMENT ON TABLE bronze_maintenance_records IS 'Raw maintenance event records from MRO system';

-- -----------------------------------------------------------------------------
-- Raw Inventory/Logistics Data
-- Source: ERP/Inventory management system
-- Volume: ~10-50K records/day
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bronze_inventory_data (
    id BIGSERIAL PRIMARY KEY,
    part_number VARCHAR(100) NOT NULL,
    part_name VARCHAR(255),
    warehouse_location VARCHAR(100),
    quantity_on_hand INTEGER,
    quantity_reserved INTEGER,
    quantity_available INTEGER,
    reorder_point INTEGER,
    unit_cost NUMERIC(10, 2),
    supplier_id VARCHAR(50),
    lead_time_days INTEGER,
    snapshot_date DATE NOT NULL,
    ingestion_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_system VARCHAR(100)
);

CREATE INDEX idx_bronze_inv_part ON bronze_inventory_data(part_number, snapshot_date);
CREATE INDEX idx_bronze_inv_date ON bronze_inventory_data(snapshot_date);

COMMENT ON TABLE bronze_inventory_data IS 'Raw inventory snapshots from ERP system';

-- -----------------------------------------------------------------------------
-- Raw Aircraft Metadata
-- Source: Fleet management system
-- Volume: ~1K records (relatively static)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bronze_aircraft_metadata (
    id BIGSERIAL PRIMARY KEY,
    aircraft_id VARCHAR(50) UNIQUE NOT NULL,
    aircraft_type VARCHAR(50), -- A320, B737, etc.
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    serial_number VARCHAR(100),
    registration_number VARCHAR(50),
    manufacture_date DATE,
    acquisition_date DATE,
    total_flight_hours NUMERIC(10, 2),
    total_flight_cycles INTEGER,
    operational_status VARCHAR(50), -- active, maintenance, retired
    base_location VARCHAR(100),
    operator VARCHAR(100),
    configuration_json JSONB, -- Specific configuration details
    ingestion_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bronze_aircraft_id ON bronze_aircraft_metadata(aircraft_id);
CREATE INDEX idx_bronze_aircraft_status ON bronze_aircraft_metadata(operational_status);

COMMENT ON TABLE bronze_aircraft_metadata IS 'Raw aircraft master data from fleet management';

-- =============================================================================
-- SILVER LAYER - Cleaned and Validated Data
-- Purpose: Store cleaned, validated, and standardized data
-- Quality: All quality checks passed, ready for analytics
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Cleaned Sensor Data
-- Transformations: Missing value handling, outlier flagging, unit standardization
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS silver_sensor_data (
    id BIGSERIAL PRIMARY KEY,
    aircraft_id VARCHAR(50) NOT NULL,
    sensor_id VARCHAR(100) NOT NULL,
    sensor_type VARCHAR(50) NOT NULL,
    measurement_timestamp TIMESTAMP NOT NULL,
    measurement_value NUMERIC(12, 4) NOT NULL,
    measurement_unit VARCHAR(20) NOT NULL, -- Standardized to SI units
    is_imputed BOOLEAN DEFAULT FALSE,
    imputation_method VARCHAR(50), -- forward_fill, median, null
    is_outlier BOOLEAN DEFAULT FALSE,
    outlier_score NUMERIC(6, 4),
    quality_score NUMERIC(3, 2), -- 0.0 to 1.0
    processing_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_record_id BIGINT REFERENCES bronze_sensor_data(id)
);

-- Partitioning recommendation: PARTITION BY RANGE (measurement_timestamp)
-- Create partitions for each month/quarter based on data volume

CREATE INDEX idx_silver_sensor_aircraft_time ON silver_sensor_data(aircraft_id, measurement_timestamp);
CREATE INDEX idx_silver_sensor_type_time ON silver_sensor_data(sensor_type, measurement_timestamp);
CREATE INDEX idx_silver_sensor_quality ON silver_sensor_data(quality_score);

COMMENT ON TABLE silver_sensor_data IS 'Cleaned and validated sensor data ready for analytics';

-- -----------------------------------------------------------------------------
-- Cleaned Maintenance Records
-- Transformations: Timestamp normalization, categorization, enrichment
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS silver_maintenance_records (
    id BIGSERIAL PRIMARY KEY,
    aircraft_id VARCHAR(50) NOT NULL,
    component_id VARCHAR(100),
    component_type VARCHAR(100), -- Normalized component taxonomy
    maintenance_type VARCHAR(50) NOT NULL,
    maintenance_action VARCHAR(100) NOT NULL,
    failure_occurred BOOLEAN DEFAULT FALSE,
    failure_severity VARCHAR(20), -- critical, major, minor
    failure_category VARCHAR(100), -- Categorized failure types
    scheduled_date TIMESTAMP,
    actual_start_date TIMESTAMP NOT NULL,
    actual_end_date TIMESTAMP,
    duration_hours NUMERIC(6, 2), -- Calculated field
    downtime_hours NUMERIC(6, 2),
    parts_replaced_count INTEGER,
    labor_hours NUMERIC(6, 2),
    total_cost NUMERIC(10, 2),
    processing_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_record_id BIGINT REFERENCES bronze_maintenance_records(id)
);

CREATE INDEX idx_silver_maint_aircraft_time ON silver_maintenance_records(aircraft_id, actual_start_date);
CREATE INDEX idx_silver_maint_component ON silver_maintenance_records(component_id);
CREATE INDEX idx_silver_maint_failure ON silver_maintenance_records(failure_occurred, failure_severity);

COMMENT ON TABLE silver_maintenance_records IS 'Cleaned maintenance events with standardized categorization';

-- -----------------------------------------------------------------------------
-- Cleaned Inventory Data
-- Transformations: Calculated fields, stock status categorization
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS silver_inventory_data (
    id BIGSERIAL PRIMARY KEY,
    part_number VARCHAR(100) NOT NULL,
    part_name VARCHAR(255),
    part_category VARCHAR(100), -- Critical, consumable, etc.
    warehouse_location VARCHAR(100),
    quantity_on_hand INTEGER NOT NULL,
    quantity_reserved INTEGER NOT NULL,
    quantity_available INTEGER NOT NULL,
    reorder_point INTEGER,
    reorder_quantity INTEGER,
    stock_status VARCHAR(50), -- in_stock, low_stock, out_of_stock, overstock
    unit_cost NUMERIC(10, 2),
    total_value NUMERIC(12, 2), -- quantity_on_hand * unit_cost
    supplier_id VARCHAR(50),
    lead_time_days INTEGER,
    criticality_level VARCHAR(20), -- high, medium, low
    snapshot_date DATE NOT NULL,
    processing_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_record_id BIGINT REFERENCES bronze_inventory_data(id)
);

CREATE INDEX idx_silver_inv_part_date ON silver_inventory_data(part_number, snapshot_date);
CREATE INDEX idx_silver_inv_status ON silver_inventory_data(stock_status, criticality_level);

COMMENT ON TABLE silver_inventory_data IS 'Cleaned inventory data with calculated stock status';

-- -----------------------------------------------------------------------------
-- Master Aircraft Dimension
-- Type: Slowly Changing Dimension Type 2 (historical tracking)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS silver_dim_aircraft (
    dim_aircraft_key BIGSERIAL PRIMARY KEY,
    aircraft_id VARCHAR(50) NOT NULL, -- Business key
    aircraft_type VARCHAR(50) NOT NULL,
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    serial_number VARCHAR(100),
    registration_number VARCHAR(50),
    manufacture_date DATE,
    acquisition_date DATE,
    operational_status VARCHAR(50),
    base_location VARCHAR(100),
    operator VARCHAR(100),

    -- SCD Type 2 fields
    effective_start_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    effective_end_date TIMESTAMP DEFAULT '9999-12-31'::TIMESTAMP,
    is_current BOOLEAN DEFAULT TRUE,
    version_number INTEGER DEFAULT 1,

    processing_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_record_id BIGINT REFERENCES bronze_aircraft_metadata(id)
);

CREATE INDEX idx_silver_dim_aircraft_id ON silver_dim_aircraft(aircraft_id, is_current);
CREATE INDEX idx_silver_dim_aircraft_current ON silver_dim_aircraft(is_current);

COMMENT ON TABLE silver_dim_aircraft IS 'Aircraft dimension with historical tracking (SCD Type 2)';

-- =============================================================================
-- GOLD LAYER - Feature Store and Analytics Tables
-- Purpose: ML-ready features and pre-aggregated analytics views
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Feature Store - Time Series Features
-- Purpose: Pre-computed features for ML model training and inference
-- Grain: Aircraft-Sensor-Hour level
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold_sensor_features (
    id BIGSERIAL PRIMARY KEY,
    aircraft_id VARCHAR(50) NOT NULL,
    sensor_id VARCHAR(100) NOT NULL,
    sensor_type VARCHAR(50) NOT NULL,
    feature_timestamp TIMESTAMP NOT NULL, -- Hour-level granularity

    -- Rolling statistics (multiple time windows)
    value_current NUMERIC(12, 4),
    value_mean_3h NUMERIC(12, 4),
    value_mean_6h NUMERIC(12, 4),
    value_mean_12h NUMERIC(12, 4),
    value_mean_24h NUMERIC(12, 4),
    value_std_3h NUMERIC(12, 4),
    value_std_6h NUMERIC(12, 4),
    value_std_12h NUMERIC(12, 4),
    value_std_24h NUMERIC(12, 4),
    value_min_24h NUMERIC(12, 4),
    value_max_24h NUMERIC(12, 4),

    -- Trend features
    trend_3h VARCHAR(20), -- increasing, decreasing, stable
    trend_12h VARCHAR(20),
    rate_of_change_1h NUMERIC(12, 4),
    rate_of_change_6h NUMERIC(12, 4),

    -- Statistical features
    coefficient_of_variation NUMERIC(6, 4),
    skewness NUMERIC(6, 4),
    kurtosis NUMERIC(6, 4),

    -- Anomaly indicators
    anomaly_score NUMERIC(6, 4), -- 0.0 to 1.0
    is_anomaly BOOLEAN DEFAULT FALSE,

    -- Context features
    operating_hours_cumulative NUMERIC(10, 2),
    days_since_last_maintenance INTEGER,

    processing_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    feature_version VARCHAR(20) -- Track feature engineering version
);

CREATE INDEX idx_gold_features_aircraft_time ON gold_sensor_features(aircraft_id, feature_timestamp);
CREATE INDEX idx_gold_features_sensor_time ON gold_sensor_features(sensor_id, feature_timestamp);

COMMENT ON TABLE gold_sensor_features IS 'Pre-computed time-series features for ML models';

-- -----------------------------------------------------------------------------
-- Feature Store - Aggregated Aircraft Features
-- Purpose: Aircraft-level aggregated features
-- Grain: Aircraft-Day level
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold_aircraft_features (
    id BIGSERIAL PRIMARY KEY,
    aircraft_id VARCHAR(50) NOT NULL,
    feature_date DATE NOT NULL,

    -- Operational metrics
    flight_hours_today NUMERIC(6, 2),
    flight_cycles_today INTEGER,
    cumulative_flight_hours NUMERIC(10, 2),
    cumulative_flight_cycles INTEGER,

    -- Maintenance context
    days_since_last_maintenance INTEGER,
    days_until_next_scheduled_maintenance INTEGER,
    maintenance_events_last_30d INTEGER,
    failure_events_last_90d INTEGER,

    -- Sensor health indicators
    sensors_with_anomalies_count INTEGER,
    avg_anomaly_score NUMERIC(6, 4),
    critical_sensors_count INTEGER, -- Sensors exceeding thresholds

    -- Component status
    components_high_risk_count INTEGER,

    -- Historical patterns
    similar_failure_history_count INTEGER, -- Historical failures with similar patterns

    processing_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    feature_version VARCHAR(20)
);

CREATE UNIQUE INDEX idx_gold_aircraft_feat_unique ON gold_aircraft_features(aircraft_id, feature_date);

COMMENT ON TABLE gold_aircraft_features IS 'Aircraft-level aggregated features for prediction';

-- -----------------------------------------------------------------------------
-- ML Training Dataset
-- Purpose: Labeled dataset for model training with target variable
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold_ml_training_dataset (
    id BIGSERIAL PRIMARY KEY,
    aircraft_id VARCHAR(50) NOT NULL,
    snapshot_timestamp TIMESTAMP NOT NULL,

    -- Target variable
    failure_within_7_days BOOLEAN NOT NULL, -- 1 = failure occurred, 0 = no failure
    actual_failure_date TIMESTAMP, -- Null if no failure
    failure_type VARCHAR(100),
    failure_component VARCHAR(100),

    -- Features (denormalized for ML training efficiency)
    features_json JSONB NOT NULL, -- All features in JSON for flexibility

    -- Metadata for training
    dataset_split VARCHAR(20), -- train, validation, test
    created_for_training_run_id VARCHAR(100),

    processing_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_gold_ml_train_aircraft ON gold_ml_training_dataset(aircraft_id, snapshot_timestamp);
CREATE INDEX idx_gold_ml_train_split ON gold_ml_training_dataset(dataset_split);
CREATE INDEX idx_gold_ml_train_target ON gold_ml_training_dataset(failure_within_7_days);

COMMENT ON TABLE gold_ml_training_dataset IS 'Labeled training dataset with features and target variable';

-- =============================================================================
-- PREDICTION RESULTS TABLES
-- Purpose: Store model predictions and alerts
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Failure Predictions
-- Purpose: Store daily batch predictions from ML model
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold_failure_predictions (
    id BIGSERIAL PRIMARY KEY,
    aircraft_id VARCHAR(50) NOT NULL,
    prediction_date DATE NOT NULL,
    prediction_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Prediction results
    failure_probability NUMERIC(5, 4) NOT NULL, -- 0.0000 to 1.0000
    failure_prediction BOOLEAN NOT NULL, -- Binary classification
    risk_level VARCHAR(20), -- low, medium, high, critical

    -- Prediction details
    predicted_failure_window_start DATE,
    predicted_failure_window_end DATE,
    most_likely_component VARCHAR(100),
    contributing_sensors_json JSONB, -- Top sensors contributing to prediction

    -- Model metadata
    model_id VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    prediction_confidence NUMERIC(5, 4), -- Model confidence score

    -- Feature snapshot reference
    feature_snapshot_id BIGINT REFERENCES gold_aircraft_features(id),

    -- Validation (for feedback loop)
    actual_failure_occurred BOOLEAN, -- Filled in after prediction window
    prediction_accuracy VARCHAR(20) -- true_positive, false_positive, true_negative, false_negative
);

CREATE INDEX idx_gold_pred_aircraft_date ON gold_failure_predictions(aircraft_id, prediction_date);
CREATE INDEX idx_gold_pred_risk ON gold_failure_predictions(risk_level);
CREATE INDEX idx_gold_pred_model ON gold_failure_predictions(model_id, model_version);

COMMENT ON TABLE gold_failure_predictions IS 'Daily failure probability predictions from ML model';

-- -----------------------------------------------------------------------------
-- Maintenance Alerts
-- Purpose: Actionable maintenance alerts for dashboard
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold_maintenance_alerts (
    id BIGSERIAL PRIMARY KEY,
    alert_id VARCHAR(100) UNIQUE NOT NULL, -- UUID for tracking
    aircraft_id VARCHAR(50) NOT NULL,
    alert_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Alert details
    alert_type VARCHAR(50) NOT NULL, -- predictive_failure, threshold_exceeded, anomaly_detected
    severity VARCHAR(20) NOT NULL, -- critical, high, medium, low
    status VARCHAR(20) DEFAULT 'open', -- open, acknowledged, in_progress, resolved, false_alarm

    -- Related prediction
    prediction_id BIGINT REFERENCES gold_failure_predictions(id),
    failure_probability NUMERIC(5, 4),

    -- Recommended action
    recommended_action TEXT,
    recommended_component VARCHAR(100),
    recommended_timeframe VARCHAR(50), -- immediate, within_24h, within_7d

    -- Tracking
    acknowledged_by VARCHAR(100),
    acknowledged_timestamp TIMESTAMP,
    resolved_by VARCHAR(100),
    resolved_timestamp TIMESTAMP,
    resolution_notes TEXT,

    -- Dashboard visibility
    is_visible_dashboard BOOLEAN DEFAULT TRUE,
    dashboard_priority INTEGER DEFAULT 1 -- Higher = more urgent
);

CREATE INDEX idx_gold_alerts_aircraft ON gold_maintenance_alerts(aircraft_id, alert_timestamp);
CREATE INDEX idx_gold_alerts_status ON gold_maintenance_alerts(status, severity);
CREATE INDEX idx_gold_alerts_type ON gold_maintenance_alerts(alert_type);

COMMENT ON TABLE gold_maintenance_alerts IS 'Actionable maintenance alerts for dashboard and notifications';

-- =============================================================================
-- INVENTORY OPTIMIZATION TABLES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Inventory Recommendations
-- Purpose: Recommended inventory actions based on failure predictions
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold_inventory_recommendations (
    id BIGSERIAL PRIMARY KEY,
    recommendation_date DATE NOT NULL,
    part_number VARCHAR(100) NOT NULL,
    part_name VARCHAR(255),

    -- Current state
    current_quantity INTEGER,
    current_reserved INTEGER,
    current_available INTEGER,

    -- Predicted demand
    predicted_demand_7d INTEGER, -- Based on failure predictions
    predicted_demand_30d INTEGER,

    -- Recommendation
    recommendation_type VARCHAR(50), -- order, expedite, reduce, no_action
    recommended_order_quantity INTEGER,
    recommended_priority VARCHAR(20), -- urgent, high, normal, low

    -- Justification
    related_predictions_count INTEGER, -- Number of predictions requiring this part
    related_aircraft_list TEXT, -- Comma-separated list
    expected_stockout_date DATE,

    -- Financial impact
    estimated_cost NUMERIC(10, 2),
    potential_downtime_cost_avoided NUMERIC(12, 2),

    processing_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_gold_inv_rec_date ON gold_inventory_recommendations(recommendation_date);
CREATE INDEX idx_gold_inv_rec_part ON gold_inventory_recommendations(part_number);
CREATE INDEX idx_gold_inv_rec_type ON gold_inventory_recommendations(recommendation_type, recommended_priority);

COMMENT ON TABLE gold_inventory_recommendations IS 'Inventory recommendations driven by failure predictions';

-- =============================================================================
-- DASHBOARD AGGREGATION VIEWS
-- Purpose: Pre-aggregated views for dashboard performance
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Daily KPI Summary
-- Purpose: High-level KPIs refreshed daily for dashboard
-- -----------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS gold_daily_kpi_summary AS
SELECT
    CURRENT_DATE as kpi_date,

    -- Fleet metrics
    COUNT(DISTINCT a.aircraft_id) as total_aircraft,
    COUNT(DISTINCT CASE WHEN a.operational_status = 'active' THEN a.aircraft_id END) as active_aircraft,

    -- Alert metrics
    COUNT(DISTINCT CASE WHEN ma.severity = 'critical' AND ma.status = 'open' THEN ma.id END) as critical_alerts_open,
    COUNT(DISTINCT CASE WHEN ma.severity = 'high' AND ma.status = 'open' THEN ma.id END) as high_alerts_open,
    COUNT(DISTINCT ma.id) as total_alerts_today,

    -- Prediction metrics
    AVG(fp.failure_probability) as avg_failure_probability,
    COUNT(DISTINCT CASE WHEN fp.risk_level = 'critical' THEN fp.aircraft_id END) as aircraft_critical_risk,
    COUNT(DISTINCT CASE WHEN fp.risk_level = 'high' THEN fp.aircraft_id END) as aircraft_high_risk,

    -- Inventory metrics
    COUNT(DISTINCT CASE WHEN ir.recommendation_type = 'order' AND ir.recommended_priority = 'urgent' THEN ir.part_number END) as urgent_part_orders,

    CURRENT_TIMESTAMP as last_refresh
FROM silver_dim_aircraft a
LEFT JOIN gold_maintenance_alerts ma ON a.aircraft_id = ma.aircraft_id
    AND ma.alert_timestamp::DATE = CURRENT_DATE
LEFT JOIN gold_failure_predictions fp ON a.aircraft_id = fp.aircraft_id
    AND fp.prediction_date = CURRENT_DATE
LEFT JOIN gold_inventory_recommendations ir ON ir.recommendation_date = CURRENT_DATE
WHERE a.is_current = TRUE;

CREATE UNIQUE INDEX idx_mv_daily_kpi_date ON gold_daily_kpi_summary(kpi_date);

COMMENT ON MATERIALIZED VIEW gold_daily_kpi_summary IS 'Daily KPI summary for dashboard (refresh hourly)';

-- Refresh schedule: Execute hourly via cron/scheduler
-- REFRESH MATERIALIZED VIEW CONCURRENTLY gold_daily_kpi_summary;

-- =============================================================================
-- DATA QUALITY AND MONITORING TABLES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Data Quality Metrics
-- Purpose: Track data quality metrics for monitoring
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS monitoring_data_quality (
    id BIGSERIAL PRIMARY KEY,
    check_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    table_name VARCHAR(100) NOT NULL,
    check_type VARCHAR(50) NOT NULL, -- completeness, validity, consistency, timeliness

    -- Metrics
    total_records BIGINT,
    records_with_issues BIGINT,
    quality_score NUMERIC(5, 4), -- 0.0 to 1.0

    -- Details
    issue_description TEXT,
    threshold_value NUMERIC(12, 4),
    actual_value NUMERIC(12, 4),
    status VARCHAR(20), -- pass, warning, fail

    -- Alerting
    alert_sent BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_monitor_dq_table ON monitoring_data_quality(table_name, check_timestamp);
CREATE INDEX idx_monitor_dq_status ON monitoring_data_quality(status);

COMMENT ON TABLE monitoring_data_quality IS 'Data quality monitoring metrics';

-- -----------------------------------------------------------------------------
-- Pipeline Execution Log
-- Purpose: Track ETL/ML pipeline execution for monitoring
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS monitoring_pipeline_execution (
    id BIGSERIAL PRIMARY KEY,
    execution_id VARCHAR(100) UNIQUE NOT NULL, -- UUID
    pipeline_name VARCHAR(100) NOT NULL,
    pipeline_stage VARCHAR(50) NOT NULL, -- ingestion, bronze_to_silver, feature_engineering, etc.

    -- Execution details
    start_timestamp TIMESTAMP NOT NULL,
    end_timestamp TIMESTAMP,
    duration_seconds INTEGER,
    status VARCHAR(20), -- running, completed, failed, cancelled

    -- Metrics
    records_processed BIGINT,
    records_failed BIGINT,

    -- Error handling
    error_message TEXT,
    error_stack_trace TEXT,

    -- Metadata
    triggered_by VARCHAR(100), -- scheduler, manual, api
    execution_environment VARCHAR(50) -- dev, staging, production
);

CREATE INDEX idx_monitor_pipe_name_time ON monitoring_pipeline_execution(pipeline_name, start_timestamp);
CREATE INDEX idx_monitor_pipe_status ON monitoring_pipeline_execution(status);

COMMENT ON TABLE monitoring_pipeline_execution IS 'Pipeline execution tracking and monitoring';

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Function to calculate stock status
CREATE OR REPLACE FUNCTION calculate_stock_status(
    quantity_available INTEGER,
    reorder_point INTEGER
) RETURNS VARCHAR AS $$
BEGIN
    IF quantity_available <= 0 THEN
        RETURN 'out_of_stock';
    ELSIF quantity_available <= reorder_point THEN
        RETURN 'low_stock';
    ELSIF quantity_available > reorder_point * 3 THEN
        RETURN 'overstock';
    ELSE
        RETURN 'in_stock';
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to categorize risk level based on failure probability
CREATE OR REPLACE FUNCTION categorize_risk_level(
    failure_probability NUMERIC
) RETURNS VARCHAR AS $$
BEGIN
    IF failure_probability >= 0.75 THEN
        RETURN 'critical';
    ELSIF failure_probability >= 0.50 THEN
        RETURN 'high';
    ELSIF failure_probability >= 0.25 THEN
        RETURN 'medium';
    ELSE
        RETURN 'low';
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- =============================================================================
-- INITIAL SETUP AND GRANTS
-- =============================================================================

-- Create application roles (adjust based on actual security requirements)
-- CREATE ROLE olpa_readonly;
-- CREATE ROLE olpa_readwrite;
-- CREATE ROLE olpa_etl;
-- CREATE ROLE olpa_ml;

-- Grant appropriate permissions
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO olpa_readonly;
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO olpa_readwrite;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO olpa_etl;
-- GRANT SELECT ON gold_* TO olpa_ml;

-- =============================================================================
-- MAINTENANCE TASKS
-- =============================================================================

-- Recommended periodic maintenance tasks:
-- 1. VACUUM ANALYZE daily on large tables
-- 2. REINDEX weekly on heavily updated indexes
-- 3. Refresh materialized views hourly (gold_daily_kpi_summary)
-- 4. Partition management: Create new partitions monthly, drop old partitions after retention period
-- 5. Statistics update: ANALYZE after large data loads

-- Example partition creation (template for automated partition management):
-- CREATE TABLE bronze_sensor_data_2025_10 PARTITION OF bronze_sensor_data
--     FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

-- =============================================================================
-- NOTES
-- =============================================================================
-- 1. For production deployment, enable table partitioning on time-series tables
-- 2. Adjust retention policies based on compliance requirements
-- 3. Implement encryption at rest and column-level encryption for sensitive data
-- 4. Set up automated backup and point-in-time recovery
-- 5. Monitor table bloat and implement regular maintenance
-- 6. Consider read replicas for analytics workload isolation
-- 7. Implement row-level security if multi-tenant deployment is needed

-- END OF SCHEMA DEFINITION
