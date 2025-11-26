"""
Setup pgvector extension and create document_embeddings table
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qnwis.data.deterministic.engine import get_engine
from sqlalchemy import text

def setup_pgvector():
    """Create pgvector extension and document_embeddings table"""
    print("="*80)
    print("📦 SETTING UP PGVECTOR IN POSTGRESQL")
    print("="*80)
    
    engine = get_engine()
    
    with engine.begin() as conn:
        # Add vector extension
        print("\n1️⃣ Adding pgvector extension...")
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            print("   ✅ pgvector extension added")
        except Exception as e:
            print(f"   ⚠️  pgvector extension: {e}")
            print("   Note: pgvector may need to be installed system-wide first")
        
        # Create embeddings table
        print("\n2️⃣ Creating document_embeddings table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS document_embeddings (
                id SERIAL PRIMARY KEY,
                document_id VARCHAR(100) UNIQUE,
                source VARCHAR(50),
                chunk_text TEXT,
                embedding vector(1536),
                metadata JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        print("   ✅ document_embeddings table created")
        
        # Create index for fast similarity search
        print("\n3️⃣ Creating similarity search index...")
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS document_embeddings_embedding_idx 
                ON document_embeddings 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """))
            print("   ✅ Similarity search index created")
        except Exception as e:
            print(f"   ⚠️  Index creation: {e}")
            print("   Note: Index will be created when pgvector extension is available")
        
        # Create source index
        print("\n4️⃣ Creating source index...")
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS document_embeddings_source_idx 
            ON document_embeddings(source)
        """))
        print("   ✅ Source index created")
    
    print(f"\n{'='*80}")
    print("✅ PGVECTOR SETUP COMPLETE")
    print(f"{'='*80}")

if __name__ == "__main__":
    setup_pgvector()
