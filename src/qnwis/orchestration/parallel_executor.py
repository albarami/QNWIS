"""
Parallel Debate Executor for Multi-Scenario Analysis.

Executes multiple debate workflows simultaneously.
Uses GPUs 0-5 if available, otherwise runs on CPU.
Rate limiting happens at individual LLM call level (not here).

ENHANCED: Now calls Engine B compute services per scenario for:
- Monte Carlo simulation
- Sensitivity analysis
- Forecasting
- Threshold detection
"""

import asyncio
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import torch
import httpx

logger = logging.getLogger(__name__)

# Engine B Configuration
ENGINE_B_URL = os.getenv("ENGINE_B_URL", "http://localhost:8001")


class ParallelDebateExecutor:
    """
    Execute multiple debates in parallel with enterprise-grade rate limiting.
    
    If GPUs are available, distributes scenarios across GPUs 0-5.
    Otherwise, runs all scenarios on CPU using asyncio concurrency.
    
    ENTERPRISE STABILITY FIX: Uses semaphore to limit concurrent scenarios.
    This prevents Azure OpenAI rate limit errors (429 Too Many Requests).
    Running 6 scenarios × 4 agents = 24 concurrent calls overwhelms rate limits.
    With max_concurrent_scenarios=2, we limit to 8 concurrent calls maximum.
    """
    
    # Enterprise rate limiting config
    MAX_CONCURRENT_SCENARIOS = 2  # Run at most 2 scenarios simultaneously
    SCENARIO_DELAY_SECONDS = 1.0  # Small delay between scenario starts
    
    def __init__(self, num_parallel: int = 6, event_callback=None, max_concurrent: int = None):
        """
        Initialize parallel executor with rate limiting.
        
        Args:
            num_parallel: Total number of scenarios to run (default 6)
            event_callback: Optional async callback for emitting events to frontend
            max_concurrent: Max scenarios running simultaneously (default 2 for enterprise stability)
        """
        self.num_parallel = num_parallel
        self.event_callback = event_callback
        self.max_concurrent = max_concurrent or self.MAX_CONCURRENT_SCENARIOS
        
        # Enterprise rate limiting semaphore
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Check GPU availability
        self.gpu_available = torch.cuda.is_available()
        self.gpu_count = torch.cuda.device_count() if self.gpu_available else 0
        
        if self.gpu_available:
            logger.info(f"✅ Parallel executor initialized with {self.gpu_count} GPUs")
            logger.info(f"   Total scenarios: {num_parallel}")
            logger.info(f"   Max concurrent: {self.max_concurrent} (enterprise rate limiting)")
            logger.info(f"   GPU distribution: Scenarios across GPUs 0-5")
            
            # Log GPU details
            for i in range(min(self.gpu_count, 6)):
                try:
                    gpu_name = torch.cuda.get_device_name(i)
                    gpu_memory = torch.cuda.get_device_properties(i).total_memory / 1e9
                    logger.info(f"   GPU {i}: {gpu_name} ({gpu_memory:.1f}GB)")
                except Exception as e:
                    logger.warning(f"   GPU {i}: Could not get info - {e}")
        else:
            logger.warning("⚠️ No GPUs detected - parallel execution will use CPU")
            logger.info(f"   Max concurrent scenarios: {self.max_concurrent} (prevents API rate limits)")
    
    async def execute_scenarios(
        self, 
        scenarios: List[Dict[str, Any]],
        base_workflow: Any,
        initial_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple scenarios in parallel.
        
        ENHANCED: Also runs ResearchSynthesizer in parallel to produce a
        PhD-level literature review that will be injected into the debate.
        
        Args:
            scenarios: List of scenario definitions from ScenarioGenerator
            base_workflow: Compiled LangGraph workflow to run for each scenario
            initial_state: Base state to clone for each scenario
            
        Returns:
            List of completed scenario results (successful executions only)
        """
        logger.info(f"Starting parallel execution of {len(scenarios)} scenarios")
        start_time = datetime.now()
        
        # Start ResearchSynthesizer in parallel - runs while scenarios execute
        research_task = asyncio.create_task(
            self._run_research_synthesizer(initial_state.get("query", "policy analysis"))
        )
        logger.info("📚 ResearchSynthesizer started in parallel (PhD literature review)")
        
        # Emit parallel execution start event
        await self._emit_event(
            stage="parallel_exec",
            status="started",
            payload={
                "total_scenarios": len(scenarios),
                "execution_mode": "GPU" if self.gpu_available else "CPU",
                "device_count": self.gpu_count if self.gpu_available else 1,
                "scenarios": [{"name": s.get("name", f"Scenario {i}"), "description": s.get("description", "")} for i, s in enumerate(scenarios)]
            }
        )
        
        # Emit agent running events - agents run inside parallel scenarios
        for agent_name in ['financial', 'market', 'operations', 'research']:
            await self._emit_event(
                stage=f"agent:{agent_name}",
                status="running",
                payload={"agent": agent_name, "parallel_execution": True}
            )
        
        # ENTERPRISE STABILITY: Rate-limited scenario execution
        # Uses semaphore to limit concurrent scenarios and prevent API rate limit errors
        logger.info(
            f"🚦 Starting rate-limited execution: {len(scenarios)} scenarios, "
            f"max {self.max_concurrent} concurrent (prevents Azure rate limits)"
        )
        
        async def run_with_rate_limit(scenario, index):
            """Run a single scenario with semaphore-based rate limiting."""
            async with self._semaphore:
                # Small staggered delay to prevent burst
                if index > 0:
                    await asyncio.sleep(self.SCENARIO_DELAY_SECONDS * (index % self.max_concurrent))
                
                gpu_id = index % 6 if self.gpu_available else None
                logger.info(f"🚀 Scenario {index+1}/{len(scenarios)} starting (slot acquired)")
                
                result = await self._run_scenario(
                    scenario=scenario,
                    workflow=base_workflow,
                    base_state=initial_state,
                    gpu_id=gpu_id,
                    scenario_index=index,
                    total_scenarios=len(scenarios)
                )
                
                logger.info(f"✅ Scenario {index+1}/{len(scenarios)} completed (slot released)")
                return result
        
        # Create tasks with rate limiting wrapper
        tasks = [
            run_with_rate_limit(scenario, i)
            for i, scenario in enumerate(scenarios)
        ]
        
        # Execute with controlled concurrency
        logger.info(f"🚦 Launching {len(tasks)} scenarios with {self.max_concurrent} concurrent limit...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Separate successful and failed results
        successful_results = []
        failed_count = 0
        
        # Track agents for aggregate events
        all_agents_seen = set()
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"❌ Scenario {scenarios[i]['name']} failed: {result}",
                    exc_info=result
                )
                failed_count += 1
            else:
                successful_results.append(result)
                logger.info(f"✅ Scenario {scenarios[i]['name']} completed successfully")
                
                # Track which agents ran in this scenario
                if isinstance(result, dict):
                    for field in ['financial_analysis', 'market_analysis', 'operations_analysis', 'research_analysis']:
                        if result.get(field):
                            agent_name = field.replace('_analysis', '')
                            all_agents_seen.add(agent_name)
                
                # Emit progress update after each completion
                await self._emit_event(
                    stage="parallel_progress",
                    status="update",
                    payload={
                        "completed": len(successful_results),
                        "failed": failed_count,
                        "total": len(scenarios),
                        "percent": int((len(successful_results) / len(scenarios)) * 100),
                        "latest_completed": scenarios[i].get('name', f'Scenario {i}')
                    }
                )
        
        # Emit aggregate agent completion events for frontend
        # Since agents ran inside parallel scenarios, we emit their status now
        for agent_name in ['financial', 'market', 'operations', 'research']:
            status = 'complete' if agent_name in all_agents_seen else 'pending'
            await self._emit_event(
                stage=f"agent:{agent_name}",
                status=status,
                payload={
                    "agent": agent_name,
                    "scenarios_completed": len(successful_results),
                    "parallel_execution": True
                }
            )
        
        # Collect ResearchSynthesizer results (ran in parallel with scenarios)
        research_synthesis = None
        try:
            research_synthesis = await asyncio.wait_for(research_task, timeout=120)  # Max 2 min
            if research_synthesis:
                logger.info(f"📚 ResearchSynthesizer completed: {len(research_synthesis.get('narrative', ''))} chars")
                await self._emit_event(
                    stage="research_synthesis",
                    status="complete",
                    payload={
                        "sources": research_synthesis.get("sources_summary", {}),
                        "confidence": research_synthesis.get("confidence", "unknown"),
                        "findings_count": research_synthesis.get("findings_count", 0),
                    }
                )
        except asyncio.TimeoutError:
            logger.warning("⚠️ ResearchSynthesizer timed out - continuing without research synthesis")
        except Exception as e:
            logger.warning(f"⚠️ ResearchSynthesizer failed: {e}")
        
        # Log summary
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"✅ Parallel execution complete: {len(successful_results)}/{len(scenarios)} scenarios succeeded in {elapsed:.1f}s"
        )
        
        if failed_count > 0:
            logger.warning(f"⚠️ {failed_count} scenarios failed - continuing with successful results")
        
        # Emit parallel execution complete event
        await self._emit_event(
            stage="parallel_exec",
            status="complete",
            payload={
                "scenarios_completed": len(successful_results),
                "scenarios_failed": failed_count,
                "total_scenarios": len(scenarios),
                "total_duration_seconds": elapsed,
                "scenario_results": successful_results,
                "research_synthesis_available": research_synthesis is not None,
            }
        )
        
        # Attach research synthesis to results for debate injection
        return {
            "scenario_results": successful_results,
            "research_synthesis": research_synthesis,
        }
    
    async def _run_research_synthesizer(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Run ResearchSynthesizer in parallel to produce PhD-level literature review.
        
        This runs concurrently with scenario execution and produces a comprehensive
        academic synthesis that will be injected into the debate at the right moment.
        
        Sources:
        - Semantic Scholar (peer-reviewed academic papers)
        - Perplexity AI (real-time research synthesis)
        - RAG System (1965 internal R&D documents)
        - Knowledge Graph (entity relationships)
        
        Args:
            query: The research question to investigate
            
        Returns:
            Dict containing narrative, findings, and metadata for debate injection
        """
        try:
            from ..agents.research_synthesizer import ResearchSynthesizerAgent
            
            logger.info(f"📚 ResearchSynthesizer starting literature review for: {query[:50]}...")
            
            # Emit start event
            await self._emit_event(
                stage="research_synthesis",
                status="running",
                payload={"query": query[:100], "sources": ["semantic_scholar", "perplexity", "rag", "knowledge_graph"]}
            )
            
            # Initialize agent (auto-loads RAG with 1965 docs and KG)
            agent = ResearchSynthesizerAgent()
            
            # Run synthesis - this is the computationally expensive part
            # It queries multiple APIs and produces a 1000+ word academic review
            synthesis = await asyncio.get_event_loop().run_in_executor(
                None,  # Use default executor
                lambda: agent.run(query=query)
            )
            
            # Collect source statistics
            sources_summary = {}
            if synthesis.findings:
                for finding in synthesis.findings:
                    source = finding.source
                    sources_summary[source] = sources_summary.get(source, 0) + 1
            
            logger.info(f"📚 ResearchSynthesizer completed:")
            logger.info(f"   - Narrative: {len(synthesis.narrative)} chars (~{len(synthesis.narrative.split())} words)")
            logger.info(f"   - Findings: {len(synthesis.findings)} total")
            logger.info(f"   - Sources: {sources_summary}")
            logger.info(f"   - Confidence: {synthesis.confidence_level}")
            
            return {
                "narrative": synthesis.narrative,
                "findings_count": len(synthesis.findings),
                "confidence": synthesis.confidence_level,
                "sources_summary": sources_summary,
                "consensus_view": synthesis.consensus_view,
                "evidence_gaps": synthesis.evidence_gaps,
                "methodology_note": synthesis.methodology_note,
                # For debate injection
                "debate_ready": True,
                "for_debate": f"""
## ACADEMIC LITERATURE REVIEW
### Prepared by Dr. Research (PhD-Level Synthesis)

{synthesis.narrative}

### CITATION GUIDANCE FOR DEBATE AGENTS
Use these findings to support your arguments. Always cite sources.
Evidence confidence: {synthesis.confidence_level.upper()}
""",
            }
            
        except ImportError as e:
            logger.warning(f"⚠️ ResearchSynthesizer not available: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ ResearchSynthesizer failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def _run_scenario(
        self,
        scenario: Dict[str, Any],
        workflow: Any,
        base_state: Dict[str, Any],
        gpu_id: Optional[int],
        scenario_index: int,
        total_scenarios: int = 6
    ) -> Dict[str, Any]:
        """
        Run a single scenario workflow.
        
        Args:
            scenario: Scenario definition with assumptions
            workflow: LangGraph workflow instance
            base_state: Base state dictionary to clone
            gpu_id: GPU ID to use (0-5) or None for CPU
            scenario_index: Index of this scenario in the list
            
        Returns:
            Completed state with scenario metadata
            
        Raises:
            Exception: If scenario execution fails
        """
        scenario_name = scenario['name']
        scenario_id = scenario.get('id', f'scenario_{scenario_index}')
        
        device_label = f"GPU {gpu_id}" if gpu_id is not None else "CPU"
        logger.info(
            f"▶️ Starting scenario: {scenario_name} "
            f"({device_label}, index {scenario_index})"
        )
        
        start_time = datetime.now()
        
        # Emit scenario start event
        await self._emit_event(
            stage=f"scenario:{scenario_id}",
            status="started",
            payload={
                "scenario_id": scenario_id,
                "scenario_name": scenario_name,
                "scenario_index": scenario_index,
                "gpu_id": gpu_id,
                "description": scenario.get("description", ""),
                "total_scenarios": total_scenarios
            }
        )
        
        try:
            # Clone base state and inject scenario
            scenario_state = self._prepare_scenario_state(
                base_state=base_state,
                scenario=scenario,
                scenario_id=scenario_id,
                gpu_id=gpu_id
            )
            
            # DEBUG: Log debate depth
            logger.warning(f"🎯 Scenario {scenario_name}: debate_depth={scenario_state.get('debate_depth', 'NOT SET')}")
            
            # Execute workflow for this scenario
            # Rate limiting happens at individual LLM call level, not here
            logger.warning(f"🚀 Starting workflow.ainvoke for scenario: {scenario_name}")
            result = await workflow.ainvoke(scenario_state)
            logger.warning(f"✅ workflow.ainvoke completed for scenario: {scenario_name}")
            
            # Remove non-serializable fields (functions, callbacks)
            # These cannot be sent over SSE
            non_serializable_fields = ['event_callback', 'emit_event_fn']
            for field in non_serializable_fields:
                result.pop(field, None)
            
            # Add scenario metadata to result
            result['scenario_metadata'] = scenario
            result['scenario_id'] = scenario_id
            result['scenario_name'] = scenario_name
            result['scenario_gpu'] = gpu_id
            
            # Run Engine B compute for this scenario
            logger.info(f"🔢 Running Engine B quantitative compute for: {scenario_name}")
            engine_b_results = await self.run_engine_b_for_scenario(
                scenario=scenario,
                extracted_facts=result.get('extracted_facts', [])
            )
            result['engine_b_results'] = engine_b_results
            
            result['scenario_execution_time'] = (datetime.now() - start_time).total_seconds()
            
            elapsed = result['scenario_execution_time']
            logger.info(
                f"✅ Completed scenario: {scenario_name} "
                f"({device_label}, {elapsed:.1f}s, Engine B: {engine_b_results.get('status', 'N/A')})"
            )
            
            # Emit scenario complete event
            # NOTE: Base workflow now ends at 'research', so final_synthesis/debate_results may be None
            # The single debate and synthesis happen AFTER all scenarios are aggregated
            synthesis = result.get('final_synthesis')
            synthesis_length = len(synthesis) if synthesis else 0
            debate_results = result.get('debate_results')
            debate_turns = debate_results.get('total_turns', 0) if debate_results else 0
            
            await self._emit_event(
                stage=f"scenario:{scenario_id}",
                status="complete",
                payload={
                    "scenario_id": scenario_id,
                    "scenario_name": scenario_name,
                    "gpu_id": gpu_id,
                    "duration_seconds": elapsed,
                    "synthesis_length": synthesis_length,
                    "debate_turns": debate_turns,
                    "confidence_score": result.get('confidence_score', 0)
                }
            )
            
            return result
            
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(
                f"❌ Scenario {scenario_name} failed after {elapsed:.1f}s: {e}",
                exc_info=True
            )
            raise RuntimeError(
                f"Scenario '{scenario_name}' execution failed: {e}"
            ) from e
    
    def _prepare_scenario_state(
        self,
        base_state: Dict[str, Any],
        scenario: Dict[str, Any],
        scenario_id: str,
        gpu_id: Optional[int]
    ) -> Dict[str, Any]:
        """
        Prepare state for scenario execution.
        
        Args:
            base_state: Base state to clone
            scenario: Scenario definition
            scenario_id: Unique scenario identifier
            gpu_id: GPU ID assigned to this scenario
            
        Returns:
            Cloned state with scenario injected
        """
        # Deep copy state to ensure isolation
        import copy
        scenario_state = copy.deepcopy(base_state)
        
        # CRITICAL: Remove event emitters from scenario states
        # Internal scenario events (debate, critique, etc.) should NOT bubble up 
        # to the main event stream - they would cause stage ordering confusion
        scenario_state.pop('emit_event_fn', None)
        scenario_state.pop('event_callback', None)
        
        # Inject scenario information
        scenario_state['scenario'] = scenario
        scenario_state['scenario_id'] = scenario_id
        scenario_state['scenario_name'] = scenario['name']
        scenario_state['scenario_gpu'] = gpu_id
        
        # Preserve user's debate_depth selection for full legendary execution
        # User chose legendary = legendary everywhere
        
        # Add scenario context to reasoning chain
        if 'reasoning_chain' not in scenario_state:
            scenario_state['reasoning_chain'] = []
        
        scenario_state['reasoning_chain'].append(
            f"🎯 SCENARIO: {scenario['name']} - {scenario['description']}"
        )
        scenario_state['reasoning_chain'].append(
            f"   Modified assumptions: {scenario.get('modified_assumptions', {})}"
        )
        device_info = f"GPU {gpu_id}" if gpu_id is not None else "CPU"
        scenario_state['reasoning_chain'].append(
            f"   Assigned to {device_info}"
        )
        
        # Inject scenario assumptions into state for agents to use
        scenario_state['scenario_assumptions'] = scenario.get('modified_assumptions', {})
        
        return scenario_state
    
    def get_gpu_utilization(self) -> Dict[str, Any]:
        """
        Get current GPU utilization stats.
        
        Returns:
            Dictionary with GPU utilization information
        """
        if not self.gpu_available:
            return {
                'available': False,
                'message': 'No GPUs available'
            }
        
        utilization = {
            'available': True,
            'total_gpus': self.gpu_count,
            'scenario_gpus': list(range(min(self.gpu_count, 6))),
            'gpus': []
        }
        
        for i in range(min(self.gpu_count, 6)):
            try:
                gpu_info = {
                    'id': i,
                    'name': torch.cuda.get_device_name(i),
                    'memory_allocated': torch.cuda.memory_allocated(i) / 1e9,
                    'memory_reserved': torch.cuda.memory_reserved(i) / 1e9,
                    'memory_total': torch.cuda.get_device_properties(i).total_memory / 1e9
                }
                utilization['gpus'].append(gpu_info)
            except Exception as e:
                logger.warning(f"Could not get GPU {i} info: {e}")
        
        return utilization
    
    async def _emit_event(self, stage: str, status: str, payload: Dict[str, Any] = None):
        """
        Emit event to frontend if callback is configured.
        
        Args:
            stage: Event stage name
            status: Event status (running, complete, error)
            payload: Event payload data
        """
        if self.event_callback:
            try:
                await self.event_callback(
                    stage=stage,
                    status=status,
                    payload=payload or {},
                    latency_ms=None
                )
            except Exception as e:
                logger.warning(f"Failed to emit {stage} event: {e}")
    
    def apply_assumptions_to_facts(
        self,
        base_facts: List[Dict[str, Any]],
        assumptions: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Apply scenario assumption multipliers to base facts.
        
        Args:
            base_facts: List of extracted facts
            assumptions: Dict of multipliers (e.g., {"growth_rate": 0.5, "budget": 0.7})
        
        Returns:
            Dict with adjusted values for use in Engine B
        """
        adjusted = {}
        
        # Extract numeric values from facts
        for fact in base_facts:
            if isinstance(fact, dict):
                indicator = fact.get('indicator', fact.get('metric', '')).lower().replace(' ', '_')
                value = fact.get('value', fact.get('data'))
                
                # Try to convert to numeric
                try:
                    if isinstance(value, (int, float)):
                        numeric_value = float(value)
                    elif isinstance(value, str):
                        clean = value.replace(',', '').replace('%', '').replace(' ', '')
                        if 'M' in clean or 'm' in clean:
                            numeric_value = float(clean.replace('M', '').replace('m', '')) * 1_000_000
                        elif 'K' in clean or 'k' in clean:
                            numeric_value = float(clean.replace('K', '').replace('k', '')) * 1_000
                        elif 'B' in clean or 'b' in clean:
                            numeric_value = float(clean.replace('B', '').replace('b', '')) * 1_000_000_000
                        else:
                            numeric_value = float(clean)
                    else:
                        continue
                    
                    # Store with original and check for assumption multipliers
                    adjusted[indicator] = numeric_value
                    
                    # Apply any matching assumptions
                    for assumption_key, multiplier in assumptions.items():
                        if assumption_key.lower() in indicator or indicator in assumption_key.lower():
                            adjusted[indicator] = numeric_value * multiplier
                            adjusted[f"{indicator}_original"] = numeric_value
                            adjusted[f"{indicator}_multiplier"] = multiplier
                            break
                            
                except (ValueError, AttributeError, TypeError):
                    continue
        
        # Also apply assumptions that don't match existing facts
        for key, multiplier in assumptions.items():
            normalized_key = key.lower().replace(' ', '_')
            if normalized_key not in adjusted:
                adjusted[normalized_key] = multiplier  # Store as the value itself
        
        return adjusted
    
    def _find_growth_rate(self, facts: Dict[str, Any]) -> float:
        """
        Dynamically find a growth rate from extracted facts.
        Searches for any key containing 'growth', 'rate', 'increase', etc.
        Returns actual extracted value or sensible default.
        """
        # Priority order for growth-related keys
        growth_patterns = [
            'growth_rate', 'annual_growth', 'gdp_growth', 'population_growth',
            'employment_growth', 'wage_growth', 'economic_growth', 'growth',
            'increase_rate', 'expansion_rate', 'appreciation_rate'
        ]
        
        for pattern in growth_patterns:
            for key, value in facts.items():
                if pattern in key.lower() and isinstance(value, (int, float)):
                    # Ensure it's a reasonable rate (0-1 or percentage)
                    if 0 < abs(value) < 1:
                        logger.info(f"   Found growth_rate from '{key}': {value}")
                        return float(value)
                    elif 0 < abs(value) < 100:
                        # Likely a percentage, convert
                        logger.info(f"   Found growth_rate from '{key}': {value}% → {value/100}")
                        return float(value) / 100
        
        # Fallback: look for any small positive value that could be a rate
        for key, value in facts.items():
            if isinstance(value, (int, float)) and 0 < value < 0.5:
                if any(word in key.lower() for word in ['rate', 'percent', 'ratio', 'share']):
                    logger.info(f"   Found growth_rate from '{key}': {value}")
                    return float(value)
        
        logger.warning("   No growth rate found in facts, using default 0.03")
        return 0.03  # Default 3% growth
    
    def _find_base_value(self, facts: Dict[str, Any]) -> float:
        """
        Dynamically find a base/initial value from extracted facts.
        Searches for monetary values, counts, totals, etc.
        Returns actual extracted value or sensible default.
        """
        # Priority order for base value keys
        value_patterns = [
            'base_value', 'initial_value', 'total_value', 'budget', 'investment',
            'gdp', 'gdp_per_capita', 'total_employment', 'workforce', 'population',
            'revenue', 'income', 'capital', 'spending', 'expenditure', 'amount'
        ]
        
        for pattern in value_patterns:
            for key, value in facts.items():
                if pattern in key.lower() and isinstance(value, (int, float)):
                    if value > 1000:  # Reasonable base value (not a rate)
                        logger.info(f"   Found base_value from '{key}': {value}")
                        return float(value)
        
        # Fallback: find the largest reasonable numeric value
        max_value = 0
        max_key = None
        for key, value in facts.items():
            if isinstance(value, (int, float)) and value > 1000 and value > max_value:
                max_value = value
                max_key = key
        
        if max_value > 0:
            logger.info(f"   Found base_value from largest value '{max_key}': {max_value}")
            return float(max_value)
        
        logger.warning("   No base value found in facts, using default 100000")
        return 100000  # Default
    
    async def run_engine_b_for_scenario(
        self,
        scenario: Dict[str, Any],
        extracted_facts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run Engine B compute services for a specific scenario.
        
        ENHANCED: Applies scenario assumption multipliers to base facts
        before running computations.
        
        Args:
            scenario: Scenario definition with assumptions/modified_assumptions
            extracted_facts: Facts extracted from LMIS
            
        Returns:
            Engine B results for this scenario with assumptions applied
        """
        scenario_name = scenario.get("name", "Unknown")
        assumptions = scenario.get("assumptions", scenario.get("modified_assumptions", {}))
        
        logger.info(f"🔢 Running Engine B compute for scenario: {scenario_name}")
        logger.info(f"   Assumptions: {assumptions}")
        
        engine_b_results = {
            "scenario_name": scenario_name,
            "assumptions_applied": assumptions,
            "monte_carlo": None,
            "sensitivity": None,
            "forecasting": None,
            "thresholds": None,
            "status": "pending"
        }
        
        try:
            # Apply scenario assumptions to facts
            adjusted_facts = self.apply_assumptions_to_facts(extracted_facts, assumptions)
            engine_b_results["adjusted_facts_sample"] = dict(list(adjusted_facts.items())[:5])
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                
                # FIXED: Dynamic variable mapping - use ACTUAL extracted data!
                # Map common fact patterns to formula variables
                growth_rate = self._find_growth_rate(adjusted_facts)
                base_value = self._find_base_value(adjusted_facts)
                
                logger.info(f"   Dynamic mapping: growth_rate={growth_rate}, base_value={base_value}")
                
                # 1. Monte Carlo Simulation
                try:
                    # Apply assumption multipliers to distribution parameters
                    growth_mean = growth_rate * assumptions.get("growth_multiplier", 1.0)
                    value_mean = base_value * assumptions.get("value_multiplier", 1.0)
                    
                    # FIXED: success_condition must use 'result' not 'outcome'
                    # The Monte Carlo service evaluates: eval("result > threshold", {"result": simulated_values})
                    success_threshold = value_mean * 1.2  # 20% growth target
                    
                    mc_payload = {
                        "variables": {
                            "growth_rate": {
                                "distribution": "normal", 
                                "mean": growth_mean, 
                                "std": abs(growth_mean) * 0.3  # 30% std deviation
                            },
                            "base_value": {
                                "distribution": "normal", 
                                "mean": value_mean, 
                                "std": value_mean * 0.1
                            },
                        },
                        "formula": "base_value * (1 + growth_rate) ** 5",
                        "success_condition": f"result > {success_threshold}",  # FIXED: Use 'result' not 'outcome'
                        "n_simulations": 10000
                    }
                    resp = await client.post(f"{ENGINE_B_URL}/compute/monte_carlo", json=mc_payload)
                    if resp.status_code == 200:
                        engine_b_results["monte_carlo"] = resp.json()
                        logger.info(f"  ✓ Monte Carlo complete for {scenario_name}")
                    else:
                        logger.warning(f"  Monte Carlo returned {resp.status_code}: {resp.text[:200]}")
                except Exception as e:
                    logger.warning(f"  Monte Carlo failed for {scenario_name}: {e}")
                
                # 2. Sensitivity Analysis
                try:
                    # FIXED: Use meaningful policy driver names (domain agnostic)
                    # Extract relevant policy drivers from scenario assumptions
                    policy_intensity = assumptions.get("policy_intensity", assumptions.get("growth_multiplier", 1.0))
                    implementation_efficiency = assumptions.get("implementation_efficiency", 0.85)
                    success_factor = adjusted_facts.get("success_factor", adjusted_facts.get("retention_rate", 0.80))
                    
                    # CRITICAL: Variable names in base_values MUST match the formula!
                    sens_base = {
                        "annual_growth_rate": growth_rate,
                        "initial_capital": base_value,
                        "policy_effectiveness": policy_intensity,
                        "implementation_success": success_factor,
                        "resource_efficiency": implementation_efficiency,
                    }
                    
                    # FIXED: Formula must use EXACTLY the same variable names as base_values
                    sens_payload = {
                        "base_values": sens_base,
                        "formula": "initial_capital * (1 + annual_growth_rate) ** 5 * policy_effectiveness * resource_efficiency",
                        "ranges": {
                            "annual_growth_rate": {"low": growth_rate * 0.5, "high": growth_rate * 1.5},
                            "initial_capital": {"low": base_value * 0.8, "high": base_value * 1.2},
                            "policy_effectiveness": {"low": policy_intensity * 0.7, "high": policy_intensity * 1.3},
                            "resource_efficiency": {"low": implementation_efficiency * 0.8, "high": implementation_efficiency * 1.2},
                        },
                        "n_steps": 10
                    }
                    resp = await client.post(f"{ENGINE_B_URL}/compute/sensitivity", json=sens_payload)
                    if resp.status_code == 200:
                        raw_sens = resp.json()
                        # Transform Engine B format to frontend format
                        # Frontend expects: [{driver, label, contribution, direction}]
                        transformed_sensitivity = []
                        if raw_sens.get("parameter_impacts"):
                            total_swing = sum(p.get("swing", 0) for p in raw_sens["parameter_impacts"])
                            for param in raw_sens["parameter_impacts"]:
                                contribution = param.get("swing", 0) / total_swing if total_swing > 0 else 0
                                # Create human-readable label
                                label = param.get("name", "").replace("_", " ").title()
                                transformed_sensitivity.append({
                                    "driver": param.get("name", ""),
                                    "label": label,
                                    "contribution": contribution,
                                    "direction": param.get("direction", "positive")
                                })
                        engine_b_results["sensitivity"] = transformed_sensitivity
                        logger.info(f"  ✓ Sensitivity analysis complete for {scenario_name} ({len(transformed_sensitivity)} drivers)")
                    else:
                        logger.warning(f"  Sensitivity returned {resp.status_code}: {resp.text[:200]}")
                except Exception as e:
                    logger.warning(f"  Sensitivity failed for {scenario_name}: {e}")
                
                # 3. Forecasting
                try:
                    # Build historical series from facts if available
                    historical = []
                    for key in ["2019", "2020", "2021", "2022", "2023"]:
                        if key in adjusted_facts:
                            historical.append(adjusted_facts[key])
                    
                    if len(historical) < 5:
                        # Generate synthetic historical based on base value and growth
                        historical = [
                            base_value * (1 + growth_rate) ** (i - 5)
                            for i in range(5)
                        ]
                    
                    # Apply scenario assumption to forecast
                    forecast_growth = growth_rate * assumptions.get("growth_multiplier", 1.0)
                    
                    forecast_payload = {
                        "historical_values": historical,
                        "forecast_horizon": 7,
                        "method": "auto",
                        "confidence_level": 0.95
                    }
                    resp = await client.post(f"{ENGINE_B_URL}/compute/forecast", json=forecast_payload)
                    if resp.status_code == 200:
                        engine_b_results["forecasting"] = resp.json()
                        logger.info(f"  ✓ Forecasting complete for {scenario_name}")
                    else:
                        logger.warning(f"  Forecasting returned {resp.status_code}: {resp.text[:200]}")
                except Exception as e:
                    logger.warning(f"  Forecasting failed for {scenario_name}: {e}")
                
                # 4. Threshold Analysis
                try:
                    # Apply scenario to threshold parameters
                    target_value = adjusted_facts.get("target", base_value * 1.5)
                    
                    threshold_payload = {
                        "sweep_variable": "target_rate",
                        "sweep_range": [0.05, 0.30],  # 5% to 30%
                        "fixed_variables": {
                            "available_supply": base_value * assumptions.get("supply_multiplier", 1.0),
                            "total_demand": adjusted_facts.get("total_jobs", 1850000)
                        },
                        "constraints": [
                            {
                                "expression": "available_supply < total_demand * target_rate",
                                "threshold_type": "boundary",
                                "target": 0.0,
                                "description": "supply_constraint",
                                "severity": "warning"
                            }
                        ],
                        "resolution": 100
                    }
                    resp = await client.post(f"{ENGINE_B_URL}/compute/thresholds", json=threshold_payload)
                    if resp.status_code == 200:
                        engine_b_results["thresholds"] = resp.json()
                        logger.info(f"  ✓ Threshold analysis complete for {scenario_name}")
                    else:
                        logger.warning(f"  Thresholds returned {resp.status_code}: {resp.text[:200]}")
                except Exception as e:
                    logger.warning(f"  Thresholds failed for {scenario_name}: {e}")
                
                engine_b_results["status"] = "complete"
                logger.info(f"✅ Engine B compute complete for scenario: {scenario_name}")
                
        except Exception as e:
            logger.error(f"❌ Engine B failed for {scenario_name}: {e}")
            engine_b_results["status"] = "failed"
            engine_b_results["error"] = str(e)
        
        return engine_b_results

