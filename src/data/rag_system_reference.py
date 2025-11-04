#!/usr/bin/env python3
"""
Phase 2.2: RAG (Retrieval-Augmented Generation) System

Complete pipeline:
Query → Embedding → ChromaDB Search → Context Assembly → LLM Answer

Components:
1. Query embedding function
2. ChromaDB retrieval function
3. Context assembly
4. LLM integration (GPT-3.5-turbo)
5. End-to-end RAG pipeline
6. Testing with sample queries
"""

import os
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer

# Load environment variables from .env file
project_root = Path(__file__).parent.parent
env_file = project_root / '.env'
load_dotenv(env_file)

# Configuration
CHROMADB_PATH = str(project_root / 'chromadb_data')
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
LLM_MODEL = 'gpt-3.5-turbo'  # Balance of quality and cost
DEFAULT_TOP_K = 5

# Initialize components
print("Initializing RAG System...")
print("-" * 80)

# ChromaDB client
chroma_client = chromadb.PersistentClient(
    path=CHROMADB_PATH,
    settings=Settings(anonymized_telemetry=False)
)

# Collections
qatar_collection = chroma_client.get_collection("qatar_open_data")
corporate_collection = chroma_client.get_collection("corporate_intelligence")

# Embedding model
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

# OpenAI client (conditional)
openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key:
    openai_client = OpenAI(api_key=openai_api_key)
    openai_available = True
else:
    openai_client = None
    openai_available = False

print("✓ ChromaDB client connected")
print("✓ Collections loaded (qatar_open_data, corporate_intelligence)")
print("✓ Embedding model loaded (all-MiniLM-L6-v2)")
if openai_available:
    print("✓ OpenAI client initialized (GPT-3.5-turbo)")
else:
    print("⚠️  OpenAI API key not found (retrieval-only mode)")
print()


# ============================================================================
# 1. Query Embedding Function
# ============================================================================

def embed_query(query: str) -> list[float]:
    """
    Convert query text to embedding vector

    Args:
        query: User's natural language query

    Returns:
        384-dimensional embedding vector
    """
    embedding = embedding_model.encode(query)
    return embedding.tolist()


# ============================================================================
# 2. ChromaDB Retrieval Function
# ============================================================================

def retrieve_datasets(
    query: str,
    category: str | None = None,
    top_k: int = DEFAULT_TOP_K,
    source_type: str | None = 'qatar_open_data'
) -> dict[str, Any]:
    """
    Retrieve top-k relevant datasets from ChromaDB

    Args:
        query: User's natural language query
        category: Optional category filter (e.g., "Tourism & Hospitality")
        top_k: Number of results to return (default: 5)
        source_type: 'qatar_open_data' or 'corporate_intelligence' or None for both

    Returns:
        Dictionary with retrieved datasets and metadata
    """
    # Generate query embedding
    query_embedding = embed_query(query)

    # Build where filter
    where_filter = {}
    if category:
        where_filter['category'] = category

    # Determine which collection(s) to search
    collections = []
    if source_type == 'qatar_open_data' or source_type is None:
        collections.append(('qatar', qatar_collection))
    if source_type == 'corporate_intelligence' or source_type is None:
        collections.append(('corporate', corporate_collection))

    all_results = []

    # Search each collection
    for coll_name, collection in collections:
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter if where_filter else None
            )

            # Parse results
            for i in range(len(results['ids'][0])):
                all_results.append({
                    'id': results['ids'][0][i],
                    'title': results['metadatas'][0][i]['source_name'],
                    'description': results['metadatas'][0][i].get('description', ''),
                    'category': results['metadatas'][0][i]['category'],
                    'confidence': results['metadatas'][0][i].get('confidence', 100),
                    'source_type': results['metadatas'][0][i].get('source_type', coll_name),
                    'similarity': 1 - results['distances'][0][i],  # Convert distance to similarity
                    'document': results['documents'][0][i]
                })
        except Exception as e:
            print(f"Warning: Error searching {coll_name} collection: {e}")
            continue

    # Deduplicate results by TITLE (prevent same dataset appearing twice)
    # Note: Some datasets have duplicate IDs in database, so we deduplicate by title
    seen_titles = set()
    unique_results = []
    for result in all_results:
        # Create unique key from title (case-insensitive)
        title_key = result['title'].lower().strip()
        if title_key not in seen_titles:
            unique_results.append(result)
            seen_titles.add(title_key)

    # Sort by similarity and take top-k
    unique_results.sort(key=lambda x: x['similarity'], reverse=True)
    unique_results = unique_results[:top_k]

    return {
        'query': query,
        'num_results': len(unique_results),
        'results': unique_results
    }


# ============================================================================
# 3. Context Assembly
# ============================================================================

def assemble_context(retrieval_results: dict[str, Any]) -> str:
    """
    Format retrieved datasets as context for LLM

    Args:
        retrieval_results: Output from retrieve_datasets()

    Returns:
        Formatted context string for LLM
    """
    results = retrieval_results['results']

    if not results:
        return "No relevant datasets found."

    context = "=== RELEVANT DATASETS ===\n\n"

    for i, result in enumerate(results, 1):
        context += f"[{i}] {result['title']}\n"
        context += f"    Category: {result['category']}\n"
        context += f"    Relevance: {result['similarity']:.1%}\n"

        if result['description']:
            # Truncate description if too long
            desc = result['description']
            if len(desc) > 300:
                desc = desc[:297] + "..."
            context += f"    Description: {desc}\n"

        context += f"    Data Quality: {result['confidence']}% confidence\n"
        context += "\n"

    return context


# ============================================================================
# 4. LLM Prompt Template
# ============================================================================

PROMPT_TEMPLATE = """You are a strategic analyst for United Development Company (UDC), Qatar's master developer.

UDC operates:
- The Pearl-Qatar (luxury residential and hospitality development)
- Lusail (smart city development)
- UDC Tower (commercial real estate)

Your role is to provide strategic insights based on Qatar's open data and UDC's corporate intelligence.

=== CONTEXT ===
{context}

=== USER QUESTION ===
{query}

=== INSTRUCTIONS ===
1. Analyze the provided datasets carefully
2. Provide strategic insights relevant to UDC's business
3. Cite specific datasets using [1], [2], etc.
4. Be concise, actionable, and business-focused
5. If data is insufficient, state limitations clearly
6. Highlight trends, opportunities, or risks

=== STRATEGIC ANALYSIS ===
"""


# ============================================================================
# 5. Answer Generation
# ============================================================================

def generate_answer(
    query: str,
    context: str,
    model: str = LLM_MODEL,
    max_tokens: int = 500
) -> str:
    """
    Generate answer using LLM

    Args:
        query: User's question
        context: Assembled context from retrieved datasets
        model: OpenAI model to use (default: gpt-3.5-turbo)
        max_tokens: Maximum tokens in response

    Returns:
        LLM-generated answer with citations
    """
    # Check if OpenAI is available
    if not openai_available or openai_client is None:
        return "[LLM NOT AVAILABLE]\n\nOpenAI API key not configured. Set OPENAI_API_KEY environment variable to enable answer generation.\n\nRetrieved context:\n" + context

    try:
        # Format prompt
        prompt = PROMPT_TEMPLATE.format(
            context=context,
            query=query
        )

        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a strategic analyst for UDC, Qatar's master developer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7  # Balance creativity and factuality
        )

        answer = response.choices[0].message.content or ""
        return answer

    except Exception as e:
        return f"Error generating answer: {str(e)}\n\nPlease check your OpenAI API key is set in environment variable OPENAI_API_KEY."


# ============================================================================
# 6. End-to-End RAG Pipeline
# ============================================================================

def rag_query(
    query: str,
    category: str | None = None,
    top_k: int = DEFAULT_TOP_K,
    source_type: str | None = 'qatar_open_data',
    return_sources: bool = True
) -> dict[str, Any]:
    """
    Complete RAG pipeline: Query → Embedding → Search → Context → Answer

    Args:
        query: User's natural language question
        category: Optional category filter
        top_k: Number of datasets to retrieve
        source_type: 'qatar_open_data', 'corporate_intelligence', or None for both
        return_sources: Include source datasets in response

    Returns:
        Dictionary with answer, sources, and metadata
    """
    # 1. Retrieve relevant datasets
    retrieval_results = retrieve_datasets(query, category, top_k, source_type)

    # 2. Assemble context
    context = assemble_context(retrieval_results)

    # 3. Generate answer
    answer = generate_answer(query, context)

    # 4. Prepare response
    response = {
        'query': query,
        'answer': answer,
        'num_sources': retrieval_results['num_results']
    }

    if return_sources:
        response['sources'] = retrieval_results['results']

    return response


# ============================================================================
# 7. Convenience Functions
# ============================================================================

def query(text: str, **kwargs) -> str:
    """
    Simple query interface that returns just the answer

    Args:
        text: User's question
        **kwargs: Additional arguments for rag_query()

    Returns:
        Answer string
    """
    result = rag_query(text, **kwargs)
    return result['answer']


def query_with_sources(text: str, **kwargs) -> dict[str, Any]:
    """
    Query interface that returns answer with source citations

    Args:
        text: User's question
        **kwargs: Additional arguments for rag_query()

    Returns:
        Full response with answer and sources
    """
    return rag_query(text, **kwargs)


# ============================================================================
# 8. Testing Function
# ============================================================================

def test_rag_system():
    """Test RAG system with sample queries"""
    print("="*100)
    print("TESTING RAG SYSTEM")
    print("="*100)
    print()

    test_queries = [
        {
            'query': "What are the latest hotel occupancy trends in Qatar?",
            'category': "Tourism & Hospitality"
        },
        {
            'query': "How is the real estate market performing for GCC citizens?",
            'category': "Real Estate & Construction"
        },
        {
            'query': "What are the key economic indicators for Qatar's economy?",
            'category': "Economic & Financial"
        },
        {
            'query': "What infrastructure projects have been completed recently?",
            'category': "Infrastructure & Utilities"
        },
        {
            'query': "What are the population demographics and growth trends?",
            'category': "Population & Demographics"
        }
    ]

    for i, test_case in enumerate(test_queries, 1):
        print(f"\n{'='*100}")
        print(f"TEST {i}: {test_case['query']}")
        print(f"Category: {test_case.get('category', 'All')}")
        print('='*100)
        print()

        # Run query
        result = rag_query(
            query=test_case['query'],
            category=test_case.get('category'),
            top_k=3  # Use top-3 for testing
        )

        # Display results
        print("SOURCES RETRIEVED:")
        print("-" * 100)
        for j, source in enumerate(result['sources'], 1):
            print(f"{j}. [{source['similarity']:.1%}] {source['title']}")
            print(f"   Category: {source['category']}")
        print()

        print("STRATEGIC ANALYSIS:")
        print("-" * 100)
        print(result['answer'])
        print()


# ============================================================================
# Main execution
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*100)
    print("RAG SYSTEM INITIALIZED")
    print("="*100)
    print()
    print("Available functions:")
    print("  - query(text) → Simple answer")
    print("  - query_with_sources(text) → Answer with citations")
    print("  - rag_query(query, category, top_k) → Full control")
    print("  - test_rag_system() → Run test queries")
    print()
    print("Example usage:")
    print('  >>> answer = query("What are hotel occupancy rates?")')
    print('  >>> result = query_with_sources("Real estate trends?")')
    print()

    # Run tests if OpenAI API key is available
    if os.getenv('OPENAI_API_KEY'):
        print("OpenAI API key found - running tests...")
        print()
        test_rag_system()
    else:
        print("⚠️  No OpenAI API key found in environment")
        print("   Set OPENAI_API_KEY to enable LLM answer generation")
        print("   Retrieval and context assembly will still work")
        print()
        print("Testing retrieval only (without LLM)...")
        print()

        # Test retrieval without LLM
        test_query = "hotel occupancy rates in Qatar"
        print(f"Query: {test_query}")
        print("-" * 80)

        results = retrieve_datasets(test_query, top_k=3)
        context = assemble_context(results)

        print("Retrieved datasets:")
        for i, r in enumerate(results['results'], 1):
            print(f"{i}. [{r['similarity']:.1%}] {r['title']}")

        print("\nContext assembled:")
        print(context)
