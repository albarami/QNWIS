"""
Unit tests for NSICScenarioGenerator.

Tests that the generator produces:
- Fixed 1+5+24 = 30 scenarios
- Scenarios derived from user question (not generic)
- Different scenarios for different questions
"""

import pytest
import asyncio
from src.nsic.scenarios.generator import (
    NSICScenarioGenerator,
    ScenarioSet,
    GeneratedScenario,
    create_scenario_generator,
    DEEP_SCENARIO_TYPES,
    BROAD_CATEGORIES,
)


class TestNSICScenarioGenerator:
    """Test NSICScenarioGenerator class."""
    
    @pytest.fixture
    def generator(self):
        """Create generator instance."""
        return create_scenario_generator()
    
    def test_generator_initialization(self, generator):
        """Test generator initializes correctly."""
        assert generator is not None
        stats = generator.get_stats()
        assert stats["deep_scenario_count"] == 5
        assert stats["total_broad_scenarios"] == 24
        assert stats["total_scenarios"] == 30
    
    @pytest.mark.asyncio
    async def test_generate_finance_question(self, generator):
        """Test scenario generation for finance question."""
        question = "Should Qatar prioritize financial hub or logistics hub?"
        
        scenario_set = await generator.generate(question)
        
        # Verify structure
        assert scenario_set.total_count == 30
        assert len(scenario_set.deep_scenarios) == 5
        assert len(scenario_set.broad_scenarios) == 24
        
        # Verify base case
        assert scenario_set.base_case is not None
        assert scenario_set.base_case.type == "base"
        assert "financial" in scenario_set.base_case.prompt.lower() or "logistics" in scenario_set.base_case.prompt.lower()
        
        # Verify deep scenarios
        deep_ids = [s.id for s in scenario_set.deep_scenarios]
        assert "deep_optimistic" in deep_ids
        assert "deep_pessimistic" in deep_ids
        assert "deep_competitive_shock" in deep_ids
        assert "deep_policy_shift" in deep_ids
        assert "deep_black_swan" in deep_ids
        
        # Verify question is in prompts
        for scenario in scenario_set.deep_scenarios:
            assert question in scenario.prompt
        
        # Verify engine assignments
        for scenario in scenario_set.engine_a_scenarios:
            assert scenario.assigned_engine == "engine_a"
        for scenario in scenario_set.engine_b_scenarios:
            assert scenario.assigned_engine == "engine_b"
    
    @pytest.mark.asyncio
    async def test_generate_labor_question(self, generator):
        """Test scenario generation for labor question."""
        question = "How to improve Qatarization in the private sector?"
        
        scenario_set = await generator.generate(question)
        
        # Verify structure
        assert scenario_set.total_count == 30
        
        # Verify domain detection
        assert scenario_set.question_context["domain"] == "labor"
        
        # Verify question is in prompts
        for scenario in scenario_set.all_scenarios:
            assert "qatarization" in scenario.prompt.lower() or question in scenario.prompt
    
    @pytest.mark.asyncio
    async def test_generate_infrastructure_question(self, generator):
        """Test scenario generation for infrastructure question."""
        question = "Should Qatar expand metro network or focus on road infrastructure?"
        
        scenario_set = await generator.generate(question)
        
        # Verify structure
        assert scenario_set.total_count == 30
        
        # Verify domain detection
        assert scenario_set.question_context["domain"] == "infrastructure"
        
        # Verify options extraction
        assert len(scenario_set.question_context["options"]) >= 1
    
    @pytest.mark.asyncio
    async def test_scenarios_are_question_specific(self, generator):
        """Test that different questions produce different scenarios."""
        question1 = "Should Qatar prioritize financial hub?"
        question2 = "How to improve Qatarization?"
        
        set1 = await generator.generate(question1)
        set2 = await generator.generate(question2)
        
        # Both have same structure
        assert set1.total_count == set2.total_count == 30
        
        # But prompts are different
        assert set1.base_case.prompt != set2.base_case.prompt
        
        # Domain detection differs
        assert set1.question_context["domain"] != set2.question_context["domain"]
    
    @pytest.mark.asyncio
    async def test_broad_scenarios_cover_all_categories(self, generator):
        """Test that broad scenarios cover all 4 categories."""
        question = "Should Qatar invest in renewable energy?"
        
        scenario_set = await generator.generate(question)
        
        categories = set(s.category for s in scenario_set.broad_scenarios)
        expected = {"economic", "competitive", "policy", "timing"}
        
        assert categories == expected
        
        # Each category has 6 scenarios
        for cat in expected:
            count = len([s for s in scenario_set.broad_scenarios if s.category == cat])
            assert count == 6, f"Category {cat} should have 6 scenarios, got {count}"
    
    @pytest.mark.asyncio
    async def test_deep_scenarios_have_target_turns(self, generator):
        """Test deep scenarios have 100 target turns."""
        question = "What strategy for technology sector development?"
        
        scenario_set = await generator.generate(question)
        
        for scenario in scenario_set.engine_a_scenarios:
            assert scenario.target_turns == 100
        
        for scenario in scenario_set.engine_b_scenarios:
            assert scenario.target_turns == 25
    
    def test_scenario_set_to_dict(self, generator):
        """Test ScenarioSet serialization."""
        scenario_set = generator.generate_sync("Test question for Qatar?")
        
        data = scenario_set.to_dict()
        
        assert "original_question" in data
        assert "base_case" in data
        assert "deep_scenarios" in data
        assert "broad_scenarios" in data
        assert data["total_count"] == 30
        assert data["engine_a_count"] == 6
        assert data["engine_b_count"] == 24


class TestQuestionAnalysis:
    """Test question analysis functionality."""
    
    @pytest.fixture
    def generator(self):
        return create_scenario_generator()
    
    @pytest.mark.asyncio
    async def test_domain_detection_finance(self, generator):
        """Test finance domain detection."""
        question = "Should Qatar expand the Qatar Financial Centre?"
        scenario_set = await generator.generate(question)
        assert scenario_set.question_context["domain"] == "finance"
    
    @pytest.mark.asyncio
    async def test_domain_detection_energy(self, generator):
        """Test energy domain detection."""
        question = "How to manage declining oil revenues?"
        scenario_set = await generator.generate(question)
        assert scenario_set.question_context["domain"] == "energy"
    
    @pytest.mark.asyncio
    async def test_domain_detection_tourism(self, generator):
        """Test tourism domain detection."""
        question = "How to sustain tourism after World Cup?"
        scenario_set = await generator.generate(question)
        assert scenario_set.question_context["domain"] == "tourism"
    
    @pytest.mark.asyncio
    async def test_options_extraction(self, generator):
        """Test extraction of options from comparative question."""
        question = "Should Qatar prioritize financial hub or logistics hub?"
        scenario_set = await generator.generate(question)
        
        options = scenario_set.question_context["options"]
        assert len(options) == 2
        assert "financial hub" in options[0].lower() or "logistics hub" in options[0].lower()
    
    @pytest.mark.asyncio
    async def test_stakeholder_identification(self, generator):
        """Test stakeholder identification."""
        question = "How to improve Qatarization in private sector?"
        scenario_set = await generator.generate(question)
        
        stakeholders = scenario_set.question_context["stakeholders"]
        assert "government" in stakeholders
        assert "private_sector" in stakeholders


class TestScenarioContent:
    """Test scenario content quality."""
    
    @pytest.fixture
    def generator(self):
        return create_scenario_generator()
    
    @pytest.mark.asyncio
    async def test_prompts_include_stake_specification(self, generator):
        """Test that prompts include stake specification guidance."""
        question = "Should Qatar build new port infrastructure?"
        scenario_set = await generator.generate(question)
        
        # Deep scenarios should have stake specification
        for scenario in scenario_set.deep_scenarios:
            assert "MAGNITUDE" in scenario.prompt or "STAKE" in scenario.prompt
    
    @pytest.mark.asyncio
    async def test_prompts_include_qatar_context(self, generator):
        """Test that prompts include Qatar context."""
        question = "How to accelerate Qatarization?"
        scenario_set = await generator.generate(question)
        
        # Base case should have Qatar context
        assert "QATAR" in scenario_set.base_case.prompt.upper()
    
    @pytest.mark.asyncio
    async def test_scenario_ids_are_unique(self, generator):
        """Test all scenario IDs are unique."""
        question = "Should Qatar invest in AI technology?"
        scenario_set = await generator.generate(question)
        
        ids = [s.id for s in scenario_set.all_scenarios]
        assert len(ids) == len(set(ids)), "Duplicate scenario IDs found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
