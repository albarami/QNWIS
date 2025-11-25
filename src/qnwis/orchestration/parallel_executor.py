"""
Parallel Debate Executor for Multi-Scenario Analysis.

Executes multiple debate workflows simultaneously across GPUs 0-5.
Rate limiting happens at individual LLM call level (not here).
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import torch

logger = logging.getLogger(__name__)


class ParallelDebateExecutor:
    """
    Execute multiple debates in parallel across available GPUs.
    
    Distributes scenarios across GPUs 0-5, with rate limiting handled
    at the individual LLM call level by the rate_limiter module.
    """
    
    def __init__(self, num_parallel: int = 6, event_callback=None):
        """
        Initialize parallel executor.
        
        Args:
            num_parallel: Number of scenarios to run simultaneously (default 6)
            event_callback: Optional async callback for emitting events to frontend
        """
        self.num_parallel = num_parallel
        self.event_callback = event_callback
        
        # Check GPU availability
        self.gpu_available = torch.cuda.is_available()
        self.gpu_count = torch.cuda.device_count() if self.gpu_available else 0
        
        if self.gpu_available:
            logger.info(f"✅ Parallel executor initialized with {self.gpu_count} GPUs")
            logger.info(f"   Will run {num_parallel} scenarios simultaneously")
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
    
    async def execute_scenarios(
        self, 
        scenarios: List[Dict[str, Any]],
        base_workflow: Any,
        initial_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple scenarios in parallel.
        
        Args:
            scenarios: List of scenario definitions from ScenarioGenerator
            base_workflow: Compiled LangGraph workflow to run for each scenario
            initial_state: Base state to clone for each scenario
            
        Returns:
            List of completed scenario results (successful executions only)
        """
        logger.info(f"Starting parallel execution of {len(scenarios)} scenarios")
        start_time = datetime.now()
        
        # Emit parallel execution start event
        await self._emit_event(
            stage="parallel_exec",
            status="started",
            payload={
                "total_scenarios": len(scenarios),
                "gpu_allocation": list(range(min(6, len(scenarios)))),
                "scenarios": [{"name": s.get("name", f"Scenario {i}"), "description": s.get("description", "")} for i, s in enumerate(scenarios)]
            }
        )
        
        # Create tasks for each scenario
        tasks = []
        for i, scenario in enumerate(scenarios):
            # Distribute across GPUs 0-5
            gpu_id = i % 6 if self.gpu_available else None
            
            task = self._run_scenario(
                scenario=scenario,
                workflow=base_workflow,
                base_state=initial_state,
                gpu_id=gpu_id,
                scenario_index=i,
                total_scenarios=len(scenarios)
            )
            tasks.append(task)
        
        # Execute all scenarios concurrently
        logger.info(f"Launching {len(tasks)} concurrent scenario executions...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Separate successful and failed results
        successful_results = []
        failed_count = 0
        
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
                "scenario_results": successful_results
            }
        )
        
        return successful_results
    
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
        
        logger.info(
            f"▶️ Starting scenario: {scenario_name} "
            f"(GPU {gpu_id if gpu_id is not None else 'CPU'}, index {scenario_index})"
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
            
            # Execute workflow for this scenario
            # Rate limiting happens at individual LLM call level, not here
            result = await workflow.ainvoke(scenario_state)
            
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
            result['scenario_execution_time'] = (datetime.now() - start_time).total_seconds()
            
            elapsed = result['scenario_execution_time']
            logger.info(
                f"✅ Completed scenario: {scenario_name} "
                f"(GPU {gpu_id if gpu_id is not None else 'CPU'}, {elapsed:.1f}s)"
            )
            
            # Emit scenario complete event
            await self._emit_event(
                stage=f"scenario:{scenario_id}",
                status="complete",
                payload={
                    "scenario_id": scenario_id,
                    "scenario_name": scenario_name,
                    "gpu_id": gpu_id,
                    "duration_seconds": elapsed,
                    "synthesis_length": len(result.get('final_synthesis', '')),
                    "debate_turns": result.get('debate_results', {}).get('total_turns', 0) if result.get('debate_results') else 0,
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
        
        # Inject scenario information
        scenario_state['scenario'] = scenario
        scenario_state['scenario_id'] = scenario_id
        scenario_state['scenario_name'] = scenario['name']
        scenario_state['scenario_gpu'] = gpu_id
        
        # Add scenario context to reasoning chain
        if 'reasoning_chain' not in scenario_state:
            scenario_state['reasoning_chain'] = []
        
        scenario_state['reasoning_chain'].append(
            f"🎯 SCENARIO: {scenario['name']} - {scenario['description']}"
        )
        scenario_state['reasoning_chain'].append(
            f"   Modified assumptions: {scenario.get('modified_assumptions', {})}"
        )
        scenario_state['reasoning_chain'].append(
            f"   Assigned to GPU {gpu_id if gpu_id is not None else 'CPU'}"
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

