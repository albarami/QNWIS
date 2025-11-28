"""
NSIC Database Integration

Connects NSIC components to the REAL QNWIS PostgreSQL database.
NO MOCKS. REAL DATA ONLY.

Tables used:
- world_bank_indicators (2,431 rows)
- employment_records (1,000 rows)
- vision_2030_targets (7 rows)
- gcc_labour_statistics (6 rows)
- ilo_labour_data (6 rows)
- document_embeddings (for embedding cache)
"""

import logging
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np

logger = logging.getLogger(__name__)

# Default database URL - matches QNWIS configuration
DEFAULT_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:1234@localhost:5432/qnwis"
)


class NSICDatabase:
    """
    Database connection for NSIC components.
    
    Provides access to:
    - World Bank economic indicators
    - GCC labour statistics
    - Vision 2030 targets
    - Employment records
    - Document embeddings (for RAG)
    """
    
    def __init__(self, database_url: str = None):
        """Initialize database connection."""
        self.database_url = database_url or DEFAULT_DATABASE_URL
        self._conn = None
        logger.info(f"NSICDatabase initialized with URL: {self.database_url[:30]}...")
    
    def _get_connection(self):
        """Get or create database connection."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                self.database_url,
                cursor_factory=RealDictCursor
            )
        return self._conn
    
    def close(self):
        """Close database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
    
    # =========================================================================
    # WORLD BANK INDICATORS
    # =========================================================================
    
    def get_world_bank_indicators(
        self,
        country_code: str = None,
        indicator_code: str = None,
        year_min: int = None,
        year_max: int = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get World Bank indicators from database.
        
        Args:
            country_code: Filter by country (e.g., 'QAT', 'ARE', 'SAU')
            indicator_code: Filter by indicator
            year_min: Minimum year
            year_max: Maximum year
            limit: Maximum rows to return
            
        Returns:
            List of indicator records
        """
        conn = self._get_connection()
        cur = conn.cursor()
        
        query = "SELECT * FROM world_bank_indicators WHERE 1=1"
        params = []
        
        if country_code:
            query += " AND country_code = %s"
            params.append(country_code)
        
        if indicator_code:
            query += " AND indicator_code = %s"
            params.append(indicator_code)
        
        if year_min:
            query += " AND year >= %s"
            params.append(year_min)
        
        if year_max:
            query += " AND year <= %s"
            params.append(year_max)
        
        query += " ORDER BY year DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        return [dict(row) for row in rows]
    
    def get_qatar_indicators(self, indicator_code: str = None) -> List[Dict[str, Any]]:
        """Get Qatar-specific indicators."""
        return self.get_world_bank_indicators(
            country_code='QAT',
            indicator_code=indicator_code
        )
    
    def get_gcc_comparison(self, indicator_code: str, year: int = 2023) -> List[Dict[str, Any]]:
        """Get GCC country comparison for an indicator."""
        conn = self._get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT * FROM world_bank_indicators
            WHERE indicator_code = %s
            AND year = %s
            AND country_code IN ('QAT', 'ARE', 'SAU', 'KWT', 'BHR', 'OMN')
            ORDER BY value DESC
        """, (indicator_code, year))
        
        return [dict(row) for row in cur.fetchall()]
    
    # =========================================================================
    # VISION 2030 TARGETS
    # =========================================================================
    
    def get_vision_2030_targets(self, category: str = None) -> List[Dict[str, Any]]:
        """Get Vision 2030 targets."""
        conn = self._get_connection()
        cur = conn.cursor()
        
        if category:
            cur.execute(
                "SELECT * FROM vision_2030_targets WHERE category = %s",
                (category,)
            )
        else:
            cur.execute("SELECT * FROM vision_2030_targets")
        
        return [dict(row) for row in cur.fetchall()]
    
    def get_qatarization_progress(self) -> Dict[str, Any]:
        """Get Qatarization progress metrics."""
        targets = self.get_vision_2030_targets(category='nationalization')
        
        return {
            "public_sector": next(
                (t for t in targets if 'Public' in t['metric_name']),
                None
            ),
            "private_sector": next(
                (t for t in targets if 'Private' in t['metric_name']),
                None
            ),
        }
    
    # =========================================================================
    # GCC LABOUR STATISTICS
    # =========================================================================
    
    def get_gcc_labour_stats(self, country: str = None) -> List[Dict[str, Any]]:
        """Get GCC labour statistics."""
        conn = self._get_connection()
        cur = conn.cursor()
        
        if country:
            cur.execute(
                "SELECT * FROM gcc_labour_statistics WHERE country = %s ORDER BY year DESC, quarter DESC",
                (country,)
            )
        else:
            cur.execute("SELECT * FROM gcc_labour_statistics ORDER BY country, year DESC")
        
        return [dict(row) for row in cur.fetchall()]
    
    # =========================================================================
    # EMPLOYMENT RECORDS
    # =========================================================================
    
    def get_employment_records(
        self,
        sector: str = None,
        nationality: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get employment records."""
        conn = self._get_connection()
        cur = conn.cursor()
        
        query = "SELECT * FROM employment_records WHERE 1=1"
        params = []
        
        if sector:
            query += " AND sector = %s"
            params.append(sector)
        
        if nationality:
            query += " AND nationality = %s"
            params.append(nationality)
        
        query += " LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]
    
    # =========================================================================
    # DOCUMENT EMBEDDINGS (for RAG)
    # =========================================================================
    
    def store_embedding(
        self,
        document_id: str,
        chunk_id: str,
        text: str,
        embedding: np.ndarray,
        metadata: Dict[str, Any] = None
    ) -> int:
        """
        Store document embedding in database.
        
        Args:
            document_id: Source document identifier
            chunk_id: Chunk identifier within document
            text: Original text content
            embedding: Embedding vector as numpy array
            metadata: Additional metadata
            
        Returns:
            Inserted row ID
        """
        conn = self._get_connection()
        cur = conn.cursor()
        
        # Convert embedding to bytes for storage
        embedding_bytes = embedding.astype(np.float32).tobytes()
        
        cur.execute("""
            INSERT INTO document_embeddings 
            (document_id, chunk_id, text_content, embedding, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            document_id,
            chunk_id,
            text,
            embedding_bytes,
            psycopg2.extras.Json(metadata or {}),
            datetime.now()
        ))
        
        row_id = cur.fetchone()['id']
        conn.commit()
        
        logger.info(f"Stored embedding for {document_id}/{chunk_id}")
        return row_id
    
    def get_embedding(self, document_id: str, chunk_id: str) -> Optional[np.ndarray]:
        """Retrieve embedding from database."""
        conn = self._get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT embedding FROM document_embeddings
            WHERE document_id = %s AND chunk_id = %s
        """, (document_id, chunk_id))
        
        row = cur.fetchone()
        if row and row['embedding']:
            return np.frombuffer(row['embedding'], dtype=np.float32)
        return None
    
    def search_similar_embeddings(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for similar embeddings using cosine similarity.
        
        Note: For production, consider using pgvector extension for faster search.
        """
        conn = self._get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id, document_id, chunk_id, text_content, embedding FROM document_embeddings")
        rows = cur.fetchall()
        
        if not rows:
            return []
        
        # Compute similarities
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
        results = []
        
        for row in rows:
            if row['embedding']:
                emb = np.frombuffer(row['embedding'], dtype=np.float32)
                emb_norm = emb / (np.linalg.norm(emb) + 1e-8)
                similarity = float(np.dot(query_norm, emb_norm))
                results.append({
                    'id': row['id'],
                    'document_id': row['document_id'],
                    'chunk_id': row['chunk_id'],
                    'text': row['text_content'],
                    'similarity': similarity
                })
        
        # Sort by similarity descending
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        return results[:top_k]
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_table_stats(self) -> Dict[str, int]:
        """Get row counts for all tables."""
        conn = self._get_connection()
        cur = conn.cursor()
        
        tables = [
            'world_bank_indicators',
            'vision_2030_targets',
            'gcc_labour_statistics',
            'employment_records',
            'ilo_labour_data',
            'document_embeddings'
        ]
        
        stats = {}
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cur.fetchone()['count']
            except:
                stats[table] = 0
        
        return stats
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


def get_nsic_database() -> NSICDatabase:
    """Factory function to get NSICDatabase instance."""
    return NSICDatabase()

