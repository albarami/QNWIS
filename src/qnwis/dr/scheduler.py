"""
Deterministic scheduler for DR backup operations.

Provides cron-like scheduling without wall-clock dependencies.
Driven by injected Clock for deterministic testing.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..utils.clock import Clock

from .models import ScheduleSpec


class CronParser:
    """
    Simple cron expression parser.

    Supports standard 5-field cron format: minute hour day month weekday
    """

    def __init__(self, cron_expr: str) -> None:
        """
        Initialize cron parser.

        Args:
            cron_expr: Cron expression (e.g., '0 2 * * *')

        Raises:
            ValueError: If expression is invalid
        """
        self.expr = cron_expr
        parts = cron_expr.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron_expr} (expected 5 fields)")

        self.minute = self._parse_field(parts[0], 0, 59)
        self.hour = self._parse_field(parts[1], 0, 23)
        self.day = self._parse_field(parts[2], 1, 31)
        self.month = self._parse_field(parts[3], 1, 12)
        self.weekday = self._parse_field(parts[4], 0, 6)

    def _parse_field(self, field: str, min_val: int, max_val: int) -> list[int]:
        """
        Parse a single cron field.

        Args:
            field: Field value (e.g., '*', '0', '0-5', '*/15')
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            List of matching values
        """
        if field == "*":
            return list(range(min_val, max_val + 1))

        if "/" in field:
            # Step values (e.g., '*/15')
            base, step = field.split("/")
            step_val = int(step)
            if base == "*":
                return list(range(min_val, max_val + 1, step_val))
            else:
                start = int(base)
                return list(range(start, max_val + 1, step_val))

        if "-" in field:
            # Range (e.g., '0-5')
            start_str, end_str = field.split("-")
            start_val = int(start_str)
            end_val = int(end_str)
            return list(range(start_val, end_val + 1))

        if "," in field:
            # List (e.g., '0,15,30,45')
            return [int(v) for v in field.split(",")]

        # Single value
        return [int(field)]

    def matches(self, dt: datetime) -> bool:
        """
        Check if datetime matches cron expression.

        Args:
            dt: Datetime to check

        Returns:
            True if matches
        """
        return (
            dt.minute in self.minute
            and dt.hour in self.hour
            and dt.day in self.day
            and dt.month in self.month
            and dt.weekday() in self.weekday
        )

    def next_run(self, after: datetime) -> datetime:
        """
        Calculate next run time after given datetime.

        Args:
            after: Reference datetime

        Returns:
            Next matching datetime
        """
        # Simple implementation: check every minute for next 7 days
        current = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
        max_check = after + timedelta(days=7)

        while current <= max_check:
            if self.matches(current):
                return current
            current += timedelta(minutes=1)

        # Fallback: return 7 days later
        return after + timedelta(days=7)


class BackupScheduler:
    """
    Deterministic backup scheduler.

    Evaluates schedules using injected clock and produces due jobs list.
    No background threads - caller must poll for due jobs.
    """

    def __init__(self, clock: Clock) -> None:
        """
        Initialize backup scheduler.

        Args:
            clock: Injected clock for deterministic time
        """
        self._clock = clock
        self._schedules: dict[str, ScheduleSpec] = {}
        self._parsers: dict[str, CronParser] = {}

    def add_schedule(self, schedule: ScheduleSpec) -> None:
        """
        Add a schedule to the scheduler.

        Args:
            schedule: Schedule specification

        Raises:
            ValueError: If cron expression is invalid
        """
        parser = CronParser(schedule.cron_expr)
        self._schedules[schedule.schedule_id] = schedule
        self._parsers[schedule.schedule_id] = parser

    def remove_schedule(self, schedule_id: str) -> None:
        """
        Remove a schedule from the scheduler.

        Args:
            schedule_id: Schedule identifier
        """
        self._schedules.pop(schedule_id, None)
        self._parsers.pop(schedule_id, None)

    def get_due_jobs(self) -> list[ScheduleSpec]:
        """
        Get list of schedules that are due to run.

        Returns:
            List of due ScheduleSpec objects
        """
        now = self._clock.now()
        due_jobs: list[ScheduleSpec] = []

        for schedule_id, schedule in self._schedules.items():
            if not schedule.enabled:
                continue

            parser = self._parsers[schedule_id]

            # Check if schedule is due
            if schedule.next_run_at:
                next_run = datetime.fromisoformat(schedule.next_run_at.replace("Z", "+00:00"))
                if now >= next_run:
                    due_jobs.append(schedule)
            else:
                # No next_run_at set, check if current time matches cron
                if parser.matches(now):
                    due_jobs.append(schedule)

        return due_jobs

    def update_next_run(self, schedule_id: str) -> ScheduleSpec | None:
        """
        Update next_run_at for a schedule after execution.

        Args:
            schedule_id: Schedule identifier

        Returns:
            Updated ScheduleSpec, or None if not found
        """
        schedule = self._schedules.get(schedule_id)
        if not schedule:
            return None

        parser = self._parsers[schedule_id]
        now = self._clock.now()
        next_run = parser.next_run(now)

        # Create updated schedule (immutable)
        updated = ScheduleSpec(
            schedule_id=schedule.schedule_id,
            spec_id=schedule.spec_id,
            cron_expr=schedule.cron_expr,
            enabled=schedule.enabled,
            next_run_at=next_run.isoformat(),
        )

        self._schedules[schedule_id] = updated
        return updated

    def list_schedules(self) -> list[ScheduleSpec]:
        """
        List all schedules.

        Returns:
            List of ScheduleSpec objects
        """
        return list(self._schedules.values())


__all__ = [
    "CronParser",
    "BackupScheduler",
]
