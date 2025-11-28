#!/usr/bin/env python3
"""
NSIC DeepSeek Native Deployment

Deploys DeepSeek-R1-Distill-Llama-70B directly on Windows using HuggingFace.
Uses tensor parallelism across GPUs 2-3 for Instance 1.

This is an alternative to vLLM Docker for Windows systems.
"""

import sys
import os

# CRITICAL: Use D: drive for HuggingFace cache (C: has limited space)
os.environ["HF_HOME"] = "D:\\huggingface_cache"
os.environ["HUGGINGFACE_HUB_CACHE"] = "D:\\huggingface_cache\\hub"
os.environ["TRANSFORMERS_CACHE"] = "D:\\huggingface_cache\\transformers"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check requirements
def check_requirements():
    """Check if required packages are installed."""
    missing = []
    
    try:
        import torch
        if not torch.cuda.is_available():
            print("❌ CUDA not available!")
            return False
        print(f"✅ PyTorch {torch.__version__} with CUDA")
    except ImportError:
        missing.append("torch")
    
    try:
        import transformers
        print(f"✅ Transformers {transformers.__version__}")
    except ImportError:
        missing.append("transformers")
    
    try:
        import accelerate
        print(f"✅ Accelerate installed")
    except ImportError:
        missing.append("accelerate")
    
    try:
        from fastapi import FastAPI
        print(f"✅ FastAPI installed")
    except ImportError:
        missing.append("fastapi")
    
    try:
        import uvicorn
        print(f"✅ Uvicorn installed")
    except ImportError:
        missing.append("uvicorn")
    
    if missing:
        print(f"\n❌ Missing packages: {missing}")
        print(f"Install with: pip install {' '.join(missing)}")
        return False
    
    return True


def get_device_map_for_instance(instance_id: int) -> Dict[str, Any]:
    """
    Get device map for specific instance.
    
    Instance 1: GPUs 2, 3
    Instance 2: GPUs 6, 7
    """
    if instance_id == 1:
        gpus = [2, 3]
    else:
        gpus = [6, 7]
    
    return {
        "device_map": "auto",
        "max_memory": {
            gpus[0]: "75GB",
            gpus[1]: "75GB",
        }
    }


class DeepSeekServer:
    """Native DeepSeek server using HuggingFace Transformers."""
    
    MODEL_NAME = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B"
    # Smaller model for faster testing - uncomment below for production
    # MODEL_NAME = "deepseek-ai/DeepSeek-R1-Distill-Llama-8B"
    
    def __init__(
        self,
        instance_id: int = 1,
        port: int = 8001,
        use_small_model: bool = True,  # Set to False for 70B
    ):
        """
        Initialize DeepSeek server.
        
        Args:
            instance_id: 1 for GPUs 2-3, 2 for GPUs 6-7
            port: Port to listen on
            use_small_model: Use 8B model for faster loading (dev mode)
        """
        self.instance_id = instance_id
        self.port = port
        self.model = None
        self.tokenizer = None
        
        # Use smaller model for faster testing
        if use_small_model:
            self.model_name = "deepseek-ai/DeepSeek-R1-Distill-Llama-8B"
            logger.info("Using DeepSeek-8B for faster loading (dev mode)")
        else:
            self.model_name = self.MODEL_NAME
            logger.info("Using DeepSeek-70B (production mode)")
        
        # GPU allocation - use 4 GPUs for 70B to maintain full FP16 quality
        # GPUs 4-5 reserved for Knowledge Graph and Deep Verification
        if instance_id == 1:
            self.gpus = [2, 3, 6, 7]  # 320GB total - combines both DeepSeek slots
        else:
            self.gpus = [2, 3]  # Fallback to smaller allocation if needed
        
        # Final GPU map:
        # GPU 0-1: Premium Embeddings (instructor-xl)
        # GPU 2-3, 6-7: DeepSeek 70B (full FP16, 320GB)
        # GPU 4: Knowledge Graph (hybrid CPU-GPU)
        # GPU 5: Deep Verification (cross-encoder, NLI)
        
        logger.info(f"DeepSeek Instance {instance_id} will use GPUs: {self.gpus}")
    
    def load_model(self):
        """Load the DeepSeek model with tensor parallelism - FULL FP16 for maximum quality."""
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import gc
        
        logger.info(f"Loading model: {self.model_name}")
        logger.info(f"Target GPUs: {self.gpus}")
        
        # Clear GPU memory first
        gc.collect()
        torch.cuda.empty_cache()
        for gpu_id in self.gpus:
            with torch.cuda.device(gpu_id):
                torch.cuda.empty_cache()
        
        start_time = time.time()
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True,
        )
        
        is_70b = "70B" in self.model_name
        
        if is_70b:
            # FULL FP16 for maximum quality - distributed across 4 GPUs (320GB)
            logger.info("Loading 70B in FULL FP16 precision across 4 GPUs for maximum quality")
            
            # Set visible GPUs for this model
            os.environ["CUDA_VISIBLE_DEVICES"] = ",".join(str(g) for g in self.gpus)
            
            # Max memory per GPU (after CUDA_VISIBLE_DEVICES remapping)
            max_memory = {i: "75GB" for i in range(len(self.gpus))}
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16,  # Full FP16 - NO quantization
                device_map="auto",
                trust_remote_code=True,
                max_memory=max_memory,
            )
        else:
            # For 8B model, use single GPU in FP16
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16,
                device_map={"": f"cuda:{self.gpus[0]}"},
                trust_remote_code=True,
            )
        
        load_time = time.time() - start_time
        logger.info(f"Model loaded in {load_time:.1f}s - FULL PRECISION (no quantization)")
        
        # Log memory usage
        for i in range(len(self.gpus)):
            mem = torch.cuda.memory_allocated(i) / 1e9
            logger.info(f"GPU {self.gpus[i]} (device {i}): {mem:.1f}GB allocated")
        
        return self
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        """Generate response from prompt."""
        import torch
        
        inputs = self.tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=temperature > 0,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Remove the prompt from response
        if response.startswith(prompt):
            response = response[len(prompt):].strip()
        
        return response
    
    def start_server(self):
        """Start FastAPI server."""
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
        import uvicorn
        
        app = FastAPI(title=f"NSIC DeepSeek Instance {self.instance_id}")
        
        class ChatMessage(BaseModel):
            role: str
            content: str
        
        class ChatRequest(BaseModel):
            model: str = "deepseek"
            messages: List[ChatMessage]
            max_tokens: int = 2048
            temperature: float = 0.7
            top_p: float = 0.9
        
        class ChatResponse(BaseModel):
            id: str
            object: str = "chat.completion"
            model: str
            choices: List[Dict[str, Any]]
            usage: Dict[str, int]
        
        @app.get("/health")
        async def health():
            return {"status": "healthy", "instance": self.instance_id}
        
        @app.get("/v1/models")
        async def list_models():
            return {
                "data": [{
                    "id": self.model_name,
                    "object": "model",
                    "owned_by": "deepseek",
                }]
            }
        
        @app.post("/v1/chat/completions")
        async def chat_completions(request: ChatRequest) -> ChatResponse:
            # Build prompt from messages
            prompt = ""
            for msg in request.messages:
                if msg.role == "system":
                    prompt += f"System: {msg.content}\n\n"
                elif msg.role == "user":
                    prompt += f"User: {msg.content}\n\n"
                elif msg.role == "assistant":
                    prompt += f"Assistant: {msg.content}\n\n"
            prompt += "Assistant: "
            
            # Generate response
            try:
                response_text = self.generate(
                    prompt=prompt,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    top_p=request.top_p,
                )
                
                return ChatResponse(
                    id=f"chatcmpl-{int(time.time())}",
                    model=self.model_name,
                    choices=[{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": response_text,
                        },
                        "finish_reason": "stop",
                    }],
                    usage={
                        "prompt_tokens": len(prompt.split()),
                        "completion_tokens": len(response_text.split()),
                        "total_tokens": len(prompt.split()) + len(response_text.split()),
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        logger.info(f"Starting server on port {self.port}...")
        uvicorn.run(app, host="0.0.0.0", port=self.port)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy DeepSeek natively")
    parser.add_argument("--instance", type=int, default=1, choices=[1, 2],
                       help="Instance ID (1 for GPUs 2-3, 2 for GPUs 6-7)")
    parser.add_argument("--port", type=int, default=8001,
                       help="Port to listen on")
    parser.add_argument("--production", action="store_true",
                       help="Use 70B model (slower loading)")
    parser.add_argument("--check-only", action="store_true",
                       help="Only check requirements")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("NSIC DeepSeek Native Deployment")
    print("=" * 60)
    print()
    
    print("Checking requirements...")
    if not check_requirements():
        sys.exit(1)
    
    if args.check_only:
        print("\n✅ All requirements met!")
        sys.exit(0)
    
    # Set port based on instance
    port = args.port if args.port != 8001 else (8001 if args.instance == 1 else 8002)
    
    print()
    print(f"Deploying Instance {args.instance} on port {port}")
    print(f"GPUs: {[2, 3] if args.instance == 1 else [6, 7]}")
    print(f"Mode: {'Production (70B)' if args.production else 'Development (8B)'}")
    print()
    
    server = DeepSeekServer(
        instance_id=args.instance,
        port=port,
        use_small_model=not args.production,
    )
    
    server.load_model()
    server.start_server()


if __name__ == "__main__":
    main()

