-- Add pgvector extension to EXISTING PostgreSQL
-- No separate ChromaDB - use existing infrastructure

-- Add vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create embeddings table in EXISTING database
CREATE TABLE IF NOT EXISTS document_embeddings (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(100) UNIQUE,
    source VARCHAR(50),
    chunk_text TEXT,
    embedding vector(1536),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for fast similarity search
CREATE INDEX IF NOT EXISTS document_embeddings_embedding_idx 
ON document_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create index for source filtering
CREATE INDEX IF NOT EXISTS document_embeddings_source_idx 
ON document_embeddings(source);

COMMENT ON TABLE document_embeddings IS 'Vector embeddings for RAG retrieval - uses EXISTING PostgreSQL';
COMMENT ON COLUMN document_embeddings.embedding IS 'OpenAI ada-002 embeddings (1536 dimensions)';
