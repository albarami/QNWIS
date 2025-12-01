"""Test Auto-GPTQ model generation speed."""
import torch
import time
import sys
import traceback

try:
    print("=" * 60)
    print("Testing Auto-GPTQ DeepSeek Model")
    print("=" * 60)
    sys.stdout.flush()

    print(f"\nGPU memory before: {torch.cuda.memory_allocated(0)/1e9:.1f} GB")
    sys.stdout.flush()
    
    print(f"Total GPU memory: {torch.cuda.get_device_properties(0).total_memory/1e9:.1f} GB")
    sys.stdout.flush()
    
    print(f"CUDA available: {torch.cuda.is_available()}")
    print(f"CUDA version: {torch.version.cuda}")
    sys.stdout.flush()

    print("\nImporting auto_gptq...")
    sys.stdout.flush()
    from auto_gptq import AutoGPTQForCausalLM
    print("auto_gptq imported")
    sys.stdout.flush()
    
    print("Importing tokenizer...")
    sys.stdout.flush()
    from transformers import AutoTokenizer
    print("tokenizer imported")
    sys.stdout.flush()

    model_path = "D:/models/deepseek-70b-gptq-4bit"
    print(f"\nLoading tokenizer from {model_path}...")
    sys.stdout.flush()
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    print("Tokenizer loaded")
    sys.stdout.flush()

    print("\nLoading model (this takes ~2-5 minutes)...")
    sys.stdout.flush()
    start = time.time()
    model = AutoGPTQForCausalLM.from_quantized(
        model_path,
        device="cuda:0",
        use_safetensors=True,
        trust_remote_code=True,
        use_triton=False,
    )
    load_time = time.time() - start
    print(f"Model loaded in {load_time:.1f}s")
    print(f"GPU memory after load: {torch.cuda.memory_allocated(0)/1e9:.1f} GB")
    sys.stdout.flush()

    # Test generation
    print("\n" + "-" * 40)
    print("Testing generation speed...")
    sys.stdout.flush()

    prompt = "What is 2+2? Answer in one word:"
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda:0")

    # Warmup
    print("Warmup run...")
    sys.stdout.flush()
    with torch.no_grad():
        _ = model.generate(**inputs, max_new_tokens=10, do_sample=False)
    print("Warmup done")
    sys.stdout.flush()

    # Timed run
    print("Timed run (50 tokens)...")
    sys.stdout.flush()
    start = time.time()
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=50, do_sample=False)
    gen_time = time.time() - start

    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    tokens_generated = outputs.shape[1] - inputs.input_ids.shape[1]

    print(f"\nPrompt: {prompt}")
    print(f"Response: {response}")
    print(f"\nGeneration time: {gen_time:.2f}s")
    print(f"Tokens generated: {tokens_generated}")
    print(f"Speed: {tokens_generated/gen_time:.2f} tokens/sec")

    print("\n" + "=" * 60)
    print("RESULT: Auto-GPTQ inference completed")
    print("=" * 60)
    
except Exception as e:
    print(f"\n\nERROR: {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.exit(1)
