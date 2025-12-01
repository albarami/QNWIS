"""
NSIC Persistent GPU Servers

Enterprise-grade persistent services for GPU-accelerated operations:
- Embeddings Server (Port 8003, GPU 0-1)
- Knowledge Graph Server (Port 8004, GPU 4)
- Verification Server (Port 8005, GPU 5)

All models are loaded at startup and kept in GPU memory permanently.
"""

from .embeddings_server import app as embeddings_app
from .kg_server import app as kg_app
from .verification_server import app as verification_app

__all__ = ["embeddings_app", "kg_app", "verification_app"]

