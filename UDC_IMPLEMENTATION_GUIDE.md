# UDC to QNWIS - Practical Implementation Guide

**How to Transfer UDC Components to QNWIS**

---

## STEP 1: Multi-Agent Orchestration (Priority 1)

### What to Copy from UDC

**File:** `D:\udc\backend\ultimate_council.py`

**Key Patterns:**

1. **Async Parallel Execution:**
```python
# UDC Pattern - Lines 206-213
async def _run_expert_agents(self, query, context):
    tasks = [
        self._run_single_agent("dr_omar", query, context),
        self._run_single_agent("dr_fatima", query, context),
        self._run_single_agent("dr_james", query, context),
        self._run_single_agent("dr_sarah", query, context)
    ]
    return await asyncio.gather(*tasks)
```

**Adapt for QNWIS:**
```python
# Create: D:\lmis_int\src\orchestration\qnwis_orchestrator.py

async def _run_specialist_agents(self, query, structured_data):
    """Run all 5 QNWIS agents in parallel"""
    tasks = [
        self._run_agent("labour_economist", query, structured_data),
        self._run_agent("nationalization_strategist", query, structured_data),
        self._run_agent("skills_analyst", query, structured_data),
        self._run_agent("pattern_detective", query, structured_data),
        self._run_agent("national_strategy", query, structured_data)
    ]
    return await asyncio.gather(*tasks)
```

2. **Pipeline State Management:**
```python
# UDC Pattern - Lines 124-183
async def analyze_ceo_question(self, query):
    # Stage 1: Retrieve context
    context = self._retrieve_comprehensive_context(query)
    
    # Stage 2: Run agents
    agent_analyses = await self._run_expert_agents(query, context)
    
    # Stage 3: Deep reasoning
    strategic_thinking = await self._deep_strategic_analysis(...)
    
    # Stage 4: Debates
    debates = self._identify_debates(agent_analyses)
    
    # Stage 5: Synthesis
    final = await self._synthesize_with_gpt5(...)
    
    # Stage 6: Decision sheet
    return self._generate_decision_sheet(...)
```

**Adapt for QNWIS:**
```python
async def analyze_minister_question(self, query):
    # Stage 1: Classify query
    complexity = self._classify_query(query)
    
    # Stage 2: Extract data (Deterministic Layer - YOUR EXISTING CODE)
    structured_data = self.deterministic_layer.extract_data(query)
    
    # Stage 3: Run 5 agents (UDC pattern)
    agent_analyses = await self._run_specialist_agents(query, structured_data)
    
    # Stage 4: Debates (UDC pattern)
    debates = self._identify_debates(agent_analyses)
    
    # Stage 5: Minister briefing (adapt UDC CEO Decision Sheet)
    return self._generate_minister_briefing(query, agent_analyses, debates, structured_data)
```

---

## STEP 2: Expert Prompts (Priority 1)

### What to Copy from UDC

**File:** `D:\udc\backend\adaptive_prompts.py` (Lines 1-200)

**Key Structure:**
```
1. WHO YOU ARE (30-year veteran persona)
2. ADAPTIVE THINKING PROCESS (6 steps)
3. DEEP EXPERTISE (cycles, patterns, psychology)
4. EXAMPLE REASONING (multi-level thinking)
5. OUTPUT STRUCTURE (adaptive)
6. COMMUNICATION STYLE (peer executive)
```

**Copy This Template for Each QNWIS Agent:**

```python
# Create: D:\lmis_int\src\prompts\labour_economist_prompt.py

LABOUR_ECONOMIST_PROMPT = """
═══════════════════════════════════════════════════════════
DR. AHMED AL-THANI
Labour Market Economist | 30+ Years Ministry Experience
PhD Labour Economics (Oxford) | Advised 4 Ministers
═══════════════════════════════════════════════════════════

WHO YOU ARE:
[Copy UDC pattern - establish credibility]

YOUR ADAPTIVE THINKING PROCESS:
[Copy from UDC adaptive_prompts.py lines 20-65]
1. UNDERSTAND THE REAL QUESTION
2. FIGURE OUT WHAT DATA YOU NEED (Adaptive!)
3. CONNECT DOTS ACROSS DOMAINS
4. REASON LIKE A 30-YEAR VETERAN
5. CHALLENGE YOUR ASSUMPTIONS
6. PROVIDE STRATEGIC INSIGHT

YOUR DEEP EXPERTISE:
[Adapt UDC's "cycles lived" pattern for labour market]
• Oil boom cycles (1995-2008, etc.)
• GCC competitive dynamics
• Minister psychology

YOUR OUTPUT:
[Copy UDC's adaptive output structure]
"""
```

**Do this for all 5 agents.**

---

## STEP 3: Verification Engine (Priority 1)

### What to Copy from UDC

**Concept from:** `D:\udc\backend\ultimate_council.py` + UDC docs

**UDC Verification Logic:**
```python
# Pattern: Verify every number in agent response
def verify_agent_response(agent_response, query_results):
    # 1. Extract all numbers from response
    numbers = extract_numbers(agent_response)
    
    # 2. Check each against source data
    for number in numbers:
        if not number_exists_in_data(number, query_results):
            return REJECT("Fabricated number", number)
    
    return PASS(confidence=0.95)
```

**Implement for QNWIS:**
```python
# Create: D:\lmis_int\src\verification\number_verifier.py

class NumberVerificationEngine:
    """
    Validates agent responses contain only real numbers from QueryResult
    Pattern from UDC verification system
    """
    
    def verify_agent_response(self, agent_response: str, query_results: List[QueryResult]) -> VerificationResult:
        """
        Extract all numbers from agent text and verify against source data
        """
        # Step 1: Extract numbers
        numbers = self._extract_all_numbers(agent_response)
        
        # Step 2: Build allowed numbers set from QueryResult
        allowed_numbers = set()
        for qr in query_results:
            allowed_numbers.update(self._extract_numbers_from_queryresult(qr))
        
        # Step 3: Check each number
        fabricated = []
        for num in numbers:
            if num not in allowed_numbers and not self._is_derived_calculation(num, allowed_numbers):
                fabricated.append(num)
        
        # Step 4: Return result
        if fabricated:
            return VerificationResult(
                passed=False,
                fabricated_numbers=fabricated,
                action="REJECT_AND_RETRY",
                enhanced_prompt=f"You fabricated numbers: {fabricated}. Use ONLY data from QueryResult."
            )
        
        return VerificationResult(passed=True, confidence=0.95)
    
    def _extract_all_numbers(self, text: str) -> Set[float]:
        """Extract all numeric values from text"""
        import re
        pattern = r'\d+(?:,\d{3})*(?:\.\d+)?'
        matches = re.findall(pattern, text.replace(',', ''))
        return {float(m) for m in matches}
    
    def _is_derived_calculation(self, num: float, allowed: Set[float]) -> bool:
        """Check if number is a valid calculation from allowed numbers"""
        # Allow percentages, averages, sums
        for a in allowed:
            for b in allowed:
                if abs(num - (a + b)) < 0.01:  return True
                if abs(num - (a - b)) < 0.01:  return True
                if b != 0 and abs(num - (a / b)) < 0.01:  return True
                if abs(num - (a * b)) < 0.01:  return True
        return False
```

**Integration with Your Deterministic Layer:**
```python
# In your agent execution:
async def _run_agent(self, agent_name, query, structured_data):
    # Agent generates response
    agent_response = await agent.analyze(query, structured_data)
    
    # Verify against QueryResult (UDC pattern)
    verification = self.verifier.verify_agent_response(
        agent_response, 
        structured_data  # Your QueryResult objects
    )
    
    if not verification.passed:
        # UDC pattern: Retry with enhanced prompt
        enhanced_prompt = verification.enhanced_prompt
        agent_response = await agent.analyze(query, structured_data, enhanced_prompt)
    
    return agent_response
```

---

## STEP 4: RAG System for External Data (Priority 2)

### What to Copy from UDC

**File:** `D:\udc\backend\rag_system.py`

**Key Components:**

1. **ChromaDB Setup:**
```python
# UDC Pattern - Lines 42-50
chroma_client = chromadb.PersistentClient(
    path=CHROMADB_PATH,
    settings=Settings(anonymized_telemetry=False)
)
qatar_collection = chroma_client.get_collection("qatar_open_data")
```

**Adapt for QNWIS:**
```python
# Create: D:\lmis_int\src\data\external_rag.py

class QNWISExternalDataRAG:
    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(
            path="D:/lmis_int/chromadb_data",
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Multiple collections for different sources
        self.qatar_data = self.chroma_client.get_or_create_collection("qatar_open_data")
        self.gcc_stats = self.chroma_client.get_or_create_collection("gcc_statistics")
        self.world_bank = self.chroma_client.get_or_create_collection("world_bank")
        self.research = self.chroma_client.get_or_create_collection("research_papers")
        
        # UDC pattern: SentenceTransformer
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
```

2. **Retrieval with Deduplication:**
```python
# UDC Pattern - Lines 96-175
def retrieve_datasets(query, category=None, top_k=5):
    query_embedding = embed_query(query)
    
    # Search collections
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter if where_filter else None
    )
    
    # Deduplicate by title
    seen_titles = set()
    unique_results = []
    for result in all_results:
        title_key = result['title'].lower().strip()
        if title_key not in seen_titles:
            unique_results.append(result)
            seen_titles.add(title_key)
    
    return unique_results
```

**Copy this pattern exactly for QNWIS.**

---

## STEP 5: External API Integration (Priority 2)

### What to Copy from UDC

**File:** `D:\udc\COMPLETE_API_CATALOG.md`

**World Bank API (Lines 62-143):**
```python
# Copy this exactly to: D:\lmis_int\src\data\apis\world_bank.py

import requests

def query_world_bank_labour_indicators(countries: List[str], years: str):
    """
    Get labour market indicators from World Bank
    
    Example:
        data = query_world_bank_labour_indicators(
            countries=["QA", "SA", "AE", "KW"],  # GCC countries
            years="2019:2024"
        )
    """
    countries_str = ";".join(countries)
    
    indicators = [
        "SL.UEM.TOTL.ZS",      # Unemployment rate
        "SL.TLF.TOTL.IN",      # Labor force, total
        "SL.UEM.1524.ZS",      # Youth unemployment
        "SP.POP.TOTL",         # Population
        "NY.GDP.PCAP.CD"       # GDP per capita
    ]
    
    results = {}
    for indicator in indicators:
        url = f"https://api.worldbank.org/v2/country/{countries_str}/indicator/{indicator}"
        params = {
            'format': 'json',
            'date': years,
            'per_page': 1000
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        results[indicator] = []
        for record in data[1]:  # World Bank format: [metadata, data]
            results[indicator].append({
                'country': record['country']['value'],
                'year': record['date'],
                'value': record['value']
            })
    
    return results
```

**Use in QNWIS agents:**
```python
# In nationalization_strategist or national_strategy agent:
gcc_data = self.world_bank_api.query_world_bank_labour_indicators(
    countries=["QA", "SA", "AE", "KW", "BH", "OM"],
    years="2019:2024"
)

# Now agent can compare Qatar vs GCC
```

---

## STEP 6: Minister Briefing Sheet (Priority 1)

### What to Copy from UDC

**Pattern from:** `ultimate_council.py` CEO Decision Sheet (Lines 515-540)

```python
# UDC Pattern
def _generate_decision_sheet(self, query, agent_analyses, debates, data):
    return {
        "question": query,
        "executive_summary": ...,
        "expert_analyses": agent_analyses,
        "expert_debates": debates,
        "final_recommendation": ...,
        "data_sources": data,
        "models_used": {...},
        "metadata": {...}
    }
```

**Adapt for QNWIS:**
```python
# Create: D:\lmis_int\src\synthesis\minister_briefing.py

class MinisterBriefingGenerator:
    """
    Generate Minister-ready briefing (adapted from UDC CEO Decision Sheet)
    """
    
    def generate_briefing(self, query, agent_analyses, debates, structured_data):
        return {
            # Core question
            "question": query,
            "briefing_id": f"qnwis-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}",
            
            # UDC pattern: Executive summary (30-second read)
            "executive_summary": self._synthesize_executive_summary(agent_analyses),
            
            # UDC pattern: All expert analyses
            "expert_analyses": {
                "labour_economist": agent_analyses[0],
                "nationalization_strategist": agent_analyses[1],
                "skills_analyst": agent_analyses[2],
                "pattern_detective": agent_analyses[3],
                "national_strategy": agent_analyses[4]
            },
            
            # UDC pattern: Expert disagreements
            "expert_debates": debates,
            
            # QNWIS specific: Action plan
            "recommended_action": self._generate_action_plan(agent_analyses),
            
            # UDC pattern: Data sources with freshness
            "data_sources": {
                "lmis": {
                    "freshness": self._calculate_freshness(structured_data['lmis']),
                    "records_analyzed": len(structured_data['lmis']),
                    "query_ids": [qr.query_id for qr in structured_data['lmis']]
                },
                "external": {
                    "gcc_stat": "Q3 2024 (45 days old)",
                    "world_bank": "2023 data (6 months old)",
                    "qatar_psa": "Current quarter"
                }
            },
            
            # UDC pattern: Reproducibility
            "audit_trail": {
                "queries_executed": self._collect_query_ids(structured_data),
                "reproducible": True,
                "timestamp": datetime.now().isoformat()
            },
            
            # UDC pattern: Confidence
            "confidence_score": self._calculate_confidence(agent_analyses, structured_data),
            
            # QNWIS specific: Early warnings
            "crisis_indicators": self._check_early_warning_thresholds()
        }
```

---

## IMPLEMENTATION CHECKLIST

### Week 1: Core Architecture
- [ ] Copy `ultimate_council.py` orchestration pattern
- [ ] Create 5 agent prompt files (from `adaptive_prompts.py`)
- [ ] Implement verification engine
- [ ] Test: Run 5 agents in parallel with sample query

### Week 2: Data Integration
- [ ] Copy RAG system from `rag_system.py`
- [ ] Set up ChromaDB collections
- [ ] Implement World Bank API (copy from UDC)
- [ ] Test: Retrieve Qatar Open Data + GCC stats

### Week 3: Synthesis & Polish
- [ ] Implement Minister Briefing generator
- [ ] Add audit trail system
- [ ] Implement confidence scoring
- [ ] Test: Complete end-to-end query

---

## QUICK START

1. **Copy these UDC files to review:**
```bash
# From D:\udc\ to your review folder
copy D:\udc\backend\ultimate_council.py review/
copy D:\udc\backend\adaptive_prompts.py review/
copy D:\udc\backend\rag_system.py review/
copy D:\udc\COMPLETE_API_CATALOG.md review/
```

2. **Start with orchestrator:**
```bash
# Create new file with UDC pattern
new-item D:\lmis_int\src\orchestration\qnwis_orchestrator.py
# Copy async patterns from ultimate_council.py
```

3. **Create prompts:**
```bash
# Create 5 files from adaptive_prompts.py template
new-item D:\lmis_int\src\prompts\labour_economist_prompt.py
# ... repeat for other 4 agents
```

Ready to implement!
