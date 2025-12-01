#!/usr/bin/env python3
"""
NSIC Llama 3.3 ExLlamaV2 Server

Runs a single Llama 3.3 70B instance using ExLlamaV2 for fast 4-bit inference.
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
    parser = argparse.ArgumentParser(description="Run ExLlamaV2 Llama 3.3 Server")
    parser.add_argument("--model", type=str, default="D:/models/Llama-3.3-70B-Instruct-exl2-8.0",
                       help="Path to EXL2 model")
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
        
        # CRITICAL: Lock to prevent concurrent generation (causes garbage output)
        import threading
        self._generation_lock = threading.Lock()
        
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
    
    def _check_garbage_patterns(self, text: str) -> bool:
        """
        Check if generated text contains garbage patterns.
        
        Added per E2E Assessment Report 2025-12-01 to stop generation
        early when garbage is detected.
        
        Args:
            text: Generated text so far
            
        Returns:
            True if garbage pattern detected, False otherwise
        """
        import re
        
        # Garbage patterns from E2E test analysis
        garbage_patterns = [
            '-##-##-##-##-',           # Hash loop (300+ times in test)
            '.<     .<     .<',        # Dot-bracket loop (200+ times)
            'owieowie',                # Nonsense pattern
            '{{{{{{{{{{',              # Brace spam
            '}}}}}}}}}}',              # Close brace spam
            '**********',              # Asterisk spam
            '##########',              # Hash spam
            '><><><><><',              # Angle bracket alternation
            '][][][][][',              # Bracket alternation
            '##SGN',                   # SGN pattern from test
        ]
        
        for pattern in garbage_patterns:
            if pattern in text:
                logger.warning(f"Garbage pattern detected: '{pattern}'")
                return True
        
        # Check for Chinese text (shouldn't appear in English generation)
        chinese_matches = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]{3,}', text)
        if len(chinese_matches) > 2:
            logger.warning(f"Chinese text detected: {chinese_matches[:3]}")
            return True
        
        # Check for extreme character repetition (30+)
        if re.search(r'(.)\1{30,}', text):
            logger.warning("Excessive character repetition detected")
            return True
        
        # Check for very long "words" (likely nonsense) - DISABLED
        # This was causing too many false positives with Llama 3.3
        # The model sometimes generates compound words that are legitimate
        # words = text.split()[-20:]
        # Keeping only the direction word check below
        
        # Check for repetitive direction/adverb spam (e.g., "onwards upwards sideways backwards")
        direction_words = ['onwards', 'upwards', 'downwards', 'sideways', 'backwards', 'forwards', 
                          'everywhere', 'anywhere', 'anytime', 'evermore', 'forever', 'etcetera',
                          'infinitum', 'peripheries', 'circumferences']
        direction_count = sum(1 for w in text.lower().split() if w in direction_words)
        if direction_count > 8:
            logger.warning(f"Repetitive word loop detected: {direction_count} direction/filler words")
            return True
        
        return False
        
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
        
        # CRITICAL: Acquire lock to prevent concurrent generation
        with self._generation_lock:
            return self._generate_impl(messages, max_tokens, temperature, top_p, top_k)
    
    def _generate_impl(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        top_p: float,
        top_k: int,
    ) -> Dict[str, Any]:
        """Internal generate implementation (called with lock held)."""
        from exllamav2.generator import ExLlamaV2Sampler
        
        # Build prompt from messages
        prompt = self._build_prompt(messages)
        
        # Tokenize prompt to get input_ids tensor
        input_ids = self.tokenizer.encode(prompt)
        prompt_tokens = input_ids.shape[-1]
        
        # Set up sampling settings - FIXED per E2E Assessment Report 2025-12-01
        settings = ExLlamaV2Sampler.Settings()
        settings.temperature = temperature if temperature else 0.5  # Lower default for stability
        settings.top_p = top_p if top_p else 0.9
        settings.top_k = 40  # Slightly more focused (was 50)
        settings.token_repetition_penalty = 1.50  # INCREASED to 1.50 to prevent repetitive loops
        
        # Start streaming generation
        # NOTE: begin_stream_ex handles cache management internally
        start_time = time.time()
        
        # Llama 3.3 stop tokens: EOS, end-of-turn, and "assistant" keyword
        stop_conditions = [
            self.tokenizer.eos_token_id,
            "assistant",  # Stop if model outputs another turn marker
            "<|eot_id|>",  # Llama 3 end-of-turn
            "<|end_of_text|>",  # Llama 3 end-of-text
        ]
        self.generator.set_stop_conditions(stop_conditions)
        self.generator.begin_stream_ex(input_ids, settings)
        
        generated_text = ""
        completion_tokens = 0
        garbage_detected = False
        
        while True:
            # stream() returns (text_chunk, eos, token_ids, ...)
            result = self.generator.stream()
            chunk = result[0]  # text chunk
            eos = result[1]    # end of sequence flag
            
            if chunk:
                generated_text += chunk
            completion_tokens += 1
            
            # FIX: Early stop on garbage patterns during streaming
            if completion_tokens % 50 == 0:  # Check every 50 tokens
                garbage_detected = self._check_garbage_patterns(generated_text)
                if garbage_detected:
                    logger.warning(f"Garbage pattern detected at token {completion_tokens}, stopping early")
                    break
            
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
            self._hf_tokenizer = AutoTokenizer.from_pretrained(self.model_path, local_files_only=True)
        
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
    
    app = FastAPI(title=f"NSIC Llama 3.3 ExLlamaV2 - GPU {gpu_id}")
    
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
                "model": "llama-3.3-70b-exl2",
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

