# Step 15: Query Classification & Routing

**Version:** 1.0  
**Status:** Implementation Complete  
**Date:** 2025-11-06

## Overview

The Query Classification & Routing layer enables natural language query support in the QNWIS orchestration workflow. Users can now provide free-text queries instead of explicit intents, and the system will automatically classify the query, extract entities, determine complexity, and route to the appropriate agent(s).

### Key Features

- **Deterministic Classification**: Pure rules/regex/lexicon-based—no LLM calls, no database access
- **Entity Extraction**: Identifies sectors, metrics, and time horizons using dictionary NER
- **Complexity Assessment**: Classifies queries as simple, medium, complex, or crisis
- **Intent Mapping**: Maps natural language to registered intents with confidence scoring
- **Data Prefetch Planning**: Generates declarative prefetch specifications for downstream optimization
- **PII Safety**: Redacts email addresses and ID-like patterns from classification reasons

## Architecture

```
┌─────────────────────┐
│  Natural Language   │
│      Query          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  QueryClassifier    │
│  ┌───────────────┐  │
│  │ Lexicons      │  │
│  │ - sectors.txt │  │
│  │ - metrics.txt │  │
│  └───────────────┘  │
│  ┌───────────────┐  │
│  │Intent Catalog │  │
│  │  YAML         │  │
│  └───────────────┘  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Classification    │
│ - intents: [...]    │
│ - complexity        │
│ - entities          │
│ - confidence        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Router Node        │
│  - Validate         │
│  - Map to agents    │
│  - Determine mode   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  RoutingDecision    │
│ - agents: [...]     │
│ - mode: single/..   │
│ - prefetch: [...]   │
└─────────────────────┘
```

## Components

### 1. QueryClassifier (`classifier.py`)

**Responsibilities:**
- Load and cache lexicons (sectors, metrics)
- Load and parse intent catalog YAML
- Extract entities from query text
- Score queries against intent patterns
- Determine complexity level
- Generate data prefetch specifications

**Key Methods:**

```python
def extract_entities(text: str) -> Entities:
    """Dictionary+regex NER for sectors, metrics, time horizons."""

def classify_text(text: str) -> Classification:
    """Return intents, complexity, entities, confidence, reasons."""

def determine_data_needs(classification: Classification) -> List[Dict]:
    """Translate intents+entities into prefetch hints."""
```

**Performance:** <10ms per query on typical inputs (pure Python, no network I/O)

### 2. Intent Catalog (`intent_catalog.yml`)

YAML configuration defining:
- **Intent definitions**: keywords, hints, examples per intent
- **Urgency lexicon**: Keywords triggering crisis classification
- **Time patterns**: Regex patterns for relative/absolute time horizons
- **Complexity weights**: Scoring rules for complexity determination
- **Thresholds**: Complexity score boundaries

### 3. Lexicons

**sectors.txt**: 100+ sector/industry terms (one per line)
- Construction, Healthcare, Finance, etc.
- Normalized to lowercase for matching
- Case-insensitive search

**metrics.txt**: 150+ labour market metrics (one per line)
- retention, salary, qatarization, turnover, etc.
- Includes variations (e.g., "retention rate", "employee retention")

### 4. Router Node (`nodes/router.py`)

**Upgraded Routing Logic:**

```python
def route_intent(state, registry) -> dict:
    """
    Mode 1: Explicit intent (backward compatible)
      - Validate intent is registered
      - Create single-mode RoutingDecision
      
    Mode 2: Natural language query
      - Initialize QueryClassifier
      - Classify query text
      - Check confidence threshold
      - Filter to registered intents
      - Determine execution mode
      - Generate prefetch specs
      - Update task with classification
    """
```

### 5. Schemas (`schemas.py`)

**New Types:**

```python
Complexity = Literal["simple", "medium", "complex", "crisis"]

class Entities(BaseModel):
    sectors: List[str]
    metrics: List[str]
    time_horizon: Optional[Dict[str, Any]]

class Classification(BaseModel):
    intents: List[str]
    complexity: Complexity
    entities: Entities
    confidence: float  # [0, 1]
    reasons: List[str]

class RoutingDecision(BaseModel):
    agents: List[str]
    mode: Literal["single", "parallel", "sequential"]
    prefetch: List[Dict[str, Any]]
    notes: List[str]
```

**Extended OrchestrationTask:**
- `query_text: Optional[str]` - Natural language input
- `classification: Optional[Classification]` - Populated by router
- `intent` is now optional (required if `query_text` not provided)

## Complexity Classification

### Rules

| Complexity | Criteria |
|-----------|----------|
| **simple** | • One intent<br>• One sector (or none)<br>• No external series<br>• Time horizon ≤ 24 months |
| **medium** | • ≤3 intents<br>• OR needs 2 LMIS datasets |
| **complex** | • ≥4 intents<br>• OR multi-sector + synthesis |
| **crisis** | • Urgency keywords ("urgent", "crisis", "alert")<br>• AND fresh horizon ≤ 3 months<br>• OR high complexity score (>60) |

### Scoring Algorithm

```
score = 0

# Intent count
if intent_count == 1: score += 10
elif intent_count > 1: score += 20

# Sector count
if sector_count == 1: score += 5
elif sector_count > 1: score += 15

# Time horizon
if months <= 24: score += 5
elif months <= 48: score += 10
else: score += 15

# Urgency present
if has_urgency: score += 30

# Metric count
if metrics <= 2: score += 5
elif metrics <= 4: score += 10
else: score += 15

# Complexity mapping
0-20: simple
21-40: medium
41-60: complex
61+: crisis
```

## Execution Modes

The router determines execution mode based on complexity and intent count:

| Mode | When | Behavior |
|------|------|----------|
| **single** | Simple query OR 1 intent | Execute single agent synchronously |
| **parallel** | Medium/complex with ≤3 intents | Execute agents in parallel (Step 16+) |
| **sequential** | Complex with >3 intents | Execute agents sequentially with synthesis (Step 16+) |

**Note:** Parallel and sequential modes are reserved for future Step 16 implementation. Currently, only the primary intent executes.

## Data Prefetch

The classifier generates **declarative** prefetch specifications that describe what data will be needed, without executing any queries. These specifications are attached to the `RoutingDecision` for downstream optimization.

### Example Prefetch Specs

```python
[
    {
        'fn': 'get_retention_by_company',
        'params': {
            'sectors': ['Construction', 'Healthcare'],
            'months': 24
        }
    },
    {
        'fn': 'get_gcc_comparison',
        'params': {
            'metrics': ['wage', 'qatarization'],
            'min_countries': 4
        }
    }
]
```

**Benefits:**
- Enables parallel data loading (Step 16)
- Supports caching and deduplication
- Provides query plan introspection
- No database/HTTP access in classification phase

## Usage

### CLI

**Natural Language Query:**
```bash
qnwis workflow --query "Which companies show unusual retention in Construction last 24 months?"
```

**Explicit Intent (backward compatible):**
```bash
qnwis workflow --intent pattern.anomalies --sector Construction --months 24
```

### Programmatic API

```python
from qnwis.orchestration.schemas import OrchestrationTask
from qnwis.orchestration.graph import create_graph

# Natural language
task = OrchestrationTask(
    query_text="Urgent: spike in turnover in Hospitality now",
    user_id="analyst@mol.gov.qa",
    request_id="req_12345"
)

# Explicit intent
task = OrchestrationTask(
    intent="pattern.anomalies",
    params={"sector": "Hospitality", "z_threshold": 2.5},
    user_id="analyst@mol.gov.qa"
)

result = graph.run(task)
print(result.ok)
print(result.sections)
```

### Accessing Classification Results

```python
# After routing
if result.task.classification:
    classification = result.task.classification
    print(f"Intents: {classification.intents}")
    print(f"Complexity: {classification.complexity}")
    print(f"Confidence: {classification.confidence:.2f}")
    print(f"Entities: {classification.entities}")
    print(f"Reasons: {classification.reasons}")

# Routing decision
if result.routing_decision:
    decision = result.routing_decision
    print(f"Mode: {decision.mode}")
    print(f"Prefetch: {decision.prefetch}")
```

## Confidence Thresholds

- **Minimum confidence:** 0.55 (configurable)
- **Individual intent threshold:** 0.30
- **Confidence calculation:** `min(1.0, max_score / 5.0)`

If confidence < min_confidence, the router returns an error asking for more specific query or explicit intent.

## Edge Cases

### Low Confidence
**Query:** "Show me some data"  
**Behavior:** Error - confidence too low, suggest using explicit intent

### No Matching Intents
**Query:** "Weather forecast for Doha"  
**Behavior:** Error - no valid intents found

### Ambiguous Multi-Intent
**Query:** "Analyze everything about Construction"  
**Behavior:** Classify all matching intents, select primary (highest score), set mode=sequential

### Crisis Detection
**Query:** "Urgent: sudden retention drop now"  
**Behavior:** Complexity=crisis, mode=parallel (high priority)

### Time Horizon Parsing
- "last 24 months" → `{type: "relative", value: 24, unit: "month", months: 24}`
- "2020-2024" → `{type: "absolute", start_year: 2020, end_year: 2024, months: 60}`
- "since 2022" → `{type: "absolute", start_year: 2022, end_year: None}`

## Security

### PII Redaction

Classification reasons are scrubbed for PII patterns:
- Email addresses: `[REDACTED]`
- 10+ digit IDs: `[REDACTED]`
- SSN-like patterns: `[REDACTED]`

### Intent Allowlist

Only registered intents can be emitted. Unregistered intents from classification are filtered out before routing.

### No External Calls

Classifier is **pure and deterministic**:
- No database queries
- No HTTP requests
- No LLM API calls
- All data from local YAML/text files

## Adding New Intents

1. **Update `intent_catalog.yml`:**
   ```yaml
   pattern.seasonal_trends:
     description: "Detect seasonal patterns in labour metrics"
     keywords:
       - "seasonal"
       - "cyclical"
       - "quarterly"
     sectors_hint: true
     metrics_hint: ["employment", "hiring"]
     examples:
       - "Seasonal hiring patterns in Retail"
   ```

2. **Update `schemas.py` Intent literal:**
   ```python
   Intent = Literal[
       # ... existing intents ...
       "pattern.seasonal_trends",
   ]
   ```

3. **Register in agent registry:**
   ```python
   registry.register("pattern.seasonal_trends", agent, "detect_seasonal")
   ```

4. **Add test samples to `routing_samples.jsonl`**

## Tuning Thresholds

### Adjust Minimum Confidence

```python
classifier = QueryClassifier(
    catalog_path=...,
    sector_lex=...,
    metric_lex=...,
    min_confidence=0.60  # Raise for stricter matching
)
```

### Modify Complexity Weights

Edit `intent_catalog.yml`:
```yaml
complexity_weights:
  intent_count:
    single: 12  # Increase weight
    multiple: 25
  urgency_present: 40  # Higher priority for urgency
```

### Update Complexity Thresholds

Edit `intent_catalog.yml`:
```yaml
complexity_thresholds:
  simple: 0-25   # Wider simple range
  medium: 26-45
  complex: 46-65
  crisis: 66+
```

## Testing

Comprehensive test suite in `tests/unit/orchestration/`:
- `test_classifier.py` - Classification logic
- `test_classifier_entities.py` - Entity extraction
- `test_classifier_complexity.py` - Complexity determination
- `test_router_classification.py` - Router integration

Integration tests in `tests/integration/`:
- `test_routing_samples.py` - All 40 routing samples
- `test_end_to_end_query.py` - Full workflow with natural language

**Coverage:** >90%

**Run tests:**
```bash
pytest tests/unit/orchestration/test_classifier*.py -v
pytest tests/integration/test_routing*.py -v
```

## Performance

- **Classification time:** <10ms per query (typical)
- **Lexicon loading:** One-time at startup (~5ms)
- **Catalog parsing:** One-time at startup (~10ms)
- **Memory footprint:** ~2MB for classifier + lexicons

## Observability

Classification events are logged via standard Python logging:

```python
import logging
logging.getLogger("qnwis.orchestration.classifier").setLevel(logging.INFO)
```

**Log levels:**
- INFO: Classification results, intent scores
- DEBUG: Entity extraction details, pattern matches
- WARNING: Low confidence, no intents found
- ERROR: File not found, invalid catalog

**Metrics (Step 14 integration):**
```python
metrics.record_classification(
    confidence=classification.confidence,
    intents=classification.intents,
    complexity=classification.complexity
)
```

## Limitations & Future Work

### Current Limitations

1. **English & Arabic mixed support**: Lexicons primarily English; Arabic NER not yet implemented
2. **Simple pattern matching**: No semantic understanding (e.g., synonyms not handled)
3. **Single primary intent**: Multi-intent execution deferred to Step 16
4. **Prefetch not executed**: Declarative only; execution in Step 16

### Future Enhancements (Step 16+)

1. **Multi-intent coordination**: Execute multiple agents and synthesize results
2. **Prefetch optimization**: Parallel data loading, caching, deduplication
3. **Arabic NLP**: Dedicated Arabic lexicons and pattern matching
4. **Semantic matching**: Embeddings-based intent similarity (optional)
5. **User feedback loop**: Collect corrections to improve classification

## Backward Compatibility

The router fully supports the existing explicit intent API:

```python
# Old code continues to work
task = OrchestrationTask(intent="pattern.anomalies", params={...})
```

No breaking changes to:
- `WorkflowState`
- `OrchestrationResult`
- Agent interfaces
- Graph structure

## File Manifest

```
src/qnwis/orchestration/
├── classifier.py              # QueryClassifier implementation
├── intent_catalog.yml         # Intent definitions and patterns
├── keywords/
│   ├── sectors.txt           # Sector lexicon (100+ terms)
│   └── metrics.txt           # Metric lexicon (150+ terms)
├── examples/
│   └── routing_samples.jsonl # 40 test samples
├── schemas.py                # Extended with Classification types
└── nodes/
    └── router.py             # Upgraded with classification support

src/qnwis/cli/
└── qnwis_workflow.py         # Added --query flag

src/qnwis/docs/orchestration/
└── step15_routing.md         # This document

tests/
├── unit/orchestration/
│   ├── test_classifier.py
│   ├── test_classifier_entities.py
│   ├── test_classifier_complexity.py
│   └── test_router_classification.py
└── integration/
    ├── test_routing_samples.py
    └── test_end_to_end_query.py
```

## References

- **Step 14**: Orchestration graph and metrics foundation
- **Step 16**: (Planned) Multi-agent coordination and prefetch execution
- **Step 18**: (Planned) Crisis escalation and real-time monitoring
- **DETERMINISTIC_DATA_LAYER_SPECIFICATION.md**: Data access patterns
- **Complete_API_Specification.md**: API contracts

---

**Implementation Status:** ✅ Complete  
**Test Coverage:** >90%  
**Performance:** <10ms classification  
**Security:** PII-safe, no external calls  
**Backward Compatible:** Yes
