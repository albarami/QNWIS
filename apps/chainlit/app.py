"""
Optional Chainlit UI demo for QNWIS synthetic data exploration.

Safe to import even if Chainlit is not installed. All actions work on
deterministic synthetic CSV data via DataAPI.
"""

from __future__ import annotations

try:
    import chainlit as cl
except Exception:  # pragma: no cover
    cl = None

from src.qnwis.data.api.client import DataAPI
from src.qnwis.ui.cards import (
    build_ewi_hotlist_cards,
    build_top_sectors_cards,
)
from src.qnwis.ui.charts import salary_yoy_series


def _api() -> DataAPI:
    """
    Create DataAPI instance for Chainlit actions.

    Returns:
        DataAPI configured for synthetic data queries
    """
    return DataAPI("src/qnwis/data/queries", ttl_s=300)


if cl:  # pragma: no cover

    @cl.on_chat_start
    async def start():
        """
        Initialize Chainlit chat session with action menu.
        """
        await cl.Message(content="QNWIS Synthetic Demo. Choose an action:").send()
        await cl.AskActionMessage(
            content="Select:",
            actions=[
                cl.Action(
                    name="Top sectors",
                    value="top",
                    description="Top 5 sectors by employment",
                ),
                cl.Action(
                    name="EWI hotlist",
                    value="ewi",
                    description="Early warning",
                ),
                cl.Action(
                    name="Salary YoY (Energy)",
                    value="salary",
                    description="YoY series",
                ),
            ],
        ).send()

    @cl.action_callback("top")
    async def top_sectors(action):  # noqa: ARG001
        """
        Handle top sectors action - display top 5 sectors by employment.

        Args:
            action: Chainlit action object (required by Chainlit callback signature)
        """
        api = _api()
        cards = build_top_sectors_cards(api, top_n=5)
        md = "\n".join(
            [f"- **{c['title']}**: {c['kpi']:,} employees" for c in cards]
        )
        await cl.Message(content=md).send()

    @cl.action_callback("ewi")
    async def ewi(action):  # noqa: ARG001
        """
        Handle EWI hotlist action - display early warning indicators.

        Args:
            action: Chainlit action object (required by Chainlit callback signature)
        """
        api = _api()
        cards = build_ewi_hotlist_cards(api, threshold=3.0, top_n=5)
        md = "\n".join([f"- **{c['title']}**: drop {c['kpi']}%" for c in cards])
        await cl.Message(content=md).send()

    @cl.action_callback("salary")
    async def salary(action):  # noqa: ARG001
        """
        Handle salary YoY action - display Energy sector salary growth.

        Args:
            action: Chainlit action object (required by Chainlit callback signature)
        """
        api = _api()
        series = salary_yoy_series(api, "Energy")["series"]
        md = "Salary YoY (Energy): " + ", ".join(
            [f"{p['x']}:{p['y']}%" for p in series if p["y"] is not None]
        )
        await cl.Message(content=md).send()
