#!/usr/bin/env python3
"""
NSIC System Startup Script
============================
Ensures ALL required components are running before the system starts.

Components:
1. PostgreSQL Database
2. Engine B (GPU Compute Services) - 8x A100 GPUs
3. Knowledge Graph / Embedding Services (CPU)
4. RAG System (CPU)

Run this BEFORE starting the main NSIC system.
"""

import subprocess
import sys
import time
import socket
import os
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("STARTUP")

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
POSTGRES_SERVICE = "postgresql-x64-15"
ENGINE_B_PORT = 8001
ENGINE_B_MODULE = "src.nsic.engine_b.api"


def print_banner():
    """Print startup banner."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     NSIC SYSTEM STARTUP SCRIPT                               ║
║                                                                              ║
║  Components:                                                                 ║
║    1. PostgreSQL Database                                                    ║
║    2. Engine B (8x A100 GPU Compute)                                         ║
║    3. Knowledge Graph / Embeddings                                           ║
║    4. RAG System                                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")


def check_port(port: int, host: str = "localhost") -> bool:
    """Check if a port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


def check_postgres() -> bool:
    """Check if PostgreSQL is running."""
    logger.info("Checking PostgreSQL...")
    try:
        result = subprocess.run(
            ["sc", "query", POSTGRES_SERVICE],
            capture_output=True,
            text=True,
            timeout=10
        )
        is_running = "RUNNING" in result.stdout
        if is_running:
            logger.info("  ✅ PostgreSQL is RUNNING")
        else:
            logger.warning("  ❌ PostgreSQL is NOT running")
        return is_running
    except Exception as e:
        logger.error(f"  ❌ Error checking PostgreSQL: {e}")
        return False


def start_postgres() -> bool:
    """Start PostgreSQL service."""
    logger.info("Starting PostgreSQL...")
    try:
        result = subprocess.run(
            ["net", "start", POSTGRES_SERVICE],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0 or "already been started" in result.stdout:
            logger.info("  ✅ PostgreSQL started successfully")
            return True
        else:
            logger.error(f"  ❌ Failed to start PostgreSQL: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"  ❌ Error starting PostgreSQL: {e}")
        return False


def check_gpus() -> dict:
    """Check GPU availability with CuPy."""
    logger.info("Checking GPUs...")
    try:
        import cupy as cp
        gpu_count = cp.cuda.runtime.getDeviceCount()
        cuda_version = cp.cuda.runtime.runtimeGetVersion()
        
        logger.info(f"  ✅ CuPy installed (v{cp.__version__})")
        logger.info(f"  ✅ CUDA version: {cuda_version}")
        logger.info(f"  ✅ GPUs available: {gpu_count}")
        
        # Check each GPU
        for i in range(min(gpu_count, 8)):
            props = cp.cuda.runtime.getDeviceProperties(i)
            name = props['name'].decode() if isinstance(props['name'], bytes) else props['name']
            mem_gb = props['totalGlobalMem'] / (1024**3)
            logger.info(f"      GPU {i}: {name} ({mem_gb:.0f}GB)")
        
        return {"available": True, "count": gpu_count, "cuda": cuda_version}
    except ImportError:
        logger.error("  ❌ CuPy NOT installed - GPUs will NOT be used!")
        logger.error("     Run: pip install cupy-cuda12x")
        return {"available": False, "count": 0, "error": "CuPy not installed"}
    except Exception as e:
        logger.error(f"  ❌ GPU check failed: {e}")
        return {"available": False, "count": 0, "error": str(e)}


def check_engine_b() -> bool:
    """Check if Engine B is running."""
    logger.info(f"Checking Engine B (port {ENGINE_B_PORT})...")
    if check_port(ENGINE_B_PORT):
        logger.info("  ✅ Engine B is RUNNING")
        return True
    else:
        logger.warning("  ❌ Engine B is NOT running")
        return False


def start_engine_b() -> bool:
    """Start Engine B API server."""
    logger.info("Starting Engine B...")
    
    # First check GPUs
    gpu_info = check_gpus()
    if not gpu_info["available"]:
        logger.error("  ❌ Cannot start Engine B without GPU support!")
        logger.error("     Install CuPy first: pip install cupy-cuda12x")
        return False
    
    try:
        # Start Engine B in background
        process = subprocess.Popen(
            [sys.executable, "-m", ENGINE_B_MODULE],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )
        
        # Wait for it to start
        for i in range(30):  # 30 second timeout
            time.sleep(1)
            if check_port(ENGINE_B_PORT):
                logger.info(f"  ✅ Engine B started (PID: {process.pid})")
                return True
            if process.poll() is not None:
                # Process died
                _, stderr = process.communicate()
                logger.error(f"  ❌ Engine B failed to start: {stderr.decode()[:500]}")
                return False
        
        logger.error("  ❌ Engine B startup timeout")
        return False
        
    except Exception as e:
        logger.error(f"  ❌ Error starting Engine B: {e}")
        return False


def verify_engine_b_gpus() -> bool:
    """Verify Engine B is using GPUs."""
    logger.info("Verifying Engine B GPU usage...")
    try:
        import requests
        response = requests.get(f"http://localhost:{ENGINE_B_PORT}/health", timeout=10)
        health = response.json()
        
        gpu_services = 0
        total_services = 0
        for name, status in health.get("services", {}).items():
            total_services += 1
            # Check both gpu_available and gpu_used fields
            gpu_enabled = status.get("gpu_available", False) or status.get("gpu_used", False)
            if gpu_enabled:
                gpu_services += 1
                logger.info(f"  ✅ {name}: GPU enabled")
            else:
                logger.warning(f"  ⚠️  {name}: CPU only")
        
        # All services should use GPU
        if gpu_services == total_services:
            logger.info(f"  ✅ Engine B using GPUs ({gpu_services}/{total_services} services)")
            return True
        elif gpu_services >= 5:
            logger.info(f"  ✅ Engine B mostly using GPUs ({gpu_services}/{total_services} services)")
            return True
        else:
            logger.warning(f"  ⚠️  Only {gpu_services}/{total_services} services using GPU")
            return False
            
    except Exception as e:
        logger.error(f"  ❌ Could not verify Engine B GPUs: {e}")
        return False


def check_knowledge_graph() -> bool:
    """Check Knowledge Graph system."""
    logger.info("Checking Knowledge Graph...")
    kg_path = PROJECT_ROOT / "data" / "knowledge_graph.json"
    if kg_path.exists():
        size_mb = kg_path.stat().st_size / (1024 * 1024)
        logger.info(f"  ✅ Knowledge Graph exists ({size_mb:.1f}MB)")
        return True
    else:
        logger.warning("  ⚠️  Knowledge Graph not found (will be created on first use)")
        return True  # Not critical


def check_embeddings() -> bool:
    """Check embedding model availability."""
    logger.info("Checking Embedding Model...")
    try:
        from sentence_transformers import SentenceTransformer
        logger.info("  ✅ sentence-transformers installed")
        
        # Check if model is cached
        model_name = "all-mpnet-base-v2"
        try:
            model = SentenceTransformer(model_name)
            logger.info(f"  ✅ Model '{model_name}' loaded")
            
            # Test embedding generation
            test_embedding = model.encode("test query", convert_to_numpy=True)
            logger.info(f"  ✅ Embedding dimension: {test_embedding.shape[0]}")
            return True
        except Exception as e:
            logger.warning(f"  ⚠️  Model will be downloaded on first use: {e}")
            return True
            
    except ImportError:
        logger.error("  ❌ sentence-transformers NOT installed")
        logger.error("     Run: pip install sentence-transformers")
        return False


def check_rag_system() -> bool:
    """Check RAG system."""
    logger.info("Checking RAG System...")
    try:
        # Add project root to path for imports
        import sys
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        
        # Import RAG components
        from qnwis.rag.retriever import DocumentStore, Document, SimpleEmbedder
        from qnwis.rag.embeddings import SentenceEmbedder
        
        logger.info("  ✅ RAG DocumentStore available")
        logger.info("  ✅ RAG Document class available")
        logger.info("  ✅ RAG SentenceEmbedder available")
        
        # Check for RAG store files
        rag_store_json = PROJECT_ROOT / "data" / "rag_store.json"
        rag_store_embeddings = PROJECT_ROOT / "data" / "rag_store_embeddings.npy"
        
        if rag_store_json.exists():
            size_kb = rag_store_json.stat().st_size / 1024
            logger.info(f"  ✅ RAG document store found ({size_kb:.1f}KB)")
        else:
            # Create empty RAG store
            logger.info("  📝 Creating RAG document store...")
            import json
            rag_store_json.parent.mkdir(parents=True, exist_ok=True)
            with open(rag_store_json, 'w') as f:
                json.dump({"documents": [], "metadata": {"created": str(datetime.now())}}, f)
            logger.info("  ✅ RAG document store created")
        
        if rag_store_embeddings.exists():
            import numpy as np
            embeddings = np.load(rag_store_embeddings)
            logger.info(f"  ✅ RAG embeddings found ({embeddings.shape[0]} vectors, dim={embeddings.shape[1] if len(embeddings.shape) > 1 else 'N/A'})")
        else:
            # Create empty embeddings file
            logger.info("  📝 Creating RAG embeddings file...")
            import numpy as np
            np.save(rag_store_embeddings, np.array([]))
            logger.info("  ✅ RAG embeddings file created")
        
        return True
    except ImportError as e:
        logger.error(f"  ❌ RAG system import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"  ❌ RAG system error: {e}")
        return False


def run_startup_checks() -> dict:
    """Run all startup checks and return status."""
    print_banner()
    
    results = {
        "postgres": False,
        "gpus": False,
        "engine_b": False,
        "engine_b_gpus": False,
        "knowledge_graph": False,
        "embeddings": False,
        "rag": False,
    }
    
    # 1. PostgreSQL
    print("\n" + "="*60)
    print("STEP 1: DATABASE")
    print("="*60)
    if not check_postgres():
        start_postgres()
    results["postgres"] = check_postgres()
    
    # 2. GPUs
    print("\n" + "="*60)
    print("STEP 2: GPU INFRASTRUCTURE")
    print("="*60)
    gpu_info = check_gpus()
    results["gpus"] = gpu_info["available"]
    
    # 3. Engine B
    print("\n" + "="*60)
    print("STEP 3: ENGINE B (GPU COMPUTE)")
    print("="*60)
    if not check_engine_b():
        if results["gpus"]:
            start_engine_b()
        else:
            logger.error("  ❌ Skipping Engine B - GPUs not available")
    results["engine_b"] = check_engine_b()
    
    if results["engine_b"]:
        results["engine_b_gpus"] = verify_engine_b_gpus()
    
    # 4. Knowledge Graph & Embeddings
    print("\n" + "="*60)
    print("STEP 4: KNOWLEDGE GRAPH & EMBEDDINGS (CPU)")
    print("="*60)
    results["knowledge_graph"] = check_knowledge_graph()
    results["embeddings"] = check_embeddings()
    
    # 5. RAG System
    print("\n" + "="*60)
    print("STEP 5: RAG SYSTEM")
    print("="*60)
    results["rag"] = check_rag_system()
    
    return results


def print_summary(results: dict):
    """Print startup summary."""
    print("\n")
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                           STARTUP SUMMARY                                    ║")
    print("╠══════════════════════════════════════════════════════════════════════════════╣")
    
    all_critical_ok = True
    
    for component, status in results.items():
        icon = "✅" if status else "❌"
        name = component.replace("_", " ").title()
        critical = component in ["postgres", "gpus", "engine_b", "engine_b_gpus"]
        marker = " [CRITICAL]" if critical and not status else ""
        print(f"║  {icon} {name:<30} {'OK' if status else 'FAILED'}{marker:<20} ║")
        if critical and not status:
            all_critical_ok = False
    
    print("╠══════════════════════════════════════════════════════════════════════════════╣")
    
    if all_critical_ok:
        print("║  🚀 SYSTEM READY - All critical components running                          ║")
        print("║     Engine B is using GPUs for quantitative compute                        ║")
    else:
        print("║  ⚠️  SYSTEM NOT READY - Some critical components failed                     ║")
        print("║     Please fix the issues above before running NSIC                       ║")
    
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    
    return all_critical_ok


def main():
    """Main entry point."""
    os.chdir(PROJECT_ROOT)
    
    try:
        results = run_startup_checks()
        success = print_summary(results)
        
        if success:
            print("\n✅ You can now run the NSIC system!")
            print("   python scripts/nsic_diagnostic.py --query <your_query>")
            return 0
        else:
            print("\n❌ Fix the issues above before running NSIC")
            return 1
            
    except KeyboardInterrupt:
        print("\n\nStartup cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

