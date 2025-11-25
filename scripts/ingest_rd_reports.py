"""
Ingest R&D PDF Reports into QNWIS RAG System.

Extracts text from 56+ R&D PDF reports and adds them to the document store
with proper chunking and metadata for semantic retrieval.

Reports include:
- Qatar labor landscape analysis
- Skills gap studies
- Vision 2030 implementation
- Future of jobs in AI era
- Knowledge-based economy reports
- Korea LMIS case study
- GenAI workforce impact studies
"""

import sys
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import re

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qnwis.rag.retriever import Document, DocumentStore, get_document_store

logger = logging.getLogger(__name__)


def safe_print(msg: str) -> None:
    """Print with ASCII fallback for Windows console compatibility."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="ignore").decode("ascii"))


def extract_text_from_pdf(pdf_path: Path) -> Optional[str]:
    """
    Extract text from a PDF file using pdfplumber or PyMuPDF.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Extracted text or None if extraction fails
    """
    try:
        # Try pdfplumber first (better for tables)
        import pdfplumber
        
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        
        return "\n\n".join(text_parts)
        
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"pdfplumber failed for {pdf_path.name}: {e}")
    
    # Fallback to PyMuPDF
    try:
        import fitz  # PyMuPDF
        
        text_parts = []
        with fitz.open(pdf_path) as doc:
            for page in doc:
                page_text = page.get_text()
                if page_text:
                    text_parts.append(page_text)
        
        return "\n\n".join(text_parts)
        
    except ImportError:
        logger.error("Neither pdfplumber nor PyMuPDF installed. Install with: pip install pdfplumber PyMuPDF")
        return None
    except Exception as e:
        logger.error(f"PyMuPDF failed for {pdf_path.name}: {e}")
        return None


def chunk_text(
    text: str,
    chunk_size: int = 1500,
    chunk_overlap: int = 200,
) -> List[str]:
    """
    Split text into overlapping chunks for better retrieval.
    
    Args:
        text: Full text to chunk
        chunk_size: Target size for each chunk (in characters)
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text:
        return []
    
    # Clean text
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to find sentence boundary
        if end < len(text):
            # Look for sentence end near chunk boundary
            for boundary in ['. ', '.\n', '? ', '! ', '\n\n']:
                last_boundary = text.rfind(boundary, start, end)
                if last_boundary > start + chunk_size // 2:
                    end = last_boundary + len(boundary)
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start with overlap
        start = end - chunk_overlap
        if start >= len(text):
            break
    
    return chunks


def extract_metadata_from_filename(filename: str) -> Dict[str, Any]:
    """
    Extract metadata from PDF filename.
    
    Args:
        filename: PDF filename
        
    Returns:
        Dictionary of metadata
    """
    metadata = {
        "filename": filename,
        "doc_type": "research_report",
        "source": "R&D Team",
    }
    
    # Extract date from filename
    date_patterns = [
        r'(\d{4}-\d{2}-\d{2})',  # 2025-01-02
        r'(\d{4}_\d{2}_\d{2})',  # 2025_01_02
        r'_(\d{4})\b',           # _2024 or _2023
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, filename)
        if match:
            date_str = match.group(1).replace('_', '-')
            if len(date_str) == 4:  # Just year
                metadata["year"] = date_str
                metadata["freshness"] = f"{date_str}-01-01"
            else:
                metadata["freshness"] = date_str
            break
    
    # Classify document type
    filename_lower = filename.lower()
    
    if 'genai' in filename_lower or 'ai' in filename_lower:
        metadata["doc_type"] = "ai_impact_study"
        metadata["topic"] = "generative_ai"
    elif 'skills' in filename_lower:
        metadata["doc_type"] = "skills_analysis"
        metadata["topic"] = "skills_gap"
    elif 'korea' in filename_lower or 'lmis' in filename_lower:
        metadata["doc_type"] = "case_study"
        metadata["topic"] = "lmis_best_practices"
    elif 'labor' in filename_lower or 'labour' in filename_lower:
        metadata["doc_type"] = "labor_analysis"
        metadata["topic"] = "labor_market"
    elif 'vision' in filename_lower or '2030' in filename_lower:
        metadata["doc_type"] = "strategic_planning"
        metadata["topic"] = "vision_2030"
    elif 'knowledge' in filename_lower or 'economy' in filename_lower:
        metadata["doc_type"] = "economic_analysis"
        metadata["topic"] = "knowledge_economy"
    elif 'research_report' in filename_lower:
        # Extract Q number for research report series
        q_match = re.search(r'Q(\d+)', filename)
        if q_match:
            metadata["series_number"] = int(q_match.group(1))
            metadata["doc_type"] = "quarterly_research"
            metadata["topic"] = "labor_market_research"
    
    return metadata


def generate_doc_id(pdf_path: Path, chunk_index: int) -> str:
    """Generate unique document ID for a chunk."""
    content = f"{pdf_path.name}_{chunk_index}"
    return f"rd_{hashlib.md5(content.encode()).hexdigest()[:12]}"


def ingest_pdf_to_store(
    pdf_path: Path,
    store: DocumentStore,
    chunk_size: int = 1500,
) -> int:
    """
    Ingest a single PDF into the document store.
    
    Args:
        pdf_path: Path to PDF file
        store: DocumentStore to add documents to
        chunk_size: Size of text chunks
        
    Returns:
        Number of chunks added
    """
    # Extract text
    text = extract_text_from_pdf(pdf_path)
    
    if not text or len(text) < 100:
        logger.warning(f"Insufficient text extracted from {pdf_path.name}")
        return 0
    
    # Extract metadata
    metadata = extract_metadata_from_filename(pdf_path.name)
    
    # Chunk text
    chunks = chunk_text(text, chunk_size=chunk_size)
    
    if not chunks:
        logger.warning(f"No chunks generated from {pdf_path.name}")
        return 0
    
    # Create documents for each chunk
    documents = []
    for i, chunk in enumerate(chunks):
        doc_id = generate_doc_id(pdf_path, i)
        
        # Add chunk context to metadata
        chunk_metadata = metadata.copy()
        chunk_metadata["chunk_index"] = i
        chunk_metadata["total_chunks"] = len(chunks)
        chunk_metadata["file_path"] = str(pdf_path)
        
        doc = Document(
            doc_id=doc_id,
            text=chunk,
            source=f"R&D Report: {pdf_path.name}",
            metadata=chunk_metadata,
            freshness=metadata.get("freshness", datetime.utcnow().strftime("%Y-%m-%d")),
            doc_type=metadata.get("doc_type", "research_report")
        )
        documents.append(doc)
    
    # Batch add to store
    store.add_documents(documents)
    
    return len(documents)


def ingest_all_rd_reports(
    reports_dir: str = "R&D team summaries and reports",
    chunk_size: int = 1500,
    max_files: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Ingest all R&D PDF reports into the RAG document store.
    
    Args:
        reports_dir: Directory containing R&D PDF reports
        chunk_size: Size of text chunks
        max_files: Optional limit on number of files to process
        
    Returns:
        Summary dictionary with statistics
    """
    safe_print("=" * 80)
    safe_print("[RAG INGESTION] R&D PDF Reports -> Document Store")
    safe_print("=" * 80)
    
    reports_path = Path(reports_dir)
    
    if not reports_path.exists():
        safe_print(f"[ERROR] Reports directory not found: {reports_path}")
        return {"status": "error", "message": f"Directory not found: {reports_path}"}
    
    # Find all PDF files
    pdf_files = list(reports_path.glob("*.pdf"))
    
    if max_files:
        pdf_files = pdf_files[:max_files]
    
    safe_print(f"   Found {len(pdf_files)} PDF files")
    safe_print(f"   Chunk size: {chunk_size} characters")
    safe_print("=" * 80)
    
    # Get document store
    store = get_document_store()
    initial_count = len(store.documents)
    
    total_chunks = 0
    successful_files = 0
    failed_files = []
    doc_types = {}
    
    for i, pdf_path in enumerate(pdf_files, 1):
        safe_print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_path.name[:60]}...")
        
        try:
            chunks_added = ingest_pdf_to_store(pdf_path, store, chunk_size)
            
            if chunks_added > 0:
                safe_print(f"   [OK] Added {chunks_added} chunks")
                total_chunks += chunks_added
                successful_files += 1
                
                # Track document types
                metadata = extract_metadata_from_filename(pdf_path.name)
                doc_type = metadata.get("doc_type", "unknown")
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            else:
                safe_print(f"   [WARN] No chunks extracted")
                failed_files.append(pdf_path.name)
                
        except Exception as e:
            safe_print(f"   [ERROR] Failed: {str(e)[:50]}")
            failed_files.append(pdf_path.name)
    
    # Summary
    final_count = len(store.documents)
    
    safe_print(f"\n{'=' * 80}")
    safe_print("[COMPLETE] R&D Report Ingestion Finished")
    safe_print(f"{'=' * 80}")
    safe_print(f"   Files processed: {successful_files}/{len(pdf_files)}")
    safe_print(f"   Total chunks added: {total_chunks}")
    safe_print(f"   Document store: {initial_count} -> {final_count} documents")
    safe_print(f"\n   Document types:")
    for doc_type, count in sorted(doc_types.items(), key=lambda x: x[1], reverse=True):
        safe_print(f"      {doc_type}: {count} files")
    
    if failed_files:
        safe_print(f"\n   [WARN] Failed files ({len(failed_files)}):")
        for f in failed_files[:5]:
            safe_print(f"      - {f[:50]}")
        if len(failed_files) > 5:
            safe_print(f"      ... and {len(failed_files) - 5} more")
    
    safe_print(f"{'=' * 80}")
    
    return {
        "status": "success",
        "files_processed": successful_files,
        "files_total": len(pdf_files),
        "chunks_added": total_chunks,
        "document_store_size": final_count,
        "doc_types": doc_types,
        "failed_files": failed_files
    }


if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="Ingest R&D PDF reports into RAG system")
    parser.add_argument("--dir", default="R&D team summaries and reports", help="Reports directory")
    parser.add_argument("--chunk-size", type=int, default=1500, help="Chunk size in characters")
    parser.add_argument("--max-files", type=int, default=None, help="Max files to process")
    
    args = parser.parse_args()
    
    result = ingest_all_rd_reports(
        reports_dir=args.dir,
        chunk_size=args.chunk_size,
        max_files=args.max_files
    )
    
    if result["status"] == "success":
        safe_print(f"\n[SUCCESS] Ingested {result['chunks_added']} chunks from {result['files_processed']} files")
    else:
        safe_print(f"\n[ERROR] {result.get('message', 'Unknown error')}")

