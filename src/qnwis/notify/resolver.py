"""
Incident resolver with state machine and auto-resolution logic.

Manages incident lifecycle: OPEN → ACK → SILENCED → RESOLVED
Auto-resolves incidents after N consecutive green evaluations.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .models import Incident, IncidentState

if TYPE_CHECKING:
    from ..utils.clock import Clock

logger = logging.getLogger(__name__)


class IncidentResolver:
    """
    Incident state machine and resolver.

    Features:
    - State transitions: OPEN → ACK → SILENCED → RESOLVED
    - Auto-resolution after N consecutive green evaluations
    - Persistent state storage in ledger
    - Deterministic timestamp injection
    """

    def __init__(
        self,
        clock: Clock,
        ledger_dir: Path | None = None,
        auto_resolve_threshold: int = 3,
    ):
        """
        Initialize incident resolver.

        Args:
            clock: Clock instance for deterministic time
            ledger_dir: Directory for incident ledger
            auto_resolve_threshold: Consecutive green evals before auto-resolve
        """
        self.clock = clock
        self.ledger_dir = ledger_dir or Path("docs/audit/incidents")
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        self.auto_resolve_threshold = auto_resolve_threshold

        # In-memory incident cache (would use database in production)
        self._incidents: dict[str, Incident] = {}
        self._ledger_offset = 0
        self._load_incidents()

    def _load_incidents(self) -> None:
        """Load incidents from ledger into memory."""
        ledger_file = self.ledger_dir / "incidents.jsonl"
        if not ledger_file.exists():
            logger.info("No incident ledger found, starting fresh")
            return

        try:
            with open(ledger_file, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        incident = Incident(**data)
                        self._incidents[incident.incident_id] = incident
            self._ledger_offset = ledger_file.stat().st_size
            logger.info(f"Loaded {len(self._incidents)} incidents from ledger")
        except Exception as e:
            logger.error(f"Failed to load incidents: {e}")

    def _refresh_from_ledger(self) -> None:
        """Load newly appended ledger entries into memory."""
        ledger_file = self.ledger_dir / "incidents.jsonl"
        if not ledger_file.exists():
            return

        try:
            with open(ledger_file, encoding="utf-8") as f:
                f.seek(self._ledger_offset)
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        incident = Incident(**data)
                        self._incidents[incident.incident_id] = incident
        except Exception as exc:
            logger.error(f"Failed to refresh incidents: {exc}")
        finally:
            try:
                self._ledger_offset = ledger_file.stat().st_size
            except OSError:
                self._ledger_offset = 0

    def _persist_incident(self, incident: Incident) -> None:
        """
        Persist incident update to ledger.

        Args:
            incident: Incident to persist
        """
        try:
            ledger_file = self.ledger_dir / "incidents.jsonl"
            with open(ledger_file, "a", encoding="utf-8") as f:
                line = incident.model_dump_json() + "\n"
                f.write(line)
            logger.debug(f"Persisted incident {incident.incident_id}")
        except Exception as e:
            logger.error(f"Failed to persist incident: {e}")

    def get_incident(self, incident_id: str) -> Incident | None:
        """
        Get incident by ID.

        Args:
            incident_id: Incident identifier

        Returns:
            Incident or None if not found
        """
        self._refresh_from_ledger()
        return self._incidents.get(incident_id)

    def list_incidents(
        self,
        state: IncidentState | None = None,
        rule_id: str | None = None,
        limit: int = 100,
    ) -> list[Incident]:
        """
        List incidents with optional filters.

        Args:
            state: Filter by state
            rule_id: Filter by rule ID
            limit: Maximum results

        Returns:
            List of incidents
        """
        self._refresh_from_ledger()
        incidents = list(self._incidents.values())

        if state:
            incidents = [i for i in incidents if i.state == state]

        if rule_id:
            incidents = [i for i in incidents if i.rule_id == rule_id]

        # Sort by created_at descending
        incidents.sort(key=lambda i: i.created_at, reverse=True)

        return incidents[:limit]

    def acknowledge(self, incident_id: str) -> Incident | None:
        """
        Acknowledge an incident (OPEN → ACK).

        Args:
            incident_id: Incident to acknowledge

        Returns:
            Updated incident or None if not found
        """
        self._refresh_from_ledger()
        incident = self._incidents.get(incident_id)
        if not incident:
            logger.warning(f"Incident {incident_id} not found")
            return None

        if incident.state != IncidentState.OPEN:
            logger.warning(f"Incident {incident_id} not in OPEN state (current: {incident.state})")
            return incident

        now = self.clock.now_iso()
        updated = incident.model_copy(
            update={
                "state": IncidentState.ACK,
                "ack_at": now,
                "updated_at": now,
            }
        )

        self._incidents[incident_id] = updated
        self._persist_incident(updated)
        logger.info(f"Acknowledged incident {incident_id}")
        return updated

    def silence(self, incident_id: str) -> Incident | None:
        """
        Silence an incident (OPEN|ACK → SILENCED).

        Args:
            incident_id: Incident to silence

        Returns:
            Updated incident or None if not found
        """
        self._refresh_from_ledger()
        incident = self._incidents.get(incident_id)
        if not incident:
            logger.warning(f"Incident {incident_id} not found")
            return None

        if incident.state == IncidentState.RESOLVED:
            logger.warning(f"Cannot silence resolved incident {incident_id}")
            return incident

        now = self.clock.now_iso()
        updated = incident.model_copy(
            update={
                "state": IncidentState.SILENCED,
                "updated_at": now,
            }
        )

        self._incidents[incident_id] = updated
        self._persist_incident(updated)
        logger.info(f"Silenced incident {incident_id}")
        return updated

    def resolve(self, incident_id: str) -> Incident | None:
        """
        Resolve an incident (any state → RESOLVED).

        Args:
            incident_id: Incident to resolve

        Returns:
            Updated incident or None if not found
        """
        self._refresh_from_ledger()
        incident = self._incidents.get(incident_id)
        if not incident:
            logger.warning(f"Incident {incident_id} not found")
            return None

        if incident.state == IncidentState.RESOLVED:
            logger.info(f"Incident {incident_id} already resolved")
            return incident

        now = self.clock.now_iso()
        updated = incident.model_copy(
            update={
                "state": IncidentState.RESOLVED,
                "resolved_at": now,
                "updated_at": now,
            }
        )

        self._incidents[incident_id] = updated
        self._persist_incident(updated)
        logger.info(f"Resolved incident {incident_id}")
        return updated

    def record_green_evaluation(self, rule_id: str) -> list[Incident]:
        """
        Record a green (non-firing) evaluation for a rule.

        Auto-resolves open incidents after N consecutive greens.

        Args:
            rule_id: Rule that evaluated green

        Returns:
            List of auto-resolved incidents
        """
        self._refresh_from_ledger()
        resolved = []

        # Find open incidents for this rule
        open_incidents = [
            i
            for i in self._incidents.values()
            if i.rule_id == rule_id and i.state in (IncidentState.OPEN, IncidentState.ACK)
        ]

        for incident in open_incidents:
            # Increment green count
            green_count = incident.consecutive_green_count + 1
            now = self.clock.now_iso()

            if green_count >= self.auto_resolve_threshold:
                # Auto-resolve
                updated = incident.model_copy(
                    update={
                        "state": IncidentState.RESOLVED,
                        "resolved_at": now,
                        "updated_at": now,
                        "consecutive_green_count": green_count,
                        "metadata": {
                            **incident.metadata,
                            "auto_resolved": True,
                            "green_count": green_count,
                        },
                    }
                )
                logger.info(f"Auto-resolved incident {incident.incident_id} after {green_count} green evals")
                resolved.append(updated)
            else:
                # Just update count
                updated = incident.model_copy(
                    update={
                        "consecutive_green_count": green_count,
                        "updated_at": now,
                    }
                )

            self._incidents[incident.incident_id] = updated
            self._persist_incident(updated)

        return resolved

    def get_stats(self) -> dict[str, Any]:
        """
        Get incident statistics.

        Returns:
            Dict with counts by state and severity
        """
        self._refresh_from_ledger()
        all_incidents = list(self._incidents.values())

        by_state: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        by_rule: dict[str, int] = {}
        stats: dict[str, Any] = {
            "total": len(all_incidents),
            "by_state": by_state,
            "by_severity": by_severity,
            "by_rule": by_rule,
        }

        # Count by state
        for state in IncidentState:
            count = len([i for i in all_incidents if i.state == state])
            by_state[state.value] = count

        # Count by severity
        from .models import Severity

        for severity in Severity:
            count = len([i for i in all_incidents if i.severity == severity])
            by_severity[severity.value] = count

        # Count by rule (top 10)
        rule_counts: dict[str, int] = {}
        for incident in all_incidents:
            rule_counts[incident.rule_id] = rule_counts.get(incident.rule_id, 0) + 1

        top_rules = sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        by_rule.update(dict(top_rules))

        return stats
