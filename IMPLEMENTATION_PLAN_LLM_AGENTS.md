# Implementation Plan: Real LLM-Powered Multi-Agent System

**Project**: Qatar National Workforce Intelligence System (QNWIS)  
**Client**: Ministry of Labour, Qatar  
**Timeline**: 4 weeks  
**Status**: CRITICAL REBUILD REQUIRED

---

## Phase 1: LLM Integration Foundation (Week 1)

### Day 1-2: LLM Client Wrapper

**Objective**: Create unified interface for Anthropic Claude and OpenAI GPT with streaming support.

**Files to Create**:
```
src/qnwis/llm/
├── __init__.py
├── client.py          # Main LLM client
├── config.py          # Model configuration
├── exceptions.py      # Custom exceptions
└── types.py           # Type definitions
```

**Implementation**:

```python
# src/qnwis/llm/client.py
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from typing import AsyncIterator, Optional
import os
import logging

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Unified LLM client supporting Anthropic and OpenAI.
    
    Provides streaming generation with fallback support.
    """
    
    def __init__(
        self,
        provider: str = "anthropic",
        model: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize LLM client.
        
        Args:
            provider: "anthropic" or "openai"
            model: Model name (defaults to best available)
            api_key: API key (defaults to environment variable)
        """
        self.provider = provider
        
        if provider == "anthropic":
            self.client = AsyncAnthropic(
                api_key=api_key or os.getenv("ANTHROPIC_API_KEY")
            )
            self.model = model or "claude-sonnet-4-20250514"
        elif provider == "openai":
            self.client = AsyncOpenAI(
                api_key=api_key or os.getenv("OPENAI_API_KEY")
            )
            self.model = model or "gpt-4-turbo-2024-04-09"
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        logger.info(f"Initialized {provider} client with model {self.model}")
    
    async def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        stop_sequences: Optional[list[str]] = None
    ) -> AsyncIterator[str]:
        """
        Stream LLM response token by token.
        
        Args:
            prompt: User prompt
            system: System prompt (optional)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            stop_sequences: Stop generation at these sequences
            
        Yields:
            Generated text tokens
        """
        try:
            if self.provider == "anthropic":
                async for token in self._stream_anthropic(
                    prompt, system, temperature, max_tokens, stop_sequences
                ):
                    yield token
            else:
                async for token in self._stream_openai(
                    prompt, system, temperature, max_tokens, stop_sequences
                ):
                    yield token
        except Exception as e:
            logger.error(f"LLM generation failed: {e}", exc_info=True)
            raise
    
    async def _stream_anthropic(
        self,
        prompt: str,
        system: Optional[str],
        temperature: float,
        max_tokens: int,
        stop_sequences: Optional[list[str]]
    ) -> AsyncIterator[str]:
        """Stream from Anthropic Claude."""
        async with self.client.messages.stream(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            system=system or "",
            temperature=temperature,
            max_tokens=max_tokens,
            stop_sequences=stop_sequences or []
        ) as stream:
            async for text in stream.text_stream:
                yield text
    
    async def _stream_openai(
        self,
        prompt: str,
        system: Optional[str],
        temperature: float,
        max_tokens: int,
        stop_sequences: Optional[list[str]]
    ) -> AsyncIterator[str]:
        """Stream from OpenAI GPT."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop_sequences,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> str:
        """
        Generate complete response (non-streaming).
        
        Args:
            prompt: User prompt
            system: System prompt (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            
        Returns:
            Complete generated text
        """
        response = ""
        async for token in self.generate_stream(
            prompt, system, temperature, max_tokens
        ):
            response += token
        return response
```

**Tests to Write**:
```python
# tests/unit/test_llm_client.py
import pytest
from src.qnwis.llm.client import LLMClient

@pytest.mark.asyncio
async def test_anthropic_streaming():
    """Test Anthropic streaming works."""
    client = LLMClient(provider="anthropic")
    
    tokens = []
    async for token in client.generate_stream(
        prompt="Count to 5",
        max_tokens=50
    ):
        tokens.append(token)
    
    response = "".join(tokens)
    assert len(tokens) > 0
    assert "1" in response

@pytest.mark.asyncio
async def test_openai_streaming():
    """Test OpenAI streaming works."""
    client = LLMClient(provider="openai")
    
    tokens = []
    async for token in client.generate_stream(
        prompt="Count to 5",
        max_tokens=50
    ):
        tokens.append(token)
    
    response = "".join(tokens)
    assert len(tokens) > 0
    assert "1" in response

@pytest.mark.asyncio
async def test_system_prompt():
    """Test system prompt is respected."""
    client = LLMClient(provider="anthropic")
    
    response = await client.generate(
        prompt="What is your role?",
        system="You are a labour economist specializing in Qatar.",
        max_tokens=100
    )
    
    assert "labour" in response.lower() or "labor" in response.lower()
```

**Deliverables**:
- ✅ LLM client with Anthropic + OpenAI support
- ✅ Streaming and non-streaming generation
- ✅ Comprehensive error handling
- ✅ Unit tests with real API calls
- ✅ Documentation

---

### Day 3-4: Agent Prompt Templates

**Objective**: Create sophisticated prompts for each specialized agent.

**Files to Create**:
```
src/qnwis/agents/prompts/
├── __init__.py
├── base.py                    # Base prompt utilities
├── labour_economist.py        # Labour economist prompts
├── nationalization.py         # Nationalization prompts
├── skills.py                  # Skills agent prompts
├── pattern_detective.py       # Pattern detection prompts
└── national_strategy.py       # Strategy prompts
```

**Implementation Example**:

```python
# src/qnwis/agents/prompts/labour_economist.py

LABOUR_ECONOMIST_SYSTEM = """
You are a senior labour economist with deep expertise in Qatar's workforce dynamics.

EXPERTISE AREAS:
- Employment trends and patterns
- Gender distribution analysis
- Year-over-year growth calculations
- Sector-specific labour market insights
- Policy implications and recommendations

ANALYTICAL FRAMEWORK:
1. Data Analysis: Examine provided data thoroughly
2. Pattern Recognition: Identify trends and anomalies
3. Contextualization: Provide Qatar-specific context
4. Implications: Draw policy-relevant conclusions
5. Recommendations: Suggest evidence-based actions

CRITICAL REQUIREMENTS:
- Use ONLY numbers from the provided data
- Cite data sources for every statistic
- Provide confidence levels for conclusions
- Acknowledge data limitations
- Be precise and ministerial-quality
"""

LABOUR_ECONOMIST_PROMPT = """
TASK: Analyze Qatar's labour market data to answer the user's question.

USER QUESTION:
{question}

DATA PROVIDED:
{data_summary}

DETAILED DATA:
{data_tables}

CONTEXT:
{context}

ANALYSIS INSTRUCTIONS:
1. Review all provided data carefully
2. Identify key metrics relevant to the question
3. Calculate derived metrics if needed (growth rates, percentages)
4. Identify patterns and trends
5. Provide interpretation and context
6. Suggest policy implications

OUTPUT FORMAT (JSON):
{{
  "title": "Brief, descriptive title",
  "summary": "2-3 sentence executive summary",
  "metrics": {{
    "metric_name": value,
    ...
  }},
  "analysis": "Detailed analysis paragraph (3-5 sentences)",
  "trends": ["Trend 1", "Trend 2", ...],
  "implications": "Policy implications paragraph",
  "recommendations": ["Recommendation 1", "Recommendation 2", ...],
  "confidence": 0.0-1.0,
  "data_quality_notes": "Any concerns about data quality",
  "citations": ["data_source_1", "data_source_2", ...]
}}

CRITICAL: All numbers in your response MUST come from the provided data.
Do not fabricate, estimate, or extrapolate beyond what the data shows.
"""

def build_labour_economist_prompt(
    question: str,
    data: dict,
    context: dict = None
) -> tuple[str, str]:
    """
    Build labour economist prompt with data.
    
    Args:
        question: User's question
        data: Dictionary of QueryResult objects
        context: Additional context
        
    Returns:
        (system_prompt, user_prompt) tuple
    """
    # Format data for prompt
    data_summary = _format_data_summary(data)
    data_tables = _format_data_tables(data)
    context_str = _format_context(context or {})
    
    user_prompt = LABOUR_ECONOMIST_PROMPT.format(
        question=question,
        data_summary=data_summary,
        data_tables=data_tables,
        context=context_str
    )
    
    return LABOUR_ECONOMIST_SYSTEM, user_prompt

def _format_data_summary(data: dict) -> str:
    """Format data summary for prompt."""
    lines = []
    for key, query_result in data.items():
        lines.append(f"- {key}: {len(query_result.rows)} rows")
        lines.append(f"  Source: {query_result.provenance.source}")
        lines.append(f"  Freshness: {query_result.freshness.asof_date}")
    return "\n".join(lines)

def _format_data_tables(data: dict) -> str:
    """Format data tables as markdown for prompt."""
    tables = []
    for key, query_result in data.items():
        tables.append(f"### {key}")
        tables.append(query_result.to_markdown())
        tables.append("")
    return "\n".join(tables)

def _format_context(context: dict) -> str:
    """Format context dictionary."""
    if not context:
        return "No additional context provided."
    
    lines = []
    for key, value in context.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)
```

**Prompts to Create**:

1. **LabourEconomistAgent**: Employment trends, gender distribution, YoY growth
2. **NationalizationAgent**: Qatarization metrics, GCC benchmarking
3. **SkillsAgent**: Skills gaps, education-employment matching
4. **PatternDetectiveAgent**: Anomaly detection, correlation analysis
5. **NationalStrategyAgent**: Vision 2030 alignment, strategic insights

**Deliverables**:
- ✅ 5 specialized agent prompts
- ✅ Prompt building utilities
- ✅ Data formatting functions
- ✅ Example outputs
- ✅ Documentation

---

### Day 5: Structured Output Parser

**Objective**: Parse and validate LLM responses into structured AgentFinding objects.

**Files to Create**:
```
src/qnwis/llm/
├── parser.py          # Output parsing
└── validator.py       # Response validation
```

**Implementation**:

```python
# src/qnwis/llm/parser.py
import json
import re
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator

class AgentFinding(BaseModel):
    """Structured output from agent LLM."""
    title: str = Field(..., description="Brief finding title")
    summary: str = Field(..., description="2-3 sentence executive summary")
    metrics: Dict[str, float] = Field(default_factory=dict)
    analysis: str = Field(..., description="Detailed analysis")
    trends: List[str] = Field(default_factory=list)
    implications: str = Field(default="")
    recommendations: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    data_quality_notes: str = Field(default="")
    citations: List[str] = Field(default_factory=list)
    
    @validator('confidence')
    def validate_confidence(cls, v):
        """Ensure confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v

class LLMResponseParser:
    """Parse LLM responses into structured findings."""
    
    def parse_agent_response(self, text: str) -> AgentFinding:
        """
        Parse LLM response into AgentFinding.
        
        Args:
            text: Raw LLM response
            
        Returns:
            Parsed AgentFinding
            
        Raises:
            ValueError: If response cannot be parsed
        """
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON found in response")
        
        json_str = json_match.group(0)
        
        try:
            data = json.loads(json_str)
            return AgentFinding(**data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
        except Exception as e:
            raise ValueError(f"Failed to parse response: {e}")
    
    def validate_numbers(
        self,
        finding: AgentFinding,
        allowed_numbers: set[float]
    ) -> tuple[bool, List[str]]:
        """
        Validate that all numbers in finding exist in allowed set.
        
        Args:
            finding: Parsed finding
            allowed_numbers: Set of valid numbers from data
            
        Returns:
            (is_valid, list_of_violations)
        """
        violations = []
        
        # Check metrics
        for key, value in finding.metrics.items():
            if not self._number_exists(value, allowed_numbers):
                violations.append(
                    f"Metric '{key}' has value {value} not in data"
                )
        
        # Check analysis text for numbers
        analysis_numbers = self._extract_numbers(finding.analysis)
        for num in analysis_numbers:
            if not self._number_exists(num, allowed_numbers):
                violations.append(
                    f"Analysis contains {num} not in data"
                )
        
        return len(violations) == 0, violations
    
    def _extract_numbers(self, text: str) -> List[float]:
        """Extract all numbers from text."""
        # Match integers and floats, including with commas
        pattern = r'\b\d+(?:,\d{3})*(?:\.\d+)?\b'
        matches = re.findall(pattern, text)
        
        numbers = []
        for match in matches:
            # Remove commas and convert to float
            clean = match.replace(',', '')
            try:
                numbers.append(float(clean))
            except ValueError:
                continue
        
        return numbers
    
    def _number_exists(
        self,
        number: float,
        allowed: set[float],
        tolerance: float = 0.01
    ) -> bool:
        """Check if number exists in allowed set with tolerance."""
        for allowed_num in allowed:
            if abs(number - allowed_num) / max(abs(allowed_num), 1) < tolerance:
                return True
        return False
```

**Tests**:
```python
# tests/unit/test_llm_parser.py
def test_parse_valid_response():
    """Test parsing valid JSON response."""
    parser = LLMResponseParser()
    
    response = '''
    Here is my analysis:
    
    {
      "title": "Employment Growth Analysis",
      "summary": "Employment increased by 5% YoY.",
      "metrics": {"growth_rate": 5.0},
      "analysis": "The data shows consistent growth.",
      "confidence": 0.85,
      "citations": ["syn_employment_latest"]
    }
    '''
    
    finding = parser.parse_agent_response(response)
    assert finding.title == "Employment Growth Analysis"
    assert finding.metrics["growth_rate"] == 5.0
    assert finding.confidence == 0.85

def test_validate_numbers():
    """Test number validation."""
    parser = LLMResponseParser()
    
    finding = AgentFinding(
        title="Test",
        summary="Test summary",
        metrics={"value": 100.0},
        analysis="The value is 100",
        confidence=0.9
    )
    
    allowed = {100.0, 200.0, 300.0}
    is_valid, violations = parser.validate_numbers(finding, allowed)
    
    assert is_valid
    assert len(violations) == 0

def test_detect_fabricated_numbers():
    """Test detection of fabricated numbers."""
    parser = LLMResponseParser()
    
    finding = AgentFinding(
        title="Test",
        summary="Test summary",
        metrics={"value": 999.0},  # Not in allowed set
        analysis="The value is 999",
        confidence=0.9
    )
    
    allowed = {100.0, 200.0, 300.0}
    is_valid, violations = parser.validate_numbers(finding, allowed)
    
    assert not is_valid
    assert len(violations) > 0
```

**Deliverables**:
- ✅ Structured output parser
- ✅ Number validation
- ✅ Comprehensive tests
- ✅ Error handling

---

## Phase 2: Rebuild Agents with LLMs (Week 2)

### Day 1: Update Base Agent Class

**Objective**: Create new base class for LLM-powered agents.

**File**: `src/qnwis/agents/base_llm.py`

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, List, Optional
import logging

from src.qnwis.agents.base import DataClient, AgentReport, Insight
from src.qnwis.llm.client import LLMClient
from src.qnwis.llm.parser import LLMResponseParser, AgentFinding
from src.qnwis.verification.number_verifier import NumberVerifier

logger = logging.getLogger(__name__)

class LLMAgent(ABC):
    """
    Base class for LLM-powered agents.
    
    All agents inherit from this and implement:
    - _fetch_data(): What data to retrieve
    - _build_prompt(): How to format prompt
    - _load_prompt_template(): Which prompt template to use
    """
    
    def __init__(
        self,
        client: DataClient,
        llm: LLMClient,
        verifier: Optional[NumberVerifier] = None
    ):
        """
        Initialize LLM agent.
        
        Args:
            client: Data client for deterministic queries
            llm: LLM client for generation
            verifier: Number verifier (optional)
        """
        self.client = client
        self.llm = llm
        self.verifier = verifier or NumberVerifier()
        self.parser = LLMResponseParser()
        self.agent_name = self.__class__.__name__.replace("Agent", "")
    
    async def run_stream(
        self,
        question: str,
        context: Optional[Dict] = None
    ) -> AsyncIterator[Dict]:
        """
        Run agent with streaming output.
        
        Yields events:
        - {"type": "status", "content": "Fetching data..."}
        - {"type": "token", "content": "Generated token"}
        - {"type": "complete", "report": AgentReport}
        
        Args:
            question: User's question
            context: Additional context
            
        Yields:
            Stream events
        """
        context = context or {}
        
        try:
            # 1. Fetch data
            yield {"type": "status", "content": f"🔍 {self.agent_name} fetching data..."}
            data = await self._fetch_data(question, context)
            
            # 2. Build prompt
            yield {"type": "status", "content": f"🤔 {self.agent_name} analyzing..."}
            system_prompt, user_prompt = self._build_prompt(question, data, context)
            
            # 3. Stream LLM response
            response_text = ""
            async for token in self.llm.generate_stream(
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.3,
                max_tokens=2000
            ):
                response_text += token
                yield {"type": "token", "content": token}
            
            # 4. Parse response
            yield {"type": "status", "content": f"✅ {self.agent_name} parsing results..."}
            finding = self.parser.parse_agent_response(response_text)
            
            # 5. Verify numbers
            allowed_numbers = self._extract_numbers_from_data(data)
            is_valid, violations = self.parser.validate_numbers(finding, allowed_numbers)
            
            if not is_valid:
                logger.warning(f"{self.agent_name} number validation failed: {violations}")
                yield {
                    "type": "warning",
                    "content": f"⚠️ Number validation warnings: {len(violations)} issues"
                }
            
            # 6. Convert to AgentReport
            insight = Insight(
                title=finding.title,
                summary=finding.summary,
                metrics=finding.metrics,
                evidence=self._build_evidence(data),
                warnings=violations if not is_valid else [],
                confidence_score=finding.confidence
            )
            
            report = AgentReport(
                agent=self.agent_name,
                findings=[insight],
                narrative=finding.analysis
            )
            
            yield {"type": "complete", "report": report}
            
        except Exception as e:
            logger.error(f"{self.agent_name} failed: {e}", exc_info=True)
            yield {
                "type": "error",
                "content": f"❌ {self.agent_name} error: {str(e)}"
            }
    
    async def run(
        self,
        question: str,
        context: Optional[Dict] = None
    ) -> AgentReport:
        """
        Run agent without streaming (for backward compatibility).
        
        Args:
            question: User's question
            context: Additional context
            
        Returns:
            AgentReport
        """
        report = None
        async for event in self.run_stream(question, context):
            if event["type"] == "complete":
                report = event["report"]
        
        if report is None:
            raise RuntimeError(f"{self.agent_name} failed to produce report")
        
        return report
    
    @abstractmethod
    async def _fetch_data(
        self,
        question: str,
        context: Dict
    ) -> Dict:
        """
        Fetch data needed for analysis.
        
        Returns:
            Dictionary of {key: QueryResult}
        """
        pass
    
    @abstractmethod
    def _build_prompt(
        self,
        question: str,
        data: Dict,
        context: Dict
    ) -> tuple[str, str]:
        """
        Build agent-specific prompt.
        
        Returns:
            (system_prompt, user_prompt) tuple
        """
        pass
    
    def _extract_numbers_from_data(self, data: Dict) -> set[float]:
        """Extract all numbers from QueryResults."""
        numbers = set()
        for query_result in data.values():
            for row in query_result.rows:
                for value in row.data.values():
                    if isinstance(value, (int, float)):
                        numbers.add(float(value))
        return numbers
    
    def _build_evidence(self, data: Dict) -> List:
        """Build evidence list from data."""
        from src.qnwis.agents.base import evidence_from
        return [evidence_from(qr) for qr in data.values()]
```

**Deliverables**:
- ✅ New LLMAgent base class
- ✅ Streaming support
- ✅ Number verification integration
- ✅ Error handling
- ✅ Documentation

---

### Day 2-5: Rebuild Each Agent

**Objective**: Rebuild all 5 agents to use LLMs.

**Example: LabourEconomistAgent**

```python
# src/qnwis/agents/labour_economist_llm.py
from src.qnwis.agents.base_llm import LLMAgent
from src.qnwis.agents.prompts.labour_economist import build_labour_economist_prompt

class LabourEconomistAgent(LLMAgent):
    """
    Labour economist agent with LLM reasoning.
    
    Analyzes employment trends, gender distribution, and YoY growth.
    """
    
    async def _fetch_data(self, question: str, context: dict) -> dict:
        """Fetch employment and trend data."""
        return {
            "employment": self.client.run("syn_employment_share_by_gender_latest"),
            "trends": self.client.run("syn_employment_trends_timeseries")
        }
    
    def _build_prompt(self, question: str, data: dict, context: dict) -> tuple[str, str]:
        """Build labour economist prompt."""
        return build_labour_economist_prompt(question, data, context)
```

**Agents to Rebuild**:
1. LabourEconomistAgent (Day 2)
2. NationalizationAgent (Day 3)
3. SkillsAgent (Day 3)
4. PatternDetectiveAgent (Day 4)
5. NationalStrategyAgent (Day 5)

**For Each Agent**:
- ✅ Implement _fetch_data()
- ✅ Implement _build_prompt()
- ✅ Write unit tests
- ✅ Test with real LLM
- ✅ Verify streaming works
- ✅ Document behavior

---

## Phase 3: LangGraph Orchestration (Week 3)

### Implementation in `IMPLEMENTATION_PLAN_LLM_AGENTS.md` continues...

---

## Success Metrics

### Week 1 Complete When:
- ✅ LLM client works with both providers
- ✅ All 5 agent prompts written
- ✅ Parser handles structured output
- ✅ All tests passing

### Week 2 Complete When:
- ✅ All 5 agents use LLMs
- ✅ Streaming works for each agent
- ✅ Number verification catches fabrication
- ✅ Response times: 5-30 seconds per agent

### Week 3 Complete When:
- ✅ LangGraph workflow orchestrates agents
- ✅ Parallel execution where possible
- ✅ Synthesis uses LLM
- ✅ End-to-end workflow streams

### Week 4 Complete When:
- ✅ Chainlit UI shows streaming
- ✅ All agents visible in UI
- ✅ Synthesis displays properly
- ✅ System ready for Ministry demo

---

**This is the real implementation plan. No shortcuts. No facades.**
