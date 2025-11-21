"""
Migrate existing in-memory DocumentStore embeddings to PostgreSQL pgvector
Uses EXISTING PostgreSQL - no separate ChromaDB
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qnwis.rag.retriever import get_document_store
from qnwis.data.deterministic.engine import get_engine
from sqlalchemy import text
import json
import numpy as np

def migrate_embeddings():
    """Move embeddings from memory to PostgreSQL"""
    print("="*80)
    print("📦 MIGRATING EMBEDDINGS TO POSTGRESQL")
    print("="*80)
    
    # Get existing in-memory store
    try:
        doc_store = get_document_store()
    except Exception as e:
        print(f"⚠️  Could not access document store: {e}")
        print("Note: This is normal if no embeddings have been created yet")
        return
    
    engine = get_engine()
    
    total_migrated = 0
    
    # Check if documents is a list or dict
    documents = doc_store.documents if hasattr(doc_store, 'documents') else []
    
    if not documents:
        print("⚠️  No documents found in document store")
        print("Note: Embeddings will be created when RAG system is first used")
        return
    
    with engine.begin() as conn:
        for doc in documents:
            # Handle both dict and object formats
            if isinstance(doc, dict):
                embedding = doc.get('embedding')
                doc_id = doc.get('doc_id') or doc.get('id')
                source = doc.get('source', 'unknown')
                text = doc.get('text', '')
                metadata = doc.get('metadata', {})
            elif hasattr(doc, 'embedding'):
                embedding = doc.embedding
                doc_id = doc.doc_id
                source = doc.source
                text = doc.text
                metadata = doc.metadata
            else:
                continue
            
            if embedding is not None:
                # Convert numpy array to list for PostgreSQL
                embedding_list = embedding.tolist() if isinstance(embedding, np.ndarray) else embedding
                
                conn.execute(
                    text("""
                        INSERT INTO document_embeddings 
                        (document_id, source, chunk_text, embedding_json, metadata)
                        VALUES (:doc_id, :source, :text, :embedding, :metadata)
                        ON CONFLICT (document_id) DO UPDATE SET
                            embedding_json = EXCLUDED.embedding_json,
                            chunk_text = EXCLUDED.chunk_text,
                            metadata = EXCLUDED.metadata
                    """),
                    {
                        "doc_id": doc_id,
                        "source": source,
                        "text": text,
                        "embedding": json.dumps(embedding_list),  # Store as JSON
                        "metadata": json.dumps(metadata) if isinstance(metadata, dict) else metadata
                    }
                )
                total_migrated += 1
                
                if total_migrated % 100 == 0:
                    print(f"   Migrated {total_migrated} documents...")
    
    print(f"\n{'='*80}")
    print(f"✅ Migrated {total_migrated} documents to PostgreSQL")
    print(f"{'='*80}")

if __name__ == "__main__":
    migrate_embeddings()
