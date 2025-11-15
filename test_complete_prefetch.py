"""Test the complete prefetch with ALL APIs."""
import asyncio

from src.qnwis.orchestration.prefetch_apis import CompletePrefetchLayer


def _safe_print(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        sanitized = message.encode("ascii", errors="ignore").decode("ascii", errors="ignore")
        print(sanitized)


async def test():
    prefetch = CompletePrefetchLayer()
    
    query = "Qatar is considering mandating 40% Qatari nationals in tech sector by 2027"
    
    facts = await prefetch.fetch_all_sources(query)
    
    _safe_print(f"\n{'='*80}")
    _safe_print(f"COMPLETE PREFETCH TEST - EXTRACTED {len(facts)} FACTS")
    _safe_print(f"{'='*80}\n")
    
    # Group by source
    by_source = {}
    for fact in facts:
        source = fact['source']
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(fact)
    
    for source, source_facts in by_source.items():
        _safe_print(f"\n📊 {source} ({len(source_facts)} facts):")
        for fact in source_facts[:3]:  # Show first 3
            _safe_print(f"   • {fact['metric']}: {str(fact['value'])[:80]}")


if __name__ == "__main__":
    asyncio.run(test())
