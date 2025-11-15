import sys
import asyncio
sys.path.insert(0, 'src')

from qnwis.agents.base import DataClient
from qnwis.llm.client import LLMClient
from qnwis.classification.classifier import Classifier
from qnwis.orchestration.streaming import run_workflow_stream

async def test():
    client = DataClient()
    llm = LLMClient(provider='stub')
    classifier = Classifier()
    
    print("Starting workflow test...")
    try:
        async for event in run_workflow_stream('What is the unemployment trend in Qatar?', client, llm, classifier=classifier):
            print(f'{event.stage}: {event.status} - {event.payload}')
            if event.stage == 'done' or event.stage == 'error':
                break
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())
