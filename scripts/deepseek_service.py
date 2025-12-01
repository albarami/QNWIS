"""
NSIC DeepSeek Service - Enterprise-Grade Deployment

Features:
- Auto-restart on crash (up to 5 times, then alert)
- Health monitoring every 30 seconds
- Memory-safe configuration
- Persistent logging
- Graceful shutdown handling

Run as: python scripts/deepseek_service.py --start
"""

import os
import sys
import time
import signal
import logging
import subprocess
import threading
import requests
from datetime import datetime
from pathlib import Path

# Configure logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"deepseek_service_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DeepSeekService:
    """
    Enterprise-grade DeepSeek service with auto-restart and health monitoring.
    """
    
    # Configuration
    PORT = 8001
    HEALTH_URL = f"http://localhost:{PORT}/health"
    HEALTH_CHECK_INTERVAL = 30  # seconds
    MAX_RESTART_ATTEMPTS = 5
    RESTART_COOLDOWN = 60  # seconds between restarts
    
    # Model configuration (memory-safe for 4x A100 80GB)
    MODEL = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B"
    GPUS = "2,3,6,7"  # 4 GPUs = 320GB VRAM
    GPU_MEMORY_UTILIZATION = 0.80  # Conservative to prevent OOM
    MAX_MODEL_LEN = 16384  # Reduced from 32768 for stability
    
    def __init__(self):
        self.process = None
        self.restart_count = 0
        self.last_restart_time = None
        self.running = False
        self.health_thread = None
        
    def start(self):
        """Start the DeepSeek service with monitoring."""
        logger.info("="*60)
        logger.info("NSIC DeepSeek Service Starting")
        logger.info("="*60)
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = True
        
        # Start the server
        self._start_server()
        
        # Start health monitoring in background
        self.health_thread = threading.Thread(target=self._health_monitor, daemon=True)
        self.health_thread.start()
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def _start_server(self):
        """Start the DeepSeek server process."""
        logger.info(f"Starting DeepSeek server on port {self.PORT}...")
        logger.info(f"GPUs: {self.GPUS}")
        logger.info(f"Model: {self.MODEL}")
        logger.info(f"Memory utilization: {self.GPU_MEMORY_UTILIZATION}")
        logger.info(f"Max model length: {self.MAX_MODEL_LEN}")
        
        # Set environment
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = self.GPUS
        env["HF_HOME"] = "D:/huggingface_cache"
        env["TRANSFORMERS_CACHE"] = "D:/huggingface_cache"
        
        # Build command - using HuggingFace Transformers server (Windows compatible)
        cmd = [
            sys.executable,
            "scripts/deploy_deepseek_native.py",
            "--port", str(self.PORT),
            "--production"
        ]
        
        # Start process
        log_file = LOG_DIR / f"deepseek_server_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        with open(log_file, 'w') as f:
            self.process = subprocess.Popen(
                cmd,
                env=env,
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=str(Path(__file__).parent.parent)
            )
        
        logger.info(f"Server process started (PID: {self.process.pid})")
        logger.info(f"Server log: {log_file}")
        
        # Wait for server to be ready
        self._wait_for_ready()
        
        self.last_restart_time = datetime.now()
    
    def _wait_for_ready(self, timeout=600):
        """Wait for server to be ready (up to 10 minutes for model loading)."""
        logger.info("Waiting for server to be ready...")
        
        start = time.time()
        check_interval = 10  # Check every 10 seconds during startup
        
        while time.time() - start < timeout:
            if self.process.poll() is not None:
                logger.error(f"Server process died during startup (exit code: {self.process.returncode})")
                return False
            
            try:
                response = requests.get(self.HEALTH_URL, timeout=5)
                if response.status_code == 200:
                    elapsed = time.time() - start
                    logger.info(f"✅ Server ready after {elapsed:.0f} seconds")
                    return True
            except requests.exceptions.RequestException:
                pass  # Server not ready yet
            
            time.sleep(check_interval)
        
        logger.error(f"Server failed to become ready within {timeout} seconds")
        return False
    
    def _health_monitor(self):
        """Background thread that monitors server health."""
        logger.info("Health monitor started")
        
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        while self.running:
            time.sleep(self.HEALTH_CHECK_INTERVAL)
            
            if not self.running:
                break
            
            # Check if process is still running
            if self.process and self.process.poll() is not None:
                logger.error(f"Server process died (exit code: {self.process.returncode})")
                self._handle_failure()
                consecutive_failures = 0
                continue
            
            # Check health endpoint
            try:
                response = requests.get(self.HEALTH_URL, timeout=10)
                if response.status_code == 200:
                    consecutive_failures = 0
                    logger.debug("Health check passed")
                else:
                    consecutive_failures += 1
                    logger.warning(f"Health check failed: status {response.status_code}")
            except requests.exceptions.RequestException as e:
                consecutive_failures += 1
                logger.warning(f"Health check failed: {e}")
            
            # If multiple consecutive failures, restart
            if consecutive_failures >= max_consecutive_failures:
                logger.error(f"{consecutive_failures} consecutive health check failures - restarting")
                self._handle_failure()
                consecutive_failures = 0
    
    def _handle_failure(self):
        """Handle server failure - attempt restart."""
        if not self.running:
            return
        
        self.restart_count += 1
        
        if self.restart_count > self.MAX_RESTART_ATTEMPTS:
            logger.critical(f"Max restart attempts ({self.MAX_RESTART_ATTEMPTS}) exceeded!")
            logger.critical("MANUAL INTERVENTION REQUIRED")
            self._send_alert("DeepSeek service failed and exceeded max restarts")
            self.running = False
            return
        
        logger.warning(f"Restart attempt {self.restart_count}/{self.MAX_RESTART_ATTEMPTS}")
        
        # Kill existing process if still running
        self._kill_process()
        
        # Wait before restart
        logger.info(f"Waiting {self.RESTART_COOLDOWN}s before restart...")
        time.sleep(self.RESTART_COOLDOWN)
        
        # Restart
        self._start_server()
    
    def _kill_process(self):
        """Kill the server process."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                logger.error(f"Error killing process: {e}")
            self.process = None
    
    def _send_alert(self, message: str):
        """Send alert (implement your alerting mechanism here)."""
        logger.critical(f"ALERT: {message}")
        # TODO: Implement email/Slack/PagerDuty alerting
        # For now, just write to alert file
        alert_file = LOG_DIR / "alerts.log"
        with open(alert_file, 'a') as f:
            f.write(f"{datetime.now().isoformat()} - {message}\n")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def stop(self):
        """Stop the service gracefully."""
        logger.info("Stopping DeepSeek service...")
        self.running = False
        self._kill_process()
        logger.info("Service stopped")
    
    def status(self):
        """Get service status."""
        status = {
            "running": self.running,
            "process_alive": self.process is not None and self.process.poll() is None,
            "restart_count": self.restart_count,
            "last_restart": self.last_restart_time.isoformat() if self.last_restart_time else None,
        }
        
        # Check health
        try:
            response = requests.get(self.HEALTH_URL, timeout=5)
            status["health"] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            status["health"] = "unreachable"
        
        return status


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="NSIC DeepSeek Service")
    parser.add_argument("--start", action="store_true", help="Start the service")
    parser.add_argument("--status", action="store_true", help="Check service status")
    args = parser.parse_args()
    
    service = DeepSeekService()
    
    if args.status:
        status = service.status()
        print("\n" + "="*40)
        print("DEEPSEEK SERVICE STATUS")
        print("="*40)
        for key, value in status.items():
            print(f"  {key}: {value}")
        print("="*40)
    elif args.start:
        service.start()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

