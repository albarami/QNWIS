#!/usr/bin/env python3
"""
NSIC DeepSeek ExLlamaV2 Server

Runs a single DeepSeek instance using ExLlamaV2 for fast 4-bit inference.
Each instance uses one A100 GPU (~37GB VRAM for 70B 4-bit model).

Usage:
    python run_exllama_server.py --gpu_id 0 --port 8001
"""

import os
import sys
import time
import logging
import argparse
from typing import List, Dict, Any, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Run ExLlamaV2 DeepSeek Server")
    parser.add_argument("--model", type=str, default="D:/models/deepseek-70b-gptq-4bit",
                       help="Path to GPTQ model")
    parser.add_argument("--gpu_id", type=int, required=True,
                       help="GPU ID to use (0-7)")
    parser.add_argument("--port", type=int, required=True,
                       help="Port to listen on")
    parser.add_argument("--max_seq_len", type=int, default=8192,
                       help="Maximum sequence length")
    return parser.parse_args()


class ExLlamaServer:
    """ExLlamaV2 server for fast 4-bit inference."""
    
    def __init__(self, model_path: str, gpu_id: int, max_seq_len: int = 8192):
        self.model_path = model_path
        self.gpu_id = gpu_id
        self.max_seq_len = max_seq_len
        self.model = None
        self.cache = None
        self.tokenizer = None
        self.generator = None
        
    def load_model(self):
        """Load the ExLlamaV2 model."""
        import torch
        from exllamav2 import (
            ExLlamaV2,
            ExLlamaV2Config,
            ExLlamaV2Cache,
            ExLlamaV2Tokenizer,
        )
        from exllamav2.generator import ExLlamaV2StreamingGenerator, ExLlamaV2Sampler
        
        logger.info(f"Loading ExLlamaV2 model from: {self.model_path}")
        logger.info(f"Target GPU: {self.gpu_id} (visible as cuda:0 after CUDA_VISIBLE_DEVICES)")
        
        start_time = time.time()
        
        # Configure model
        self.config = ExLlamaV2Config()
        self.config.model_dir = self.model_path
        self.config.prepare()
        
        # Set max sequence length
        self.config.max_seq_len = self.max_seq_len
        
        # Load model - use gpu_split to allocate ~70GB on single GPU (A100 80GB)
        # After CUDA_VISIBLE_DEVICES=X, the GPU appears as device 0
        self.model = ExLlamaV2(self.config)
        # gpu_split specifies GB per GPU - 70GB for the 4-bit 70B model
        self.model.load(gpu_split=[70])
        
        # Load tokenizer
        self.tokenizer = ExLlamaV2Tokenizer(self.config)
        
        # Create cache (batch_size=1 for single requests)
        self.cache = ExLlamaV2Cache(self.model, batch_size=1)
        
        # Create streaming generator for real-time debate display
        self.generator = ExLlamaV2StreamingGenerator(
            self.model,
            self.cache,
            self.tokenizer,
        )
        
        load_time = time.time() - start_time
        logger.info(f"Model loaded in {load_time:.1f}s")
        
        # Log memory usage (device 0 after CUDA_VISIBLE_DEVICES remapping)
        mem_allocated = torch.cuda.memory_allocated(0) / 1e9
        mem_reserved = torch.cuda.memory_reserved(0) / 1e9
        logger.info(f"GPU (physical {self.gpu_id}): {mem_allocated:.1f}GB allocated, {mem_reserved:.1f}GB reserved")
        
    def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
    ) -> Dict[str, Any]:
        """Generate response from messages with streaming support."""
        from exllamav2.generator import ExLlamaV2Sampler
        
        # Build prompt from messages
        prompt = self._build_prompt(messages)
        
        # Tokenize prompt to get input_ids tensor
        input_ids = self.tokenizer.encode(prompt)
        prompt_tokens = input_ids.shape[-1]
        
        # Set up sampling settings
        settings = ExLlamaV2Sampler.Settings()
        settings.temperature = temperature
        settings.top_p = top_p
        settings.top_k = top_k
        settings.token_repetition_penalty = 1.05
        
        # Start streaming generation
        start_time = time.time()
        
        self.generator.set_stop_conditions([self.tokenizer.eos_token_id])
        self.generator.begin_stream_ex(input_ids, settings)
        
        generated_text = ""
        completion_tokens = 0
        
        while True:
            # stream() returns (text_chunk, eos, token_ids, ...)
            result = self.generator.stream()
            chunk = result[0]  # text chunk
            eos = result[1]    # end of sequence flag
            
            if chunk:
                generated_text += chunk
            completion_tokens += 1
            
            if eos or completion_tokens >= max_tokens:
                break
        
        gen_time = time.time() - start_time
        tokens_per_sec = completion_tokens / gen_time if gen_time > 0 else 0
        
        logger.info(f"Generated {completion_tokens} tokens in {gen_time:.1f}s ({tokens_per_sec:.1f} tok/s)")
        
        return {
            "content": generated_text.strip(),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_time_ms": gen_time * 1000,
            "tokens_per_second": tokens_per_sec,
        }
    
    def _build_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Build prompt from chat messages using HuggingFace tokenizer's chat template."""
        # Use the HuggingFace tokenizer for correct chat template formatting
        from transformers import AutoTokenizer
        
        if not hasattr(self, '_hf_tokenizer'):
            self._hf_tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        
        prompt = self._hf_tokenizer.apply_chat_template(
            messages, 
            tokenize=False, 
            add_generation_prompt=True
        )
        return prompt


def create_app(server: ExLlamaServer, gpu_id: int):
    """Create FastAPI app."""
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    import torch
    
    app = FastAPI(title=f"NSIC DeepSeek ExLlamaV2 - GPU {gpu_id}")
    
    class ChatMessage(BaseModel):
        role: str
        content: str
    
    class ChatRequest(BaseModel):
        model: str = "deepseek-exllama"
        messages: List[ChatMessage]
        max_tokens: int = 2048
        temperature: float = 0.7
        top_p: float = 0.9
    
    @app.get("/health")
    async def health():
        # Device 0 after CUDA_VISIBLE_DEVICES remapping
        mem = torch.cuda.memory_allocated(0) / 1e9
        return {
            "status": "healthy",
            "gpu_id": gpu_id,  # Physical GPU ID for reference
            "model_loaded": server.model is not None,
            "gpu_memory_gb": round(mem, 2),
        }
    
    @app.post("/v1/chat/completions")
    async def chat_completions(request: ChatRequest):
        if server.model is None:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        try:
            messages = [{"role": m.role, "content": m.content} for m in request.messages]
            result = server.generate(
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
            )
            
            return {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "deepseek-exllama",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result["content"],
                    },
                    "finish_reason": "stop",
                }],
                "usage": {
                    "prompt_tokens": result["prompt_tokens"],
                    "completion_tokens": result["completion_tokens"],
                    "total_tokens": result["prompt_tokens"] + result["completion_tokens"],
                },
                "instance_id": gpu_id,
                "tokens_per_second": result["tokens_per_second"],
            }
        except Exception as e:
            logger.error(f"Generation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return app


def main():
    args = parse_args()
    
    # Set CUDA device
    os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu_id)
    
    logger.info("=" * 60)
    logger.info(f"NSIC DeepSeek ExLlamaV2 Server")
    logger.info(f"GPU: {args.gpu_id}, Port: {args.port}")
    logger.info("=" * 60)
    
    # Create and load server
    server = ExLlamaServer(
        model_path=args.model,
        gpu_id=0,  # After CUDA_VISIBLE_DEVICES, always use 0
        max_seq_len=args.max_seq_len,
    )
    server.load_model()
    
    # Create app
    app = create_app(server, args.gpu_id)
    
    # Run server
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()

