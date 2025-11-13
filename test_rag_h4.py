"""Test script for H4 RAG implementation."""

import sys
import asyncio
sys.path.insert(0, 'src')

from qnwis.rag.retriever import (
    Document,
    DocumentStore,
    SimpleEmbedder,
    get_document_store,
    retrieve_external_context,
    format_rag_context_for_prompt
)

def test_basic_components():
    """Test basic RAG components."""
    print("=" * 60)
    print("TEST 1: Basic Components")
    print("=" * 60)
    
    # Test Document
    doc = Document(
        doc_id="test_doc",
        text="Qatar has the lowest unemployment rate in the GCC region",
        source="Test Source",
        freshness="2025-11-13"
    )
    print(f"✅ Document created: {doc.doc_id}")
    print(f"   Text: {doc.text[:50]}...")
    
    # Test SimpleEmbedder
    embedder = SimpleEmbedder()
    tokens = embedder.embed_text("unemployment rate Qatar")
    print(f"✅ Embedder tokenized: {len(tokens)} tokens")
    print(f"   Tokens: {tokens[:5]}")
    
    # Test similarity
    query_tokens = embedder.embed_text("unemployment")
    doc_tokens = embedder.embed_text("Qatar unemployment rate")
    score = embedder.compute_similarity(query_tokens, doc_tokens)
    print(f"✅ Similarity score: {score:.3f}")
    
    print()
    return True

def test_document_store():
    """Test DocumentStore functionality."""
    print("=" * 60)
    print("TEST 2: Document Store")
    print("=" * 60)
    
    store = DocumentStore()
    print(f"✅ DocumentStore created with TTL: {store.cache_ttl}")
    
    # Add test documents
    docs = [
        Document("doc1", "Unemployment rates in Qatar are among lowest in GCC", "Test1"),
        Document("doc2", "GCC regional labour market statistics", "Test2"),
        Document("doc3", "Qatar Vision 2030 workforce development goals", "Test3"),
    ]
    store.add_documents(docs)
    print(f"✅ Added {len(docs)} documents")
    
    # Test search
    results = store.search("unemployment Qatar", top_k=2, min_score=0.1)
    print(f"✅ Search for 'unemployment Qatar': {len(results)} results")
    for i, (doc, score) in enumerate(results, 1):
        print(f"   {i}. {doc.doc_id}: {score:.3f} - {doc.text[:40]}...")
    
    # Test stats
    stats = store.get_stats()
    print(f"✅ Store stats: {stats['total_documents']} documents")
    
    print()
    return len(results) > 0

def test_knowledge_base():
    """Test pre-initialized knowledge base."""
    print("=" * 60)
    print("TEST 3: Knowledge Base Initialization")
    print("=" * 60)
    
    store = get_document_store()
    print(f"✅ Global document store retrieved")
    
    stats = store.get_stats()
    print(f"✅ Knowledge base initialized:")
    print(f"   Total documents: {stats['total_documents']}")
    print(f"   Sources: {list(stats['sources'].keys())}")
    print(f"   Freshness range: {stats['oldest_freshness']} to {stats['newest_freshness']}")
    
    # Test search on initialized KB
    results = store.search("GCC unemployment comparison", top_k=3)
    print(f"✅ Search 'GCC unemployment': {len(results)} results")
    for i, (doc, score) in enumerate(results, 1):
        print(f"   {i}. [{score:.3f}] {doc.doc_id} ({doc.source})")
    
    print()
    return stats['total_documents'] >= 6

async def test_rag_retrieval():
    """Test full RAG retrieval."""
    print("=" * 60)
    print("TEST 4: RAG Retrieval")
    print("=" * 60)
    
    # Test 1: GCC query
    result1 = await retrieve_external_context(
        "How does Qatar compare to other GCC countries on unemployment?",
        max_snippets=2
    )
    print(f"✅ GCC Query:")
    print(f"   Retrieved: {result1['metadata']['snippet_count']} snippets")
    print(f"   Sources: {result1['sources']}")
    if result1['snippets']:
        print(f"   Top relevance: {result1['snippets'][0]['relevance_score']:.3f}")
    
    # Test 2: Qatarization query
    result2 = await retrieve_external_context(
        "What are Qatar's Vision 2030 workforce targets?",
        max_snippets=2
    )
    print(f"✅ Vision 2030 Query:")
    print(f"   Retrieved: {result2['metadata']['snippet_count']} snippets")
    print(f"   Sources: {result2['sources']}")
    
    # Test 3: General employment query
    result3 = await retrieve_external_context(
        "unemployment trends and labour market indicators",
        max_snippets=3
    )
    print(f"✅ General Query:")
    print(f"   Retrieved: {result3['metadata']['snippet_count']} snippets")
    print(f"   Sources: {result3['sources']}")
    
    print()
    return result1['metadata']['snippet_count'] > 0

async def test_prompt_formatting():
    """Test RAG context formatting for prompts."""
    print("=" * 60)
    print("TEST 5: Prompt Formatting")
    print("=" * 60)
    
    result = await retrieve_external_context(
        "Qatar unemployment and GCC comparison",
        max_snippets=2
    )
    
    formatted = format_rag_context_for_prompt(result)
    print(f"✅ Formatted context for prompt:")
    print(formatted[:300] + "...")
    
    print()
    return len(formatted) > 0

async def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("TESTING H4 RAG IMPLEMENTATION")
    print("=" * 60 + "\n")
    
    results = []
    
    try:
        results.append(("Basic Components", test_basic_components()))
        results.append(("Document Store", test_document_store()))
        results.append(("Knowledge Base", test_knowledge_base()))
        results.append(("RAG Retrieval", await test_rag_retrieval()))
        results.append(("Prompt Formatting", await test_prompt_formatting()))
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(r[1] for r in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED - H4 RAG IS WORKING CORRECTLY")
    else:
        print("❌ SOME TESTS FAILED - NEEDS FIXES")
    print("=" * 60 + "\n")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
