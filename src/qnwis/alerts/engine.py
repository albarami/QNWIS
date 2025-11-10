"""
Deterministic alert evaluation engine.

Implements threshold, yoy_delta_pct, slope_window, and break_event triggers.
Re-uses CUSUM from analysis.change_points module.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

from ..analysis.change_points import cusum_breaks
from ..analysis.trend_utils import window_slopes, yoy
from .rules import AlertRule, TriggerOperator, TriggerType

logger = logging.getLogger(__name__)


@dataclass
class AlertDecision:
    """
    Result of alert rule evaluation.

    Attributes:
        rule_id: Rule identifier
        triggered: Whether alert condition was met
        evidence: Supporting data (QIDs, params, deltas, etc.)
        message: Human-readable explanation
        timestamp: ISO timestamp of evaluation
    """

    rule_id: str
    triggered: bool
    evidence: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    timestamp: str = ""


class AlertEngine:
    """
    Deterministic alert evaluation engine.

    Evaluates rules against time-series data using predefined trigger logic.
    All computations are reproducible and guard against edge cases.
    """

    def __init__(self) -> None:
        """Initialize the alert engine."""
        self._evaluators = {
            TriggerType.THRESHOLD: self._eval_threshold,
            TriggerType.YOY_DELTA_PCT: self._eval_yoy_delta_pct,
            TriggerType.SLOPE_WINDOW: self._eval_slope_window,
            TriggerType.BREAK_EVENT: self._eval_break_event,
        }

    def evaluate(
        self,
        rule: AlertRule,
        series: list[float],
        timestamps: list[str] | None = None,
    ) -> AlertDecision:
        """
        Evaluate an alert rule against time-series data.

        Args:
            rule: Alert rule specification
            series: Time-series values (most recent last)
            timestamps: Optional ISO timestamps corresponding to series

        Returns:
            AlertDecision with triggered flag and evidence

        Raises:
            ValueError: If series is empty or contains invalid values
        """
        if not series:
            return AlertDecision(
                rule_id=rule.rule_id,
                triggered=False,
                message="Empty series provided",
            )

        # Guard against NaN/Inf
        if any(math.isnan(v) or math.isinf(v) for v in series):
            return AlertDecision(
                rule_id=rule.rule_id,
                triggered=False,
                message="Series contains NaN or Inf values",
            )

        # Clamp rates if applicable
        if rule.is_rate_metric():
            series = [rule.clamp_rate(v) for v in series]

        evaluator = self._evaluators.get(rule.trigger.type)
        if not evaluator:
            return AlertDecision(
                rule_id=rule.rule_id,
                triggered=False,
                message=f"Unknown trigger type: {rule.trigger.type}",
            )

        return evaluator(rule, series, timestamps or [])

    def _eval_threshold(
        self,
        rule: AlertRule,
        series: list[float],
        timestamps: list[str],
    ) -> AlertDecision:
        """
        Evaluate threshold-based trigger.

        Checks if the most recent value meets the threshold condition.
        """
        current_value = series[-1]
        threshold = rule.trigger.value
        op = rule.trigger.op

        triggered = False
        if op == TriggerOperator.LT:
            triggered = current_value < threshold
        elif op == TriggerOperator.LTE:
            triggered = current_value <= threshold
        elif op == TriggerOperator.GT:
            triggered = current_value > threshold
        elif op == TriggerOperator.GTE:
            triggered = current_value >= threshold
        elif op == TriggerOperator.EQ:
            triggered = abs(current_value - threshold) < 1e-9

        message = (
            f"Current value {current_value:.4f} "
            f"{op.value if op else 'cmp'} threshold {threshold:.4f}"
        )

        return AlertDecision(
            rule_id=rule.rule_id,
            triggered=triggered,
            evidence={
                "current_value": current_value,
                "threshold": threshold,
                "operator": op.value if op else None,
            },
            message=message,
        )

    def _eval_yoy_delta_pct(
        self,
        rule: AlertRule,
        series: list[float],
        timestamps: list[str],
    ) -> AlertDecision:
        """
        Evaluate year-over-year delta percentage trigger.

        Computes YoY change and checks against threshold.
        """
        if len(series) < 13:  # Need 12+ months for YoY
            return AlertDecision(
                rule_id=rule.rule_id,
                triggered=False,
                message="Insufficient data for YoY calculation (need 13+ points)",
            )

        yoy_deltas = yoy(series)
        if not yoy_deltas:
            return AlertDecision(
                rule_id=rule.rule_id,
                triggered=False,
                message="YoY calculation returned empty",
            )

        # Most recent YoY delta
        latest_yoy = yoy_deltas[-1]
        threshold = rule.trigger.value
        op = rule.trigger.op or TriggerOperator.LTE

        triggered = False
        if op == TriggerOperator.LT:
            triggered = latest_yoy < threshold
        elif op == TriggerOperator.LTE:
            triggered = latest_yoy <= threshold
        elif op == TriggerOperator.GT:
            triggered = latest_yoy > threshold
        elif op == TriggerOperator.GTE:
            triggered = latest_yoy >= threshold

        message = (
            f"YoY delta {latest_yoy:.2f}% "
            f"{op.value} threshold {threshold:.2f}%"
        )

        return AlertDecision(
            rule_id=rule.rule_id,
            triggered=triggered,
            evidence={
                "yoy_delta_pct": latest_yoy,
                "threshold": threshold,
                "operator": op.value,
            },
            message=message,
        )

    def _eval_slope_window(
        self,
        rule: AlertRule,
        series: list[float],
        timestamps: list[str],
    ) -> AlertDecision:
        """
        Evaluate slope-based trigger over window.

        Computes linear slope over the specified window and checks threshold.
        """
        window_size = rule.window.months
        if len(series) < window_size:
            return AlertDecision(
                rule_id=rule.rule_id,
                triggered=False,
                message=f"Insufficient data for window (need {window_size}+ points)",
            )

        slope_entries = window_slopes(series, windows=(window_size,))
        if not slope_entries:
            return AlertDecision(
                rule_id=rule.rule_id,
                triggered=False,
                message="Slope calculation returned empty",
            )

        # Most recent slope (single entry tuple)
        _, latest_slope = slope_entries[-1]
        if latest_slope is None:
            return AlertDecision(
                rule_id=rule.rule_id,
                triggered=False,
                message=f"Slope calculation unavailable for window {window_size}",
            )

        threshold = rule.trigger.value
        op = rule.trigger.op or TriggerOperator.LT

        triggered = False
        if op == TriggerOperator.LT:
            triggered = latest_slope < threshold
        elif op == TriggerOperator.LTE:
            triggered = latest_slope <= threshold
        elif op == TriggerOperator.GT:
            triggered = latest_slope > threshold
        elif op == TriggerOperator.GTE:
            triggered = latest_slope >= threshold

        message = (
            f"Slope {latest_slope:.4f} over {window_size} months "
            f"{op.value} threshold {threshold:.4f}"
        )

        return AlertDecision(
            rule_id=rule.rule_id,
            triggered=triggered,
            evidence={
                "slope": latest_slope,
                "window_months": window_size,
                "threshold": threshold,
                "operator": op.value,
            },
            message=message,
        )

    def _eval_break_event(
        self,
        rule: AlertRule,
        series: list[float],
        timestamps: list[str],
    ) -> AlertDecision:
        """
        Evaluate structural break detection trigger.

        Uses CUSUM to detect change points in recent window.
        """
        window_size = rule.window.months
        if len(series) < window_size:
            return AlertDecision(
                rule_id=rule.rule_id,
                triggered=False,
                message=f"Insufficient data for break detection (need {window_size}+ points)",
            )

        # Use recent window
        recent_series = series[-window_size:]

        # CUSUM parameters from trigger value (h threshold)
        h_threshold = abs(rule.trigger.value)
        breaks = cusum_breaks(recent_series, k=0.25, h=h_threshold)

        triggered = len(breaks) > 0

        message = (
            f"{'Detected' if triggered else 'No'} structural break "
            f"in recent {window_size} months (CUSUM h={h_threshold:.1f})"
        )

        return AlertDecision(
            rule_id=rule.rule_id,
            triggered=triggered,
            evidence={
                "break_count": len(breaks),
                "break_indices": breaks,
                "window_months": window_size,
                "cusum_h": h_threshold,
            },
            message=message,
        )

    def batch_evaluate(
        self,
        rules: list[AlertRule],
        data_provider: Any,
    ) -> list[AlertDecision]:
        """
        Evaluate multiple rules in batch.

        Args:
            rules: List of alert rules to evaluate
            data_provider: Callable that returns (series, timestamps) for a rule

        Returns:
            List of AlertDecisions in same order as rules
        """
        decisions = []
        for rule in rules:
            if not rule.enabled:
                decisions.append(
                    AlertDecision(
                        rule_id=rule.rule_id,
                        triggered=False,
                        message="Rule disabled",
                    )
                )
                continue

            try:
                series, timestamps = data_provider(rule)
                decision = self.evaluate(rule, series, timestamps)
                decisions.append(decision)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
                decisions.append(
                    AlertDecision(
                        rule_id=rule.rule_id,
                        triggered=False,
                        message=f"Evaluation error: {e}",
                    )
                )

        return decisions
