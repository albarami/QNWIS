-- ============================================================================
-- QNWIS Domain-Agnostic Universal Schema
-- Supports all domains: Labor, Health, Education, Energy, Trade, Tourism, etc.
-- ============================================================================

-- Arab Development Portal Indicators Table
CREATE TABLE IF NOT EXISTS adp_indicators (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(3) NOT NULL,
    indicator_code VARCHAR(100) NOT NULL,
    indicator_name VARCHAR(300) NOT NULL,
    theme VARCHAR(100),  -- Labor, Education, Trade, Health, Energy, Tourism, etc.
    year INTEGER NOT NULL,
    value DECIMAL(20, 6),
    unit VARCHAR(50),
    source_org VARCHAR(100),  -- UN, IMF, World Bank, etc.
    source_url TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(country_code, indicator_code, year)
);

-- UN Comtrade / ESCWA Trade Data
CREATE TABLE IF NOT EXISTS trade_data (
    id SERIAL PRIMARY KEY,
    reporter_code VARCHAR(10) NOT NULL,
    reporter_name VARCHAR(100),
    partner_code VARCHAR(10) NOT NULL,
    partner_name VARCHAR(100),
    commodity_code VARCHAR(20) NOT NULL,
    commodity_desc VARCHAR(300),
    flow_code VARCHAR(5) NOT NULL,  -- M=Import, X=Export
    year INTEGER NOT NULL,
    trade_value_usd DECIMAL(20, 2),
    netweight_kg DECIMAL(20, 2),
    quantity DECIMAL(20, 2),
    quantity_unit VARCHAR(50),
    source VARCHAR(50) DEFAULT 'UN Comtrade',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(reporter_code, partner_code, commodity_code, flow_code, year)
);

-- Skills Taxonomy (from BGI Skills Compass)
CREATE TABLE IF NOT EXISTS skills_taxonomy (
    id SERIAL PRIMARY KEY,
    skill_id VARCHAR(50) NOT NULL UNIQUE,
    skill_name VARCHAR(200) NOT NULL,
    skill_category VARCHAR(100),
    skill_type VARCHAR(50),  -- technical, soft, cognitive
    demand_trend VARCHAR(20),  -- growing, stable, declining
    source VARCHAR(100),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Universal Indicator Table (Domain-Agnostic)
CREATE TABLE IF NOT EXISTS universal_indicators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain VARCHAR(50) NOT NULL,       -- 'Health', 'Energy', 'Labor', 'Trade', etc.
    indicator_code VARCHAR(100),
    indicator_name VARCHAR(255) NOT NULL,
    source VARCHAR(100) NOT NULL,      -- 'ADP', 'ESCWA', 'World Bank', etc.
    frequency VARCHAR(20),             -- 'Annual', 'Quarterly', 'Monthly'
    unit VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Universal Data Points Table (Time-Series with Quality Tracking)
CREATE TABLE IF NOT EXISTS universal_data_points (
    id SERIAL PRIMARY KEY,
    indicator_id UUID REFERENCES universal_indicators(id),
    entity_code VARCHAR(10) NOT NULL,  -- Country code (QAT, SAU, etc.)
    entity_name VARCHAR(100),
    date DATE NOT NULL,
    value DOUBLE PRECISION,
    metadata JSONB,                     -- Store extra dimensions (Gender, Age, Partner Country)
    data_version INTEGER DEFAULT 1,
    source_last_updated TIMESTAMP,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    quality_score NUMERIC(3,2),         -- 0.00-1.00 reliability score
    quality_flags JSONB,                -- {"outlier": false, "estimated": false, "preliminary": true}
    UNIQUE(indicator_id, entity_code, date, data_version)
);

-- Data Lineage Tracking (Which analyses used which data)
CREATE TABLE IF NOT EXISTS analysis_data_lineage (
    id SERIAL PRIMARY KEY,
    analysis_id UUID NOT NULL,
    analysis_type VARCHAR(50),          -- 'workflow_run', 'report', 'dashboard'
    indicator_id UUID REFERENCES universal_indicators(id),
    data_version INTEGER,
    data_point_ids INTEGER[],
    analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    query_hash VARCHAR(64),             -- Hash of original query
    metadata JSONB
);

-- Knowledge Graph Nodes (for R&D report entities)
CREATE TABLE IF NOT EXISTS knowledge_graph_nodes (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,   -- 'sector', 'skill', 'policy', 'metric', 'occupation'
    entity_name VARCHAR(200) NOT NULL,
    properties JSONB,
    source_document VARCHAR(200),
    embedding VECTOR(768),              -- For semantic similarity (requires pgvector)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_type, entity_name)
);

-- Knowledge Graph Edges (relationships)
CREATE TABLE IF NOT EXISTS knowledge_graph_edges (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES knowledge_graph_nodes(id),
    target_id INTEGER REFERENCES knowledge_graph_nodes(id),
    relationship_type VARCHAR(100) NOT NULL,  -- 'BELONGS_TO', 'AFFECTS', 'REQUIRES', 'HAS_METRIC'
    weight DECIMAL(5, 4) DEFAULT 1.0,
    source_document VARCHAR(200),
    confidence DECIMAL(3, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- R&D Reports Metadata (for RAG tracking)
CREATE TABLE IF NOT EXISTS rd_reports (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(300) NOT NULL UNIQUE,
    title VARCHAR(500),
    doc_type VARCHAR(50),               -- 'research_report', 'case_study', 'policy_analysis'
    topics TEXT[],
    total_chunks INTEGER,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    freshness DATE,
    metadata JSONB
);

-- ============================================================================
-- INDEXES for Performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_adp_country_theme ON adp_indicators(country_code, theme, year DESC);
CREATE INDEX IF NOT EXISTS idx_trade_reporter_year ON trade_data(reporter_code, year DESC);
CREATE INDEX IF NOT EXISTS idx_skills_category ON skills_taxonomy(skill_category);
CREATE INDEX IF NOT EXISTS idx_universal_indicators_domain ON universal_indicators(domain, source);
CREATE INDEX IF NOT EXISTS idx_universal_data_entity_date ON universal_data_points(entity_code, date DESC);
CREATE INDEX IF NOT EXISTS idx_universal_data_quality ON universal_data_points(quality_score DESC) WHERE quality_score IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_kg_nodes_type ON knowledge_graph_nodes(entity_type);
CREATE INDEX IF NOT EXISTS idx_kg_edges_source ON knowledge_graph_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_kg_edges_target ON knowledge_graph_edges(target_id);
CREATE INDEX IF NOT EXISTS idx_rd_reports_type ON rd_reports(doc_type);

-- ============================================================================
-- VIEWS for Easy Access
-- ============================================================================

-- Latest data points per indicator per country
CREATE OR REPLACE VIEW latest_universal_data AS
SELECT DISTINCT ON (d.indicator_id, d.entity_code)
    d.id,
    i.domain,
    i.indicator_name,
    i.source,
    d.entity_code,
    d.entity_name,
    d.date,
    d.value,
    d.quality_score,
    d.ingestion_timestamp
FROM universal_data_points d
JOIN universal_indicators i ON d.indicator_id = i.id
ORDER BY d.indicator_id, d.entity_code, d.date DESC;

-- Domain summary
CREATE OR REPLACE VIEW domain_data_summary AS
SELECT 
    i.domain,
    COUNT(DISTINCT i.id) as indicator_count,
    COUNT(DISTINCT d.entity_code) as country_count,
    MIN(d.date) as earliest_data,
    MAX(d.date) as latest_data,
    AVG(d.quality_score) as avg_quality_score,
    COUNT(d.id) as total_data_points
FROM universal_indicators i
LEFT JOIN universal_data_points d ON i.id = d.indicator_id
GROUP BY i.domain
ORDER BY indicator_count DESC;

-- Trade balance summary
CREATE OR REPLACE VIEW qatar_trade_balance AS
SELECT 
    year,
    SUM(CASE WHEN flow_code = 'X' THEN trade_value_usd ELSE 0 END) as exports_usd,
    SUM(CASE WHEN flow_code = 'M' THEN trade_value_usd ELSE 0 END) as imports_usd,
    SUM(CASE WHEN flow_code = 'X' THEN trade_value_usd ELSE 0 END) - 
    SUM(CASE WHEN flow_code = 'M' THEN trade_value_usd ELSE 0 END) as balance_usd
FROM trade_data
WHERE reporter_code = 'QAT'
GROUP BY year
ORDER BY year DESC;

