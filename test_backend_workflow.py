"""
Direct backend workflow test - see actual agent conversation and debate.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from qnwis.orchestration.streaming import run_workflow_stream


async def test_workflow():
    """Test the backend workflow directly."""
    
    print("=" * 80)
    print("BACKEND WORKFLOW TEST - DIRECT EXECUTION")
    print("=" * 80)
    print()
    
    query = "What are the implications of raising minimum wage?"
    print(f"QUERY: {query}")
    print()
    print("=" * 80)
    print()
    
    event_count = 0
    
    async for event in run_workflow_stream(
        question=query,
        provider="anthropic"
    ):
        event_count += 1
        
        print(f"\n{'='*80}")
        print(f"EVENT #{event_count}: {event.stage}")
        print(f"Status: {event.status}")
        print(f"{'='*80}")
        
        if event.payload:
            print(f"\nPAYLOAD:")
            
            # Show agent analysis
            if event.stage.startswith('agent:'):
                agent_name = event.stage.replace('agent:', '')
                print(f"\n🤖 AGENT: {agent_name.upper()}")
                
                if 'analysis' in event.payload:
                    analysis = event.payload['analysis']
                    if analysis:
                        print(f"\nANALYSIS ({len(str(analysis))} chars):")
                        print(str(analysis)[:500] + "..." if len(str(analysis)) > 500 else str(analysis))
                
                if 'report' in event.payload:
                    report = event.payload['report']
                    if report:
                        print(f"\nREPORT ({len(str(report))} chars):")
                        print(str(report)[:500] + "..." if len(str(report)) > 500 else str(report))
            
            # Show debate conversation
            elif event.stage == 'debate':
                print(f"\n💬 DEBATE RESULTS:")
                debate = event.payload
                
                if 'contradictions' in debate:
                    print(f"\nContradictions: {len(debate.get('contradictions', []))}")
                    for i, contra in enumerate(debate.get('contradictions', [])[:3], 1):
                        print(f"\n  Contradiction {i}:")
                        print(f"    {contra}")
                
                if 'consensus_narrative' in debate:
                    narrative = debate['consensus_narrative']
                    print(f"\nConsensus Narrative ({len(str(narrative))} chars):")
                    print(str(narrative)[:500] + "..." if len(str(narrative)) > 500 else str(narrative))
                
                if 'resolutions' in debate:
                    print(f"\nResolutions: {len(debate.get('resolutions', []))}")
                    for i, res in enumerate(debate.get('resolutions', [])[:2], 1):
                        print(f"\n  Resolution {i}: {res}")
            
            # Show extracted facts
            elif event.stage == 'prefetch':
                facts = event.payload.get('extracted_facts', [])
                print(f"\n📊 EXTRACTED FACTS: {len(facts)} facts")
                if facts:
                    for i, fact in enumerate(facts[:5], 1):
                        print(f"  {i}. {str(fact)[:100]}")
            
            # Show classification
            elif event.stage == 'classify':
                print(f"\n🎯 CLASSIFICATION:")
                print(f"  Complexity: {event.payload.get('complexity', 'unknown')}")
                if 'reasoning' in event.payload:
                    print(f"  Reasoning: {event.payload['reasoning']}")
            
            # Show synthesis
            elif event.stage == 'synthesize':
                synthesis = event.payload.get('final_synthesis') or event.payload.get('text')
                if synthesis:
                    print(f"\n📝 SYNTHESIS ({len(str(synthesis))} chars):")
                    print(str(synthesis)[:500] + "..." if len(str(synthesis)) > 500 else str(synthesis))
        
        print()
    
    print(f"\n{'='*80}")
    print(f"WORKFLOW COMPLETE - {event_count} events emitted")
    print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(test_workflow())
