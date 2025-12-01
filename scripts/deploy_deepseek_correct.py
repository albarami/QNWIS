#!/usr/bin/env python3
"""
NSIC DeepSeek CORRECT Deployment

CORRECT GPU Allocation:
- GPU 0-1: Embeddings (instructor-xl)
- GPU 2-3: DeepSeek Instance 1 (port 8001)
- GPU 4:   Knowledge Graph  
- GPU 5:   Deep Verification
- GPU 6-7: DeepSeek Instance 2 (port 8002)

This script starts the CORRECT configuration.
"""

import sys
import os
import subprocess
import time
import signal

# CRITICAL: Set cache to D: drive
os.environ["HF_HOME"] = "D:\\huggingface_cache"
os.environ["HUGGINGFACE_HUB_CACHE"] = "D:\\huggingface_cache\\hub"
os.environ["TRANSFORMERS_CACHE"] = "D:\\huggingface_cache\\transformers"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from typing import Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class InstanceConfig:
    """Configuration for a DeepSeek instance."""
    instance_id: int
    gpu_ids: list
    port: int
    scenarios: str
    
    @property
    def cuda_devices(self) -> str:
        return ",".join(str(g) for g in self.gpu_ids)


# CORRECT GPU ALLOCATION - DO NOT MODIFY
INSTANCE_1 = InstanceConfig(
    instance_id=1,
    gpu_ids=[2, 3],  # GPU 2-3 ONLY
    port=8001,
    scenarios="1-12 (Economic + Competitive)"
)

INSTANCE_2 = InstanceConfig(
    instance_id=2,
    gpu_ids=[6, 7],  # GPU 6-7 ONLY
    port=8002,
    scenarios="13-24 (Policy + Timing)"
)


class DeepSeekInstance:
    """A single DeepSeek instance on specific GPUs."""
    
    MODEL_NAME = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B"
    
    def __init__(self, config: InstanceConfig):
        self.config = config
        self.model = None
        self.tokenizer = None
        self.app = None
        
    def load_model(self):
        """Load model on the CORRECT GPUs."""
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import gc
        
        # CRITICAL: Set CUDA_VISIBLE_DEVICES BEFORE any torch operations
        os.environ["CUDA_VISIBLE_DEVICES"] = self.config.cuda_devices
        logger.info(f"CUDA_VISIBLE_DEVICES set to: {self.config.cuda_devices}")
        
        # Clear any existing CUDA context
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        # Verify GPU access
        gpu_count = torch.cuda.device_count()
        logger.info(f"Instance {self.config.instance_id}: {gpu_count} GPUs visible")
        
        if gpu_count < 2:
            raise RuntimeError(f"Need 2 GPUs, only {gpu_count} visible")
        
        for i in range(gpu_count):
            name = torch.cuda.get_device_name(i)
            mem = torch.cuda.get_device_properties(i).total_memory / 1e9
            logger.info(f"  Device {i}: {name} ({mem:.0f}GB)")
        
        logger.info(f"Loading {self.MODEL_NAME}...")
        start = time.time()
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.MODEL_NAME,
            trust_remote_code=True,
        )
        
        # Load model across the 2 visible GPUs (they appear as 0 and 1 due to CUDA_VISIBLE_DEVICES)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.MODEL_NAME,
            torch_dtype=torch.float16,  # Full FP16 - NO quantization
            device_map="auto",
            trust_remote_code=True,
            max_memory={
                0: "75GB",  # First GPU in CUDA_VISIBLE_DEVICES
                1: "75GB",  # Second GPU in CUDA_VISIBLE_DEVICES
            },
        )
        
        elapsed = time.time() - start
        logger.info(f"Model loaded in {elapsed:.0f}s on GPUs {self.config.gpu_ids}")
        
        return self
    
    def generate(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7) -> str:
        """Generate response."""
        import torch
        
        inputs = self.tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                do_sample=temperature > 0,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        if response.startswith(prompt):
            response = response[len(prompt):].strip()
        
        return response
    
    def start_server(self):
        """Start FastAPI server with multi-worker support."""
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
        from typing import List, Dict, Any
        import uvicorn
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        app = FastAPI(title=f"NSIC DeepSeek Instance {self.config.instance_id}")
        
        # Thread pool for non-blocking inference
        executor = ThreadPoolExecutor(max_workers=2)
        
        class ChatMessage(BaseModel):
            role: str
            content: str
        
        class ChatRequest(BaseModel):
            model: str = "deepseek"
            messages: List[ChatMessage]
            max_tokens: int = 2048
            temperature: float = 0.7
        
        @app.get("/health")
        async def health():
            """Health check - MUST respond immediately."""
            return {
                "status": "healthy",
                "instance": self.config.instance_id,
                "gpus": self.config.gpu_ids,
                "port": self.config.port,
            }
        
        @app.get("/v1/models")
        async def list_models():
            return {"data": [{"id": self.MODEL_NAME, "object": "model"}]}
        
        @app.post("/v1/chat/completions")
        async def chat_completions(request: ChatRequest):
            """Chat completion with async inference."""
            prompt = ""
            for msg in request.messages:
                if msg.role == "system":
                    prompt += f"System: {msg.content}\n\n"
                elif msg.role == "user":
                    prompt += f"User: {msg.content}\n\n"
                elif msg.role == "assistant":
                    prompt += f"Assistant: {msg.content}\n\n"
            prompt += "Assistant: "
            
            try:
                # Run inference in thread pool to not block health checks
                loop = asyncio.get_event_loop()
                response_text = await loop.run_in_executor(
                    executor,
                    lambda: self.generate(prompt, request.max_tokens, request.temperature)
                )
                
                return {
                    "id": f"chatcmpl-{int(time.time())}",
                    "object": "chat.completion",
                    "model": self.MODEL_NAME,
                    "choices": [{
                        "index": 0,
                        "message": {"role": "assistant", "content": response_text},
                        "finish_reason": "stop",
                    }],
                    "usage": {
                        "prompt_tokens": len(prompt.split()),
                        "completion_tokens": len(response_text.split()),
                        "total_tokens": len(prompt.split()) + len(response_text.split()),
                    }
                }
            except Exception as e:
                logger.error(f"Generation error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        logger.info(f"Starting server on port {self.config.port}...")
        uvicorn.run(app, host="0.0.0.0", port=self.config.port, workers=1)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy DeepSeek Instance")
    parser.add_argument("--instance", type=int, required=True, choices=[1, 2],
                       help="Instance 1 (GPUs 2-3, port 8001) or Instance 2 (GPUs 6-7, port 8002)")
    args = parser.parse_args()
    
    config = INSTANCE_1 if args.instance == 1 else INSTANCE_2
    
    print("=" * 60)
    print(f"NSIC DeepSeek Instance {config.instance_id}")
    print("=" * 60)
    print(f"GPUs: {config.gpu_ids}")
    print(f"Port: {config.port}")
    print(f"Scenarios: {config.scenarios}")
    print(f"Model: DeepSeek-R1-Distill-Llama-70B (Full FP16)")
    print("=" * 60)
    
    instance = DeepSeekInstance(config)
    instance.load_model()
    instance.start_server()


if __name__ == "__main__":
    main()

