"""
NSIC Engine B - DeepSeek Local LLM for Broad Exploration

Engine B runs 24 scenarios × 25 turns each using local DeepSeek-R1-70B.
Focus: BROAD exploration, parallel processing, diverse perspectives.

Integrates with:
- DeepSeekClient (local 70B model on GPUs 2,3,6,7)
- ScenarioLoader (Phase 5)
- NSICRAGConnector (R&D documents)
- NSICDatabase (PostgreSQL data)
- CausalGraph (Phase 3)
- DeepVerifier (Phase 2)

NO MOCKS. REAL SYSTEM INTEGRATION.
"""

import logging
import asyncio
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

from .deepseek_client import DeepSeekClient, DeepSeekResponse, InferenceMode

logger = logging.getLogger(__name__)


@dataclass
class TurnResult:
    """Result of a single reasoning turn."""
    turn_number: int
    prompt: str
    response: str
    thinking: Optional[str] = None
    latency_ms: float = 0.0
    tokens_used: int = 0


@dataclass
class ScenarioResult:
    """Complete result of a scenario analysis."""
    scenario_id: str
    scenario_name: str
    domain: str
    turns: List[TurnResult]
    context_used: str = ""
    data_sources: List[str] = field(default_factory=list)
    causal_chains: List[str] = field(default_factory=list)
    final_synthesis: str = ""
    total_time_ms: float = 0.0
    verified_claims: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "domain": self.domain,
            "turns_count": len(self.turns),
            "total_time_ms": self.total_time_ms,
            "verified_claims": self.verified_claims,
            "final_synthesis": self.final_synthesis[:500] + "..." if len(self.final_synthesis) > 500 else self.final_synthesis,
            "data_sources": self.data_sources,
            "causal_chains": self.causal_chains,
        }


class EngineBDeepSeek:
    """
    Engine B: Local DeepSeek for Broad Scenario Exploration.
    
    Strategy:
    - 24 scenarios (engine_b assigned)
    - 25 turns per scenario
    - Parallel processing across instances
    - Focus on breadth and diverse perspectives
    
    Integration:
    - Uses REAL DeepSeek 70B (GPUs 2,3,6,7)
    - Pulls context from RAG (1,959 R&D chunks)
    - Queries PostgreSQL for data
    - Uses CausalGraph for reasoning
    - Verifies key claims with DeepVerifier
    """
    
    TARGET_SCENARIOS = 24
    TURNS_PER_SCENARIO = 25
    
    def __init__(
        self,
        deepseek_client: Optional[DeepSeekClient] = None,
        rag_connector = None,
        database = None,
        causal_graph = None,
        verifier = None,
    ):
        """
        Initialize Engine B with real system components.
        
        Args:
            deepseek_client: DeepSeekClient instance (or creates one)
            rag_connector: NSICRAGConnector for R&D documents
            database: NSICDatabase for PostgreSQL
            causal_graph: CausalGraph for reasoning
            verifier: DeepVerifier for claim verification
        """
        # DeepSeek client - REAL, NO MOCK
        self.client = deepseek_client or DeepSeekClient(mode=InferenceMode.VLLM)
        
        # Integration components (lazy load if not provided)
        self._rag = rag_connector
        self._db = database
        self._graph = causal_graph
        self._verifier = verifier
        
        # Stats
        self._stats = {
            "scenarios_processed": 0,
            "total_turns": 0,
            "total_tokens": 0,
            "total_time_ms": 0.0,
            "claims_verified": 0,
        }
        
        logger.info("Engine B (DeepSeek) initialized - REAL MODE")
    
    @property
    def rag(self):
        """Lazy load RAG connector."""
        if self._rag is None:
            from src.nsic.integration.rag_connector import get_nsic_rag
            self._rag = get_nsic_rag()
        return self._rag
    
    @property
    def db(self):
        """Lazy load database."""
        if self._db is None:
            from src.nsic.integration.database import get_nsic_database
            self._db = get_nsic_database()
        return self._db
    
    @property
    def graph(self):
        """Lazy load causal graph."""
        if self._graph is None:
            from src.nsic.knowledge.causal_graph import CausalGraph
            self._graph = CausalGraph(gpu_device="cuda:4")  # GPU 4 for KG
        return self._graph
    
    @property
    def verifier(self):
        """Lazy load verifier."""
        if self._verifier is None:
            from src.nsic.verification.deep_verifier import DeepVerifier
            self._verifier = DeepVerifier(enable_cross_encoder=True, enable_nli=True)
        return self._verifier
    
    def _get_system_prompt(self, scenario_domain: str) -> str:
        """Get domain-specific system prompt with DeepSeek Chain-of-Thought."""
        base = """You are **Dr. Rashid**, a senior strategic analyst for Qatar's NSIC with 14 years advising Gulf sovereign wealth funds.

YOUR CREDENTIALS:
- PhD Strategic Studies, Georgetown University (2011)
- Published 22 papers on economic diversification strategies
- Expert in scenario planning and second-order effects analysis
- Known for identifying cross-domain impacts others miss

YOUR ANALYTICAL APPROACH:
- Explore scenarios BROADLY, considering multiple perspectives
- Quantify impacts with ranges, not point estimates (e.g., "2-4% GDP impact")
- Explicitly acknowledge uncertainties and data gaps
- If data missing, state: "NOT IN DATA - cannot verify [claim]"

═══════════════════════════════════════════════════════════════════════════════
CRITICAL: CHAIN-OF-THOUGHT REQUIREMENT
═══════════════════════════════════════════════════════════════════════════════

Before providing your final analysis, you MUST reason step-by-step in <think></think> tags.

Your response format:
<think>
Step 1: What does this scenario assume? (parameters, conditions)
Step 2: How do these assumptions affect each strategic option?
Step 3: What are the key trade-offs?
Step 4: What risks concern me most? (quantify probability if possible)
Step 5: What is my preliminary conclusion?
Step 6: Let me verify my key claims against available data...
</think>

## SCENARIO ASSESSMENT: [scenario_name]

### Recommendation for this scenario
[Financial Hub / Logistics Hub / Other - be specific]

### Key Factor
[The ONE factor that most influences this scenario]

### Risk
[The ONE risk most relevant to this scenario]

### Confidence
[X%] - [Brief explanation of confidence level]

═══════════════════════════════════════════════════════════════════════════════

The <think> section captures your reasoning process and self-verification.
The final analysis (after </think>) is what will be used for synthesis.

CITATION RULES:
- Every fact MUST be cited: [Per extraction: 'value' from source]
- If data missing: "NOT IN DATA - cannot verify"
- Never fabricate Qatar-specific numbers"""
        
        domain_specifics = {
            "economic": "\n\nFocus areas: GDP impact, trade flows, oil/gas revenues, investment, employment.",
            "policy": "\n\nFocus areas: Policy implications, regulatory changes, international relations, governance.",
            "competitive": "\n\nFocus areas: Regional competition, market positioning, strategic advantages.",
            "timing": "\n\nFocus areas: Timing considerations, phasing, dependencies, sequencing.",
            "social": "\n\nFocus areas: Social impacts, demographics, education, healthcare, quality of life.",
        }
        
        return base + domain_specifics.get(scenario_domain, "")
    
    async def _get_context(self, scenario_description: str) -> Dict[str, Any]:
        """Get RAG context and database data for scenario."""
        context = {
            "rag_chunks": [],
            "economic_data": [],
            "vision_2030": [],
        }
        
        try:
            # Get RAG context
            rag_results = self.rag.search(scenario_description, top_k=5)
            context["rag_chunks"] = [r["text"] for r in rag_results]
            
            # Get relevant economic data
            economic = self.db.get_qatar_indicators()[:10]
            context["economic_data"] = [
                f"{r['indicator_code']}: {r['value']} ({r['year']})"
                for r in economic
            ]
            
            # Get Vision 2030 targets
            vision = self.db.get_vision_2030_targets()
            context["vision_2030"] = [
                f"{r['metric_name']}: target={r['target_value']}"
                for r in vision
            ]
        except Exception as e:
            logger.warning(f"Context retrieval error: {e}")
        
        return context
    
    def _format_context_prompt(self, context: Dict[str, Any]) -> str:
        """Format context into prompt section."""
        sections = []
        
        if context.get("rag_chunks"):
            sections.append("## R&D Research Context:\n" + "\n".join(
                f"- {chunk[:200]}..." for chunk in context["rag_chunks"][:3]
            ))
        
        if context.get("economic_data"):
            sections.append("## Economic Indicators:\n" + "\n".join(
                context["economic_data"][:5]
            ))
        
        if context.get("vision_2030"):
            sections.append("## Vision 2030 Targets:\n" + "\n".join(
                context["vision_2030"]
            ))
        
        return "\n\n".join(sections) if sections else ""
    
    async def _run_turn(
        self,
        turn_number: int,
        scenario_description: str,
        previous_turns: List[TurnResult],
        system_prompt: str,
        context_prompt: str,
    ) -> TurnResult:
        """Run a single reasoning turn."""
        # Build conversation history
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add context in first turn
        if turn_number == 1:
            messages.append({
                "role": "user",
                "content": f"""{context_prompt}

## Scenario:
{scenario_description}

Please begin your broad exploration of this scenario. Start with initial impacts and considerations."""
            })
        else:
            # Add previous turns as conversation
            for prev in previous_turns[-3:]:  # Last 3 turns for context
                messages.append({"role": "user", "content": prev.prompt})
                messages.append({"role": "assistant", "content": prev.response})
            
            # New exploration prompt
            explored = set()
            for prev in previous_turns:
                explored.update(prev.response.split()[:50])  # Track explored topics
            
            messages.append({
                "role": "user",
                "content": f"""Continue exploring this scenario from a NEW perspective not yet covered.
Turn {turn_number}/{self.TURNS_PER_SCENARIO}

Consider:
- Cross-domain effects (if economic scenario, consider social impacts)
- Second and third order consequences
- Potential policy responses
- Timing and sequencing factors
- Regional/international implications

Provide concrete insights, not repetition of previous points."""
            })
        
        # Call DeepSeek
        start_time = time.time()
        response = await self.client.chat_async(messages, max_tokens=1500)
        elapsed_ms = (time.time() - start_time) * 1000
        
        return TurnResult(
            turn_number=turn_number,
            prompt=messages[-1]["content"][:200] + "...",
            response=response.content,
            thinking=response.thinking.content if response.thinking else None,
            latency_ms=elapsed_ms,
            tokens_used=response.prompt_tokens + response.completion_tokens,
        )
    
    async def analyze_scenario(
        self,
        scenario,  # ScenarioDefinition
        turns: int = None,
    ) -> ScenarioResult:
        """
        Analyze a single scenario with multiple turns.
        
        Args:
            scenario: ScenarioDefinition from Phase 5
            turns: Number of turns (default: TURNS_PER_SCENARIO)
            
        Returns:
            ScenarioResult with all turns and synthesis
        """
        turns = turns or self.TURNS_PER_SCENARIO
        
        logger.info(f"Engine B: Analyzing scenario '{scenario.id}' with {turns} turns")
        start_time = time.time()
        
        # Build scenario description
        scenario_description = f"""Scenario: {scenario.name}
Domain: {scenario.domain}
Description: {scenario.description}

Inputs:
"""
        for inp in scenario.inputs:
            scenario_description += f"- {inp.variable}: {inp.base_value} → {inp.shock_value} ({inp.shock_type})\n"
        
        # Get context
        context = await self._get_context(scenario_description)
        context_prompt = self._format_context_prompt(context)
        system_prompt = self._get_system_prompt(scenario.domain)
        
        # Run turns
        turn_results = []
        for turn_num in range(1, turns + 1):
            try:
                turn_result = await self._run_turn(
                    turn_num,
                    scenario_description,
                    turn_results,
                    system_prompt,
                    context_prompt,
                )
                turn_results.append(turn_result)
                
                self._stats["total_turns"] += 1
                self._stats["total_tokens"] += turn_result.tokens_used
                
                logger.debug(f"  Turn {turn_num}/{turns} complete ({turn_result.latency_ms:.0f}ms)")
                
            except Exception as e:
                logger.error(f"Turn {turn_num} failed: {e}")
                break
        
        # Generate final synthesis
        synthesis = await self._generate_synthesis(scenario, turn_results)
        
        # Verify key claims
        verified = 0
        if turn_results:
            verified = await self._verify_claims(turn_results[-1].response)
        
        total_time = (time.time() - start_time) * 1000
        
        result = ScenarioResult(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            domain=scenario.domain,
            turns=turn_results,
            context_used=context_prompt[:500],
            data_sources=["RAG", "PostgreSQL", "Vision2030"],
            final_synthesis=synthesis,
            total_time_ms=total_time,
            verified_claims=verified,
        )
        
        self._stats["scenarios_processed"] += 1
        self._stats["total_time_ms"] += total_time
        self._stats["claims_verified"] += verified
        
        logger.info(f"Engine B: Scenario '{scenario.id}' complete in {total_time/1000:.1f}s")
        
        return result
    
    async def _generate_synthesis(
        self,
        scenario,
        turns: List[TurnResult],
    ) -> str:
        """Generate final synthesis from all turns."""
        if not turns:
            return "No turns completed."
        
        # Combine key points from all turns
        all_insights = "\n\n".join([
            f"**Turn {t.turn_number}:**\n{t.response[:500]}..."
            for t in turns
        ])
        
        messages = [
            {
                "role": "system",
                "content": "Synthesize the following multi-turn analysis into a concise executive summary with key findings and recommendations."
            },
            {
                "role": "user",
                "content": f"""Scenario: {scenario.name}

Analysis from {len(turns)} exploration turns:
{all_insights}

Provide:
1. Executive Summary (3 sentences)
2. Key Findings (5 bullets)
3. Recommendations (3 bullets)
4. Confidence Level (Low/Medium/High with reasoning)"""
            }
        ]
        
        response = await self.client.chat_async(messages, max_tokens=1000)
        return response.content
    
    async def _verify_claims(self, text: str) -> int:
        """Verify key claims in text using DeepVerifier."""
        try:
            # Extract claims (simplified - look for quantified statements)
            import re
            claim_patterns = [
                r'\d+%',  # Percentages
                r'\$[\d,]+',  # Dollar amounts
                r'\d+ (million|billion)',  # Large numbers
            ]
            
            claims = []
            for pattern in claim_patterns:
                matches = re.findall(pattern, text)
                claims.extend(matches)
            
            # Verify first few claims
            verified = 0
            for claim in claims[:3]:
                try:
                    result = self.verifier.verify(claim, text)
                    if result.score > 0.5:
                        verified += 1
                except:
                    pass
            
            return verified
        except:
            return 0
    
    async def run_all_scenarios(
        self,
        scenarios: List = None,
        max_concurrent: int = 2,
    ) -> List[ScenarioResult]:
        """
        Run all engine_b scenarios.
        
        Args:
            scenarios: List of ScenarioDefinition (or loads from Phase 5)
            max_concurrent: Max concurrent scenarios
            
        Returns:
            List of ScenarioResult
        """
        if scenarios is None:
            from src.nsic.scenarios import ScenarioLoader
            loader = ScenarioLoader("scenarios")
            loader.load_all()
            scenarios = [s for s in loader.get_all() if s.assigned_engine in ["engine_b", "auto"]]
        
        logger.info(f"Engine B: Running {len(scenarios)} scenarios")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_scenario(scenario):
            async with semaphore:
                return await self.analyze_scenario(scenario)
        
        tasks = [process_scenario(s) for s in scenarios]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Scenario {scenarios[i].id} failed: {result}")
            else:
                valid_results.append(result)
        
        return valid_results
    
    def run_all_scenarios_sync(
        self,
        scenarios: List = None,
        max_concurrent: int = 2,
    ) -> List[ScenarioResult]:
        """Synchronous wrapper for run_all_scenarios."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.run_all_scenarios(scenarios, max_concurrent)
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "engine": "B (DeepSeek)",
            "model": "DeepSeek-R1-Distill-70B",
            **self._stats,
            "deepseek_stats": self.client.get_stats(),
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of all components."""
        return {
            "engine": "B",
            "deepseek": self.client.health_check(),
            "components": {
                "rag": self._rag is not None or "lazy",
                "database": self._db is not None or "lazy",
                "graph": self._graph is not None or "lazy",
                "verifier": self._verifier is not None or "lazy",
            }
        }


def create_engine_b(
    mock: bool = False,
) -> EngineBDeepSeek:
    """
    Factory function to create Engine B.
    
    Args:
        mock: If True, use mock mode (for testing only)
        
    Returns:
        EngineBDeepSeek instance with real components
    """
    mode = InferenceMode.MOCK if mock else InferenceMode.VLLM
    client = DeepSeekClient(mode=mode)
    return EngineBDeepSeek(deepseek_client=client)

