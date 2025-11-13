-- QNWIS Database Schema
-- Qatar National Workforce Intelligence System
-- Created: November 2025

-- ============================================================================
-- EMPLOYMENT RECORDS (Main LMIS Data)
-- ============================================================================

CREATE TABLE IF NOT EXISTS employment_records (
    id BIGSERIAL PRIMARY KEY,
    person_id VARCHAR(50) NOT NULL,
    company_id VARCHAR(50) NOT NULL,
    month DATE NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('employed', 'unemployed', 'inactive')),
    nationality VARCHAR(50) NOT NULL,
    gender VARCHAR(10) NOT NULL CHECK (gender IN ('Male', 'Female')),
    age INTEGER CHECK (age >= 15 AND age <= 80),
    education_level VARCHAR(50),
    sector VARCHAR(100),
    job_title VARCHAR(200),
    salary_qar DECIMAL(12, 2) CHECK (salary_qar >= 0),
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CHECK (end_date IS NULL OR end_date >= start_date),
    CHECK (month >= DATE '2000-01-01')
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_employment_month ON employment_records(month);
CREATE INDEX IF NOT EXISTS idx_employment_nationality ON employment_records(nationality);
CREATE INDEX IF NOT EXISTS idx_employment_sector ON employment_records(sector);
CREATE INDEX IF NOT EXISTS idx_employment_status ON employment_records(status);
CREATE INDEX IF NOT EXISTS idx_employment_company ON employment_records(company_id);
CREATE INDEX IF NOT EXISTS idx_employment_person_month ON employment_records(person_id, month);
CREATE INDEX IF NOT EXISTS idx_employment_gender ON employment_records(gender);
CREATE INDEX IF NOT EXISTS idx_employment_education ON employment_records(education_level);

-- ============================================================================
-- GCC LABOUR STATISTICS (Regional Benchmarking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS gcc_labour_statistics (
    id SERIAL PRIMARY KEY,
    country VARCHAR(50) NOT NULL,
    year INTEGER NOT NULL CHECK (year >= 2000 AND year <= 2100),
    quarter INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    unemployment_rate DECIMAL(5, 2) CHECK (unemployment_rate >= 0 AND unemployment_rate <= 100),
    labor_force_participation DECIMAL(5, 2) CHECK (labor_force_participation >= 0 AND labor_force_participation <= 100),
    population_working_age BIGINT CHECK (population_working_age >= 0),
    youth_unemployment_rate DECIMAL(5, 2),
    female_labor_participation DECIMAL(5, 2),
    source VARCHAR(100),
    source_url TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(country, year, quarter)
);

CREATE INDEX IF NOT EXISTS idx_gcc_country_year ON gcc_labour_statistics(country, year DESC, quarter DESC);
CREATE INDEX IF NOT EXISTS idx_gcc_year_quarter ON gcc_labour_statistics(year DESC, quarter DESC);

-- ============================================================================
-- VISION 2030 TARGETS (National Strategic Goals)
-- ============================================================================

CREATE TABLE IF NOT EXISTS vision_2030_targets (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    target_value DECIMAL(10, 2) NOT NULL,
    target_year INTEGER NOT NULL CHECK (target_year >= 2020 AND target_year <= 2050),
    current_value DECIMAL(10, 2),
    baseline_value DECIMAL(10, 2),
    baseline_year INTEGER,
    last_measured DATE,
    unit VARCHAR(20),
    category VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(metric_name, target_year)
);

CREATE INDEX IF NOT EXISTS idx_vision_category ON vision_2030_targets(category);
CREATE INDEX IF NOT EXISTS idx_vision_year ON vision_2030_targets(target_year);

-- ============================================================================
-- ILO LABOUR STANDARDS (International Labour Organization Data)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ilo_labour_data (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(3) NOT NULL,
    country_name VARCHAR(100) NOT NULL,
    indicator_code VARCHAR(100) NOT NULL,
    indicator_name VARCHAR(200) NOT NULL,
    year INTEGER NOT NULL CHECK (year >= 1990 AND year <= 2100),
    value DECIMAL(15, 4),
    sex VARCHAR(20),
    age_group VARCHAR(50),
    education_level VARCHAR(100),
    source VARCHAR(100) DEFAULT 'ILO',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(country_code, indicator_code, year, sex, age_group, education_level)
);

CREATE INDEX IF NOT EXISTS idx_ilo_country_year ON ilo_labour_data(country_code, year DESC);
CREATE INDEX IF NOT EXISTS idx_ilo_indicator ON ilo_labour_data(indicator_code);
CREATE INDEX IF NOT EXISTS idx_ilo_country_indicator ON ilo_labour_data(country_code, indicator_code, year DESC);

-- ============================================================================
-- WORLD BANK INDICATORS (Economic Context)
-- ============================================================================

CREATE TABLE IF NOT EXISTS world_bank_indicators (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(3) NOT NULL,
    country_name VARCHAR(100) NOT NULL,
    indicator_code VARCHAR(100) NOT NULL,
    indicator_name VARCHAR(300) NOT NULL,
    year INTEGER NOT NULL CHECK (year >= 1960 AND year <= 2100),
    value DECIMAL(20, 6),
    unit VARCHAR(50),
    source VARCHAR(100) DEFAULT 'World Bank',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(country_code, indicator_code, year)
);

CREATE INDEX IF NOT EXISTS idx_wb_country_year ON world_bank_indicators(country_code, year DESC);
CREATE INDEX IF NOT EXISTS idx_wb_indicator ON world_bank_indicators(indicator_code);
CREATE INDEX IF NOT EXISTS idx_wb_country_indicator ON world_bank_indicators(country_code, indicator_code, year DESC);

-- ============================================================================
-- QATAR OPEN DATA (National Statistics)
-- ============================================================================

CREATE TABLE IF NOT EXISTS qatar_open_data (
    id SERIAL PRIMARY KEY,
    dataset_id VARCHAR(100) NOT NULL,
    dataset_name VARCHAR(200) NOT NULL,
    category VARCHAR(100),
    indicator_name VARCHAR(300) NOT NULL,
    time_period VARCHAR(50) NOT NULL,
    value DECIMAL(20, 6),
    unit VARCHAR(50),
    gender VARCHAR(20),
    nationality VARCHAR(50),
    age_group VARCHAR(50),
    metadata JSONB,
    source_url TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_qod_dataset ON qatar_open_data(dataset_id);
CREATE INDEX IF NOT EXISTS idx_qod_category ON qatar_open_data(category);
CREATE INDEX IF NOT EXISTS idx_qod_time ON qatar_open_data(time_period);
CREATE INDEX IF NOT EXISTS idx_qod_metadata ON qatar_open_data USING gin(metadata);

-- ============================================================================
-- QUERY AUDIT LOG (System Monitoring)
-- ============================================================================

CREATE TABLE IF NOT EXISTS query_audit_log (
    id BIGSERIAL PRIMARY KEY,
    query_id VARCHAR(100) NOT NULL,
    executed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER CHECK (execution_time_ms >= 0),
    row_count INTEGER CHECK (row_count >= 0),
    cache_hit BOOLEAN DEFAULT FALSE,
    user_id VARCHAR(100),
    session_id VARCHAR(100),
    ip_address VARCHAR(45),
    parameters JSONB,
    error_message TEXT,
    status VARCHAR(20) DEFAULT 'success' CHECK (status IN ('success', 'error', 'timeout'))
);

CREATE INDEX IF NOT EXISTS idx_audit_query_executed ON query_audit_log(query_id, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_executed_at ON query_audit_log(executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user ON query_audit_log(user_id, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_status ON query_audit_log(status, executed_at DESC);

-- ============================================================================
-- DATA FRESHNESS TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS data_freshness_log (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(100) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    last_successful_fetch TIMESTAMP,
    last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    record_count INTEGER,
    fetch_status VARCHAR(20) CHECK (fetch_status IN ('success', 'failed', 'partial')),
    error_message TEXT,
    next_scheduled_fetch TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(source_name, source_type)
);

CREATE INDEX IF NOT EXISTS idx_freshness_source ON data_freshness_log(source_name);
CREATE INDEX IF NOT EXISTS idx_freshness_status ON data_freshness_log(fetch_status, last_attempt DESC);

-- ============================================================================
-- MATERIALIZED VIEWS FOR PERFORMANCE
-- ============================================================================

-- Monthly employment summary
CREATE MATERIALIZED VIEW IF NOT EXISTS employment_summary_monthly AS
SELECT
    month,
    nationality,
    gender,
    sector,
    status,
    COUNT(*) as employee_count,
    AVG(salary_qar) as avg_salary,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary_qar) as median_salary,
    COUNT(DISTINCT company_id) as company_count,
    COUNT(DISTINCT person_id) as person_count
FROM employment_records
GROUP BY month, nationality, gender, sector, status;

CREATE INDEX IF NOT EXISTS idx_emp_summary_month ON employment_summary_monthly (month DESC, nationality);
CREATE INDEX IF NOT EXISTS idx_emp_summary_sector ON employment_summary_monthly (sector, month DESC);

-- Qatarization summary by sector
CREATE MATERIALIZED VIEW IF NOT EXISTS qatarization_summary AS
SELECT
    month,
    sector,
    COUNT(CASE WHEN nationality = 'Qatari' THEN 1 END) as qatari_count,
    COUNT(*) as total_count,
    COUNT(CASE WHEN nationality = 'Qatari' THEN 1 END)::DECIMAL / 
        NULLIF(COUNT(*), 0) * 100 as qatarization_rate,
    AVG(CASE WHEN nationality = 'Qatari' THEN salary_qar END) as avg_qatari_salary,
    AVG(CASE WHEN nationality != 'Qatari' THEN salary_qar END) as avg_expat_salary
FROM employment_records
WHERE status = 'employed'
  AND sector IS NOT NULL
GROUP BY month, sector;

CREATE INDEX IF NOT EXISTS idx_qatar_summary_sector ON qatarization_summary (sector, month DESC);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to refresh all materialized views
CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW employment_summary_monthly;
    REFRESH MATERIALIZED VIEW qatarization_summary;
END;
$$ LANGUAGE plpgsql;

-- Function to log query execution
CREATE OR REPLACE FUNCTION log_query_execution(
    p_query_id VARCHAR,
    p_execution_time_ms INTEGER,
    p_row_count INTEGER,
    p_cache_hit BOOLEAN DEFAULT FALSE,
    p_user_id VARCHAR DEFAULT NULL,
    p_parameters JSONB DEFAULT NULL
)
RETURNS BIGINT AS $$
DECLARE
    v_log_id BIGINT;
BEGIN
    INSERT INTO query_audit_log (
        query_id, execution_time_ms, row_count, cache_hit, user_id, parameters
    ) VALUES (
        p_query_id, p_execution_time_ms, p_row_count, p_cache_hit, p_user_id, p_parameters
    ) RETURNING id INTO v_log_id;
    
    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- INITIAL DATA VALIDATION
-- ============================================================================

COMMENT ON TABLE employment_records IS 'Core LMIS employment data - main workforce tracking table';
COMMENT ON TABLE gcc_labour_statistics IS 'GCC regional labour market statistics for benchmarking';
COMMENT ON TABLE vision_2030_targets IS 'Qatar Vision 2030 strategic workforce targets';
COMMENT ON TABLE ilo_labour_data IS 'International Labour Organization standards and indicators';
COMMENT ON TABLE world_bank_indicators IS 'World Bank economic and development indicators';
COMMENT ON TABLE qatar_open_data IS 'Qatar national statistics from open data portal';
COMMENT ON TABLE query_audit_log IS 'System audit log for query execution monitoring';
COMMENT ON TABLE data_freshness_log IS 'Tracking of external data source updates';

-- Grant permissions (adjust as needed for production)
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO qnwis_readonly;
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO qnwis_app;

-- Schema version
CREATE TABLE IF NOT EXISTS schema_version (
    version VARCHAR(20) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_version (version, description) VALUES
    ('1.0.0', 'Initial QNWIS database schema with C4 implementation')
ON CONFLICT (version) DO NOTHING;

-- Completion marker
DO $$
BEGIN
    RAISE NOTICE '✅ QNWIS Database Schema Created Successfully';
    RAISE NOTICE '   Tables: employment_records, gcc_labour_statistics, vision_2030_targets, ';
    RAISE NOTICE '           ilo_labour_data, world_bank_indicators, qatar_open_data';
    RAISE NOTICE '   Views: employment_summary_monthly, qatarization_summary';
    RAISE NOTICE '   Ready for data loading';
END $$;
