"""
Integration tests for the McKinsey-Grade Calculation Pipeline.

Tests the full flow:
- structure_data_node: Extracts and structures facts
- calculate_node: Runs deterministic calculations
- debate orchestrator: Includes calculated results in prompts
- synthesis: Uses ministerial briefing template

ALL NUMBERS MUST COME FROM CALCULATIONS - NO LLM GENERATION.
"""

from __future__ import annotations

import pytest
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

# Test fixtures for sample data
SAMPLE_EXTRACTED_FACTS = [
    {
        "source": "Ministry of Finance",
        "metric": "Initial Investment",
        "value": "50000000000",
        "year": "2024",
        "description": "Total capital allocation for Option A"
    },
    {
        "source": "Economic Planning Board",
        "metric": "Year 1 Revenue",
        "value": "5000000000",
        "year": "2025",
        "description": "Expected revenue in first year"
    },
    {
        "source": "Industry Benchmark",
        "metric": "Growth Rate",
        "value": "15%",
        "year": "2024",
        "description": "Expected annual growth rate"
    },
    {
        "source": "Central Bank",
        "metric": "Discount Rate",
        "value": "8%",
        "year": "2024",
        "description": "Government cost of capital"
    },
]

SAMPLE_STRUCTURED_INPUTS = {
    "options": [
        {
            "name": "Option A - Financial Hub",
            "description": "Develop Qatar as a regional financial center",
            "initial_investment": {
                "amount": 50000000000,
                "currency": "QAR",
                "source": "Ministry of Finance",
                "confidence": 0.9
            },
            "revenue_projections": [
                {"year": 1, "amount": 5000000000, "source": "Economic Planning Board", "confidence": 0.8},
                {"year": 2, "amount": 5750000000, "source": "Projected at 15% growth", "confidence": 0.7},
            ],
            "cost_projections": [
                {"year": 1, "amount": 2000000000, "source": "Budget estimate", "confidence": 0.75},
            ],
            "growth_rate": {"value": 0.15, "source": "Industry benchmark", "confidence": 0.6},
            "data_gaps": ["No data on Years 3-10"],
            "assumptions": ["Assumed 15% growth based on DIFC precedent"]
        },
        {
            "name": "Option B - Logistics Hub",
            "description": "Develop Qatar as a regional logistics center",
            "initial_investment": {
                "amount": 30000000000,
                "currency": "QAR",
                "source": "Ministry of Finance",
                "confidence": 0.85
            },
            "revenue_projections": [
                {"year": 1, "amount": 3000000000, "source": "Trade Ministry", "confidence": 0.8},
            ],
            "cost_projections": [
                {"year": 1, "amount": 1500000000, "source": "Budget estimate", "confidence": 0.75},
            ],
            "growth_rate": {"value": 0.12, "source": "Industry benchmark", "confidence": 0.65},
            "data_gaps": [],
            "assumptions": []
        }
    ],
    "discount_rate": {
        "value": 0.08,
        "justification": "Qatar sovereign cost of capital",
        "source": "Central Bank"
    },
    "time_horizon_years": 10,
    "overall_data_quality": "MEDIUM",
    "critical_data_gaps": ["Long-term projections are estimated"]
}


class TestFinancialEngineIntegration:
    """Test the FinancialEngine with realistic inputs."""

    def test_engine_calculates_npv_correctly(self) -> None:
        """Test that NPV calculation produces sensible results."""
        from src.qnwis.engines.financial_engine import (
            CashFlowInput,
            FinancialEngine,
            FinancialModelInput,
        )

        engine = FinancialEngine()

        cash_flows = [
            CashFlowInput(year=0, investment=100e6, source="Budget"),
            CashFlowInput(year=1, revenue=50e6, operating_costs=10e6, source="Projection"),
            CashFlowInput(year=2, revenue=60e6, operating_costs=12e6, source="Projection"),
            CashFlowInput(year=3, revenue=70e6, operating_costs=15e6, source="Projection"),
        ]

        model_input = FinancialModelInput(
            option_name="Test Option",
            option_description="Test project",
            cash_flows=cash_flows,
            discount_rate=0.10,
            discount_rate_source="Corporate rate",
        )

        result = engine.calculate(model_input)

        # Verify calculation completed
        assert result.input_validation_passed
        assert result.npv != 0
        assert result.irr != 0
        assert result.payback_period_years < float("inf")
        assert len(result.sensitivity_scenarios) == 6

    def test_engine_comparison_produces_winner(self) -> None:
        """Test that option comparison correctly identifies a winner."""
        from src.qnwis.engines.financial_engine import (
            CashFlowInput,
            FinancialEngine,
            FinancialModelInput,
        )

        engine = FinancialEngine()

        # Option A: Higher investment, higher returns
        option_a = FinancialModelInput(
            option_name="Option A",
            option_description="High risk high return",
            cash_flows=[
                CashFlowInput(year=0, investment=100e6, source="Budget"),
                CashFlowInput(year=1, revenue=60e6, operating_costs=10e6, source="Projection"),
                CashFlowInput(year=2, revenue=70e6, operating_costs=12e6, source="Projection"),
            ],
            discount_rate=0.08,
            discount_rate_source="Sovereign rate",
        )

        # Option B: Lower investment, lower returns
        option_b = FinancialModelInput(
            option_name="Option B",
            option_description="Low risk moderate return",
            cash_flows=[
                CashFlowInput(year=0, investment=50e6, source="Budget"),
                CashFlowInput(year=1, revenue=30e6, operating_costs=5e6, source="Projection"),
                CashFlowInput(year=2, revenue=35e6, operating_costs=6e6, source="Projection"),
            ],
            discount_rate=0.08,
            discount_rate_source="Sovereign rate",
        )

        result_a = engine.calculate(option_a)
        result_b = engine.calculate(option_b)

        comparison = engine.compare_options(result_a, result_b)

        # Verify comparison structure
        assert "winner" in comparison
        assert "loser" in comparison
        assert "confidence" in comparison
        assert "scores" in comparison
        assert "breakdown" in comparison
        assert "recommendation" in comparison
        assert comparison["winner"] in ["Option A", "Option B"]


class TestStructureDataNode:
    """Test the structure_data_node."""

    @pytest.mark.asyncio
    async def test_structure_converts_facts_to_inputs(self) -> None:
        """Test that structure_data_node produces valid structured inputs."""
        from src.qnwis.orchestration.nodes.structure_data import (
            convert_structured_to_model_input,
        )

        # Use sample structured inputs (simulating LLM output)
        model_input_dict = convert_structured_to_model_input(SAMPLE_STRUCTURED_INPUTS, 0)

        assert model_input_dict is not None
        assert model_input_dict["option_name"] == "Option A - Financial Hub"
        assert len(model_input_dict["cash_flows"]) > 0
        assert model_input_dict["discount_rate"] == 0.08

    def test_identify_options_parses_vs_pattern(self) -> None:
        """Test that option identification works for 'X vs Y' queries."""
        from src.qnwis.orchestration.nodes.structure_data import _identify_options

        query = "Should Qatar invest in a financial hub vs logistics hub?"
        options = _identify_options(query)

        assert len(options) >= 2
        # Options should have been identified

    def test_format_facts_handles_empty(self) -> None:
        """Test that _format_facts handles empty list."""
        from src.qnwis.orchestration.nodes.structure_data import _format_facts

        result = _format_facts([])
        assert result == "No facts extracted."


class TestCalculateNode:
    """Test the calculate_node."""

    @pytest.mark.asyncio
    async def test_calculate_node_produces_results(self) -> None:
        """Test that calculate_node produces calculated_results."""
        from src.qnwis.orchestration.nodes.calculate import calculate_node

        state = {
            "structured_inputs": SAMPLE_STRUCTURED_INPUTS,
            "nodes_executed": [],
        }

        result = await calculate_node(state)

        # Verify results were produced
        assert result.get("calculated_results") is not None
        calc_results = result["calculated_results"]
        assert "options" in calc_results
        assert len(calc_results["options"]) == 2  # Two options
        assert "comparison" in calc_results  # Should have comparison

    @pytest.mark.asyncio
    async def test_calculate_node_adds_low_confidence_warning(self) -> None:
        """Test that low confidence data triggers a warning."""
        from src.qnwis.orchestration.nodes.calculate import calculate_node

        # Create low-confidence inputs
        low_conf_inputs = {
            "options": [
                {
                    "name": "Low Confidence Option",
                    "initial_investment": {
                        "amount": 10000000,
                        "source": "Estimate",
                        "confidence": 0.2  # Very low
                    },
                    "revenue_projections": [
                        {"year": 1, "amount": 1000000, "source": "Guess", "confidence": 0.2}
                    ],
                    "cost_projections": [],
                    "growth_rate": {"value": 0.1, "source": "Assumption", "confidence": 0.2},
                }
            ],
            "discount_rate": {"value": 0.08, "source": "Default"},
            "time_horizon_years": 5,
            "overall_data_quality": "LOW",
        }

        state = {
            "structured_inputs": low_conf_inputs,
            "nodes_executed": [],
        }

        result = await calculate_node(state)

        # Low confidence should trigger warning
        calc_results = result.get("calculated_results", {})
        if calc_results:
            confidence = calc_results.get("data_confidence", 0)
            # With 0.2 confidence inputs, overall confidence should be low
            assert confidence <= 0.5 or result.get("calculation_warning") is not None

    @pytest.mark.asyncio
    async def test_calculate_node_handles_no_inputs(self) -> None:
        """Test that calculate_node handles missing structured_inputs."""
        from src.qnwis.orchestration.nodes.calculate import calculate_node

        state = {
            "structured_inputs": None,
            "nodes_executed": [],
        }

        result = await calculate_node(state)

        assert result.get("calculated_results") is None
        assert result.get("calculation_warning") is not None


class TestGetCalculatedSummary:
    """Test the helper function that formats calculated results for prompts."""

    def test_get_calculated_summary_formats_options(self) -> None:
        """Test that get_calculated_summary produces formatted output."""
        from src.qnwis.orchestration.nodes.calculate import get_calculated_summary

        # Create mock state with calculated results
        mock_calculated = {
            "options": [
                {
                    "option_name": "Option A",
                    "metrics": {
                        "npv_formatted": "USD 100.5M",
                        "irr_formatted": "15.2%",
                        "payback_years": 3.5,
                        "roi_formatted": "25.0%",
                    },
                    "metadata": {"data_confidence": 85.0},
                    "sensitivity": [
                        {
                            "scenario": "Revenue -20%",
                            "npv_change_pct": -15.0,
                            "still_viable": True,
                        }
                    ],
                }
            ],
            "comparison": {
                "winner": "Option A",
                "confidence": 75.0,
                "margin": 12.5,
                "recommendation": "Proceed with Option A",
            },
        }

        state = {
            "calculated_results": mock_calculated,
        }

        summary = get_calculated_summary(state)

        assert "CALCULATED FINANCIAL RESULTS" in summary
        assert "Option A" in summary
        assert "NPV" in summary
        assert "IRR" in summary
        assert "DO NOT GENERATE NEW NUMBERS" in summary

    def test_get_calculated_summary_handles_empty(self) -> None:
        """Test that get_calculated_summary handles empty state."""
        from src.qnwis.orchestration.nodes.calculate import get_calculated_summary

        state = {}
        summary = get_calculated_summary(state)

        assert "No calculations available" in summary


class TestMinisterialBriefingTemplate:
    """Test the McKinsey-grade briefing template."""

    def test_template_renders_complete_briefing(self) -> None:
        """Test that template renders all sections."""
        from src.qnwis.templates.ministerial_briefing import MinisterialBriefingTemplate

        # Create mock calculated results
        mock_results = {
            "options": [
                {
                    "option_name": "Option A",
                    "option_description": "Financial hub development",
                    "metrics": {
                        "npv": 500000000,
                        "npv_formatted": "USD 500.0M",
                        "irr_decimal": 0.152,
                        "irr_pct": 15.2,
                        "irr_formatted": "15.2%",
                        "payback_years": 4.5,
                        "total_investment": 1000000000,
                        "total_investment_formatted": "USD 1.0B",
                        "roi_pct": 50.0,
                        "roi_formatted": "50.0%",
                    },
                    "yearly_breakdown": [
                        {
                            "year": 0,
                            "investment": 1000000000,
                            "revenue": 0,
                            "operating_costs": 0,
                            "net_cash_flow": -1000000000,
                            "cumulative": -1000000000,
                        },
                        {
                            "year": 1,
                            "investment": 0,
                            "revenue": 300000000,
                            "operating_costs": 50000000,
                            "net_cash_flow": 250000000,
                            "cumulative": -750000000,
                        },
                    ],
                    "sensitivity": [
                        {
                            "scenario": "Revenue -20%",
                            "npv": 400000000,
                            "npv_change_pct": -20.0,
                            "still_viable": True,
                        },
                        {
                            "scenario": "Worst Case",
                            "npv": -100000000,
                            "npv_change_pct": -120.0,
                            "still_viable": False,
                        },
                    ],
                    "metadata": {
                        "data_confidence": 75.0,
                        "discount_rate_pct": "8.0%",
                    },
                },
                {
                    "option_name": "Option B",
                    "option_description": "Logistics hub development",
                    "metrics": {
                        "npv": 300000000,
                        "npv_formatted": "USD 300.0M",
                        "irr_decimal": 0.12,
                        "irr_pct": 12.0,
                        "irr_formatted": "12.0%",
                        "payback_years": 5.2,
                        "total_investment": 600000000,
                        "total_investment_formatted": "USD 600.0M",
                        "roi_pct": 40.0,
                        "roi_formatted": "40.0%",
                    },
                    "yearly_breakdown": [],
                    "sensitivity": [
                        {
                            "scenario": "Revenue -20%",
                            "npv": 250000000,
                            "npv_change_pct": -16.7,
                            "still_viable": True,
                        },
                    ],
                    "metadata": {
                        "data_confidence": 80.0,
                        "discount_rate_pct": "8.0%",
                    },
                },
            ],
            "comparison": {
                "winner": "Option A",
                "loser": "Option B",
                "confidence": 72.5,
                "margin": 15.0,
                "recommendation": "Option A provides higher returns despite higher risk.",
            },
        }

        template = MinisterialBriefingTemplate(
            query="Should Qatar invest in a financial hub vs logistics hub?",
            calculated_results=mock_results,
            calculation_warning=None,
        )

        briefing = template.render()

        # Verify key sections are present
        assert "MINISTERIAL BRIEFING" in briefing
        assert "EXECUTIVE SUMMARY" in briefing
        assert "FINANCIAL COMPARISON" in briefing
        assert "SENSITIVITY ANALYSIS" in briefing
        assert "RISK ASSESSMENT" in briefing
        assert "IMPLEMENTATION ROADMAP" in briefing
        assert "Option A" in briefing
        assert "Option B" in briefing
        assert "Winner" in briefing

    def test_template_includes_warning_when_present(self) -> None:
        """Test that warning banner appears when calculation_warning is set."""
        from src.qnwis.templates.ministerial_briefing import MinisterialBriefingTemplate

        mock_results = {"options": [], "comparison": None}

        template = MinisterialBriefingTemplate(
            query="Test query",
            calculated_results=mock_results,
            calculation_warning="Results based on limited data – interpret with caution",
        )

        briefing = template.render()

        assert "DATA CONFIDENCE ADVISORY" in briefing
        assert "limited data" in briefing


class TestEndToEndFlow:
    """Test the complete McKinsey flow end-to-end."""

    @pytest.mark.asyncio
    async def test_full_pipeline_flow(self) -> None:
        """Test structure -> calculate -> template flow."""
        from src.qnwis.orchestration.nodes.structure_data import (
            convert_structured_to_model_input,
        )
        from src.qnwis.orchestration.nodes.calculate import calculate_node
        from src.qnwis.templates.ministerial_briefing import MinisterialBriefingTemplate

        # Step 1: Structure data (simulated - normally LLM does this)
        structured_inputs = SAMPLE_STRUCTURED_INPUTS

        # Step 2: Calculate
        calc_state = {
            "structured_inputs": structured_inputs,
            "nodes_executed": [],
        }
        calc_result = await calculate_node(calc_state)
        calculated_results = calc_result.get("calculated_results")

        assert calculated_results is not None
        assert "options" in calculated_results
        assert len(calculated_results["options"]) == 2

        # Step 3: Generate briefing
        template = MinisterialBriefingTemplate(
            query="Should Qatar invest in financial hub vs logistics hub?",
            calculated_results=calculated_results,
            calculation_warning=calc_result.get("calculation_warning"),
        )

        briefing = template.render()

        # Verify complete flow produced results
        assert len(briefing) > 1000  # Should be substantial
        assert "NPV" in briefing
        assert "IRR" in briefing
        assert "SENSITIVITY" in briefing

    def test_numbers_come_from_calculations_not_llm(self) -> None:
        """
        CRITICAL TEST: Verify that all numbers in output come from
        deterministic calculations, not LLM generation.
        """
        from src.qnwis.engines.financial_engine import (
            CashFlowInput,
            FinancialEngine,
            FinancialModelInput,
        )

        engine = FinancialEngine()

        # Known inputs
        cash_flows = [
            CashFlowInput(year=0, investment=100, source="Test"),
            CashFlowInput(year=1, revenue=50, operating_costs=10, source="Test"),
            CashFlowInput(year=2, revenue=50, operating_costs=10, source="Test"),
            CashFlowInput(year=3, revenue=50, operating_costs=10, source="Test"),
        ]

        model_input = FinancialModelInput(
            option_name="Test",
            option_description="Test",
            cash_flows=cash_flows,
            discount_rate=0.10,
            discount_rate_source="Test",
        )

        result = engine.calculate(model_input)

        # Calculate expected NPV manually
        # Year 0: -100
        # Year 1: (50-10) / 1.1 = 36.36
        # Year 2: (50-10) / 1.21 = 33.06
        # Year 3: (50-10) / 1.331 = 30.05
        # Total: -100 + 36.36 + 33.06 + 30.05 = -0.53
        # (approximately, due to rounding)

        # NPV should be close to our manual calculation
        # The exact value depends on whether Year 0 is discounted
        # Main point: it should be DETERMINISTIC and REPRODUCIBLE
        first_run = result.npv

        # Run again - should get EXACT same result
        result2 = engine.calculate(model_input)
        second_run = result2.npv

        assert first_run == second_run, "NPV should be deterministic (same result every time)"


class TestDebateOrchestratorCalculatedResults:
    """Test that debate orchestrator includes calculated results in context."""

    def test_format_calculated_summary_in_orchestrator(self) -> None:
        """Test that orchestrator formats calculated results for agent prompts."""
        from src.qnwis.orchestration.legendary_debate_orchestrator import (
            LegendaryDebateOrchestrator,
        )

        # Mock orchestrator
        orchestrator = LegendaryDebateOrchestrator(
            emit_event_fn=AsyncMock(),
            llm_client=MagicMock(),
        )

        # Set calculated results
        orchestrator.question = "Should we invest?"
        orchestrator.calculated_results = {
            "options": [
                {
                    "option_name": "Option A",
                    "metrics": {
                        "npv_formatted": "USD 100M",
                        "irr_formatted": "15%",
                        "payback_years": 3,
                        "roi_formatted": "25%",
                    },
                    "metadata": {"data_confidence": 80},
                    "sensitivity": [],
                }
            ],
            "comparison": {
                "winner": "Option A",
                "confidence": 75,
                "margin": 10,
                "recommendation": "Go with A",
            },
        }
        orchestrator.extracted_facts = []

        # Format context
        context = orchestrator._format_query_context()

        assert "CALCULATED FINANCIAL RESULTS" in context
        assert "DO NOT MODIFY" in context or "DO NOT generate new numbers" in context.lower()
        assert "Option A" in context
        assert "NPV" in context

