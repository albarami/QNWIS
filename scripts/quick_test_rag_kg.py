"""Quick test to verify RAG and KG are working."""
import os
import sys
from pathlib import Path

# Load env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ.setdefault(k, v)

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.qnwis.agents.research_synthesizer import ResearchSynthesizerAgent

# Initialize - should auto-load RAG and KG
print("Initializing ResearchSynthesizerAgent...")
agent = ResearchSynthesizerAgent()

print("\n" + "="*60)
print("TESTING RAG (R&D Papers)")
print("="*60)
if agent.rag_client:
    results = agent.rag_client.search('labor market skills gap Qatar', top_k=5)
    print(f"✅ RAG found {len(results)} results")
    for r in results[:3]:
        title = r.get("title", "Unknown")[:60]
        print(f"  - {title}...")
else:
    print("❌ RAG not available")

print("\n" + "="*60)
print("TESTING KNOWLEDGE GRAPH")
print("="*60)
if agent.kg_client:
    results = agent.kg_client.query('employment workforce')
    print(f"✅ KG found {len(results)} relationships")
    for r in results[:3]:
        subj = r.get("subject", "?")
        obj = r.get("object", "?")
        rel = r.get("relation_type", "->")
        print(f"  - {subj} [{rel}] {obj}")
else:
    print("❌ KG not available")

print("\n" + "="*60)
print("FULL SYNTHESIS TEST")
print("="*60)
query = "What are the key skills gaps in Qatar's workforce?"
print(f"Query: {query}")

synthesis = agent.run(query=query)

print(f"\n📚 SOURCES:")
for source in ["semantic_scholar", "rag", "perplexity", "knowledge_graph"]:
    count = len([f for f in synthesis.findings if f.source == source])
    icon = "✅" if count > 0 else "⚠️"
    print(f"  {icon} {source}: {count} findings")

print(f"\n📝 NARRATIVE LENGTH: {len(synthesis.narrative)} characters")
print(f"📊 CONFIDENCE: {synthesis.confidence_level}")

# Check narrative content
if len(synthesis.narrative) > 500:
    print("\n📄 NARRATIVE PREVIEW (first 800 chars):")
    print("-" * 60)
    print(synthesis.narrative[:800])
    print("-" * 60)

