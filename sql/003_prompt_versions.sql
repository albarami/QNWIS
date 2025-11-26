-- Migration: Add prompt_versions table
-- Created: 2024-11-26
-- Description: Stores versioned prompts with performance scoring for A/B testing

CREATE TABLE IF NOT EXISTS prompt_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name VARCHAR(100) NOT NULL,
    prompt_type VARCHAR(50) NOT NULL DEFAULT 'system',
    version INTEGER NOT NULL DEFAULT 1,
    content TEXT NOT NULL,
    provider VARCHAR(50) NOT NULL DEFAULT 'universal',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT FALSE,
    performance_score NUMERIC(4,2),
    metadata JSONB DEFAULT '{}',
    
    -- Ensure unique version per agent/type/provider combination
    CONSTRAINT unique_prompt_version 
        UNIQUE (agent_name, prompt_type, provider, version)
);

-- Index for fast active prompt lookups
CREATE INDEX IF NOT EXISTS idx_prompt_versions_active 
    ON prompt_versions (agent_name, prompt_type, provider) 
    WHERE is_active = TRUE;

-- Index for version history queries
CREATE INDEX IF NOT EXISTS idx_prompt_versions_history 
    ON prompt_versions (agent_name, prompt_type, provider, version DESC);

-- Index for performance comparison queries
CREATE INDEX IF NOT EXISTS idx_prompt_versions_performance 
    ON prompt_versions (agent_name, performance_score DESC NULLS LAST) 
    WHERE performance_score IS NOT NULL;

-- Comments
COMMENT ON TABLE prompt_versions IS 'Stores versioned prompts for agents with A/B testing support';
COMMENT ON COLUMN prompt_versions.agent_name IS 'Name of the agent using this prompt';
COMMENT ON COLUMN prompt_versions.prompt_type IS 'Type of prompt: system, user_template, few_shot';
COMMENT ON COLUMN prompt_versions.version IS 'Version number (increments per agent/type/provider)';
COMMENT ON COLUMN prompt_versions.content IS 'The actual prompt content';
COMMENT ON COLUMN prompt_versions.provider IS 'Target LLM provider: anthropic, azure, openai, universal';
COMMENT ON COLUMN prompt_versions.is_active IS 'Whether this version is currently active';
COMMENT ON COLUMN prompt_versions.performance_score IS 'Performance score from A/B testing (0.00-1.00)';
COMMENT ON COLUMN prompt_versions.metadata IS 'Additional metadata (e.g., test results, notes)';

