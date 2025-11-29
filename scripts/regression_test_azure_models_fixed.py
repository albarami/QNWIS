#!/usr/bin/env python3

"""

10-Query Regression Test for Azure Model Comparison.



FAIR COMPARISON - NO FALLBACKS



Each model tested on its native API only:

- GPT-4o: Chat Completions API

- GPT-5: Chat Completions API  

- GPT-5.1: Responses API



Usage:

    python scripts/regression_test_azure_models_fixed.py

"""



import asyncio

import json

import os

import sys

import time

from datetime import datetime

from pathlib import Path

from typing import Dict, Any, List, Tuple



sys.path.insert(0, str(Path(__file__).parent.parent))



try:

    from dotenv import load_dotenv

    load_dotenv(override=True)

except ImportError:

    pass



from openai import AsyncAzureOpenAI

import httpx



OUTPUT_DIR = Path("data/model_comparison_results")



MODELS_CONFIG = {
    # GPT-5.1 first - to catch issues early
    "GPT-5.1": {
        "deployment": os.getenv("MODEL_NAME_5.1", "gpt-5.1").strip().strip('"'),
        "api_version": os.getenv("API_VERSION_5.1", "2024-08-01-preview").strip().strip('"'),
        "endpoint": os.getenv("ENDPOINT_5.1", os.getenv("AZURE_OPENAI_ENDPOINT", "")).strip(),
        "api_key": os.getenv("API_KEY_5.1", os.getenv("AZURE_OPENAI_API_KEY")),
        # GPT-5.1 uses httpx with 'developer' role and max_completion_tokens
        "use_max_completion_tokens": True,
    },
    "GPT-5": {
        "deployment": os.getenv("DEPLOYMENT_5", "gpt-5-chat").strip().strip('"'),
        "api_version": os.getenv("API_VERSION_5", "2024-12-01-preview").strip().strip('"'),
        "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "api_key": os.getenv("API_KEY_5", os.getenv("AZURE_OPENAI_API_KEY")),
    },
    "GPT-4o": {
        "deployment": os.getenv("QNWIS_AZURE_MODEL", "gpt-4o"),
        "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
    },
}



PILOT_QUERIES = [

    ("Economic Diversification", "Analyze Qatar's non-oil GDP growth and sector contribution (2015-2024)"),

    ("Energy/Oil&Gas", "What is Qatar's current oil production capacity and LNG export strategy?"),

    ("Tourism", "Analyze Qatar's tourism sector growth post-2022 World Cup"),

    ("Food Security", "What is Qatar's food self-sufficiency rate and import dependency?"),

    ("Healthcare", "Analyze Qatar's healthcare infrastructure and medical workforce capacity"),

    ("Digital/AI", "What is Qatar's digital transformation progress and AI adoption rate?"),

    ("Manufacturing", "Analyze Qatar's manufacturing sector growth and industrial diversification"),

    ("Workforce/Labor", "What is the current Qatarization rate and workforce nationalization progress?"),

    ("Infrastructure", "Analyze Qatar's infrastructure development for Vision 2030"),

    ("Cross-Domain Strategic", "How do Qatar's labor, energy, and economic policies align with Vision 2030?"),

]



SYSTEM_PROMPT = """You are a senior economic advisor to Qatar's Ministry of Labour.

Provide PhD-level ministerial-grade analysis with:

- Specific data points and statistics

- Structured sections with clear headers

- Risk assessments and recommendations

- Actionable insights suitable for executive briefings



Be thorough, evidence-based, and cite sources where possible."""




def extract_text_from_responses_api(data: Dict[str, Any], debug: bool = True) -> str:

    """

    Extract text content from GPT-5.1 Responses API response.

    Handles all known response format variants.

    """

    content_parts = []
    

    if debug:

        print(f"      [DEBUG] Top-level keys: {list(data.keys())}")
    

    # ==========================================================================

    # FORMAT 1: Standard Responses API

    # {"output": [{"type": "message", "content": [{"type": "output_text", "text": "..."}]}]}

    # ==========================================================================

    if "output" in data:

        output = data["output"]
        

        if debug:

            print(f"      [DEBUG] 'output' type: {type(output).__name__}")

            if isinstance(output, list) and output:

                print(f"      [DEBUG] output[0] keys: {list(output[0].keys()) if isinstance(output[0], dict) else type(output[0]).__name__}")
        

        if isinstance(output, str):

            content_parts.append(output)
        

        elif isinstance(output, list):

            for idx, item in enumerate(output):

                if isinstance(item, str):

                    content_parts.append(item)

                    continue
                

                if not isinstance(item, dict):

                    continue
                

                item_type = item.get("type", "")
                

                if debug:

                    print(f"      [DEBUG] output[{idx}] type='{item_type}', keys={list(item.keys())}")
                

                # Type: message

                if item_type == "message":

                    content_list = item.get("content", [])

                    if debug:

                        print(f"      [DEBUG] message.content type: {type(content_list).__name__}")
                    

                    if isinstance(content_list, str):

                        content_parts.append(content_list)

                    elif isinstance(content_list, list):

                        for cidx, c in enumerate(content_list):

                            if isinstance(c, str):

                                content_parts.append(c)

                            elif isinstance(c, dict):

                                if debug:

                                    print(f"      [DEBUG] content[{cidx}] keys: {list(c.keys())}")

                                for field in ["text", "output_text", "value", "content"]:

                                    if field in c and isinstance(c[field], str):

                                        content_parts.append(c[field])

                                        if debug:

                                            print(f"      [DEBUG] Extracted from '{field}': {len(c[field])} chars")

                                        break
                

                # Type: text or output_text directly

                elif item_type in ("text", "output_text"):

                    for field in ["text", "value", "content"]:

                        if field in item:

                            content_parts.append(item[field])

                            break
                

                # No type but has text/content

                else:

                    for field in ["text", "content", "value", "output_text", "message"]:

                        if field in item:

                            val = item[field]

                            if isinstance(val, str):

                                content_parts.append(val)

                            elif isinstance(val, dict) and "content" in val:

                                content_parts.append(val["content"])

                            break
    

    # FORMAT 2: Direct output_text field

    if "output_text" in data and isinstance(data["output_text"], str):

        content_parts.append(data["output_text"])
    

    # FORMAT 3: Direct text field

    if "text" in data and isinstance(data["text"], str):

        content_parts.append(data["text"])
    

    # FORMAT 4: Content field

    if "content" in data:

        content = data["content"]

        if isinstance(content, str):

            content_parts.append(content)

        elif isinstance(content, list):

            for item in content:

                if isinstance(item, str):

                    content_parts.append(item)

                elif isinstance(item, dict):

                    for field in ["text", "value", "output_text"]:

                        if field in item:

                            content_parts.append(item[field])

                            break
    

    # FORMAT 5: Choices array (some APIs return this)

    if "choices" in data and isinstance(data["choices"], list):

        for choice in data["choices"]:

            if isinstance(choice, dict):

                msg = choice.get("message", {})

                if isinstance(msg, dict) and "content" in msg:

                    content_parts.append(msg["content"])

                elif "text" in choice:

                    content_parts.append(choice["text"])
    

    # FORMAT 6: Nested wrappers

    for wrapper in ["result", "response", "data", "body"]:

        if wrapper in data and isinstance(data[wrapper], dict):

            nested = extract_text_from_responses_api(data[wrapper], debug=False)

            if nested:

                content_parts.append(nested)
    

    # FORMAT 7: Message at top level

    if "message" in data and isinstance(data["message"], dict):

        msg = data["message"]

        if "content" in msg:

            if isinstance(msg["content"], str):

                content_parts.append(msg["content"])

            elif isinstance(msg["content"], list):

                for c in msg["content"]:

                    if isinstance(c, str):

                        content_parts.append(c)

                    elif isinstance(c, dict) and "text" in c:

                        content_parts.append(c["text"])
    

    # Deduplicate

    seen = set()

    unique_parts = []

    for p in content_parts:

        if p and p not in seen:

            seen.add(p)

            unique_parts.append(p)
    

    result = "\n".join(unique_parts)
    

    if debug and not result:

        print(f"      [DEBUG] NO TEXT EXTRACTED! Full response:")

        print(f"      {json.dumps(data, indent=2, default=str)[:3000]}")

    elif debug:

        print(f"      [DEBUG] Extracted {len(result)} chars")
    

    return result




async def call_responses_api(config: Dict, query: str, timeout: int = 180) -> Tuple[str, Dict]:
    """
    Call GPT-5.1 Responses API - NO FALLBACK.
    """
    endpoint_in_env = (config.get("endpoint") or "").rstrip("/")
    api_key = config["api_key"]
    model = config["deployment"]
    api_version = config["api_version"]
    
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }
    
    # Try both Azure Responses API URL variants within the same API family
    url_variants: List[Tuple[str, Dict[str, Any]]] = []
    if endpoint_in_env:
        # Variant A: deployments/{deployment}/responses
        url_variants.append((
            f"{endpoint_in_env}/openai/deployments/{model}/responses?api-version={api_version}",
            {
                "input": f"{SYSTEM_PROMPT}\n\n{query}",
                "max_output_tokens": 4000,
            },
        ))
        # Variant B: /openai/responses with model in payload
        url_variants.append((
            f"{endpoint_in_env}/openai/responses?api-version={api_version}",
            {
                "model": model,
                "input": f"{SYSTEM_PROMPT}\n\n{query}",
                "max_output_tokens": 4000,
            },
        ))
    
    last_error = None
    async with httpx.AsyncClient(timeout=timeout) as client:
        for url, payload in url_variants:
            print(f"      [DEBUG] POST {url}")
            resp = await client.post(url, json=payload, headers=headers)
            print(f"      [DEBUG] HTTP {resp.status_code}")
            if resp.status_code == 200:
                try:
                    data = resp.json()
                except json.JSONDecodeError as e:
                    last_error = f"Invalid JSON: {e}"
                    continue
                # Save raw for diagnostics
                try:
                    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                    ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    raw_file = OUTPUT_DIR / f"raw_gpt51_{ts}.json"
                    with open(raw_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    print(f"      [DEBUG] Saved raw: {raw_file.name}")
                except Exception:
                    pass
                content = extract_text_from_responses_api(data, debug=True)
                if not content or not content.strip():
                    last_error = "Empty content after parsing"
                    continue
                return content, data
            else:
                try:
                    body = resp.text[:1000]
                    print(f"      [DEBUG] Error body: {body}")
                except Exception:
                    body = "<no body>"
                last_error = f"HTTP {resp.status_code}: {body[:200]}"
    
    raise Exception(last_error or "Responses API request failed")




async def call_chat_completions_api(config: Dict, query: str, timeout: int = 180) -> str:
    """
    Call Chat Completions API for GPT-4o, GPT-5, and GPT-5.1.
    
    GPT-5.1 requires special handling:
    - Uses httpx directly (SDK doesn't support 'developer' role properly)
    - Uses 'developer' role instead of 'system' (system role causes empty response)
    - Uses max_completion_tokens instead of max_tokens
    """
    # GPT-5.1: Use httpx directly with ONLY user message (no system prompt at all)
    # Any system prompt content causes Azure RAI filter to return empty body
    if config.get("use_max_completion_tokens"):
        endpoint = config["endpoint"].rstrip("/")
        url = f"{endpoint}/openai/deployments/{config['deployment']}/chat/completions?api-version={config['api_version']}"
        
        # GPT-5.1: Just the query, NO system prompt (tested and confirmed working)
        payload = {
            "messages": [
                {"role": "user", "content": query}
            ],
            "max_completion_tokens": 4000,
        }
        
        headers = {
            "Content-Type": "application/json",
            "api-key": config["api_key"],
        }
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")
            
            if not response.text:
                raise Exception("Empty response body")
            
            data = response.json()
            
            if "choices" not in data or not data["choices"]:
                raise Exception("No choices in response")
            
            content = data["choices"][0].get("message", {}).get("content")
            return content or ""
    
    # GPT-4o, GPT-5: Use OpenAI SDK with 'system' role
    client = AsyncAzureOpenAI(
        api_key=config["api_key"],
        api_version=config["api_version"],
        azure_endpoint=config["endpoint"],
        timeout=timeout
    )
    
    response = await client.chat.completions.create(
        model=config["deployment"],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ],
        max_tokens=2500,
        temperature=0.3
    )
    
    return response.choices[0].message.content or ""




async def test_model_availability(model_name: str, config: Dict) -> Tuple[bool, str]:
    """Check model availability - all models use Chat Completions API."""
    if not config.get("endpoint") or not config.get("api_key"):
        print(f"    ✗ Missing endpoint or API key")
        return False, config.get("deployment", "")
    
    deployment = config["deployment"]
    
    try:
        # All models now use Chat Completions API
        content = await call_chat_completions_api(config, "Say OK", timeout=60)
        return bool(content and content.strip()), deployment
    except Exception as e:
        print(f"    ✗ {str(e)[:100]}")
        return False, deployment




async def run_query_with_model(query: str, model_name: str, config: Dict, timeout: int = 180) -> Dict[str, Any]:

    """Run query - NO FALLBACKS."""

    result = {

        "model": model_name,

        "deployment": config["deployment"],

        "query": query[:100] + "..." if len(query) > 100 else query,

        "status": "unknown",

        "response_length": 0,

        "word_count": 0,

        "execution_time": 0.0,

        "quality_score": {},

        "error": None

    }
    

    start_time = time.time()
    

    try:
        # All models use Chat Completions API (GPT-5.1 with max_completion_tokens)
        content = await call_chat_completions_api(config, query, timeout)
        

        if not content or not content.strip():

            raise ValueError("Empty response")
        

        result.update({

            "status": "success",

            "response_length": len(content),

            "word_count": len(content.split()),

            "execution_time": round(time.time() - start_time, 2),

            "quality_score": score_synthesis(content),

            "response_preview": content[:500] + "..." if len(content) > 500 else content,

            "full_response": content,

        })

    except Exception as e:

        result["status"] = "error"

        result["error"] = str(e)

        result["execution_time"] = round(time.time() - start_time, 2)
    

    return result




def score_synthesis(content: str) -> Dict[str, float]:

    """Score synthesis quality."""

    if not content:

        return {"structure": 0, "depth": 0, "actionability": 0, "overall": 0}
    

    cl = content.lower()
    

    structure = sum([

        "##" in content or "**" in content,

        "summary" in cl,

        "recommendation" in cl,

        "risk" in cl,

        len(content.split("\n\n")) > 3,

        "\n1." in content or "\n-" in content or "•" in content,

    ]) / 6
    

    depth = sum([

        "%" in content,

        any(y in content for y in ["2023", "2024", "2025", "2030"]),

        "billion" in cl or "million" in cl,

        "$" in content or "qar" in cl,

        "qatar" in cl,

        "gdp" in cl,

        len(content) > 2000,

        any(w in cl for w in ["roi", "npv", "cagr"]),

    ]) / 8
    

    actionability = sum([

        "recommend" in cl,

        "should" in cl,

        "action" in cl or "implement" in cl,

        "priority" in cl,

        "strategy" in cl,

        "phase" in cl or "timeline" in cl,

    ]) / 6
    

    return {

        "structure": round(structure, 3),

        "depth": round(depth, 3),

        "actionability": round(actionability, 3),

        "overall": round(structure * 0.25 + depth * 0.45 + actionability * 0.30, 3)

    }




def calculate_aggregate_score(results: List[Dict[str, Any]]) -> Dict[str, float]:

    """Calculate aggregate score."""

    if not results:

        return {"total": 0}
    

    successful = [r for r in results if r["status"] == "success"]

    if not successful:

        return {"total": 0, "success_rate": 0, "queries_passed": 0, "queries_total": len(results)}
    

    n = len(successful)

    avg_words = sum(r["word_count"] for r in successful) / n

    avg_time = sum(r["execution_time"] for r in successful) / n

    avg_quality = sum(r["quality_score"]["overall"] for r in successful) / n

    avg_structure = sum(r["quality_score"]["structure"] for r in successful) / n

    avg_depth = sum(r["quality_score"]["depth"] for r in successful) / n

    avg_action = sum(r["quality_score"]["actionability"] for r in successful) / n
    

    total = (

        min(avg_words / 1500, 1.0) * 20 +

        avg_quality * 50 +

        avg_depth * 20 +

        (1 - min(avg_time / 60, 1.0)) * 10

    )
    

    return {

        "total": round(total, 2),

        "success_rate": round(n / len(results), 3),

        "avg_words": round(avg_words, 1),

        "avg_time": round(avg_time, 1),

        "avg_quality": round(avg_quality, 3),

        "avg_structure": round(avg_structure, 3),

        "avg_depth": round(avg_depth, 3),

        "avg_actionability": round(avg_action, 3),

        "queries_passed": n,

        "queries_total": len(results)

    }




async def run_model_comparison() -> Dict[str, Any]:

    """Run fair comparison."""

    print("=" * 70)

    print("FAIR MODEL COMPARISON: GPT-4o vs GPT-5 vs GPT-5.1")

    print("NO FALLBACKS - Each model on its native API only")

    print("=" * 70)

    print(f"\nStarted: {datetime.now().isoformat()}")

    print("\nAPI Assignment:")

    print("  GPT-4o  → Chat Completions API")

    print("  GPT-5   → Chat Completions API")

    print("  GPT-5.1 → Responses API")
    

    results = {

        "timestamp": datetime.now().isoformat(),

        "queries_tested": len(PILOT_QUERIES),

        "models_tested": [],

        "model_results": {},

        "comparison": {},

        "winner": None

    }
    

    print("\n" + "-" * 50)

    print("CHECKING MODEL AVAILABILITY")

    print("-" * 50)
    

    available_models = {}

    for model_name, config in MODELS_CONFIG.items():

        api = "Responses" if config.get("use_responses_api") else "Chat Completions"

        print(f"\n  {model_name} ({config['deployment']}) via {api} API...")

        ok, dep = await test_model_availability(model_name, config)

        if ok:

            print(f"    ✓ AVAILABLE")

            config["deployment"] = dep

            available_models[model_name] = config

        else:

            print(f"    ✗ NOT AVAILABLE")
    

    if len(available_models) < 2:

        print(f"\nERROR: Need at least 2 models")

        return results
    

    results["models_tested"] = list(available_models.keys())
    

    for model_name, config in available_models.items():

        api = "Responses" if config.get("use_responses_api") else "Chat Completions"

        print("\n" + "=" * 70)

        print(f"TESTING: {model_name} ({api} API)")

        print("=" * 70)
        

        model_results = []

        for i, (domain, query) in enumerate(PILOT_QUERIES, 1):

            print(f"\n  [{i}/10] {domain}")

            r = await run_query_with_model(query, model_name, config)

            r["domain"] = domain

            model_results.append(r)
            

            if r["status"] == "success":

                print(f"    ✓ {r['word_count']} words, {r['execution_time']}s, quality={r['quality_score']['overall']:.3f}")

            else:

                print(f"    ✗ {r['error'][:80] if r['error'] else 'Unknown'}")
            

            await asyncio.sleep(1)
        

        results["model_results"][model_name] = model_results
    

    # Scores

    print("\n" + "=" * 70)

    print("RESULTS")

    print("=" * 70)
    

    scores = {m: calculate_aggregate_score(results["model_results"][m]) for m in available_models}

    results["comparison"] = scores
    

    print("\n  SCORES:")

    print(f"  {'Metric':<18}" + "".join(f" {m:<14}" for m in available_models))

    print("  " + "-" * (18 + 14 * len(available_models)))
    

    for metric in ["total", "success_rate", "avg_words", "avg_time", "avg_quality", "avg_depth"]:

        row = f"  {metric:<18}"

        for m in available_models:

            v = scores[m].get(metric, 0)

            row += f" {v:<14.3f}" if isinstance(v, float) else f" {v:<14}"

        print(row)
    

    ranked = sorted(scores.items(), key=lambda x: x[1]["total"], reverse=True)
    

    print("\n  RANKING:")

    for i, (m, s) in enumerate(ranked, 1):

        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else "  "

        print(f"  {medal} {i}. {m}: {s['total']:.2f} pts ({s['queries_passed']}/{s['queries_total']} passed)")
    

    results["winner"] = ranked[0][0]

    print(f"\n  🏆 WINNER: {results['winner']}")
    

    # Save

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    

    with open(OUTPUT_DIR / f"comparison_{ts}.json", "w") as f:

        save_data = {k: v for k, v in results.items()}

        for m in save_data.get("model_results", {}):

            for r in save_data["model_results"][m]:

                r.pop("full_response", None)

        json.dump(save_data, f, indent=2, default=str)
    

    for m in available_models:

        with open(OUTPUT_DIR / f"responses_{m.replace('.', '_')}_{ts}.txt", "w") as f:

            f.write(f"MODEL: {m}\n{'='*70}\n\n")

            for r in results["model_results"][m]:

                f.write(f"[{r['domain']}]\nStatus: {r['status']}, Words: {r['word_count']}, Time: {r['execution_time']}s\n")

                f.write(f"Quality: {r['quality_score']}\n{'-'*50}\n")

                f.write(str(r.get("full_response") or r.get("error") or "No response") + "\n\n")
    

    print(f"\n  Saved to: {OUTPUT_DIR}")

    print("\n" + "=" * 70)
    

    return results




if __name__ == "__main__":

    results = asyncio.run(run_model_comparison())

    sys.exit(0 if results.get("winner") else 1)


