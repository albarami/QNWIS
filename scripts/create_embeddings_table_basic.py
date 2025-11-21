"""
Create document_embeddings table WITHOUT pgvector dependency
This is a proper fallback until pgvector is installed system-wide
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qnwis.data.deterministic.engine import get_engine
from sqlalchemy import text

def create_embeddings_table():
    """Create document_embeddings table using standard PostgreSQL types"""
    print("="*80)
    print("📦 CREATING DOCUMENT_EMBEDDINGS TABLE (Standard PostgreSQL)")
    print("="*80)
    
    engine = get_engine()
    
    with engine.begin() as conn:
        # Create embeddings table WITHOUT vector type
        print("\n1️⃣ Creating document_embeddings table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS document_embeddings (
                id SERIAL PRIMARY KEY,
                document_id VARCHAR(100) UNIQUE,
                source VARCHAR(50),
                chunk_text TEXT,
                embedding_json JSONB,  -- Store embedding as JSON array until pgvector installed
                metadata JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        print("   ✅ document_embeddings table created")
        
        # Create indexes
        print("\n2️⃣ Creating indexes...")
        
        # Source index for filtering
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS document_embeddings_source_idx 
            ON document_embeddings(source)
        """))
        print("   ✅ Source index created")
        
        # Document ID index
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS document_embeddings_doc_id_idx 
            ON document_embeddings(document_id)
        """))
        print("   ✅ Document ID index created")
        
        # GIN index on embedding JSON for faster lookups
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS document_embeddings_embedding_gin_idx 
            ON document_embeddings 
            USING gin (embedding_json)
        """))
        print("   ✅ JSON embedding index created")
    
    print(f"\n{'='*80}")
    print("✅ DOCUMENT_EMBEDDINGS TABLE CREATED")
    print("="*80)
    print("\nNOTE: Table uses JSONB for embeddings (standard PostgreSQL)")
    print("To upgrade to pgvector later:")
    print("1. Install pgvector extension")
    print("2. Run: ALTER TABLE document_embeddings ADD COLUMN embedding vector(1536);")
    print("3. Migrate data: UPDATE document_embeddings SET embedding = embedding_json::text::vector;")
    print("4. Drop old column: ALTER TABLE document_embeddings DROP COLUMN embedding_json;")

if __name__ == "__main__":
    create_embeddings_table()
