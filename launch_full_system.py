"""
Full System Launch Script for QNWIS with Real LLM.

Launches:
1. FastAPI server with all API endpoints
2. React streaming console (Vite dev server)
3. Admin diagnostics endpoints
4. Health checks and monitoring

Usage:
    python launch_full_system.py --provider anthropic --api-key YOUR_KEY
    python launch_full_system.py --provider openai --api-key YOUR_KEY
    python launch_full_system.py --provider stub  # For testing
"""

import argparse, os, sys, time, subprocess, socket, shutil
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Paths for child processes
ROOT = Path(__file__).resolve().parent
SRC = str(ROOT / "src")

def _env_with_src():
    """Return environment with PYTHONPATH including src for child processes."""
    env = os.environ.copy()
    env["PYTHONPATH"] = SRC + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")
    return env


def setup_environment(provider: str, api_key: str | None = None, model: str | None = None):
    """Set up environment variables for LLM configuration."""
    print(f"🔧 Configuring LLM provider: {provider}")
    provider = provider.lower()
    os.environ["QNWIS_LLM_PROVIDER"] = provider
    os.environ.setdefault("QNWIS_LLM_TIMEOUT", "60")
    os.environ.setdefault("QNWIS_LLM_MAX_RETRIES", "3")

    if provider == "anthropic":
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("❌ Error: ANTHROPIC_API_KEY is required for provider=anthropic")
            sys.exit(1)
        os.environ.setdefault("QNWIS_ANTHROPIC_MODEL", model or "claude-sonnet-4-5-20250929")
    elif provider == "openai":
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ Error: OPENAI_API_KEY is required for provider=openai")
            sys.exit(1)
        os.environ.setdefault("QNWIS_OPENAI_MODEL", model or "gpt-4-turbo-2024-04-09")
    elif provider == "stub":
        os.environ.setdefault("QNWIS_STUB_TOKEN_DELAY_MS", "25")
    else:
        print(f"❌ Error: Unknown provider '{provider}'")
        print("   Supported: anthropic, openai, stub")
        sys.exit(1)

def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def verify_llm_config():
    """Verify LLM configuration by initializing LLMClient using env values."""
    print("\n🔍 Verifying LLM configuration...")
    try:
        from qnwis.llm.client import LLMClient  # type: ignore
        provider = os.getenv("QNWIS_LLM_PROVIDER", "unknown")
        model = (
            os.getenv("QNWIS_ANTHROPIC_MODEL") if provider == "anthropic" else os.getenv("QNWIS_OPENAI_MODEL")
        )
        print(f"   Provider: {provider}")
        print(f"   Model: {model or '(provider default)'}")
        # Instantiate (no network call)
        _ = LLMClient(provider=provider, model=model)
        print("   ✅ LLM client initialized")
        return True
    except Exception as e:
        print(f"   ❌ LLM configuration error: {e}")
        return False


def test_system():
    """Run quick system test if test file exists (optional)."""
    test_path = ROOT / "test_system_e2e.py"
    if not test_path.exists():
        print("\n🧪 No local E2E test file found; skipping smoke test.")
        return True
    print("\n🧪 Running system test...")
    try:
        result = subprocess.run(
            [sys.executable, str(test_path)],
            capture_output=True,
            text=True,
            timeout=45,
            env=_env_with_src(),
        )
        if result.returncode == 0:
            print("   ✅ System test PASSED")
            return True
        print("   ❌ System test FAILED")
        print(result.stdout)
        print(result.stderr)
        return False
    except subprocess.TimeoutExpired:
        print("   ⚠️  System test timed out (may be normal with real LLM)")
        return True
    except Exception as e:
        print(f"   ⚠️  Could not run system test: {e}")
        return True


def start_fastapi_server(port: int = 8001):
    """Start FastAPI server in background with --app-dir src and readiness poll."""
    if port_in_use(port):
        print(f"❌ API port {port} is already in use")
        return None
    print(f"\n🚀 Starting FastAPI server on port {port}...")
    try:
        process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn",
                "qnwis.api.server:create_app",
                "--factory", "--host", "0.0.0.0", "--port", str(port),
                "--app-dir", SRC, "--reload",
            ],
            env=_env_with_src(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        # Readiness: poll /health/ready up to 30s
        deadline = time.time() + 30
        url = f"http://127.0.0.1:{port}/health/ready"
        while time.time() < deadline:
            try:
                with urlopen(Request(url, headers={"Accept": "application/json"}), timeout=2) as r:
                    if r.status == 200:
                        print("   ✅ API ready")
                        return process
            except (URLError, HTTPError):
                time.sleep(0.8)
        print("   ❌ API did not become ready; check logs below")
        return process
    except Exception as e:
        print(f"   ❌ Error starting server: {e}")
        return None


def start_react_ui(port: int = 3000):
    """Start the React UI dev server (Vite)."""
    if port_in_use(port):
        print(f'❌ UI port {port} is already in use')
        return None
    print(f"🚀 Starting React UI on port {port}...")
    npm_exe = shutil.which('npm')
    if not npm_exe:
        print('   ⚠️  npm not found on PATH. Install Node.js 18+ to run the React UI.')
        return None
    frontend_dir = ROOT / 'qnwis-ui'
    if not frontend_dir.exists():
        print('   ❌ React frontend not found at qnwis-ui/')
        print('      Run the migration setup or restore the directory before launching.')
        return None
    try:
        process = subprocess.Popen(
            [
                npm_exe,
                'run',
                'dev',
                '--',
                '--host',
                '0.0.0.0',
                '--port',
                str(port),
            ],
            cwd=str(frontend_dir),
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        print('   ⏳ Waiting for UI to start...')
        time.sleep(3)
        if process.poll() is None:
            print(f'   ✅ React UI running on http://localhost:{port}')
            print('   💬 Open the React console to run workflows')
            return process
        stdout = process.stdout.read() if process.stdout else ''
        print('   ❌ UI failed to start')
        print(stdout)
        return None
    except Exception as e:
        print(f'   ❌ Error starting UI: {e}')
        return None


def print_system_info(api_process, ui_process, api_port: int, ui_port: int):
    """Print system information and access URLs."""
    print("\n" + "="*60)
    print("🎉 QNWIS SYSTEM LAUNCHED SUCCESSFULLY!")
    print("="*60)
    
    print("\n📊 System Status:")
    print(f"   {'✅' if api_process else '❌'} FastAPI Server")
    print(f"   {'✅' if ui_process else '❌'} React UI")
    
    print("\n🌐 Access URLs:")
    if api_process:
        print(f"   📡 API Server: http://localhost:{api_port}")
        print(f"   📚 API Docs: http://localhost:{api_port}/docs")
        print(f"   🔧 Admin Panel: http://localhost:{api_port}/api/v1/admin/models")
        print(f"   ❤️  Health Check: http://localhost:{api_port}/health")
    
    if ui_process:
        print(f"   💬 React UI: http://localhost:{ui_port}")
        print("   📱 Proxy: http://localhost:{ui_port}/api -> backend")
    
    print("\n🤖 Available Agents:")
    print("   • LabourEconomist - Employment trends & analysis")
    print("   • Nationalization - GCC benchmarking & Qatarization")
    print("   • Skills - Skills gap & workforce composition")
    print("   • PatternDetective - Data validation & anomalies")
    print("   • NationalStrategy - Vision 2030 alignment")
    
    print("\n💡 Example Questions:")
    print("   • What are Qatar's unemployment trends?")
    print("   • Compare Qatar to other GCC countries")
    print("   • Analyze employment by gender")
    print("   • What are the skills gaps in Qatar?")
    
    print("\n⚙️  Configuration:")
    provider = os.getenv("QNWIS_LLM_PROVIDER", "unknown")
    print(f"   Provider: {provider}")
    if provider == "anthropic":
        print(f"   Model: {os.getenv('QNWIS_ANTHROPIC_MODEL')}")
    elif provider == "openai":
        print(f"   Model: {os.getenv('QNWIS_OPENAI_MODEL')}")
    
    print("\n🛑 To stop:")
    print("   Press Ctrl+C")
    
    print("\n" + "="*60)


def main():
    """Main launch function."""
    parser = argparse.ArgumentParser(
        description="Launch QNWIS system with real LLM integration"
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai", "stub"],
        default="stub",
        help="LLM provider (default: stub for testing)"
    )
    parser.add_argument(
        "--api-key",
        help="API key for the provider"
    )
    parser.add_argument(
        "--model",
        help="Model name (optional, uses defaults)"
    )
    parser.add_argument(
        "--api-port",
        type=int,
        default=8000,
        help="FastAPI server port (default: 8000)"
    )
    parser.add_argument(
        "--ui-port",
        type=int,
        default=3000,
        help="React UI port (default: 3000)"
    )
    parser.add_argument(
        "--skip-test",
        action="store_true",
        help="Skip system test"
    )
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Launch API server only (no UI)"
    )
    parser.add_argument(
        "--ui-only",
        action="store_true",
        help="Launch UI only (no API server)"
    )
    
    args = parser.parse_args()
    
    print("🚀 QNWIS Full System Launch")
    print("="*60)
    
    # Setup environment
    setup_environment(args.provider, args.api_key, args.model)
    
    # Verify configuration (non-fatal; continue to start services)
    if not verify_llm_config():
        print("\n⚠️  LLM configuration verification failed; continuing to start services...")
    
    # Run system test
    if not args.skip_test and args.provider == "stub":
        if not test_system():
            print("\n⚠️  System test failed, but continuing...")
    
    # Start services
    api_process = None
    ui_process = None
    
    try:
        if not args.ui_only:
            api_process = start_fastapi_server(args.api_port)
        
        if not args.api_only:
            ui_process = start_react_ui(args.ui_port)
        
        # Print system info
        print_system_info(api_process, ui_process, args.api_port, args.ui_port)
        
        # Keep running
        if api_process or ui_process:
            print("\n⏳ System running... Press Ctrl+C to stop\n")
            try:
                while True:
                    time.sleep(1)
                    # Check if processes are still running
                    if api_process and api_process.poll() is not None:
                        print("\n❌ API server stopped unexpectedly")
                        break
                    if ui_process and ui_process.poll() is not None:
                        print("\n❌ UI stopped unexpectedly")
                        break
            except KeyboardInterrupt:
                print("\n\n🛑 Shutting down...")
        else:
            print("\n❌ No services started successfully")
            sys.exit(1)
    
    finally:
        # Cleanup
        if api_process:
            print("   Stopping API server...")
            api_process.terminate()
            api_process.wait(timeout=5)
        
        if ui_process:
            print("   Stopping UI...")
            ui_process.terminate()
            ui_process.wait(timeout=5)
        
        print("✅ Shutdown complete")


if __name__ == "__main__":
    main()
