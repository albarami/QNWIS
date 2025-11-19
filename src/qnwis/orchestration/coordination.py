"""
Coordinator for multi-agent execution.

Schedules single/parallel/sequential agent calls, executes them,
and merges outputs into a single uniform report.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, cast

from ..agents.base import AgentReport
from ..orchestration.merge import merge_results
from ..orchestration.policies import DEFAULT_POLICY, CoordinationPolicy
from ..orchestration.registry import AgentRegistry
from ..orchestration.schemas import (
    Citation,
    Freshness,
    OrchestrationResult,
    ReportSection,
    Reproducibility,
)
from ..orchestration.types import AgentCallSpec, ExecutionTrace

logger = logging.getLogger(__name__)


class CoordinationError(Exception):
    """Raised when coordination fails."""


class Coordinator:
    """
    Schedules and executes multi-agent workflows.

    Supports three execution modes:
    - single: Execute one agent
    - parallel: Execute multiple agents concurrently (within limits)
    - sequential: Execute agents in waves, each wave in parallel
    """

    def __init__(
        self,
        registry: AgentRegistry,
        policy: CoordinationPolicy | None = None,
    ) -> None:
        """
        Initialize the coordinator.

        Args:
            registry: AgentRegistry for intent resolution
            policy: CoordinationPolicy for execution limits
        """
        self.registry = registry
        self.policy = policy or DEFAULT_POLICY

    def _normalize_specs(self, specs: list[AgentCallSpec]) -> list[AgentCallSpec]:
        """
        Validate and normalize agent call specifications.

        Ensures intents are registered, methods match the registry, assigns default
        aliases, and materializes dependency lists for later execution.

        Args:
            specs: Raw agent call specifications

        Returns:
            Normalized list of agent call specifications

        Raises:
            CoordinationError: If specs reference unknown intents, unregistered
                methods, or contain duplicate aliases/dependencies
        """
        normalized: list[AgentCallSpec] = []
        seen_aliases: set[str] = set()

        for raw_spec in specs:
            spec = cast(AgentCallSpec, dict(raw_spec))
            intent = spec["intent"]

            agent, registered_method = self.registry.resolve(intent)
            declared_method = spec["method"]

            if declared_method != registered_method:
                raise CoordinationError(
                    f"Intent '{intent}' is registered for method '{registered_method}', "
                    f"but specification attempted '{declared_method}'."
                )

            alias = spec.get("alias") or intent
            if alias in seen_aliases:
                raise CoordinationError(f"Duplicate agent alias detected: {alias}")
            seen_aliases.add(alias)

            depends_on = list(spec.get("depends_on", []))

            # Normalize fields
            spec["alias"] = alias
            if depends_on:
                spec["depends_on"] = depends_on
            else:
                spec.pop("depends_on", None)
            spec["method"] = registered_method
            # Ensure params is a shallow copy to avoid accidental mutation
            spec["params"] = dict(spec.get("params", {}))

            normalized.append(spec)

        aliases = {spec["alias"] for spec in normalized}
        for spec in normalized:
            alias = spec["alias"]
            for dependency in spec.get("depends_on", []):
                if dependency not in aliases:
                    raise CoordinationError(
                        f"Specification '{alias}' depends on unknown alias '{dependency}'."
                    )
                if dependency == alias:
                    raise CoordinationError(
                        f"Specification '{alias}' cannot declare a self dependency."
                    )

        return normalized

    def _validate_sequential_dependencies(self, specs: list[AgentCallSpec]) -> None:
        """
        Validate that sequential execution respects declared dependencies.

        Args:
            specs: Normalized specifications ordered for execution

        Raises:
            CoordinationError: If a dependency would execute after its dependent
        """
        executed: set[str] = set()
        for spec in specs:
            alias = spec["alias"]
            for dependency in spec.get("depends_on", []):
                if dependency not in executed:
                    raise CoordinationError(
                        f"Sequential execution requires dependency '{dependency}' to "
                        f"run before '{alias}'."
                    )
            executed.add(alias)

    @staticmethod
    def _build_trace(
        intent: str,
        agent_name: str,
        method_name: str,
        elapsed_ms: float,
        attempt: int,
        success: bool,
        warnings: list[str],
        error: str | None = None,
    ) -> ExecutionTrace:
        """
        Construct an execution trace envelope for agent tracking.

        Args:
            intent: Intent executed
            agent_name: Agent class name
            method_name: Method name executed
            elapsed_ms: Execution duration in milliseconds
            attempt: Attempt number producing the trace
            success: Whether execution succeeded
            warnings: Warnings produced during execution
            error: Optional error message for failures

        Returns:
            ExecutionTrace object
        """
        trace: ExecutionTrace = {
            "intent": intent,
            "agent": agent_name,
            "method": method_name,
            "elapsed_ms": elapsed_ms,
            "attempt": attempt,
            "success": success,
            "warnings": list(warnings),
        }
        if error:
            trace["error"] = error
        return trace

    def _build_placeholder_result(
        self,
        spec: AgentCallSpec,
        warning: str,
        attempt: int,
        success: bool,
        elapsed_ms: float,
        error: str | None = None,
    ) -> OrchestrationResult:
        """
        Create a placeholder orchestration result for skipped/failed executions.

        Args:
            spec: Agent call specification
            warning: Warning message to surface
            attempt: Attempt that produced this outcome (0 for not executed)
            success: Whether the placeholder should be marked successful
            elapsed_ms: Recorded execution time in milliseconds
            error: Optional error detail

        Returns:
            OrchestrationResult capturing the failure metadata
        """
        agent, method_name = self.registry.resolve(spec["intent"])
        agent_name = type(agent).__name__
        warnings = [warning] if warning else []
        trace = self._build_trace(
            intent=spec["intent"],
            agent_name=agent_name,
            method_name=method_name,
            elapsed_ms=elapsed_ms,
            attempt=attempt,
            success=success,
            warnings=warnings,
            error=error,
        )

        sections: list[ReportSection] = []
        if warning:
            sections.append(
                ReportSection(
                    title="Warnings",
                    body_md=f"- {warning}",
                )
            )

        return OrchestrationResult(
            ok=success,
            intent=spec["intent"],  # type: ignore[assignment]
            sections=sections,
            citations=[],
            freshness={},
            reproducibility=Reproducibility(
                method=f"{agent_name}.{method_name}",
                params=dict(spec.get("params", {})),
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            ),
            warnings=warnings,
            agent_traces=[trace],
        )

    def _record_wave_skip(
        self,
        wave: list[AgentCallSpec],
        reason: str,
        alias_status: dict[str, bool],
    ) -> list[OrchestrationResult]:
        """
        Produce placeholder results for an entire wave that is being skipped.

        Args:
            wave: Wave specification to skip
            reason: Reason to include in warnings
            alias_status: Map tracking alias success/failure

        Returns:
            List of placeholder results for the skipped wave
        """
        skipped_results: list[OrchestrationResult] = []
        for spec in wave:
            alias = spec.get("alias", spec["intent"])
            warning = f"{reason} (alias='{alias}')"
            result = self._build_placeholder_result(
                spec=spec,
                warning=warning,
                attempt=0,
                success=False,
                elapsed_ms=0.0,
            )
            alias_status[alias] = False
            skipped_results.append(result)
        return skipped_results

    def plan(
        self,
        route: str,
        specs: list[AgentCallSpec],
        mode: str,
    ) -> list[list[AgentCallSpec]]:
        """
        Plan execution waves based on mode.

        Args:
            route: Primary intent route
            specs: List of AgentCallSpec declarations
            mode: Execution mode (single, parallel, sequential)

        Returns:
            List of execution waves, each wave is a list of specs to run in parallel

        Raises:
            ValueError: If mode is invalid or specs don't match mode
        """
        if not specs:
            raise ValueError("Cannot plan execution with empty specs")

        normalized_specs = self._normalize_specs(specs)

        if mode == "single":
            if len(normalized_specs) != 1:
                raise ValueError(
                    f"Single mode requires exactly 1 spec, got {len(normalized_specs)}"
                )
            logger.info(
                "Planned single execution for route=%s alias=%s",
                route,
                normalized_specs[0]["alias"],
            )
            return [[normalized_specs[0]]]

        if mode == "parallel":
            # Split into waves based on policy max_parallel
            max_parallel = self.policy.max_parallel
            waves: list[list[AgentCallSpec]] = []
            for i in range(0, len(normalized_specs), max_parallel):
                wave = normalized_specs[i : i + max_parallel]
                waves.append(wave)
            logger.info(
                "Planned parallel execution: %d specs in %d waves (max %d per wave)",
                len(normalized_specs),
                len(waves),
                max_parallel,
            )
            return waves

        if mode == "sequential":
            # Each spec gets its own wave
            self._validate_sequential_dependencies(normalized_specs)
            waves = [[spec] for spec in normalized_specs]
            dependency_counts = sum(bool(spec.get("depends_on")) for spec in normalized_specs)
            logger.info(
                "Planned sequential execution: %d waves (dependencies=%d)",
                len(waves),
                dependency_counts,
            )
            return waves

        raise ValueError(f"Unknown execution mode: {mode}")

    def _execute_wave_parallel(
        self,
        wave: list[AgentCallSpec],
        prefetch_cache: dict[str, Any],
        alias_status: dict[str, bool],
        mode: str,
    ) -> list[OrchestrationResult]:
        """
        Execute a wave of agent calls in parallel using ThreadPoolExecutor.
        
        Args:
            wave: List of agent specs to execute in parallel
            prefetch_cache: Read-only cache from prefetcher
            alias_status: Map tracking alias success/failure
            mode: Execution mode (for dependency checking)
            
        Returns:
            List of OrchestrationResult instances from the wave
        """
        wave_results: list[OrchestrationResult] = []
        
        # For sequential mode or single-spec waves, use serial execution
        if mode == "sequential" or len(wave) == 1:
            for spec in wave:
                alias = spec.get("alias", spec["intent"])
                dependencies = spec.get("depends_on", [])
                
                # Check dependencies for sequential mode
                unmet_dependencies = [
                    dep for dep in dependencies if alias_status.get(dep) is False
                ]
                if mode == "sequential" and unmet_dependencies:
                    warning = (
                        f"Skipped alias '{alias}' because dependency "
                        f"{', '.join(unmet_dependencies)} returned ok=False."
                    )
                    logger.warning(warning)
                    placeholder = self._build_placeholder_result(
                        spec=spec,
                        warning=warning,
                        attempt=0,
                        success=False,
                        elapsed_ms=0.0,
                    )
                    alias_status[alias] = False
                    wave_results.append(placeholder)
                    continue
                
                try:
                    result, _ = self._execute_single(spec, prefetch_cache)
                    alias_status[alias] = result.ok
                    wave_results.append(result)
                except Exception as exc:
                    error_message = (
                        f"Execution failed for alias '{alias}' (intent={spec['intent']}): {exc}"
                    )
                    logger.exception(error_message)
                    placeholder = self._build_placeholder_result(
                        spec=spec,
                        warning=error_message,
                        attempt=1,
                        success=False,
                        elapsed_ms=0.0,
                        error=str(exc),
                    )
                    alias_status[alias] = False
                    wave_results.append(placeholder)
            
            return wave_results
        
        # Parallel execution for multi-spec waves
        max_workers = min(len(wave), self.policy.max_parallel)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all specs in the wave
            future_to_spec = {
                executor.submit(self._execute_single, spec, prefetch_cache): spec
                for spec in wave
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_spec):
                spec = future_to_spec[future]
                alias = spec.get("alias", spec["intent"])
                
                try:
                    result, _ = future.result()
                    alias_status[alias] = result.ok
                    wave_results.append(result)
                    
                    if not result.ok:
                        logger.warning(
                            "Agent returned ok=False for alias '%s' (intent=%s, method=%s)",
                            alias,
                            spec["intent"],
                            spec["method"],
                        )
                except Exception as exc:
                    error_message = (
                        f"Execution failed for alias '{alias}' (intent={spec['intent']}): {exc}"
                    )
                    logger.exception(error_message)
                    placeholder = self._build_placeholder_result(
                        spec=spec,
                        warning=error_message,
                        attempt=1,
                        success=False,
                        elapsed_ms=0.0,
                        error=str(exc),
                    )
                    alias_status[alias] = False
                    wave_results.append(placeholder)
        
        return wave_results

    def execute(
        self,
        waves: list[list[AgentCallSpec]],
        prefetch_cache: dict[str, Any],
        mode: str = "parallel",
    ) -> list[OrchestrationResult]:
        """
        Execute agent call waves and collect results.

        Args:
            waves: List of execution waves
            prefetch_cache: Read-only cache from prefetcher
            mode: Execution mode that produced the waves (single/parallel/sequential)

        Returns:
            List of OrchestrationResult instances produced by the execution

        Raises:
            CoordinationError: If no results are produced
        """
        logger.info(
            "Executing %d waves (mode=%s) with prefetch cache containing %d entries",
            len(waves),
            mode,
            len(prefetch_cache),
        )

        results: list[OrchestrationResult] = []
        alias_status: dict[str, bool] = {}
        total_start = time.perf_counter()
        total_timeout_ms = self.policy.total_timeout_ms

        for wave_index, wave in enumerate(waves):
            wave_number = wave_index + 1
            elapsed_before_wave = (time.perf_counter() - total_start) * 1000
            if elapsed_before_wave >= total_timeout_ms:
                timeout_reason = (
                    f"Total execution timeout {total_timeout_ms}ms exceeded before wave "
                    f"{wave_number} ({elapsed_before_wave:.0f}ms elapsed)."
                )
                logger.warning(timeout_reason)
                results.extend(self._record_wave_skip(wave, timeout_reason, alias_status))
                skip_reason = "Skipped due to earlier total timeout breach"
                for remaining_wave in waves[wave_index + 1 :]:
                    results.extend(
                        self._record_wave_skip(remaining_wave, skip_reason, alias_status)
                    )
                break

            logger.info(
                "Executing wave %d/%d with %d agents (parallelism=%d)",
                wave_number,
                len(waves),
                len(wave),
                min(len(wave), self.policy.max_parallel),
            )
            wave_start = time.perf_counter()
            
            # Execute wave in parallel
            wave_results = self._execute_wave_parallel(wave, prefetch_cache, alias_status, mode)
            results.extend(wave_results)
            
            # Check for timeout after wave completion
            total_elapsed_ms = (time.perf_counter() - total_start) * 1000
            wave_aborted = False
            
            if total_elapsed_ms >= total_timeout_ms:
                timeout_warning = (
                    f"Total execution timeout {total_timeout_ms}ms exceeded after wave "
                    f"{wave_number} ({total_elapsed_ms:.0f}ms). Remaining waves skipped."
                )
                logger.warning(timeout_warning)
                
                for remaining_wave in waves[wave_index + 1 :]:
                    skipped_remaining = self._record_wave_skip(
                        remaining_wave,
                        "Skipped due to total timeout breach",
                        alias_status,
                    )
                    results.extend(skipped_remaining)
                
                wave_aborted = True
            
            wave_elapsed_ms = (time.perf_counter() - wave_start) * 1000
            success_count = sum(1 for res in wave_results if res.ok)
            logger.info(
                "Wave %d completed in %.0fms (parallelism=%d, success=%d/%d)",
                wave_number,
                wave_elapsed_ms,
                min(len(wave), self.policy.max_parallel),
                success_count,
                len(wave_results) or len(wave),
            )

            if wave_aborted:
                break

        if not results:
            msg = f"All {len(waves)} waves failed to produce results"
            logger.error(msg)
            raise CoordinationError(msg)

        total_elapsed_ms = (time.perf_counter() - total_start) * 1000
        logger.info(
            "Execution complete in %.0fms: %d results from %d waves",
            total_elapsed_ms,
            len(results),
            len(waves),
        )

        return results

    def _execute_single(
        self,
        spec: AgentCallSpec,
        prefetch_cache: dict[str, Any],
    ) -> tuple[OrchestrationResult, ExecutionTrace]:
        """
        Execute a single agent call.

        Args:
            spec: AgentCallSpec to execute
            prefetch_cache: Read-only prefetch cache

        Returns:
            Tuple of (OrchestrationResult, ExecutionTrace)

        Raises:
            Exception: If execution fails
        """
        intent = spec["intent"]
        declared_method = spec["method"]
        params = spec["params"]
        alias = spec.get("alias", intent)

        logger.debug(
            "Executing agent alias=%s intent=%s method=%s params_keys=%s",
            alias,
            intent,
            declared_method,
            list(params.keys()),
        )

        start_time = time.perf_counter()
        attempt = 1

        agent, registered_method = self.registry.resolve(intent)
        if declared_method != registered_method:
            raise CoordinationError(
                f"Spec for intent '{intent}' attempted to call "
                f"'{declared_method}' but registry only permits '{registered_method}'."
            )

        method = getattr(agent, registered_method)
        if not callable(method):
            raise CoordinationError(
                f"Resolved attribute '{registered_method}' on {type(agent).__name__} is not callable."
            )

        agent_report = method(**params)
        if not isinstance(agent_report, AgentReport):
            raise CoordinationError(
                f"Agent {type(agent).__name__}.{registered_method} returned "
                f"{type(agent_report).__name__}, expected AgentReport."
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        warnings = list(agent_report.warnings)
        ok = True

        if elapsed_ms > self.policy.per_agent_timeout_ms:
            timeout_warning = (
                f"Agent {type(agent).__name__}.{registered_method} exceeded per-agent "
                f"timeout of {self.policy.per_agent_timeout_ms}ms "
                f"(elapsed={elapsed_ms:.0f}ms)."
            )
            logger.warning(timeout_warning)
            warnings.append(timeout_warning)
            ok = False

        trace = self._build_trace(
            intent=intent,
            agent_name=type(agent).__name__,
            method_name=registered_method,
            elapsed_ms=elapsed_ms,
            attempt=attempt,
            success=ok,
            warnings=warnings,
        )

        result = self._convert_to_orchestration_result(
            agent_report=agent_report,
            intent=intent,
            method=registered_method,
            params=params,
            warnings=warnings,
            ok=ok,
            trace=trace,
        )

        logger.info(
            "Agent executed: %s.%s in %.0fms (ok=%s)",
            type(agent).__name__,
            registered_method,
            elapsed_ms,
            ok,
        )

        return result, trace

    def _convert_to_orchestration_result(
        self,
        *,
        agent_report: AgentReport,
        intent: str,
        method: str,
        params: dict[str, Any],
        warnings: list[str],
        ok: bool,
        trace: ExecutionTrace,
    ) -> OrchestrationResult:
        """
        Convert AgentReport to OrchestrationResult.

        Args:
            agent_report: Report from agent execution
            intent: Intent that was executed
            method: Method name
            params: Parameters used
            warnings: Aggregated warnings to attach
            ok: Whether the execution should be marked as successful
            trace: Execution trace envelope for the agent call

        Returns:
            OrchestrationResult
        """
        # Build sections from findings
        sections: list[ReportSection] = []

        # Executive Summary
        if agent_report.findings:
            summary_text = "\n\n".join(
                f"**{finding.title}**: {finding.summary}"
                for finding in agent_report.findings[:3]
            )
            sections.append(
                ReportSection(
                    title="Executive Summary",
                    body_md=summary_text or "No findings available.",
                )
            )

        # Key Findings
        findings_text = "\n\n".join(
            f"### {finding.title}\n\n{finding.summary}\n\n"
            f"**Metrics**: {', '.join(f'{k}={v:.2f}' for k, v in (finding.metrics or {}).items())}"
            for finding in agent_report.findings
        )
        if findings_text:
            sections.append(
                ReportSection(
                    title="Key Findings",
                    body_md=findings_text,
                )
            )

        # Evidence
        evidence_items = []
        for finding in agent_report.findings:
            for evidence in finding.evidence:
                evidence_items.append(
                    f"- **{evidence.dataset_id}** ({evidence.query_id}): {evidence.locator}"
                )
        if evidence_items:
            sections.append(
                ReportSection(
                    title="Evidence",
                    body_md="\n".join(evidence_items),
                )
            )

        # Build citations
        citations: list[Citation] = []
        freshness_map: dict[str, Freshness] = {}

        for finding in agent_report.findings:
            for evidence in finding.evidence:
                citation = Citation(
                    query_id=evidence.query_id,
                    dataset_id=evidence.dataset_id,
                    locator=evidence.locator,
                    fields=evidence.fields,
                    timestamp=evidence.freshness_updated_at,
                )
                citations.append(citation)

                # Track freshness
                if evidence.freshness_as_of:
                    freshness_map[evidence.dataset_id] = Freshness(
                        source=evidence.dataset_id,
                        last_updated=evidence.freshness_as_of,
                        age_days=None,
                        min_timestamp=evidence.freshness_as_of,
                        max_timestamp=evidence.freshness_as_of,
                    )

        # Reproducibility
        reproducibility = Reproducibility(
            method=f"{agent_report.agent}.{method}",
            params=params,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        # Warnings section if any
        if warnings:
            sections.append(
                ReportSection(
                    title="Warnings",
                    body_md="\n".join(f"- {w}" for w in warnings),
                )
            )

        return OrchestrationResult(
            ok=ok,
            intent=intent,  # type: ignore[assignment]
            sections=sections,
            citations=citations,
            freshness=freshness_map,
            reproducibility=reproducibility,
            warnings=list(warnings),
            agent_traces=[trace],
        )

    def aggregate(self, partials: list[OrchestrationResult]) -> OrchestrationResult:
        """
        Merge partial results into a single final report.

        Args:
            partials: List of partial OrchestrationResult objects

        Returns:
            Single merged OrchestrationResult

        Raises:
            ValueError: If partials list is empty
        """
        logger.info("Aggregating %d partial results", len(partials))

        if not partials:
            raise ValueError("Cannot aggregate empty partials list")

        # Use deterministic merger
        merged = merge_results(partials)

        logger.info("Aggregation complete: %d sections", len(merged.sections))

        return merged
