import sys
import asyncio
import os
sys.path.insert(0, 'src')

# Set environment variables
os.environ['DATABASE_URL'] = 'postgresql://postgres:1234@localhost:5432/qnwis'

from qnwis.agents.base import DataClient
from qnwis.llm.client import LLMClient
from qnwis.classification.classifier import Classifier
from qnwis.orchestration.streaming import run_workflow_stream

async def test():
    client = DataClient()
    llm = LLMClient(provider='stub')
    classifier = Classifier()
    
    print("Starting workflow test with database...")
    print(f"Queries loaded: {len(client.registry.all_ids())}")
    
    try:
        async for event in run_workflow_stream(
            'What is the unemployment trend in Qatar?', 
            client, 
            llm, 
            classifier=classifier
        ):
            print(f'{event.stage}: {event.status}')
            if event.stage in ['done', 'error', 'synthesize'] and event.status == 'complete':
                if event.payload:
                    print(f'  Payload keys: {list(event.payload.keys())}')
                break
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())
