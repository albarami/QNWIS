"""
NSIC Timing Logger - Stage-level performance tracking

Logs timing for every stage of the dual-engine workflow:
- Embeddings generation
- Knowledge graph queries
- Engine A (Azure GPT-5) inference
- Engine B (DeepSeek) inference
- Verification
- Arbitration
- Synthesis

NO MOCKS. REAL PERFORMANCE METRICS.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from contextlib import contextmanager
from enum import Enum

logger = logging.getLogger(__name__)


class Stage(Enum):
    """Processing stages for timing."""
    SCENARIO_LOAD = "scenario_load"
    CONTEXT_RETRIEVAL = "context_retrieval"
    EMBEDDING_GENERATION = "embedding_generation"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    ENGINE_A = "engine_a"
    ENGINE_B = "engine_b"
    VERIFICATION = "verification"
    ARBITRATION = "arbitration"
    SYNTHESIS = "synthesis"
    TOTAL = "total"


@dataclass
class TimingEntry:
    """Single timing measurement."""
    stage: Stage
    scenario_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def complete(self):
        """Mark entry as complete and calculate duration."""
        self.end_time = datetime.now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "scenario_id": self.scenario_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


@dataclass
class ScenarioTimingReport:
    """Complete timing report for a scenario."""
    scenario_id: str
    entries: List[TimingEntry] = field(default_factory=list)
    total_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        stage_times = {}
        for entry in self.entries:
            stage_times[entry.stage.value] = entry.duration_ms
        
        return {
            "scenario_id": self.scenario_id,
            "total_time_ms": self.total_time_ms,
            "stage_breakdown": stage_times,
            "entries": [e.to_dict() for e in self.entries],
        }


class TimingLogger:
    """
    Logs timing for all stages of dual-engine processing.
    
    Usage:
        logger = TimingLogger()
        
        with logger.time_stage(Stage.ENGINE_A, "scenario_001"):
            # Run engine A
            pass
        
        report = logger.get_report("scenario_001")
    """
    
    def __init__(self):
        """Initialize timing logger."""
        self._entries: Dict[str, List[TimingEntry]] = {}  # scenario_id -> entries
        self._active_entries: Dict[str, TimingEntry] = {}  # key -> active entry
        self._stats = {
            "total_entries": 0,
            "total_time_ms": 0.0,
            "by_stage": {stage.value: 0.0 for stage in Stage},
        }
        
        logger.info("TimingLogger initialized")
    
    def _make_key(self, stage: Stage, scenario_id: str) -> str:
        """Create unique key for active entry tracking."""
        return f"{stage.value}:{scenario_id}"
    
    @contextmanager
    def time_stage(
        self,
        stage: Stage,
        scenario_id: str,
        **metadata,
    ):
        """
        Context manager for timing a stage.
        
        Args:
            stage: Processing stage
            scenario_id: Scenario being processed
            **metadata: Additional metadata to log
            
        Yields:
            TimingEntry for the stage
        """
        entry = TimingEntry(
            stage=stage,
            scenario_id=scenario_id,
            start_time=datetime.now(),
            metadata=metadata,
        )
        
        key = self._make_key(stage, scenario_id)
        self._active_entries[key] = entry
        
        try:
            yield entry
        finally:
            entry.complete()
            del self._active_entries[key]
            
            # Store entry
            if scenario_id not in self._entries:
                self._entries[scenario_id] = []
            self._entries[scenario_id].append(entry)
            
            # Update stats
            self._stats["total_entries"] += 1
            self._stats["total_time_ms"] += entry.duration_ms
            self._stats["by_stage"][stage.value] += entry.duration_ms
            
            logger.debug(
                f"Stage {stage.value} for {scenario_id}: {entry.duration_ms:.1f}ms"
            )
    
    def start_stage(
        self,
        stage: Stage,
        scenario_id: str,
        **metadata,
    ) -> TimingEntry:
        """
        Manually start timing a stage.
        
        Args:
            stage: Processing stage
            scenario_id: Scenario being processed
            **metadata: Additional metadata
            
        Returns:
            TimingEntry (call .complete() when done)
        """
        entry = TimingEntry(
            stage=stage,
            scenario_id=scenario_id,
            start_time=datetime.now(),
            metadata=metadata,
        )
        
        key = self._make_key(stage, scenario_id)
        self._active_entries[key] = entry
        
        return entry
    
    def end_stage(
        self,
        stage: Stage,
        scenario_id: str,
    ) -> Optional[TimingEntry]:
        """
        Manually end timing a stage.
        
        Args:
            stage: Processing stage
            scenario_id: Scenario being processed
            
        Returns:
            Completed TimingEntry or None if not found
        """
        key = self._make_key(stage, scenario_id)
        entry = self._active_entries.pop(key, None)
        
        if entry:
            entry.complete()
            
            if scenario_id not in self._entries:
                self._entries[scenario_id] = []
            self._entries[scenario_id].append(entry)
            
            self._stats["total_entries"] += 1
            self._stats["total_time_ms"] += entry.duration_ms
            self._stats["by_stage"][stage.value] += entry.duration_ms
            
            logger.debug(
                f"Stage {stage.value} for {scenario_id}: {entry.duration_ms:.1f}ms"
            )
        
        return entry
    
    def get_report(self, scenario_id: str) -> Optional[ScenarioTimingReport]:
        """
        Get timing report for a scenario.
        
        Args:
            scenario_id: Scenario to get report for
            
        Returns:
            ScenarioTimingReport or None if not found
        """
        entries = self._entries.get(scenario_id, [])
        if not entries:
            return None
        
        total_time = sum(e.duration_ms for e in entries)
        
        return ScenarioTimingReport(
            scenario_id=scenario_id,
            entries=entries,
            total_time_ms=total_time,
        )
    
    def get_all_reports(self) -> List[ScenarioTimingReport]:
        """Get timing reports for all scenarios."""
        reports = []
        for scenario_id in self._entries:
            report = self.get_report(scenario_id)
            if report:
                reports.append(report)
        return reports
    
    def get_stage_summary(self) -> Dict[str, Dict[str, float]]:
        """
        Get summary of timing by stage across all scenarios.
        
        Returns:
            Dict with stage -> {total_ms, avg_ms, count}
        """
        summary = {}
        
        for stage in Stage:
            stage_entries = [
                e for entries in self._entries.values()
                for e in entries
                if e.stage == stage
            ]
            
            if stage_entries:
                total_ms = sum(e.duration_ms for e in stage_entries)
                avg_ms = total_ms / len(stage_entries)
                summary[stage.value] = {
                    "total_ms": total_ms,
                    "avg_ms": avg_ms,
                    "count": len(stage_entries),
                }
        
        return summary
    
    def get_stats(self) -> Dict[str, Any]:
        """Get overall timing statistics."""
        return {
            **self._stats,
            "scenarios_count": len(self._entries),
            "active_entries": len(self._active_entries),
        }
    
    def clear(self):
        """Clear all timing data."""
        self._entries.clear()
        self._active_entries.clear()
        self._stats = {
            "total_entries": 0,
            "total_time_ms": 0.0,
            "by_stage": {stage.value: 0.0 for stage in Stage},
        }


# Global timing logger instance
_global_logger: Optional[TimingLogger] = None


def get_timing_logger() -> TimingLogger:
    """Get or create global timing logger."""
    global _global_logger
    if _global_logger is None:
        _global_logger = TimingLogger()
    return _global_logger


def reset_timing_logger():
    """Reset global timing logger."""
    global _global_logger
    _global_logger = TimingLogger()
