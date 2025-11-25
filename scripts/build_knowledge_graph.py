"""
Build Knowledge Graph from R&D Reports.

Extracts entities and relationships from R&D reports to build a
knowledge graph for cross-domain reasoning.

Usage:
    python scripts/build_knowledge_graph.py
    python scripts/build_knowledge_graph.py --output data/knowledge_graph.json
"""

import sys
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qnwis.knowledge.graph_builder import (
    QNWISKnowledgeGraph,
    build_graph_from_documents,
    EntityType,
    RelationType,
)

logger = logging.getLogger(__name__)


def safe_print(msg: str) -> None:
    """Print with ASCII fallback for Windows console compatibility."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="ignore").decode("ascii"))


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF file."""
    try:
        import pdfplumber
        
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:20]:  # Limit to first 20 pages for efficiency
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        
        return "\n\n".join(text_parts)
        
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"pdfplumber failed for {pdf_path.name}: {e}")
    
    try:
        import fitz
        
        text_parts = []
        with fitz.open(pdf_path) as doc:
            for page in doc[:20]:  # Limit pages
                page_text = page.get_text()
                if page_text:
                    text_parts.append(page_text)
        
        return "\n\n".join(text_parts)
        
    except ImportError:
        logger.error("Neither pdfplumber nor PyMuPDF installed")
        return ""
    except Exception as e:
        logger.error(f"PyMuPDF failed for {pdf_path.name}: {e}")
        return ""


def add_qatar_context(graph: QNWISKnowledgeGraph) -> None:
    """Add Qatar-specific context to the knowledge graph."""
    
    # Add core sectors
    sectors = [
        ("Energy", {"subsectors": ["Oil", "Gas", "LNG", "Petrochemicals"]}),
        ("Finance", {"subsectors": ["Banking", "Insurance", "Investment"]}),
        ("Healthcare", {"subsectors": ["Hospitals", "Pharmaceuticals"]}),
        ("Education", {"subsectors": ["Higher Education", "Vocational Training"]}),
        ("Tourism", {"subsectors": ["Hotels", "Aviation", "Events"]}),
        ("Construction", {"subsectors": ["Real Estate", "Infrastructure"]}),
        ("Technology", {"subsectors": ["IT", "Digital", "Telecom"]}),
    ]
    
    for sector, props in sectors:
        graph.add_entity(sector, EntityType.SECTOR, properties=props)
    
    # Add key policies
    policies = [
        ("Qatar Vision 2030", {"start_year": 2008, "pillars": ["Human", "Social", "Economic", "Environmental"]}),
        ("Qatarization", {"target_sectors": ["Government", "Energy", "Finance"]}),
        ("National Development Strategy", {"phases": ["NDS1", "NDS2"]}),
    ]
    
    for policy, props in policies:
        graph.add_entity(policy, EntityType.POLICY, properties=props)
    
    # Add key metrics
    metrics = [
        ("Qatarization Rate", {"unit": "percentage", "target": 60}),
        ("GDP Per Capita", {"unit": "USD", "latest": 84500}),
        ("Unemployment Rate", {"unit": "percentage", "latest": 0.1}),
        ("Labor Force Participation", {"unit": "percentage", "latest": 88}),
        ("Foreign Worker Ratio", {"unit": "percentage", "latest": 95}),
    ]
    
    for metric, props in metrics:
        graph.add_entity(metric, EntityType.METRIC, properties=props)
    
    # Add relationships
    relationships = [
        ("Qatar Vision 2030", EntityType.POLICY, "Qatarization Rate", EntityType.METRIC, RelationType.TARGETS),
        ("Qatar Vision 2030", EntityType.POLICY, "GDP Per Capita", EntityType.METRIC, RelationType.TARGETS),
        ("Qatarization", EntityType.POLICY, "Qatarization Rate", EntityType.METRIC, RelationType.TARGETS),
        ("Energy", EntityType.SECTOR, "GDP Per Capita", EntityType.METRIC, RelationType.AFFECTS),
        ("Energy", EntityType.SECTOR, "Foreign Worker Ratio", EntityType.METRIC, RelationType.HAS_METRIC),
    ]
    
    for source, source_type, target, target_type, rel_type in relationships:
        graph.add_relationship(
            source, source_type,
            target, target_type,
            rel_type,
            weight=0.9,
            confidence=0.95
        )


def build_graph_from_pdfs(
    reports_dir: str = "R&D team summaries and reports",
    output_path: str = "data/knowledge_graph.json",
    max_files: int = None,
) -> Dict[str, Any]:
    """
    Build knowledge graph from R&D PDF reports.
    
    Args:
        reports_dir: Directory containing R&D PDF reports
        output_path: Path to save the knowledge graph
        max_files: Optional limit on number of files to process
        
    Returns:
        Summary dictionary with statistics
    """
    safe_print("=" * 80)
    safe_print("[KNOWLEDGE GRAPH] Building from R&D Reports")
    safe_print("=" * 80)
    
    reports_path = Path(reports_dir)
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    if not reports_path.exists():
        safe_print(f"[ERROR] Reports directory not found: {reports_path}")
        return {"status": "error", "message": f"Directory not found: {reports_path}"}
    
    # Find PDF files
    pdf_files = list(reports_path.glob("*.pdf"))
    
    if max_files:
        pdf_files = pdf_files[:max_files]
    
    safe_print(f"   Found {len(pdf_files)} PDF files")
    safe_print("=" * 80)
    
    # Initialize graph with Qatar context
    graph = QNWISKnowledgeGraph()
    add_qatar_context(graph)
    
    safe_print(f"\n[INIT] Added Qatar context: {graph.get_stats()['total_nodes']} nodes")
    
    # Process documents
    documents = []
    
    for i, pdf_path in enumerate(pdf_files, 1):
        safe_print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_path.name[:50]}...")
        
        try:
            text = extract_text_from_pdf(pdf_path)
            
            if text and len(text) > 100:
                documents.append({
                    "text": text,
                    "source": pdf_path.name
                })
                
                # Extract entities from this document
                entities = graph.extract_entities_from_text(text, source_document=pdf_path.name)
                safe_print(f"   [OK] Extracted {len(entities)} entities")
            else:
                safe_print(f"   [WARN] Insufficient text extracted")
                
        except Exception as e:
            safe_print(f"   [ERROR] Failed: {str(e)[:50]}")
    
    # Infer relationships
    safe_print("\n[INFER] Inferring relationships...")
    relationship_count = graph.infer_relationships()
    safe_print(f"   Added {relationship_count} inferred relationships")
    
    # Save graph
    graph.save(output_file)
    safe_print(f"\n[SAVE] Saved to {output_file}")
    
    # Summary
    stats = graph.get_stats()
    
    safe_print(f"\n{'=' * 80}")
    safe_print("[COMPLETE] Knowledge Graph Built")
    safe_print(f"{'=' * 80}")
    safe_print(f"   Total nodes: {stats['total_nodes']}")
    safe_print(f"   Total edges: {stats['total_edges']}")
    safe_print(f"   Graph density: {stats['density']:.4f}")
    safe_print(f"   Source documents: {stats['source_documents']}")
    safe_print(f"\n   Entity types:")
    for entity_type, count in sorted(stats['entity_types'].items(), key=lambda x: x[1], reverse=True):
        safe_print(f"      {entity_type}: {count}")
    safe_print(f"{'=' * 80}")
    
    return {
        "status": "success",
        "stats": stats,
        "output_path": str(output_file),
        "documents_processed": len(documents),
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="Build knowledge graph from R&D reports")
    parser.add_argument("--dir", default="R&D team summaries and reports", help="Reports directory")
    parser.add_argument("--output", default="data/knowledge_graph.json", help="Output path")
    parser.add_argument("--max-files", type=int, default=None, help="Max files to process")
    
    args = parser.parse_args()
    
    result = build_graph_from_pdfs(
        reports_dir=args.dir,
        output_path=args.output,
        max_files=args.max_files
    )
    
    if result["status"] == "success":
        safe_print(f"\n[SUCCESS] Built knowledge graph: {result['stats']['total_nodes']} nodes, {result['stats']['total_edges']} edges")
    else:
        safe_print(f"\n[ERROR] {result.get('message', 'Unknown error')}")

