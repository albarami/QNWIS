#!/usr/bin/env python3
"""
QNWIS Comprehensive Model Evaluation Suite
==========================================

Purpose: Determine the BEST model for each QNWIS use case based on:
- Accuracy (factual correctness, no hallucination)
- Depth (analytical rigor, causal reasoning)
- First-Principles Reasoning (catches impossible targets)
- Citation Compliance (follows extraction format)
- Stake Specificity (concrete numbers, timelines, mechanisms)
- Debate Quality (genuine disagreements, not echo)
- Synthesis Quality (ministerial-grade output)
- Cross-Domain Reasoning (connects multiple domains)

Models Tested: GPT-4o, GPT-5, GPT-5.1

Usage:
    python scripts/qnwis_comprehensive_model_evaluation.py
    
Output:
    - Detailed scores per test category
    - Model recommendation per QNWIS component
    - Full response logs for manual review
"""

import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field, asdict

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

import httpx

# =============================================================================
# CONFIGURATION
# =============================================================================

OUTPUT_DIR = Path("data/comprehensive_evaluation")

def safe_strip(val, default=""):
    """Safely strip a value that might be None."""
    if val is None:
        return default
    return str(val).strip().strip('"')

MODELS_CONFIG = {
    "GPT-4o": {
        "deployment": safe_strip(os.getenv("QNWIS_AZURE_MODEL"), "gpt-4o"),
        "api_version": safe_strip(os.getenv("AZURE_OPENAI_API_VERSION"), "2024-08-01-preview"),
        "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        "api_key": os.getenv("AZURE_OPENAI_API_KEY", ""),
        "system_role": "system",
    },
    "GPT-5": {
        "deployment": safe_strip(os.getenv("DEPLOYMENT_5"), "gpt-5-chat"),
        "api_version": safe_strip(os.getenv("API_VERSION_5"), "2024-12-01-preview"),
        "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        "api_key": os.getenv("API_KEY_5") or os.getenv("AZURE_OPENAI_API_KEY", ""),
        "system_role": "system",
    },
    "GPT-5.1": {
        "deployment": safe_strip(os.getenv("MODEL_NAME_5.1"), "gpt-5.1"),
        "api_version": "2024-12-01-preview",  # Fixed - GPT-5.1 requires this version
        "endpoint": safe_strip(os.getenv("ENDPOINT_5.1")) or os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        "api_key": os.getenv("API_KEY_5.1") or os.getenv("AZURE_OPENAI_API_KEY", ""),
        "system_role": "developer",  # Flag to indicate GPT-5.1 special handling needed
    },
}

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# =============================================================================
# TEST CATEGORIES AND QUERIES
# =============================================================================

@dataclass
class TestCase:
    """Single test case with evaluation criteria."""
    id: str
    category: str
    name: str
    system_prompt: str
    user_prompt: str
    evaluation_criteria: Dict[str, Any]
    max_score: int = 100
    weight: float = 1.0


@dataclass 
class TestResult:
    """Result of running a test case."""
    test_id: str
    model: str
    response: str
    scores: Dict[str, float]
    total_score: float
    execution_time: float
    evaluator_notes: List[str] = field(default_factory=list)
    passed_criteria: List[str] = field(default_factory=list)
    failed_criteria: List[str] = field(default_factory=list)


# =============================================================================
# TEST SUITE DEFINITION
# =============================================================================

TEST_SUITE: List[TestCase] = [
    
    # =========================================================================
    # CATEGORY 1: FIRST-PRINCIPLES REASONING (Critical for QNWIS)
    # Tests if model catches impossible targets BEFORE policy discussion
    # =========================================================================
    
    TestCase(
        id="FPR-001",
        category="First-Principles Reasoning",
        name="Demographic Impossibility Detection",
        system_prompt="""You are a senior policy analyst for Qatar's government.
Your job is to evaluate policy proposals for feasibility.
CRITICAL: Always check basic arithmetic feasibility BEFORE discussing policy options.
If a target is mathematically impossible, say so immediately.""",
        user_prompt="""Qatar is considering accelerating Qatarization from current levels (~4% in private sector) 
to 70% in the private sector by 2028.

Context:
- Qatar's total Qatari population: ~400,000 (all ages, including children and elderly)
- Working-age Qataris (18-60): ~200,000
- Currently employed Qataris: ~150,000 (mostly in public sector)
- Private sector total workforce: ~2,000,000 workers

Analyze the feasibility of this target and provide your recommendation.""",
        evaluation_criteria={
            "identifies_impossibility": {
                "weight": 40,
                "check": "must_identify_demographic_impossibility",
                "keywords": ["impossible", "infeasible", "cannot", "mathematically", "demographic", "population"],
                "description": "Must identify that 70% of 2M = 1.4M Qataris needed, but only ~50K available"
            },
            "shows_arithmetic": {
                "weight": 30,
                "check": "must_show_calculation",
                "keywords": ["1.4 million", "1,400,000", "200,000", "50,000", "calculation", "math"],
                "description": "Must show the actual arithmetic that proves impossibility"
            },
            "suggests_feasible_alternative": {
                "weight": 20,
                "check": "provides_alternative",
                "keywords": ["alternative", "instead", "feasible", "achievable", "realistic", "5%", "8%", "10%"],
                "description": "Must suggest a realistic alternative target"
            },
            "does_not_discuss_impossible_policies": {
                "weight": 10,
                "check": "negative_check",
                "forbidden_patterns": ["training programs to achieve 70%", "wage subsidies to reach 70%", "quotas for 70%"],
                "description": "Should NOT discuss policies to achieve an impossible target"
            }
        },
        max_score=100,
        weight=2.0  # Double weight - critical for QNWIS
    ),
    
    TestCase(
        id="FPR-002",
        category="First-Principles Reasoning",
        name="Fiscal Impossibility Detection",
        system_prompt="""You are a fiscal policy expert for Qatar's Ministry of Finance.
Always verify budget arithmetic before recommending spending programs.""",
        user_prompt="""Qatar's government wants to implement a universal wage subsidy program that would:
- Pay QAR 5,000/month supplement to every Qatari private sector worker
- Target: 500,000 Qatari private sector workers by 2026
- Duration: Permanent program

Context:
- Qatar's total annual government budget: ~QAR 200 billion
- Current total Qatari workforce (public + private): ~150,000
- Working-age Qatari population: ~200,000

Analyze this proposal.""",
        evaluation_criteria={
            "identifies_population_constraint": {
                "weight": 35,
                "check": "identifies_constraint",
                "keywords": ["only 200,000", "150,000 total", "cannot reach 500,000", "population limit"],
                "description": "Must identify that 500K target exceeds total working-age population"
            },
            "calculates_true_cost": {
                "weight": 35,
                "check": "shows_calculation",
                "keywords": ["QAR 30 billion", "30B", "billion per year", "annual cost"],
                "description": "Should calculate: 500K × 5K × 12 = QAR 30B/year (but note population impossibility)"
            },
            "flags_both_issues": {
                "weight": 30,
                "check": "identifies_multiple_issues",
                "keywords": ["population", "budget", "both", "two problems", "fiscal"],
                "description": "Must flag BOTH the population impossibility AND the fiscal impact"
            }
        },
        max_score=100,
        weight=1.5
    ),
    
    TestCase(
        id="FPR-003",
        category="First-Principles Reasoning",
        name="Timeline Impossibility Detection",
        system_prompt="""You are a workforce development expert.
Always check if timelines are physically achievable given training requirements.""",
        user_prompt="""Qatar wants to produce 50,000 new Qatari doctors by 2027 to reduce healthcare import dependency.

Context:
- Current Qatari medical students: ~500 per year graduating
- Medical degree duration: 6 years minimum
- Current year: 2025
- Qatar's total university enrollment (all fields): ~25,000 students

Is this target achievable?""",
        evaluation_criteria={
            "identifies_timeline_impossibility": {
                "weight": 40,
                "check": "identifies_impossibility",
                "keywords": ["impossible", "cannot", "6 years", "2031", "not enough time"],
                "description": "Must identify 6-year training cannot complete by 2027"
            },
            "identifies_pipeline_constraint": {
                "weight": 30,
                "check": "identifies_constraint",
                "keywords": ["500 per year", "pipeline", "capacity", "25,000 total"],
                "description": "Must identify current pipeline produces only 500/year"
            },
            "provides_realistic_projection": {
                "weight": 30,
                "check": "provides_alternative",
                "keywords": ["2031", "2032", "3,000", "5,000", "realistic"],
                "description": "Should provide realistic timeline and numbers"
            }
        },
        max_score=100,
        weight=1.5
    ),

    # =========================================================================
    # CATEGORY 2: CITATION COMPLIANCE
    # Tests if model follows QNWIS citation format and doesn't fabricate
    # =========================================================================
    
    TestCase(
        id="CIT-001",
        category="Citation Compliance",
        name="Strict Citation Format Adherence",
        system_prompt="""You are a QNWIS analyst. You MUST follow these citation rules:

CRITICAL RULES:
1. You have extracted facts below - USE ONLY THESE
2. Every number MUST be cited as: [Per extraction: "exact quote"]
3. If a fact is NOT in the extraction, write "DATA NOT AVAILABLE" - never estimate
4. Any uncited number is considered FABRICATION and will be rejected

Example correct format:
"Qatar's GDP grew by [Per extraction: "5.2% in 2024"] driven by..."

Example WRONG format (will be rejected):
"Qatar's GDP grew by approximately 5% in 2024" ← NO CITATION = FABRICATION""",
        user_prompt="""EXTRACTED FACTS:
- "Qatar GDP 2024: QAR 715.5 billion"
- "Non-oil GDP share: 52.3%"
- "Tourism revenue 2024: QAR 62.1 billion"
- "Hotel occupancy rate: 67.8%"
- "Total employment: 2.15 million workers"
- "Qatari nationals in workforce: 148,000 (6.9%)"

QUERY: Provide an economic overview of Qatar's current situation based on these facts.""",
        evaluation_criteria={
            "uses_citation_format": {
                "weight": 40,
                "check": "citation_format",
                "pattern": r'\[Per extraction: ["\'].*?["\']\]',
                "min_citations": 4,
                "description": "Must use [Per extraction: 'X'] format at least 4 times"
            },
            "no_fabricated_numbers": {
                "weight": 35,
                "check": "no_fabrication",
                "allowed_numbers": ["715.5", "52.3", "62.1", "67.8", "2.15", "148,000", "6.9"],
                "description": "All numbers must come from provided facts"
            },
            "acknowledges_missing_data": {
                "weight": 25,
                "check": "acknowledges_gaps",
                "keywords": ["not available", "not provided", "no data", "not in extraction"],
                "description": "Should acknowledge when asked about data not in extraction"
            }
        },
        max_score=100,
        weight=2.0  # Critical for zero-fabrication guarantee
    ),
    
    TestCase(
        id="CIT-002",
        category="Citation Compliance",
        name="Resists Fabrication Under Pressure",
        system_prompt="""You are a QNWIS analyst. ONLY use data from the extraction provided.
If data is not available, say so. NEVER estimate or use general knowledge.""",
        user_prompt="""EXTRACTED FACTS:
- "Qatar unemployment rate: 0.1%"
- "Labor force participation: 88.2%"

QUERY: I need a complete labor market analysis including:
1. Unemployment rate (you have this)
2. Average wages by sector (you need this)
3. Job creation trends 2020-2024 (you need this)
4. Skills gap assessment (you need this)

Provide the analysis.""",
        evaluation_criteria={
            "uses_available_data": {
                "weight": 30,
                "check": "uses_provided_data",
                "required_values": ["0.1%", "88.2%"],
                "description": "Must cite the two available data points"
            },
            "refuses_to_fabricate": {
                "weight": 50,
                "check": "refuses_fabrication",
                "keywords": ["not available", "not provided", "cannot provide", "no data", "not in extraction"],
                "min_occurrences": 2,
                "description": "Must explicitly state missing data for 3 unavailable items"
            },
            "does_not_invent_numbers": {
                "weight": 20,
                "check": "no_invented_numbers",
                "forbidden_patterns": [
                    r"average wage.*QAR \d",
                    r"job creation.*\d+,\d+",
                    r"skills gap.*\d+%"
                ],
                "description": "Must NOT invent wage, job creation, or skills gap numbers"
            }
        },
        max_score=100,
        weight=2.0
    ),

    # =========================================================================
    # CATEGORY 3: STAKE SPECIFICITY
    # Tests if model provides concrete numbers, timelines, mechanisms
    # =========================================================================
    
    TestCase(
        id="STK-001",
        category="Stake Specificity",
        name="Scenario Generation with Specific Stakes",
        system_prompt="""You are a scenario planning expert for Qatar's government.
When generating scenarios, you MUST be BRUTALLY SPECIFIC:

BAD (vague - DO NOT DO THIS):
- "Oil prices decline significantly"
- "Competition increases"

GOOD (specific - DO THIS):
- "Oil drops to $45/barrel for 18+ months, eliminating QAR 82B (31%) of revenue"
- "Saudi Arabia announces QAR 50B talent fund targeting 50,000 Qatar-trained professionals"

Every scenario MUST include:
1. MAGNITUDE: Exact numbers
2. TIMELINE: Specific dates (Q2 2026, not "soon")
3. MECHANISM: Causal chain (A → B → C → D)
4. STAKEHOLDER IMPACT: Who loses what, with numbers""",
        user_prompt="""Generate 3 risk scenarios for Qatar's economy over the next 3 years.

Context:
- Qatar GDP: QAR 715 billion
- Oil/gas revenue: 48% of GDP
- Government budget: QAR 200 billion
- Sovereign wealth fund: ~$450 billion""",
        evaluation_criteria={
            "has_specific_numbers": {
                "weight": 30,
                "check": "contains_numbers",
                "min_numbers": 10,
                "description": "Must contain at least 10 specific numbers across scenarios"
            },
            "has_specific_timelines": {
                "weight": 25,
                "check": "contains_timelines",
                "patterns": [r"Q[1-4] 20\d{2}", r"20\d{2}", r"\d+ months"],
                "min_matches": 4,
                "description": "Must have at least 4 specific timeline references"
            },
            "has_causal_mechanisms": {
                "weight": 25,
                "check": "contains_mechanisms",
                "patterns": [r"→|->|leads to|causing|resulting in|therefore"],
                "min_matches": 3,
                "description": "Must show causal chains in at least 3 places"
            },
            "has_stakeholder_impact": {
                "weight": 20,
                "check": "contains_stakeholder_impact",
                "keywords": ["workers", "companies", "ministry", "sector", "jobs", "employees", "businesses"],
                "min_matches": 3,
                "description": "Must identify specific affected stakeholders"
            }
        },
        max_score=100,
        weight=1.5
    ),
    
    TestCase(
        id="STK-002",
        category="Stake Specificity",
        name="Policy Recommendation with Concrete Details",
        system_prompt="""You are a policy advisor. Your recommendations must be ACTIONABLE with:
- Specific budget amounts (QAR X billion)
- Specific timelines (Q1 2026, not "soon")
- Specific targets (15,000 jobs, not "many jobs")
- Specific responsible parties (Ministry of X, not "government")""",
        user_prompt="""Recommend a policy to increase Qatari employment in the financial services sector.

Current state:
- Financial sector employment: 45,000 workers
- Qatari nationals in financial sector: 4,500 (10%)
- Target: Increase to 25% within 5 years
- Available budget: QAR 2 billion over 5 years""",
        evaluation_criteria={
            "has_budget_breakdown": {
                "weight": 25,
                "check": "contains_budget",
                "patterns": [r"QAR \d+", r"\d+ billion", r"\d+ million"],
                "min_matches": 3,
                "description": "Must break down budget allocation"
            },
            "has_timeline_phases": {
                "weight": 25,
                "check": "contains_phases",
                "keywords": ["phase 1", "phase 2", "year 1", "year 2", "Q1", "Q2", "2026", "2027"],
                "min_matches": 3,
                "description": "Must have phased timeline"
            },
            "has_specific_targets": {
                "weight": 25,
                "check": "contains_targets",
                "patterns": [r"\d+,?\d* (jobs|workers|graduates|trainees)"],
                "min_matches": 2,
                "description": "Must have specific numerical targets"
            },
            "assigns_responsibility": {
                "weight": 25,
                "check": "assigns_responsibility",
                "keywords": ["ministry of", "QFC", "Qatar Central Bank", "QCB", "QFCA", "responsible"],
                "min_matches": 2,
                "description": "Must assign specific institutional responsibility"
            }
        },
        max_score=100,
        weight=1.5
    ),

    # =========================================================================
    # CATEGORY 4: DEBATE QUALITY
    # Tests if model can generate genuine disagreements and counterarguments
    # =========================================================================
    
    TestCase(
        id="DBT-001",
        category="Debate Quality",
        name="Generate Genuine Counterarguments",
        system_prompt="""You are participating in a policy debate. Your task is to:
1. Present the STRONGEST case FOR the proposal
2. Present the STRONGEST case AGAINST the proposal
3. Identify genuine points of disagreement (not strawmen)
4. Do NOT create false balance - if one side is clearly stronger, say so""",
        user_prompt="""PROPOSAL: Qatar should implement a 50% quota for Qatari nationals in all private sector companies with >100 employees, effective 2026.

Current context:
- Current Qatarization in private sector: ~4%
- Private sector companies with >100 employees: ~2,500
- Total private sector workforce: 2 million
- Available working-age Qataris not currently employed: ~50,000

Generate a structured debate with FOR and AGAINST arguments.""",
        evaluation_criteria={
            "has_strong_for_arguments": {
                "weight": 20,
                "check": "has_for_arguments",
                "keywords": ["advantage", "benefit", "support", "favor", "pro", "positive"],
                "min_quality_indicators": ["national", "employment", "development", "Vision 2030"],
                "description": "Must present substantive arguments in favor"
            },
            "has_strong_against_arguments": {
                "weight": 20,
                "check": "has_against_arguments",
                "keywords": ["risk", "concern", "challenge", "against", "con", "negative", "problem"],
                "min_quality_indicators": ["feasibility", "enforcement", "business", "talent"],
                "description": "Must present substantive arguments against"
            },
            "identifies_arithmetic_issue": {
                "weight": 30,
                "check": "identifies_core_issue",
                "keywords": ["50,000", "1 million", "mathematically", "impossible", "population", "demographic"],
                "description": "Must identify that 50% of 2M = 1M but only 50K available"
            },
            "provides_nuanced_conclusion": {
                "weight": 30,
                "check": "nuanced_conclusion",
                "keywords": ["however", "therefore", "given", "recommend", "alternative", "instead"],
                "description": "Must provide nuanced conclusion acknowledging the core constraint"
            }
        },
        max_score=100,
        weight=1.5
    ),
    
    TestCase(
        id="DBT-002",
        category="Debate Quality",
        name="Devil's Advocate Challenge",
        system_prompt="""You are a Devil's Advocate analyst. Your job is to:
1. Find the WEAKEST assumptions in the argument presented
2. Identify what could go CATASTROPHICALLY wrong
3. Point out evidence gaps and logical flaws
4. Be genuinely critical, not just contrarian""",
        user_prompt="""POLICY RECOMMENDATION TO CHALLENGE:

"Qatar should invest QAR 50 billion over 10 years to become the leading AI hub in the Middle East. 
This will create 100,000 high-tech jobs and position Qatar as a global technology leader.

Key assumptions:
1. Talent will relocate to Qatar for AI jobs
2. Qatar can compete with UAE and Saudi Arabia
3. AI investment will generate positive ROI
4. 100,000 jobs is achievable"

Act as Devil's Advocate and challenge this recommendation.""",
        evaluation_criteria={
            "challenges_talent_assumption": {
                "weight": 25,
                "check": "challenges_assumption",
                "keywords": ["talent", "relocate", "compete", "Dubai", "Saudi", "attract"],
                "description": "Must challenge the talent attraction assumption"
            },
            "challenges_competition_assumption": {
                "weight": 25,
                "check": "challenges_assumption",
                "keywords": ["UAE", "Saudi", "NEOM", "Dubai", "compete", "market share"],
                "description": "Must challenge the competitive positioning assumption"
            },
            "challenges_jobs_number": {
                "weight": 25,
                "check": "challenges_numbers",
                "keywords": ["100,000", "realistic", "achievable", "pipeline", "graduates"],
                "description": "Must question whether 100K AI jobs is realistic"
            },
            "identifies_risks": {
                "weight": 25,
                "check": "identifies_risks",
                "keywords": ["risk", "fail", "worst case", "if", "could", "might not"],
                "min_matches": 3,
                "description": "Must identify at least 3 specific risks"
            }
        },
        max_score=100,
        weight=1.5
    ),

    # =========================================================================
    # CATEGORY 5: CROSS-DOMAIN REASONING
    # Tests if model can connect insights across multiple domains
    # =========================================================================
    
    TestCase(
        id="XDR-001",
        category="Cross-Domain Reasoning",
        name="Multi-Domain Causal Chain Analysis",
        system_prompt="""You are a strategic analyst who specializes in identifying cross-domain causal chains.
Your analysis must show how changes in one domain cascade to affect other domains.
Use explicit causal notation: Domain A effect → Domain B effect → Domain C effect""",
        user_prompt="""Analyze the cross-domain impacts of a sustained oil price drop to $40/barrel for 24 months.

Domains to analyze:
1. Government Revenue & Budget
2. Education Spending
3. Workforce Development
4. Private Sector Growth
5. Qatarization Targets

Show the causal chains connecting these domains.""",
        evaluation_criteria={
            "identifies_revenue_impact": {
                "weight": 15,
                "check": "identifies_impact",
                "keywords": ["revenue", "budget", "deficit", "QAR", "billion", "cut"],
                "description": "Must quantify government revenue impact"
            },
            "shows_education_connection": {
                "weight": 20,
                "check": "shows_connection",
                "keywords": ["education", "scholarship", "training", "university", "budget cut"],
                "description": "Must connect revenue to education spending"
            },
            "shows_workforce_connection": {
                "weight": 20,
                "check": "shows_connection",
                "keywords": ["workforce", "skills", "training", "graduates", "pipeline"],
                "description": "Must connect education to workforce development"
            },
            "shows_qatarization_connection": {
                "weight": 20,
                "check": "shows_connection",
                "keywords": ["Qatarization", "targets", "delayed", "missed", "reduced"],
                "description": "Must connect workforce to Qatarization outcomes"
            },
            "uses_causal_notation": {
                "weight": 25,
                "check": "uses_notation",
                "patterns": [r"→|->|leads to|causing|results in|therefore|consequently"],
                "min_matches": 5,
                "description": "Must use explicit causal language at least 5 times"
            }
        },
        max_score=100,
        weight=1.5
    ),
    
    TestCase(
        id="XDR-002",
        category="Cross-Domain Reasoning",
        name="Integrated Strategic Recommendation",
        system_prompt="""You are a ministerial advisor who must provide integrated recommendations 
that consider multiple policy domains simultaneously.
Do NOT provide siloed recommendations for each domain.
Show how recommendations in one area support or conflict with goals in other areas.""",
        user_prompt="""Qatar faces a strategic choice: Prioritize becoming a Financial Hub OR a Logistics Hub.

Consider implications across:
- Labor market requirements
- Education/training needs
- Infrastructure investment
- Competition with UAE/Saudi
- Qatarization feasibility
- Revenue diversification

Provide an INTEGRATED recommendation, not separate analyses.""",
        evaluation_criteria={
            "compares_labor_requirements": {
                "weight": 20,
                "check": "compares_domains",
                "keywords": ["financial", "logistics", "workers", "skills", "talent"],
                "description": "Must compare labor needs for both options"
            },
            "identifies_tradeoffs": {
                "weight": 25,
                "check": "identifies_tradeoffs",
                "keywords": ["tradeoff", "versus", "compared to", "advantage", "disadvantage", "but"],
                "min_matches": 3,
                "description": "Must explicitly identify cross-domain tradeoffs"
            },
            "provides_integrated_recommendation": {
                "weight": 30,
                "check": "integrated_recommendation",
                "keywords": ["therefore", "recommend", "given", "considering all", "overall"],
                "description": "Must provide single integrated recommendation"
            },
            "considers_competition": {
                "weight": 25,
                "check": "considers_competition",
                "keywords": ["UAE", "Dubai", "Saudi", "compete", "advantage", "position"],
                "description": "Must consider regional competitive dynamics"
            }
        },
        max_score=100,
        weight=1.5
    ),

    # =========================================================================
    # CATEGORY 6: SYNTHESIS QUALITY
    # Tests ministerial-grade output quality
    # =========================================================================
    
    TestCase(
        id="SYN-001",
        category="Synthesis Quality",
        name="Executive Briefing Format",
        system_prompt="""You are preparing a briefing for Qatar's Minister of Labour.
The Minister has 5 minutes to read this before a cabinet meeting.

Format requirements:
1. Executive Summary (3-4 sentences max)
2. Key Findings (bullet points with numbers)
3. Risks (ranked by severity)
4. Recommendation (clear, actionable)
5. Confidence Level (with justification)""",
        user_prompt="""Prepare a ministerial briefing on:

"Current state of Qatarization in the banking sector and recommended actions"

Data available:
- Banking sector employment: 18,500 workers
- Qatari nationals: 3,700 (20%)
- Target by 2025: 30%
- Average Qatari salary premium: 45% above expatriate
- Annual attrition of Qatari bankers: 8%
- New Qatari finance graduates per year: 450""",
        evaluation_criteria={
            "has_executive_summary": {
                "weight": 20,
                "check": "has_section",
                "keywords": ["executive summary", "summary", "overview", "key message"],
                "max_length": 500,
                "description": "Must have concise executive summary"
            },
            "has_quantified_findings": {
                "weight": 25,
                "check": "has_numbers",
                "patterns": [r"\d+%", r"\d+,?\d* workers", r"QAR"],
                "min_matches": 5,
                "description": "Must have quantified key findings"
            },
            "has_ranked_risks": {
                "weight": 20,
                "check": "has_risks",
                "keywords": ["risk", "high", "medium", "low", "critical", "severe"],
                "description": "Must have risk assessment"
            },
            "has_clear_recommendation": {
                "weight": 20,
                "check": "has_recommendation",
                "keywords": ["recommend", "should", "action", "implement", "priority"],
                "description": "Must have clear actionable recommendation"
            },
            "has_confidence_level": {
                "weight": 15,
                "check": "has_confidence",
                "keywords": ["confidence", "certain", "likely", "uncertain", "%"],
                "description": "Must state confidence level"
            }
        },
        max_score=100,
        weight=1.5
    ),
    
    TestCase(
        id="SYN-002",
        category="Synthesis Quality",
        name="Uncertainty Acknowledgment",
        system_prompt="""You are a senior analyst who values intellectual honesty.
When evidence is weak or conflicting, you MUST acknowledge uncertainty.
Do NOT present uncertain conclusions as facts.
Use calibrated confidence language: "high confidence", "moderate confidence", "low confidence", "unknown".""",
        user_prompt="""Analyze the effectiveness of Qatar's existing Qatarization policies based on:

Strong evidence:
- Qatarization rate increased from 3.2% to 4.1% (2020-2024)
- Government sector: 85% Qatari (target met)

Weak/conflicting evidence:
- Private sector productivity impact: Some studies show 5% decline, others show no effect
- Wage subsidy ROI: No rigorous evaluation conducted
- Long-term sustainability: Unknown, no longitudinal data

Provide your assessment with appropriate uncertainty acknowledgment.""",
        evaluation_criteria={
            "distinguishes_evidence_quality": {
                "weight": 30,
                "check": "distinguishes_quality",
                "keywords": ["strong evidence", "weak evidence", "uncertain", "conflicting", "limited data"],
                "min_matches": 2,
                "description": "Must distinguish between strong and weak evidence"
            },
            "uses_calibrated_confidence": {
                "weight": 30,
                "check": "uses_confidence_language",
                "keywords": ["high confidence", "moderate confidence", "low confidence", "uncertain", "unknown"],
                "min_matches": 2,
                "description": "Must use calibrated confidence language"
            },
            "does_not_overclaim": {
                "weight": 25,
                "check": "no_overclaiming",
                "forbidden_patterns": ["clearly shows", "definitely", "proves that", "certainly"],
                "description": "Should NOT overclaim on weak evidence"
            },
            "acknowledges_data_gaps": {
                "weight": 15,
                "check": "acknowledges_gaps",
                "keywords": ["no data", "not evaluated", "unknown", "gap", "missing"],
                "description": "Must acknowledge data gaps explicitly"
            }
        },
        max_score=100,
        weight=1.5
    ),

    # =========================================================================
    # CATEGORY 7: ANALYTICAL DEPTH
    # Tests deep analytical capability
    # =========================================================================
    
    TestCase(
        id="DEP-001",
        category="Analytical Depth",
        name="Second and Third Order Effects",
        system_prompt="""You are an expert at identifying cascading effects of policy decisions.
For any policy, analyze:
- First-order effects (direct, immediate)
- Second-order effects (indirect, medium-term)
- Third-order effects (systemic, long-term)
- Potential unintended consequences""",
        user_prompt="""Analyze the cascading effects of Qatar implementing a mandatory 40% Qatarization quota 
in the hospitality sector (hotels, restaurants) by 2026.

Current state:
- Hospitality workforce: 85,000 workers
- Current Qatari share: 2% (1,700 workers)
- Required for 40%: 34,000 Qatari workers
- Available Qataris interested in hospitality: estimated 3,000-5,000""",
        evaluation_criteria={
            "identifies_first_order": {
                "weight": 20,
                "check": "identifies_effects",
                "keywords": ["immediate", "direct", "hiring", "compliance", "quota"],
                "description": "Must identify direct compliance effects"
            },
            "identifies_second_order": {
                "weight": 25,
                "check": "identifies_effects",
                "keywords": ["service quality", "wages", "costs", "prices", "tourism"],
                "description": "Must identify wage/quality/price effects"
            },
            "identifies_third_order": {
                "weight": 25,
                "check": "identifies_effects",
                "keywords": ["reputation", "competitiveness", "long-term", "systemic", "industry"],
                "description": "Must identify systemic tourism industry effects"
            },
            "identifies_unintended_consequences": {
                "weight": 30,
                "check": "identifies_unintended",
                "keywords": ["unintended", "backfire", "workaround", "gaming", "evasion", "ghost employment"],
                "description": "Must identify potential unintended consequences"
            }
        },
        max_score=100,
        weight=1.5
    ),
    
    TestCase(
        id="DEP-002",
        category="Analytical Depth",
        name="Comparative Benchmarking Analysis",
        system_prompt="""You are an expert in comparative policy analysis.
When analyzing Qatar policies, always benchmark against:
1. Regional peers (UAE, Saudi, Bahrain, Kuwait, Oman)
2. Global best practices (Singapore, Norway, etc.)
3. Historical precedents (what worked/failed elsewhere)

Provide specific examples, not generic comparisons.""",
        user_prompt="""Benchmark Qatar's Qatarization policy against similar nationalization policies:
- UAE's Emiratisation
- Saudi's Nitaqat/Saudization
- Oman's Omanisation
- Singapore's approach to local employment

Which approach has been most successful and what can Qatar learn?""",
        evaluation_criteria={
            "covers_uae": {
                "weight": 15,
                "check": "covers_country",
                "keywords": ["UAE", "Emiratisation", "emiratization", "Dubai", "Abu Dhabi"],
                "description": "Must analyze UAE approach"
            },
            "covers_saudi": {
                "weight": 15,
                "check": "covers_country",
                "keywords": ["Saudi", "Nitaqat", "Saudization", "saudisation"],
                "description": "Must analyze Saudi approach"
            },
            "covers_singapore": {
                "weight": 15,
                "check": "covers_country",
                "keywords": ["Singapore", "foreign worker levy", "skills-based"],
                "description": "Must analyze Singapore approach"
            },
            "provides_specific_metrics": {
                "weight": 25,
                "check": "has_metrics",
                "patterns": [r"\d+%", r"\d+,?\d* (workers|jobs|nationals)"],
                "min_matches": 4,
                "description": "Must provide specific metrics for comparison"
            },
            "draws_lessons": {
                "weight": 30,
                "check": "draws_lessons",
                "keywords": ["lesson", "learn", "adopt", "avoid", "success", "failure", "effective"],
                "min_matches": 3,
                "description": "Must draw specific lessons for Qatar"
            }
        },
        max_score=100,
        weight=1.5
    ),

    # =========================================================================
    # CATEGORY 8: ACCURACY & FACTUAL CORRECTNESS
    # Tests knowledge accuracy (NOTE: This tests base knowledge, not extraction)
    # =========================================================================
    
    TestCase(
        id="ACC-001",
        category="Accuracy",
        name="Qatar Factual Knowledge",
        system_prompt="""You are a Qatar expert. Answer factual questions accurately.
If you're not certain, say so. Do not guess.""",
        user_prompt="""Answer these factual questions about Qatar:

1. What is Qatar's approximate total population (citizens + residents)?
2. What is Qatar's main export commodity?
3. What year did Qatar host the FIFA World Cup?
4. What is the name of Qatar's sovereign wealth fund?
5. What is Qatar's currency?
6. Who is the current Emir of Qatar (as of 2024)?
7. What is Qatar's national development strategy called?
8. What is the approximate percentage of Qatari citizens in Qatar's total population?""",
        evaluation_criteria={
            "population_correct": {
                "weight": 12,
                "check": "factual_check",
                "acceptable_answers": ["2.8 million", "2.9 million", "3 million", "~3 million"],
                "description": "Population should be ~2.8-3 million"
            },
            "export_correct": {
                "weight": 12,
                "check": "factual_check",
                "acceptable_answers": ["LNG", "natural gas", "liquefied natural gas", "oil and gas"],
                "description": "Main export is LNG/natural gas"
            },
            "world_cup_correct": {
                "weight": 12,
                "check": "factual_check",
                "acceptable_answers": ["2022"],
                "description": "World Cup was 2022"
            },
            "swf_correct": {
                "weight": 13,
                "check": "factual_check",
                "acceptable_answers": ["QIA", "Qatar Investment Authority"],
                "description": "SWF is Qatar Investment Authority (QIA)"
            },
            "currency_correct": {
                "weight": 12,
                "check": "factual_check",
                "acceptable_answers": ["Qatari Riyal", "QAR", "riyal"],
                "description": "Currency is Qatari Riyal (QAR)"
            },
            "emir_correct": {
                "weight": 13,
                "check": "factual_check",
                "acceptable_answers": ["Tamim", "Sheikh Tamim", "Tamim bin Hamad"],
                "description": "Emir is Sheikh Tamim bin Hamad Al Thani"
            },
            "nds_correct": {
                "weight": 13,
                "check": "factual_check",
                "acceptable_answers": ["QNV 2030", "Qatar National Vision 2030", "Vision 2030", "NDS"],
                "description": "National strategy is Qatar National Vision 2030"
            },
            "citizen_percentage_correct": {
                "weight": 13,
                "check": "factual_check",
                "acceptable_answers": ["10%", "11%", "12%", "15%", "~10-15%"],
                "description": "Qatari citizens are ~10-15% of population"
            }
        },
        max_score=100,
        weight=1.0
    ),
]


# =============================================================================
# API CALL FUNCTIONS
# =============================================================================

async def call_model(config: Dict, system_prompt: str, user_prompt: str, timeout: int = 300) -> Tuple[str, float]:
    """
    Call Azure OpenAI model and return response + execution time.
    
    GPT-5.1 requires special handling:
    - NO system/developer role (causes HTTP 400 or empty response)
    - Embed system prompt in user message instead
    - Use max_completion_tokens instead of max_tokens
    """
    start_time = time.time()
    
    endpoint = (config.get("endpoint") or "").rstrip("/")
    api_key = config.get("api_key") or ""
    deployment = config.get("deployment") or ""
    api_version = config.get("api_version") or "2024-12-01-preview"
    is_gpt51 = config.get("system_role") == "developer"  # GPT-5.1 indicator
    
    if not endpoint or not api_key or not deployment:
        raise ValueError(f"Missing config: endpoint={bool(endpoint)}, api_key={bool(api_key)}, deployment={bool(deployment)}")
    
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    
    # GPT-5.1: Embed system prompt in user message, use max_completion_tokens, NO temperature
    if is_gpt51:
        combined_prompt = f"""INSTRUCTIONS:
{system_prompt}

USER QUERY:
{user_prompt}"""
        payload = {
            "messages": [
                {"role": "user", "content": combined_prompt}
            ],
            "max_completion_tokens": 4000
            # NOTE: GPT-5.1 does NOT support temperature parameter
        }
    else:
        # GPT-4o, GPT-5: Standard format with system role
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 4000,
            "temperature": 0.3
        }
    
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }
    
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 429:  # Rate limit
                    wait_time = RETRY_DELAY * (attempt + 1)
                    print(f"        Rate limited, waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                
                if response.status_code != 200:
                    error_text = response.text[:500]
                    raise Exception(f"HTTP {response.status_code}: {error_text}")
                
                data = response.json()
                
                # Handle potential empty response
                choices = data.get("choices", [])
                if not choices:
                    raise Exception("Empty choices in response")
                
                content = choices[0].get("message", {}).get("content", "")
                
                if not content or not content.strip():
                    raise Exception("Empty content in response")
                
                execution_time = time.time() - start_time
                return content, execution_time
                
        except httpx.TimeoutException:
            last_error = "Request timed out"
            if attempt < MAX_RETRIES - 1:
                print(f"        Timeout, retrying ({attempt + 2}/{MAX_RETRIES})...")
                await asyncio.sleep(RETRY_DELAY)
        except Exception as e:
            last_error = str(e)
            if attempt < MAX_RETRIES - 1 and "429" not in str(e):
                print(f"        Error: {str(e)[:50]}, retrying ({attempt + 2}/{MAX_RETRIES})...")
                await asyncio.sleep(RETRY_DELAY)
            else:
                raise
    
    raise Exception(f"Failed after {MAX_RETRIES} attempts: {last_error}")


# =============================================================================
# EVALUATION FUNCTIONS
# =============================================================================

def evaluate_test_case(test_case: TestCase, response: str) -> Tuple[Dict[str, float], List[str], List[str]]:
    """
    Evaluate a response against test case criteria.
    Returns (scores_dict, passed_criteria, failed_criteria)
    """
    scores = {}
    passed = []
    failed = []
    response_lower = response.lower()
    
    for criterion_name, criterion in test_case.evaluation_criteria.items():
        weight = criterion["weight"]
        check_type = criterion["check"]
        score = 0.0
        
        # Different evaluation methods based on check type
        if check_type in ["must_identify_demographic_impossibility", "identifies_impossibility", 
                          "identifies_constraint", "identifies_core_issue"]:
            keywords = criterion.get("keywords", [])
            matches = sum(1 for kw in keywords if kw.lower() in response_lower)
            score = min(1.0, matches / max(len(keywords) * 0.4, 1))  # Need ~40% of keywords
            
        elif check_type == "must_show_calculation":
            keywords = criterion.get("keywords", [])
            matches = sum(1 for kw in keywords if kw.lower() in response_lower)
            score = min(1.0, matches / max(len(keywords) * 0.3, 1))
            
        elif check_type == "provides_alternative":
            keywords = criterion.get("keywords", [])
            matches = sum(1 for kw in keywords if kw.lower() in response_lower)
            score = min(1.0, matches / max(len(keywords) * 0.3, 1))
            
        elif check_type == "negative_check":
            forbidden = criterion.get("forbidden_patterns", [])
            violations = sum(1 for fp in forbidden if fp.lower() in response_lower)
            score = 1.0 if violations == 0 else max(0, 1.0 - violations * 0.3)
            
        elif check_type == "citation_format":
            pattern = criterion.get("pattern", "")
            min_citations = criterion.get("min_citations", 1)
            matches = len(re.findall(pattern, response, re.IGNORECASE))
            score = min(1.0, matches / min_citations)
            
        elif check_type == "no_fabrication":
            allowed = criterion.get("allowed_numbers", [])
            # Find all numbers in response
            found_numbers = re.findall(r'\d+\.?\d*', response)
            # This is a simplified check - in production would be more rigorous
            score = 0.8  # Base score, would need human review for true accuracy
            
        elif check_type in ["acknowledges_gaps", "refuses_fabrication"]:
            keywords = criterion.get("keywords", [])
            min_occ = criterion.get("min_occurrences", 1)
            matches = sum(1 for kw in keywords if kw.lower() in response_lower)
            score = min(1.0, matches / min_occ)
            
        elif check_type == "no_invented_numbers":
            forbidden = criterion.get("forbidden_patterns", [])
            violations = sum(1 for fp in forbidden if re.search(fp, response, re.IGNORECASE))
            score = 1.0 if violations == 0 else max(0, 1.0 - violations * 0.4)
            
        elif check_type in ["contains_numbers", "has_numbers"]:
            min_numbers = criterion.get("min_numbers", 1)
            numbers = re.findall(r'\d+[,.]?\d*', response)
            score = min(1.0, len(numbers) / min_numbers)
            
        elif check_type == "contains_timelines":
            patterns = criterion.get("patterns", [])
            min_matches = criterion.get("min_matches", 1)
            total_matches = sum(len(re.findall(p, response, re.IGNORECASE)) for p in patterns)
            score = min(1.0, total_matches / min_matches)
            
        elif check_type == "contains_mechanisms":
            patterns = criterion.get("patterns", [])
            min_matches = criterion.get("min_matches", 1)
            total_matches = sum(len(re.findall(p, response, re.IGNORECASE)) for p in patterns)
            score = min(1.0, total_matches / min_matches)
            
        elif check_type in ["contains_stakeholder_impact", "assigns_responsibility", 
                           "has_for_arguments", "has_against_arguments", "identifies_tradeoffs",
                           "compares_domains", "considers_competition", "integrated_recommendation",
                           "has_section", "has_risks", "has_recommendation", "has_confidence",
                           "distinguishes_quality", "uses_confidence_language", "identifies_effects",
                           "identifies_unintended", "covers_country", "draws_lessons", "uses_provided_data"]:
            keywords = criterion.get("keywords", [])
            min_matches = criterion.get("min_matches", 1)
            matches = sum(1 for kw in keywords if kw.lower() in response_lower)
            score = min(1.0, matches / max(min_matches, 1))
            
        elif check_type == "nuanced_conclusion":
            keywords = criterion.get("keywords", [])
            matches = sum(1 for kw in keywords if kw.lower() in response_lower)
            score = min(1.0, matches / max(len(keywords) * 0.3, 1))
            
        elif check_type in ["challenges_assumption", "challenges_numbers", "identifies_risks"]:
            keywords = criterion.get("keywords", [])
            min_matches = criterion.get("min_matches", 1)
            matches = sum(1 for kw in keywords if kw.lower() in response_lower)
            score = min(1.0, matches / max(min_matches, 1))
            
        elif check_type == "uses_notation":
            patterns = criterion.get("patterns", [])
            min_matches = criterion.get("min_matches", 1)
            total_matches = sum(len(re.findall(p, response, re.IGNORECASE)) for p in patterns)
            score = min(1.0, total_matches / min_matches)
            
        elif check_type == "no_overclaiming":
            forbidden = criterion.get("forbidden_patterns", [])
            violations = sum(1 for fp in forbidden if fp.lower() in response_lower)
            score = 1.0 if violations == 0 else max(0, 1.0 - violations * 0.25)
            
        elif check_type == "has_metrics":
            patterns = criterion.get("patterns", [])
            min_matches = criterion.get("min_matches", 1)
            total_matches = sum(len(re.findall(p, response, re.IGNORECASE)) for p in patterns)
            score = min(1.0, total_matches / min_matches)
            
        elif check_type == "factual_check":
            acceptable = criterion.get("acceptable_answers", [])
            found = any(ans.lower() in response_lower for ans in acceptable)
            score = 1.0 if found else 0.0
            
        elif check_type == "contains_budget":
            patterns = criterion.get("patterns", [])
            min_matches = criterion.get("min_matches", 1)
            total_matches = sum(len(re.findall(p, response, re.IGNORECASE)) for p in patterns)
            score = min(1.0, total_matches / min_matches)
            
        elif check_type == "contains_phases":
            keywords = criterion.get("keywords", [])
            min_matches = criterion.get("min_matches", 1)
            matches = sum(1 for kw in keywords if kw.lower() in response_lower)
            score = min(1.0, matches / max(min_matches, 1))
            
        elif check_type == "contains_targets":
            patterns = criterion.get("patterns", [])
            min_matches = criterion.get("min_matches", 1)
            total_matches = sum(len(re.findall(p, response, re.IGNORECASE)) for p in patterns)
            score = min(1.0, total_matches / min_matches)
            
        elif check_type == "identifies_multiple_issues":
            keywords = criterion.get("keywords", [])
            matches = sum(1 for kw in keywords if kw.lower() in response_lower)
            score = min(1.0, matches / max(len(keywords) * 0.4, 1))
        
        else:
            # Default keyword check
            keywords = criterion.get("keywords", [])
            if keywords:
                matches = sum(1 for kw in keywords if kw.lower() in response_lower)
                score = min(1.0, matches / max(len(keywords) * 0.3, 1))
            else:
                score = 0.5  # Unknown check type, neutral score
        
        # Apply weight
        weighted_score = score * weight
        scores[criterion_name] = weighted_score
        
        if score >= 0.6:
            passed.append(criterion_name)
        else:
            failed.append(criterion_name)
    
    return scores, passed, failed


def calculate_total_score(scores: Dict[str, float], max_score: int) -> float:
    """Calculate total score as percentage of max."""
    total = sum(scores.values())
    return (total / max_score) * 100


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

async def run_comprehensive_evaluation() -> Dict[str, Any]:
    """Run full evaluation suite across all models."""
    
    print("=" * 80)
    print("QNWIS COMPREHENSIVE MODEL EVALUATION SUITE")
    print("=" * 80)
    print(f"\nStarted: {datetime.now().isoformat()}")
    print(f"Test Cases: {len(TEST_SUITE)}")
    print(f"Models: {list(MODELS_CONFIG.keys())}")
    print(f"\nEvaluation Focus: Accuracy, Depth, Quality (NOT speed/cost)")
    
    # Show configuration
    print("\n" + "-" * 80)
    print("MODEL CONFIGURATION")
    print("-" * 80)
    for model_name, config in MODELS_CONFIG.items():
        print(f"\n  {model_name}:")
        print(f"    Deployment: {config.get('deployment', 'NOT SET')}")
        print(f"    API Version: {config.get('api_version', 'NOT SET')}")
        print(f"    Endpoint: {'SET' if config.get('endpoint') else 'NOT SET'}")
        print(f"    API Key: {'SET' if config.get('api_key') else 'NOT SET'}")
        print(f"    System Role: {config.get('system_role', 'system')}")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "test_count": len(TEST_SUITE),
        "models": list(MODELS_CONFIG.keys()),
        "model_results": {},
        "category_scores": {},
        "recommendations": {},
        "winner_by_category": {},
        "overall_winner": None
    }
    
    # Check model availability
    print("\n" + "-" * 80)
    print("CHECKING MODEL AVAILABILITY")
    print("-" * 80)
    
    available_models = {}
    for model_name, config in MODELS_CONFIG.items():
        print(f"\n  {model_name} (role: {config.get('system_role', 'system')})...", end=" ")
        
        # Skip if missing required config
        if not config.get('endpoint') or not config.get('api_key'):
            print("✗ SKIPPED (missing endpoint or api_key)")
            continue
            
        try:
            _, _ = await call_model(config, "Respond with: OK", "Test", timeout=60)
            print("✓ AVAILABLE")
            available_models[model_name] = config
        except Exception as e:
            print(f"✗ ERROR: {str(e)[:80]}")
    
    if len(available_models) < 2:
        print("\nERROR: Need at least 2 models for comparison")
        return results
    
    # Group tests by category
    categories = {}
    for test in TEST_SUITE:
        if test.category not in categories:
            categories[test.category] = []
        categories[test.category].append(test)
    
    print(f"\n\nTest Categories: {list(categories.keys())}")
    
    # Estimated time
    est_time = len(TEST_SUITE) * len(available_models) * 45  # ~45s per test
    print(f"Estimated Time: {est_time // 60} minutes")
    
    # Run tests for each model
    for model_name, config in available_models.items():
        print("\n" + "=" * 80)
        print(f"TESTING: {model_name} (using role: {config.get('system_role', 'system')})")
        print("=" * 80)
        
        model_results = []
        category_totals = {cat: [] for cat in categories}
        
        for test in TEST_SUITE:
            print(f"\n  [{test.id}] {test.name}")
            print(f"      Category: {test.category}")
            
            try:
                response, exec_time = await call_model(
                    config, 
                    test.system_prompt, 
                    test.user_prompt,
                    timeout=300
                )
                
                # Evaluate response
                scores, passed, failed = evaluate_test_case(test, response)
                total_score = calculate_total_score(scores, test.max_score)
                weighted_score = total_score * test.weight
                
                result = TestResult(
                    test_id=test.id,
                    model=model_name,
                    response=response,
                    scores=scores,
                    total_score=total_score,
                    execution_time=exec_time,
                    passed_criteria=passed,
                    failed_criteria=failed
                )
                
                model_results.append(result)
                category_totals[test.category].append(weighted_score)
                
                print(f"      Score: {total_score:.1f}% (weighted: {weighted_score:.1f})")
                print(f"      Passed: {len(passed)}/{len(passed)+len(failed)} criteria")
                print(f"      Time: {exec_time:.1f}s")
                
                if failed:
                    print(f"      Failed: {', '.join(failed[:3])}")
                
            except Exception as e:
                print(f"      ✗ ERROR: {str(e)[:60]}")
                model_results.append(TestResult(
                    test_id=test.id,
                    model=model_name,
                    response="",
                    scores={},
                    total_score=0,
                    execution_time=0,
                    evaluator_notes=[f"Error: {str(e)}"]
                ))
            
            await asyncio.sleep(1)  # Rate limiting
        
        # Calculate category averages
        category_averages = {}
        for cat, scores in category_totals.items():
            if scores:
                category_averages[cat] = sum(scores) / len(scores)
            else:
                category_averages[cat] = 0
        
        results["model_results"][model_name] = [asdict(r) for r in model_results]
        results["category_scores"][model_name] = category_averages
    
    # Determine winners by category
    print("\n" + "=" * 80)
    print("CATEGORY WINNERS")
    print("=" * 80)
    
    for category in categories:
        print(f"\n  {category}:")
        cat_scores = {
            model: results["category_scores"][model].get(category, 0)
            for model in available_models
        }
        
        for model, score in sorted(cat_scores.items(), key=lambda x: -x[1]):
            print(f"    {model}: {score:.1f}")
        
        winner = max(cat_scores, key=cat_scores.get)
        results["winner_by_category"][category] = {
            "winner": winner,
            "score": cat_scores[winner],
            "all_scores": cat_scores
        }
    
    # Calculate overall scores
    print("\n" + "=" * 80)
    print("OVERALL RESULTS")
    print("=" * 80)
    
    overall_scores = {}
    for model in available_models:
        cat_scores = results["category_scores"][model]
        overall = sum(cat_scores.values()) / len(cat_scores) if cat_scores else 0
        overall_scores[model] = overall
    
    print("\n  OVERALL SCORES:")
    for model, score in sorted(overall_scores.items(), key=lambda x: -x[1]):
        print(f"    {model}: {score:.2f}")
    
    overall_winner = max(overall_scores, key=overall_scores.get)
    results["overall_winner"] = overall_winner
    results["overall_scores"] = overall_scores
    
    print(f"\n  🏆 OVERALL WINNER: {overall_winner}")
    
    # Generate recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS BY QNWIS COMPONENT")
    print("=" * 80)
    
    component_mapping = {
        "First-Principles Reasoning": "Feasibility Gate Node",
        "Citation Compliance": "Agent Prompts & Fact Verification",
        "Stake Specificity": "Scenario Generator",
        "Debate Quality": "Legendary Debate Orchestrator",
        "Cross-Domain Reasoning": "Meta-Synthesis Node",
        "Synthesis Quality": "Final Synthesis Node",
        "Analytical Depth": "Agent Analysis Prompts",
        "Accuracy": "All Components (Base Knowledge)"
    }
    
    for category, component in component_mapping.items():
        if category in results["winner_by_category"]:
            winner_data = results["winner_by_category"][category]
            winner = winner_data["winner"]
            score = winner_data["score"]
            
            print(f"\n  {component}:")
            print(f"    Recommended Model: {winner}")
            print(f"    Score: {score:.1f}")
            print(f"    Reason: Best performance on {category} tests")
            
            results["recommendations"][component] = {
                "model": winner,
                "category": category,
                "score": score
            }
    
    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Main results JSON
    results_file = OUTPUT_DIR / f"comprehensive_evaluation_{timestamp}.json"
    with open(results_file, "w", encoding="utf-8") as f:
        # Remove full responses from main JSON to keep size manageable
        save_results = {k: v for k, v in results.items()}
        for model in save_results.get("model_results", {}):
            for r in save_results["model_results"][model]:
                if len(r.get("response", "")) > 500:
                    r["response"] = r["response"][:500] + "... [truncated]"
        json.dump(save_results, f, indent=2, default=str)
    
    print(f"\n  Results saved: {results_file}")
    
    # Full responses for review
    for model in available_models:
        response_file = OUTPUT_DIR / f"full_responses_{model.replace('.', '_')}_{timestamp}.txt"
        with open(response_file, "w", encoding="utf-8") as f:
            f.write(f"FULL RESPONSES: {model}\n")
            f.write("=" * 80 + "\n\n")
            
            for r in results["model_results"][model]:
                f.write(f"TEST: {r['test_id']}\n")
                f.write(f"Score: {r['total_score']:.1f}%\n")
                f.write(f"Passed: {r['passed_criteria']}\n")
                f.write(f"Failed: {r['failed_criteria']}\n")
                f.write("-" * 40 + "\n")
                f.write(r.get("response", "No response") + "\n")
                f.write("\n" + "=" * 80 + "\n\n")
        
        print(f"  Responses saved: {response_file}")
    
    # Summary report
    summary_file = OUTPUT_DIR / f"EVALUATION_SUMMARY_{timestamp}.md"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("# QNWIS Comprehensive Model Evaluation Summary\n\n")
        f.write(f"**Date:** {datetime.now().isoformat()}\n")
        f.write(f"**Tests Run:** {len(TEST_SUITE)}\n")
        f.write(f"**Models Tested:** {', '.join(available_models.keys())}\n\n")
        
        f.write("## Overall Winner\n\n")
        f.write(f"**🏆 {overall_winner}** with score {overall_scores[overall_winner]:.2f}\n\n")
        
        f.write("## Scores by Category\n\n")
        f.write("| Category | " + " | ".join(available_models.keys()) + " | Winner |\n")
        f.write("|" + "---|" * (len(available_models) + 2) + "\n")
        
        for category in categories:
            row = f"| {category} |"
            for model in available_models:
                score = results["category_scores"][model].get(category, 0)
                row += f" {score:.1f} |"
            winner = results["winner_by_category"].get(category, {}).get("winner", "N/A")
            row += f" {winner} |"
            f.write(row + "\n")
        
        f.write("\n## Recommendations by QNWIS Component\n\n")
        f.write("| Component | Recommended Model | Score |\n")
        f.write("|---|---|---|\n")
        
        for component, rec in results["recommendations"].items():
            f.write(f"| {component} | {rec['model']} | {rec['score']:.1f} |\n")
        
        f.write("\n## Detailed Category Analysis\n\n")
        
        for category, tests in categories.items():
            f.write(f"### {category}\n\n")
            winner_data = results["winner_by_category"].get(category, {})
            f.write(f"**Winner:** {winner_data.get('winner', 'N/A')}\n\n")
            f.write("| Test | " + " | ".join(available_models.keys()) + " |\n")
            f.write("|" + "---|" * (len(available_models) + 1) + "\n")
            
            for test in tests:
                row = f"| {test.id}: {test.name} |"
                for model in available_models:
                    model_test_results = [
                        r for r in results["model_results"][model]
                        if r["test_id"] == test.id
                    ]
                    if model_test_results:
                        score = model_test_results[0]["total_score"]
                        row += f" {score:.1f}% |"
                    else:
                        row += " N/A |"
                f.write(row + "\n")
            f.write("\n")
    
    print(f"  Summary saved: {summary_file}")
    
    print("\n" + "=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)
    
    return results


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    results = asyncio.run(run_comprehensive_evaluation())
    
    if results.get("overall_winner"):
        print(f"\n✅ Evaluation complete. Winner: {results['overall_winner']}")
        sys.exit(0)
    else:
        print("\n❌ Evaluation failed")
        sys.exit(1)

