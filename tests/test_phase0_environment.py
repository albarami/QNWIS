"""
Phase 0: Environment Setup Tests

These tests verify that the NSIC environment is properly configured.
ALL tests must pass before proceeding to Phase 1.

Run with: pytest tests/test_phase0_environment.py -v
"""

import pytest
import sys
import platform
from pathlib import Path


class TestPythonEnvironment:
    """Test Python environment."""

    def test_python_version(self):
        """Python version must be 3.10+."""
        assert sys.version_info.major == 3
        assert sys.version_info.minor >= 10, f"Python 3.10+ required, got {sys.version_info.minor}"


class TestCorePackages:
    """Test core package installation."""

    def test_torch_installed(self):
        """PyTorch must be installed."""
        import torch
        assert torch is not None

    def test_torch_cuda_available(self):
        """CUDA must be available in PyTorch (REQUIRED for GPU machine)."""
        import torch
        assert torch.cuda.is_available(), (
            "CUDA not available! Install CUDA PyTorch with:\n"
            "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121"
        )

    def test_torch_gpu_count(self):
        """Must have 8 GPUs available."""
        import torch
        gpu_count = torch.cuda.device_count()
        assert gpu_count >= 8, f"Expected 8 GPUs, got {gpu_count}"

    def test_sentence_transformers_installed(self):
        """sentence-transformers must be installed."""
        from sentence_transformers import SentenceTransformer
        assert SentenceTransformer is not None

    def test_transformers_installed(self):
        """transformers must be installed."""
        import transformers
        assert transformers is not None


class TestRequiredPackages:
    """Test required package installation for Phase 0."""

    def test_faiss_installed(self):
        """faiss must be installed (CPU or GPU version)."""
        import faiss
        assert faiss is not None
        # Verify basic functionality
        import numpy as np
        d = 64  # dimension
        nb = 100  # database size
        xb = np.random.random((nb, d)).astype('float32')
        index = faiss.IndexFlatL2(d)
        index.add(xb)
        assert index.ntotal == nb, "faiss index not working properly"

    def test_diskcache_installed(self):
        """diskcache must be installed for embedding cache."""
        import diskcache
        assert diskcache is not None
        # Verify basic functionality
        import tempfile
        import shutil
        tmpdir = tempfile.mkdtemp()
        try:
            cache = diskcache.Cache(tmpdir)
            cache.set("test_key", "test_value")
            assert cache.get("test_key") == "test_value"
            cache.close()  # Must close before cleanup on Windows
        finally:
            # On Windows, may need to ignore cleanup errors due to file locking
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass  # Cleanup failure is OK, diskcache works

    def test_vllm_or_transformers_for_inference(self):
        """
        vLLM (Linux) or HuggingFace Transformers (Windows) must be available.
        
        Note: vLLM is Linux-only. On Windows, we use HuggingFace Transformers
        with AutoModelForCausalLM + device_map='auto' for multi-GPU inference.
        This provides equivalent functionality for DeepSeek-R1-70B.
        """
        if platform.system() == "Linux":
            # On Linux, prefer vLLM for best performance
            try:
                import vllm
                assert vllm is not None
            except ImportError:
                # Fall back to transformers on Linux too
                import transformers
                from transformers import AutoModelForCausalLM
                assert AutoModelForCausalLM is not None
        else:
            # On Windows, use HuggingFace Transformers
            import transformers
            from transformers import AutoModelForCausalLM, AutoTokenizer
            assert AutoModelForCausalLM is not None
            assert AutoTokenizer is not None


class TestDirectoryStructure:
    """Test NSIC directory structure."""

    def test_nsic_root_exists(self):
        """src/nsic directory must exist."""
        path = Path("src/nsic")
        assert path.exists(), f"Directory {path} does not exist"

    def test_nsic_rag_exists(self):
        """src/nsic/rag directory must exist."""
        path = Path("src/nsic/rag")
        assert path.exists(), f"Directory {path} does not exist"

    def test_nsic_verification_exists(self):
        """src/nsic/verification directory must exist."""
        path = Path("src/nsic/verification")
        assert path.exists(), f"Directory {path} does not exist"

    def test_nsic_knowledge_exists(self):
        """src/nsic/knowledge directory must exist."""
        path = Path("src/nsic/knowledge")
        assert path.exists(), f"Directory {path} does not exist"

    def test_nsic_orchestration_exists(self):
        """src/nsic/orchestration directory must exist."""
        path = Path("src/nsic/orchestration")
        assert path.exists(), f"Directory {path} does not exist"

    def test_nsic_arbitration_exists(self):
        """src/nsic/arbitration directory must exist."""
        path = Path("src/nsic/arbitration")
        assert path.exists(), f"Directory {path} does not exist"

    def test_nsic_scenarios_exists(self):
        """src/nsic/scenarios directory must exist."""
        path = Path("src/nsic/scenarios")
        assert path.exists(), f"Directory {path} does not exist"

    def test_scenarios_dirs_exist(self):
        """scenarios subdirectories must exist."""
        for category in ["economic", "competitive", "policy", "timing"]:
            path = Path(f"scenarios/{category}")
            assert path.exists(), f"Directory {path} does not exist"


class TestNSICImports:
    """Test NSIC module can be imported."""

    def test_nsic_import(self):
        """nsic module must be importable."""
        # Add src to path if needed
        src_path = Path("src")
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        
        import nsic
        assert nsic.__version__ == "2.0.0"

    def test_nsic_rag_import(self):
        """nsic.rag module must be importable."""
        src_path = Path("src")
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        
        from nsic import rag
        assert rag is not None

    def test_nsic_verification_import(self):
        """nsic.verification module must be importable."""
        src_path = Path("src")
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        
        from nsic import verification
        assert verification is not None


class TestConfigFiles:
    """Test configuration files."""

    def test_config_dir_exists(self):
        """config directory must exist."""
        path = Path("config")
        assert path.exists(), f"Directory {path} does not exist"

    def test_nsic_gpu_config_exists(self):
        """NSIC GPU config file must exist."""
        path = Path("config/nsic_gpu_config.yaml")
        assert path.exists(), f"Config file {path} does not exist"


class TestGPUAllocation:
    """Test GPU allocation is correct for NSIC architecture."""

    def test_gpu_memory_sufficient(self):
        """Each GPU must have at least 40GB for DeepSeek-R1-70B."""
        import torch
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            memory_gb = props.total_memory / (1024**3)
            assert memory_gb >= 40, f"GPU {i} has only {memory_gb:.1f}GB, need at least 40GB"

    def test_gpu_compute_capability(self):
        """GPUs must have compute capability 8.0+ for A100."""
        import torch
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            cc = f"{props.major}.{props.minor}"
            assert props.major >= 8, f"GPU {i} has compute capability {cc}, need 8.0+ for A100"


# Summary fixture for test report
@pytest.fixture(scope="session", autouse=True)
def test_summary(request):
    """Print summary after all tests."""
    yield
    print("\n" + "=" * 60)
    print("PHASE 0 ENVIRONMENT TESTS COMPLETE")
    print("=" * 60)
    print("\nIf all tests passed, proceed with:")
    print("  git add .")
    print('  git commit -m "feat(phase0): NSIC environment setup complete"')
    print("  git push origin HEAD")
    print("\nThen start Phase 1: Premium Embeddings + Cache")
    print("=" * 60)
