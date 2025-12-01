#!/usr/bin/env python3
"""
NSIC FULL END-TO-END TEST WITH MCKINSEY-GRADE EVALUATION

Enhanced with QNWIS diagnostic features:
- 10 domain test queries (healthcare, education, energy, etc.)
- Command line arguments (--query, --batch, --list, --random)
- Weighted scoring system (PASS/WARN/FAIL)
- McKinsey compliance checklist
- LIVE debate streaming with turn-by-turn output
- Full debate transcripts saved to files
- Turn count verification and timing sanity checks
- Grade system: LEGENDARY → NEEDS WORK

Usage:
    python scripts/test_full_e2e.py                    # Default query
    python scripts/test_full_e2e.py --query healthcare # Specific query
    python scripts/test_full_e2e.py --batch            # All queries
    python scripts/test_full_e2e.py --list             # List queries
    python scripts/test_full_e2e.py --random           # Random query
"""

import asyncio
import time
import sys
import os
import re
import json
import argparse
import random
import requests
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

# Load .env file FIRST
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Set DATABASE_URL if not already set (required for QNWIS workflow)
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "postgresql://postgres:1234@localhost:5432/qnwis"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# SCORING SYSTEM
# =============================================================================

class ScoreLevel(Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class CheckResult:
    """Result of a single diagnostic check."""
    name: str
    passed: bool
    score: float  # 0-100
    level: ScoreLevel
    details: str = ""
    evidence: Any = None


@dataclass
class StageResult:
    """Result of a diagnostic stage."""
    stage_name: str
    checks: List[CheckResult] = field(default_factory=list)
    overall_score: float = 0.0
    overall_level: ScoreLevel = ScoreLevel.FAIL
    
    def add_check(self, check: CheckResult):
        self.checks.append(check)
        self._recalculate_overall()
    
    def _recalculate_overall(self):
        if not self.checks:
            self.overall_score = 0.0
            self.overall_level = ScoreLevel.FAIL
            return
        
        self.overall_score = sum(c.score for c in self.checks) / len(self.checks)
        
        if self.overall_score >= 80:
            self.overall_level = ScoreLevel.PASS
        elif self.overall_score >= 50:
            self.overall_level = ScoreLevel.WARN
        else:
            self.overall_level = ScoreLevel.FAIL


# =============================================================================
# TEST QUERY LIBRARY - 10 DOMAINS
# =============================================================================

TEST_QUERIES = {
    "economic_diversification": {
        "name": "Economic Diversification Strategy",
        "domain": "Economic Policy",
        "complexity": "complex",
        "query": """Qatar must choose its primary economic diversification focus for the next decade.
The Ministry of Finance has budget for ONE major initiative (QAR 50 billion over 10 years).

Option A: Financial Services Hub
- Target: Become the leading Islamic finance and wealth management center in the GCC
- Compete directly with Dubai International Financial Centre (DIFC)
- Leverage QIA's $450B sovereign wealth for anchor investments

Option B: Advanced Logistics & Trade Hub
- Target: Become the GCC's premier air cargo and re-export hub
- Expand Hamad International Airport cargo capacity 3x
- Leverage geographic position between Europe, Asia, and Africa

Current Context:
- Qatar Financial Centre currently employs 1,200 Qataris (5% of target 25,000)
- Hamad Airport handles 2.5M tons cargo/year (Dubai: 2.7M tons)
- Dubai has 40+ year head start in financial services
- Saudi Arabia investing $100B in NEOM logistics zone
- Qatari STEM/business graduates: 4,500 per year combined

Which option should Qatar prioritize and why?"""
    },
    
    "healthcare": {
        "name": "Healthcare System Transformation",
        "domain": "Healthcare Policy",
        "complexity": "complex",
        "query": """Qatar's Ministry of Public Health must decide on the next phase of healthcare development.
Budget allocation: QAR 30 billion over 8 years.

Option A: Specialized Medical Tourism Hub
- Build 3 world-class specialty hospitals (cardiac, oncology, orthopedics)
- Target: Attract 500,000 medical tourists annually by 2032
- Partner with Mayo Clinic, Cleveland Clinic for expertise

Option B: Universal Primary Care Expansion
- Build 50 new primary care centers across Qatar
- Implement AI-driven preventive care system
- Train 5,000 Qatari nurses and 1,000 Qatari physicians

Current Context:
- Hamad Medical Corporation handles 2.1M patient visits/year
- 78% of healthcare workers are expatriates
- Qatar spends 2.5% of GDP on healthcare (GCC average: 3.8%)
- Chronic diseases account for 70% of deaths

Which strategy should Qatar pursue?"""
    },
    
    "education": {
        "name": "Education System Modernization",
        "domain": "Education Policy",
        "complexity": "complex",
        "query": """Qatar's Ministry of Education is planning a major reform initiative.
Budget: QAR 15 billion over 6 years.

Option A: Elite STEM University Cluster
- Expand Education City with 3 new world-class STEM universities
- Target: Produce 2,000 Qatari engineers and scientists annually
- Attract top global faculty with competitive packages

Option B: Vocational Training Revolution
- Build 25 technical colleges across Qatar
- Partner with German/Swiss vocational systems
- Target: 10,000 skilled Qatari technicians per year

Current Context:
- Qatar University graduates 3,500 Qataris annually
- Only 12% of graduates are in STEM fields
- Private sector complains of skills mismatch
- Youth unemployment among Qataris: 8%
- 85% of private sector jobs held by expatriates

Which approach should Qatar prioritize?"""
    },
    
    "energy": {
        "name": "Energy Transition Strategy",
        "domain": "Energy Policy",
        "complexity": "complex",
        "query": """Qatar's Ministry of Energy must plan for the post-hydrocarbon era.
Investment envelope: QAR 100 billion over 15 years.

Option A: Green Hydrogen Superpower
- Build 10 GW green hydrogen production capacity
- Target: Capture 10% of global hydrogen export market by 2040
- Leverage existing LNG infrastructure and customer relationships

Option B: Solar Manufacturing & Export Hub
- Build 5 GW solar panel manufacturing capacity
- Develop 20 GW domestic solar farms
- Target: Energy independence + regional export

Current Context:
- Qatar produces 77M tons LNG/year (20% of global trade)
- LNG revenues: $50-80 billion annually
- Current renewable energy: <2% of generation
- Solar irradiance: 2,000 kWh/m²/year (excellent)

Which path should Qatar take?"""
    },
    
    "housing": {
        "name": "Affordable Housing Crisis",
        "domain": "Urban Development",
        "complexity": "complex",
        "query": """Qatar's Ministry of Municipality faces a housing challenge for young Qatari families.
Budget: QAR 25 billion over 7 years.

Option A: New Satellite City Development
- Build new planned city for 100,000 residents (25,000 units)
- Location: 40km from Doha
- Full infrastructure: schools, hospitals, commercial

Option B: Urban Densification & Renovation
- Acquire and renovate 15,000 units in existing Doha neighborhoods
- Build 10,000 new units in mixed-use developments
- Improve public transit connectivity

Current Context:
- 35,000 Qatari families on housing waitlist
- Average wait time: 7 years
- Average Qatari household size: 6.2 persons
- Young Qataris (25-35) increasingly unable to afford homes

Which approach should Qatar adopt?"""
    },
    
    "food_security": {
        "name": "Food Security Strategy",
        "domain": "Agriculture & Food Policy",
        "complexity": "complex",
        "query": """After the 2017 blockade exposed vulnerabilities, Qatar must secure its food supply.
Investment: QAR 10 billion over 5 years.

Option A: High-Tech Domestic Production
- Build 100 vertical farms and 50 solar-powered greenhouses
- Develop aquaculture capacity for 50,000 tons fish/year
- Target: 70% self-sufficiency in vegetables, 40% in protein

Option B: Strategic Reserve & Diversified Imports
- Build strategic food reserves for 2 years of consumption
- Acquire farmland in friendly nations (Sudan, Pakistan, Morocco)
- Create bilateral food security agreements with 10+ nations

Current Context:
- Qatar imports 90% of food
- 2017 blockade disrupted 40% of food imports temporarily
- Arable land: <1% of territory
- Water: Entirely desalinated, expensive

Which strategy should Qatar pursue?"""
    },
    
    "tourism": {
        "name": "Post-World Cup Tourism Strategy",
        "domain": "Tourism & Hospitality",
        "complexity": "complex",
        "query": """After FIFA World Cup 2022, Qatar must sustain tourism momentum.
Budget: QAR 20 billion over 5 years.

Option A: Luxury & Business Tourism Focus
- Position as ultra-premium destination
- Target: 2 million high-spending visitors/year
- Develop exclusive experiences (desert luxury, cultural immersion)

Option B: Mass Market & Family Tourism
- Develop theme parks, beaches, entertainment
- Target: 8 million visitors/year
- Compete with Dubai on volume

Current Context:
- World Cup hosted 1.4 million visitors in 4 weeks
- Current annual visitors: 3 million
- Hotel capacity: 45,000 rooms (30,000 added for World Cup)
- Dubai attracts 16 million visitors/year

Which tourism model should Qatar pursue?"""
    },
    
    "labor": {
        "name": "Labor Market Nationalization",
        "domain": "Labor Policy",
        "complexity": "complex",
        "query": """Qatar must accelerate Qatarization while maintaining economic competitiveness.
The Ministry of Labour is considering two approaches.

Option A: Aggressive Quota Enforcement
- Mandate 50% Qatari workforce in all companies >100 employees
- Heavy fines for non-compliance (QAR 50,000/month per missing Qatari)
- Timeline: Full compliance within 3 years

Option B: Incentive-Based Transformation
- Tax benefits for companies exceeding Qatarization targets
- Government-funded training programs (2-year bootcamps)
- Gradual targets: 20% by 2025, 35% by 2030, 50% by 2035

Current Context:
- Qataris: 12% of total population (350,000 of 2.9 million)
- Qataris in private sector: 6% of private workforce
- Qatari unemployment: 0.5% (effectively full employment)
- Average Qatari salary expectations: 3-4x expatriate equivalent

Which approach should Qatar implement?"""
    },
    
    "simple_revenue": {
        "name": "Simple Revenue Query",
        "domain": "Finance",
        "complexity": "simple",
        "query": """What was Qatar's total LNG export revenue in 2023, and how does this compare 
to 2022? What are the projections for 2024?"""
    },
    
    "medium_analysis": {
        "name": "Medium Complexity Analysis",
        "domain": "Economic Analysis",
        "complexity": "medium",
        "query": """Analyze Qatar's current Qatarization progress in the banking sector:
1. What is the current percentage of Qatari employees in major banks?
2. How does this compare to the government target?
3. What are the main barriers to increasing Qatarization?
4. Recommend specific interventions to accelerate progress."""
    },
}


# =============================================================================
# WEIGHTED SCORING CONFIG
# =============================================================================

STAGE_WEIGHTS = {
    "data_flow": 0.10,
    "engine_a_execution": 0.15,
    "engine_b_execution": 0.15,
    "debate_quality": 0.15,
    "zero_fabrication": 0.10,
    "qatar_specificity": 0.10,
    "cross_validation": 0.05,
    "risk_analysis": 0.05,
    "roadmap": 0.05,
    "mckinsey_compliance": 0.10,
}


# =============================================================================
# COMPREHENSIVE DEBATE LOGGING - ALL 1,200 TURNS SAVED TO FILES
# =============================================================================

class DebateStreamLogger:
    """
    Comprehensive logger that saves EVERY debate turn to files.
    
    Creates:
    - outputs/debates/engine_a/scenario_X.txt - Full transcript per scenario
    - outputs/debates/engine_b/gpuX_scenario_Y.txt - Full transcript per scenario
    - outputs/debates/master_debate_log.json - Summary with verification
    
    ALL content is saved untruncated for full audit capability.
    """
    
    def __init__(self, output_dir: str, question: str = ""):
        self.output_dir = output_dir
        self.question = question
        self.transcripts = {}  # scenario_id -> list of turns
        self.turn_counts = {}  # scenario_id -> turn count
        self.start_times = {}  # scenario_id -> start time
        self.scenario_metadata = {}  # scenario_id -> metadata dict
        self.file_handles = {}  # scenario_id -> open file handle
        self.files_created = {"engine_a": [], "engine_b": []}
        
        # Create directory structure
        self.engine_a_dir = os.path.join(output_dir, "engine_a")
        self.engine_b_dir = os.path.join(output_dir, "engine_b")
        os.makedirs(self.engine_a_dir, exist_ok=True)
        os.makedirs(self.engine_b_dir, exist_ok=True)
        
        # Stats tracking
        self.stats = {
            "engine_a_turns": 0,
            "engine_b_turns": 0,
            "engine_a_scenarios": 0,
            "engine_b_scenarios": 0,
            "think_blocks": 0,
            "total_words": 0,
        }
    
    def _get_file_path(self, engine: str, scenario_id: str, gpu_id: int = None) -> str:
        """Get file path for a scenario transcript."""
        safe_name = re.sub(r'[^\w\-]', '_', scenario_id)[:50]
        
        if engine == "A":
            filename = f"{safe_name}.txt"
            return os.path.join(self.engine_a_dir, filename)
        else:
            gpu_prefix = f"gpu{gpu_id}_" if gpu_id is not None else ""
            filename = f"{gpu_prefix}{safe_name}.txt"
            return os.path.join(self.engine_b_dir, filename)
    
    def _ensure_file_open(self, engine: str, scenario_id: str, scenario_name: str, gpu_id: int = None):
        """Ensure file is open and header is written."""
        if scenario_id in self.file_handles:
            return
        
        filepath = self._get_file_path(engine, scenario_id, gpu_id)
        
        # Open file for writing
        f = open(filepath, 'w', encoding='utf-8')
        self.file_handles[scenario_id] = f
        
        # Track files created
        if engine == "A":
            self.files_created["engine_a"].append(filepath)
        else:
            self.files_created["engine_b"].append(filepath)
        
        # Write header
        f.write("=" * 80 + "\n")
        if engine == "A":
            f.write(f"ENGINE A - SCENARIO: {scenario_name}\n")
            f.write("=" * 80 + "\n")
            f.write(f"Scenario ID: {scenario_id}\n")
            f.write(f"Question: {self.question[:200]}...\n")
            f.write(f"Agents: Dr. Ahmed, Dr. Sarah, Dr. Mohammed, Dr. Layla, PatternDetective\n")
        else:
            f.write(f"ENGINE B - GPU {gpu_id} - SCENARIO: {scenario_name}\n")
            f.write("=" * 80 + "\n")
            f.write(f"Scenario ID: {scenario_id}\n")
            f.write(f"Question: {self.question[:200]}...\n")
            f.write(f"Agents: Dr. Rashid, Dr. Noor, Dr. Hassan (rotating)\n")
        
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")
        f.flush()
    
    def log_turn(self, engine: str, scenario_id: str, scenario_name: str,
                 turn_num: int, agent_name: str, content: str, gpu_id: int = None):
        """
        Log a debate turn - called for EACH turn as it happens.
        
        Writes FULL content to file immediately (not buffered).
        Prints progress to console.
        """
        
        # Initialize tracking
        if scenario_id not in self.transcripts:
            self.transcripts[scenario_id] = []
            self.turn_counts[scenario_id] = 0
            self.start_times[scenario_id] = time.time()
            self.scenario_metadata[scenario_id] = {
                "engine": engine,
                "name": scenario_name,
                "gpu_id": gpu_id,
            }
        
        self.turn_counts[scenario_id] = turn_num
        
        # Ensure file is open
        self._ensure_file_open(engine, scenario_id, scenario_name, gpu_id)
        
        # Store turn in memory
        turn_data = {
            "turn": turn_num,
            "agent": agent_name,
            "content": content,  # FULL content, not truncated
            "timestamp": datetime.now().isoformat(),
            "has_think": "<think>" in content if content else False,
        }
        self.transcripts[scenario_id].append(turn_data)
        
        # Update stats
        if engine == "A":
            self.stats["engine_a_turns"] += 1
        else:
            self.stats["engine_b_turns"] += 1
        
        if content:
            self.stats["total_words"] += len(content.split())
            if "<think>" in content:
                self.stats["think_blocks"] += 1
        
        # WRITE TO FILE IMMEDIATELY (not buffered)
        f = self.file_handles.get(scenario_id)
        if f:
            f.write(f"\nTURN {turn_num} | {agent_name}\n")
            f.write("-" * 80 + "\n")
            f.write(content if content else "[No content]\n")
            f.write("\n")
            f.flush()  # Force write immediately
        
        # Print live progress to console
        show_turn = (engine == "A" and turn_num % 10 == 0) or \
                    (engine == "B" and turn_num % 5 == 0) or \
                    turn_num == 1
        
        if show_turn:
            gpu_str = f" GPU {gpu_id}" if gpu_id is not None else ""
            snippet = content[:80].replace('\n', ' ') if content else "[no content]"
            think_marker = " 🧠" if turn_data["has_think"] else ""
            print(f"  [Engine {engine}{gpu_str}] Turn {turn_num} | {agent_name}{think_marker}: {snippet}...")
    
    def log_scenario_complete(self, engine: str, scenario_id: str, scenario_name: str,
                               turns_completed: int, expected_turns: int, gpu_id: int = None):
        """Log scenario completion with summary footer."""
        elapsed = time.time() - self.start_times.get(scenario_id, time.time())
        sec_per_turn = elapsed / max(turns_completed, 1)
        
        # Update scenario counts
        if engine == "A":
            self.stats["engine_a_scenarios"] += 1
        else:
            self.stats["engine_b_scenarios"] += 1
        
        # Write summary footer to file
        f = self.file_handles.get(scenario_id)
        if f:
            turns = self.transcripts.get(scenario_id, [])
            total_words = sum(len(t.get("content", "").split()) for t in turns)
            think_count = sum(1 for t in turns if t.get("has_think"))
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("SCENARIO SUMMARY\n")
            f.write("=" * 80 + "\n")
            f.write(f"Total Turns: {turns_completed}\n")
            f.write(f"Expected Turns: {expected_turns}\n")
            f.write(f"Total Words: {total_words:,}\n")
            f.write(f"<think> Blocks: {think_count}/{turns_completed}\n")
            f.write(f"Time: {elapsed:.1f}s ({sec_per_turn:.2f}s/turn)\n")
            f.write("=" * 80 + "\n")
            f.flush()
            f.close()
            del self.file_handles[scenario_id]
        
        # Timing sanity check
        timing_ok = sec_per_turn >= 0.3
        timing_status = "✅" if timing_ok else "⚠️ FAST"
        
        # Turn count verification
        turn_ok = turns_completed >= expected_turns * 0.8
        turn_status = "✅" if turn_ok else f"❌ {turns_completed}/{expected_turns}"
        
        gpu_str = f" GPU {gpu_id}" if gpu_id is not None else ""
        print(f"  [Engine {engine}{gpu_str}] ✓ {scenario_name[:40]}... | Turns: {turn_status} | {timing_status}")
    
    def finalize(self) -> Dict[str, Any]:
        """
        Close all files and create master log.
        
        Returns verification summary.
        """
        # Close any remaining open files
        for scenario_id, f in list(self.file_handles.items()):
            try:
                f.close()
            except:
                pass
        self.file_handles.clear()
        
        # Build master log
        master_log = {
            "timestamp": datetime.now().isoformat(),
            "question": self.question,
            "total_scenarios": len(self.transcripts),
            "total_turns": self.stats["engine_a_turns"] + self.stats["engine_b_turns"],
            "total_words": self.stats["total_words"],
            "think_blocks": self.stats["think_blocks"],
            
            "engine_a": {
                "scenarios": self.stats["engine_a_scenarios"],
                "turns": self.stats["engine_a_turns"],
                "expected_turns_per_scenario": 100,
                "agents": ["Dr. Ahmed", "Dr. Sarah", "Dr. Mohammed", "Dr. Layla", "PatternDetective"],
                "files": [os.path.basename(f) for f in self.files_created["engine_a"]],
            },
            
            "engine_b": {
                "scenarios": self.stats["engine_b_scenarios"],
                "turns": self.stats["engine_b_turns"],
                "expected_turns_per_scenario": 25,
                "agents": ["Dr. Rashid", "Dr. Noor", "Dr. Hassan"],
                "files": [os.path.basename(f) for f in self.files_created["engine_b"]],
            },
            
            "verification": {
                "engine_a_turns_logged": self.stats["engine_a_turns"],
                "engine_b_turns_logged": self.stats["engine_b_turns"],
                "all_files_created": len(self.files_created["engine_a"]) + len(self.files_created["engine_b"]),
                "scenarios_by_id": {},
            },
        }
        
        # Add per-scenario verification
        suspicious = []
        for scenario_id, turns in self.transcripts.items():
            meta = self.scenario_metadata.get(scenario_id, {})
            elapsed = time.time() - self.start_times.get(scenario_id, time.time())
            turn_count = len(turns)
            sec_per_turn = elapsed / max(turn_count, 1)
            
            is_suspicious = sec_per_turn < 0.3
            if is_suspicious:
                suspicious.append(scenario_id)
            
            master_log["verification"]["scenarios_by_id"][scenario_id] = {
                "engine": meta.get("engine", "unknown"),
                "turns_logged": turn_count,
                "time_seconds": round(elapsed, 1),
                "sec_per_turn": round(sec_per_turn, 2),
                "suspicious": is_suspicious,
            }
        
        master_log["verification"]["suspicious_scenarios"] = suspicious
        master_log["verification"]["verification_passed"] = len(suspicious) == 0
        
        # Save master log
        master_log_path = os.path.join(self.output_dir, "master_debate_log.json")
        with open(master_log_path, 'w', encoding='utf-8') as f:
            json.dump(master_log, f, indent=2)
        
        print(f"\n📁 Master log saved: {master_log_path}")
        print(f"📁 Engine A transcripts: {len(self.files_created['engine_a'])} files in {self.engine_a_dir}")
        print(f"📁 Engine B transcripts: {len(self.files_created['engine_b'])} files in {self.engine_b_dir}")
        
        return master_log
    
    def get_verification_summary(self) -> Dict[str, Any]:
        """Get summary for verification checking."""
        return {
            "engine_a_turns": self.stats["engine_a_turns"],
            "engine_b_turns": self.stats["engine_b_turns"],
            "total_turns": self.stats["engine_a_turns"] + self.stats["engine_b_turns"],
            "scenarios_logged": len(self.transcripts),
            "files_created": len(self.files_created["engine_a"]) + len(self.files_created["engine_b"]),
            "total_words": self.stats["total_words"],
            "think_blocks": self.stats["think_blocks"],
        }


# =============================================================================
# DATA FLOW VERIFICATION
# =============================================================================

def verify_data_flow_services():
    """Verify all data services are working before running test."""
    print("=" * 70)
    print("DATA FLOW VERIFICATION")
    print("=" * 70)
    print()
    
    results = {"all_pass": True}
    stage = StageResult(stage_name="data_flow")
    
    # 1. CPU Services
    print("CPU SERVICES:")
    services = [
        ("Embeddings", 8100),
        ("KG", 8101),
        ("Verification", 8102),
    ]
    for name, port in services:
        try:
            r = requests.get(f"http://localhost:{port}/health", timeout=30)  # 30s timeout
            data = r.json()
            print(f"  ✅ {name} (port {port}): healthy")
            results[name.lower()] = True
            stage.add_check(CheckResult(
                name=f"{name.lower()}_service",
                passed=True, score=100, level=ScoreLevel.PASS,
                details=f"{name} service healthy"
            ))
        except Exception as e:
            print(f"  ❌ {name} (port {port}): FAILED - {e}")
            results[name.lower()] = False
            results["all_pass"] = False
            stage.add_check(CheckResult(
                name=f"{name.lower()}_service",
                passed=False, score=0, level=ScoreLevel.FAIL,
                details=f"{name} service failed: {e}"
            ))
    print()
    
    # 2. Test RAG/Embeddings
    print("RAG/EMBEDDINGS TEST:")
    try:
        r = requests.post(
            "http://localhost:8100/embed",
            json={"texts": ["Qatar financial hub economic diversification"]},
            timeout=30
        )
        if r.status_code == 200:
            data = r.json()
            dim = data.get("dimension", 0)
            print(f"  ✅ Embeddings working (dimension: {dim})")
            results["rag_search"] = 1
            results["embedding_dim"] = dim
            stage.add_check(CheckResult(
                name="embeddings_test",
                passed=True, score=100, level=ScoreLevel.PASS,
                details=f"Embeddings working, dimension={dim}"
            ))
        else:
            print(f"  ❌ Embeddings failed: {r.status_code}")
            results["rag_search"] = 0
            results["all_pass"] = False
            stage.add_check(CheckResult(
                name="embeddings_test",
                passed=False, score=0, level=ScoreLevel.FAIL,
                details=f"Embeddings returned {r.status_code}"
            ))
    except Exception as e:
        print(f"  ❌ Embeddings failed: {e}")
        results["rag_search"] = 0
        results["all_pass"] = False
        stage.add_check(CheckResult(
            name="embeddings_test",
            passed=False, score=0, level=ScoreLevel.FAIL,
            details=f"Embeddings exception: {e}"
        ))
    print()
    
    # 3. Test KG Query
    print("KNOWLEDGE GRAPH TEST:")
    try:
        r = requests.post(
            "http://localhost:8101/query",
            json={"question": "What factors affect Qatar financial sector?", "max_results": 5},
            timeout=30
        )
        if r.status_code == 200:
            data = r.json()
            results_count = len(data.get("results", []))
            print(f"  ✅ KG returned {results_count} results")
            results["kg_chains"] = results_count
            stage.add_check(CheckResult(
                name="kg_query_test",
                passed=True, score=100, level=ScoreLevel.PASS,
                details=f"KG returned {results_count} results"
            ))
        else:
            print(f"  ❌ KG query failed: {r.status_code}")
            results["kg_chains"] = 0
            results["all_pass"] = False
            stage.add_check(CheckResult(
                name="kg_query_test",
                passed=False, score=0, level=ScoreLevel.FAIL,
                details=f"KG returned {r.status_code}"
            ))
    except Exception as e:
        print(f"  ❌ KG query failed: {e}")
        results["kg_chains"] = 0
        results["all_pass"] = False
        stage.add_check(CheckResult(
            name="kg_query_test",
            passed=False, score=0, level=ScoreLevel.FAIL,
            details=f"KG exception: {e}"
        ))
    print()
    
    # 4. Test Verification
    print("VERIFICATION SERVICE TEST:")
    try:
        r = requests.post(
            "http://localhost:8102/verify",
            json={
                "claim": "Qatar's GDP is approximately $180 billion",
                "evidence": "Qatar has a GDP of around 180 billion USD"
            },
            timeout=30
        )
        if r.status_code == 200:
            data = r.json()
            score = data.get("score", 0)
            print(f"  ✅ Verification working (score: {score:.3f})")
            results["verification_score"] = score
            stage.add_check(CheckResult(
                name="verification_test",
                passed=True, score=100, level=ScoreLevel.PASS,
                details=f"Verification working, score={score:.3f}"
            ))
        else:
            print(f"  ❌ Verification failed: {r.status_code}")
            results["verification_score"] = 0
            results["all_pass"] = False
            stage.add_check(CheckResult(
                name="verification_test",
                passed=False, score=0, level=ScoreLevel.FAIL,
                details=f"Verification returned {r.status_code}"
            ))
    except Exception as e:
        print(f"  ❌ Verification failed: {e}")
        results["verification_score"] = 0
        results["all_pass"] = False
        stage.add_check(CheckResult(
            name="verification_test",
            passed=False, score=0, level=ScoreLevel.FAIL,
            details=f"Verification exception: {e}"
        ))
    print()
    
    # 5. Test DeepSeek Instances (with retry to prevent false failures)
    print("DEEPSEEK INSTANCES:")
    healthy = 0
    for i in range(8):
        port = 8001 + i
        instance_ok = False
        last_error = ""
        
        # Retry up to 3 times with 30s timeout each
        for attempt in range(3):
            try:
                r = requests.get(f"http://localhost:{port}/health", timeout=30)
                data = r.json()
                mem = data.get("gpu_memory_gb", 0)
                print(f"  ✅ Instance {i+1} (GPU {i}, port {port}): {mem:.1f}GB")
                healthy += 1
                instance_ok = True
                break
            except Exception as e:
                last_error = str(e)[:50]
                if attempt < 2:
                    time.sleep(2)  # Wait 2s before retry
        
        if not instance_ok:
            print(f"  ❌ Instance {i+1} (GPU {i}, port {port}): FAILED after 3 attempts - {last_error}")
    results["deepseek_healthy"] = healthy
    if healthy < 8:
        results["all_pass"] = False
    
    stage.add_check(CheckResult(
        name="deepseek_instances",
        passed=healthy == 8,
        score=healthy / 8 * 100,
        level=ScoreLevel.PASS if healthy == 8 else ScoreLevel.WARN if healthy >= 4 else ScoreLevel.FAIL,
        details=f"{healthy}/8 DeepSeek instances healthy"
    ))
    print()
    
    # 6. Test DeepSeek Inference
    print("DEEPSEEK INFERENCE TEST:")
    try:
        r = requests.post(
            "http://localhost:8001/v1/chat/completions",
            json={
                "model": "deepseek",
                "messages": [{"role": "user", "content": "Say 'test passed' in 5 words or less."}],
                "max_tokens": 20,
                "temperature": 0.1,
            },
            timeout=60
        )
        if r.status_code == 200:
            data = r.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            tps = data.get("tokens_per_second", 0)
            print(f"  ✅ Inference working: '{content[:50]}' ({tps:.1f} tok/s)")
            results["deepseek_inference"] = True
            stage.add_check(CheckResult(
                name="deepseek_inference",
                passed=True, score=100, level=ScoreLevel.PASS,
                details=f"Inference working at {tps:.1f} tok/s"
            ))
        else:
            print(f"  ❌ Inference failed: {r.status_code}")
            results["deepseek_inference"] = False
            results["all_pass"] = False
            stage.add_check(CheckResult(
                name="deepseek_inference",
                passed=False, score=0, level=ScoreLevel.FAIL,
                details=f"Inference returned {r.status_code}"
            ))
    except Exception as e:
        print(f"  ❌ Inference failed: {e}")
        results["deepseek_inference"] = False
        results["all_pass"] = False
        stage.add_check(CheckResult(
            name="deepseek_inference",
            passed=False, score=0, level=ScoreLevel.FAIL,
            details=f"Inference exception: {e}"
        ))
    print()
    
    # Summary
    print("=" * 70)
    if results["all_pass"]:
        print("✅ ALL DATA FLOW CHECKS PASSED - READY FOR FULL TEST")
    else:
        print("❌ SOME CHECKS FAILED - FIX BEFORE PROCEEDING")
    print("=" * 70)
    print()
    
    results["stage_result"] = stage
    return results


# =============================================================================
# QUALITY EVALUATION FUNCTIONS
# =============================================================================

def evaluate_debate_quality(content: str, scenario_name: str, transcript_dir: str = None) -> dict:
    """
    Evaluate the quality of a debate/analysis.
    
    FIX 7: Now reads full transcripts if available for more accurate evaluation.
    
    Args:
        content: Content to evaluate (may be truncated)
        scenario_name: Name of the scenario
        transcript_dir: Optional directory containing full transcript files
        
    Returns:
        Dictionary with quality metrics
    """
    metrics = {
        "on_topic": False,
        "has_thinking": False,
        "citation_count": 0,
        "challenge_count": 0,
        "data_references": 0,
        "word_count": 0,
        "has_phases": False,
        "phase_list": [],
    }
    
    # FIX 7: Try to read full transcript if available
    if transcript_dir and scenario_name:
        safe_name = re.sub(r'[^\w\-]', '_', scenario_name)[:50]
        for subdir in ['engine_a', 'engine_b']:
            transcript_path = os.path.join(transcript_dir, subdir, f"{safe_name}.txt")
            if os.path.exists(transcript_path):
                try:
                    with open(transcript_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    break
                except Exception:
                    pass
    
    if not content:
        return metrics
    
    content_lower = content.lower()
    metrics["word_count"] = len(content.split())
    
    # Check if on-topic
    topic_keywords = ["financial", "logistics", "hub", "qatar", "diversification", "economic",
                      "healthcare", "education", "energy", "housing", "food", "tourism", "labor"]
    topic_hits = sum(1 for kw in topic_keywords if kw in content_lower)
    metrics["on_topic"] = topic_hits >= 2
    
    # Check for <think> blocks
    metrics["has_thinking"] = "<think>" in content or "step 1:" in content_lower
    
    # Count citations
    metrics["citation_count"] = len(re.findall(r'\[per extraction|source:|citation:|data shows', content_lower))
    
    # Count challenges
    challenge_patterns = [r'however', r'i disagree', r'challenge', r'but ', r'contrary', r'on the other hand']
    metrics["challenge_count"] = sum(len(re.findall(p, content_lower)) for p in challenge_patterns)
    
    # Count data references
    data_patterns = [r'\d+%', r'\$\d+', r'\d+ billion', r'\d+ million', r'gdp', r'growth rate']
    metrics["data_references"] = sum(len(re.findall(p, content_lower)) for p in data_patterns)
    
    # Check for debate phases
    phases = []
    if "opening" in content_lower or "initial" in content_lower:
        phases.append("opening")
    if "challenge" in content_lower or "disagree" in content_lower or "however" in content_lower:
        phases.append("challenge")
    if "risk" in content_lower:
        phases.append("risk")
    if "consensus" in content_lower or "agree" in content_lower or "conclusion" in content_lower:
        phases.append("consensus")
    
    metrics["has_phases"] = len(phases) >= 2
    metrics["phase_list"] = phases
    
    return metrics


def check_zero_fabrication(all_results: list) -> dict:
    """Check for fabrication - all numbers must be cited."""
    metrics = {
        "citations_found": 0,
        "uncited_numbers": 0,
        "fabrication_rate": 0.0,
        "sample_issues": [],
    }
    
    for r in all_results:
        content = r.get("final_content", "") or ""
        content_lower = content.lower()
        
        citations = len(re.findall(r'\[per extraction|source:|citation:|data shows|\[qsa|\[imf|\[world bank', content_lower))
        metrics["citations_found"] += citations
        
        numbers = re.findall(r'\b\d+(?:\.\d+)?(?:%| billion| million| percent)\b', content_lower)
        for num in numbers:
            idx = content_lower.find(num)
            if idx >= 0:
                context = content_lower[max(0, idx-100):idx+100]
                if not re.search(r'\[per extraction|source:|citation:', context):
                    metrics["uncited_numbers"] += 1
                    if len(metrics["sample_issues"]) < 5:
                        metrics["sample_issues"].append(f"Uncited: '{num}' in {r.get('scenario_name', 'unknown')[:30]}")
    
    total = metrics["citations_found"] + metrics["uncited_numbers"]
    if total > 0:
        metrics["fabrication_rate"] = (metrics["uncited_numbers"] / total) * 100
    
    return metrics


def check_qatar_specificity(all_results: list) -> dict:
    """Check for Qatar-specific content."""
    qatar_institutions = {
        "qia": "Qatar Investment Authority",
        "qfc": "Qatar Financial Centre",
        "qfza": "Qatar Free Zones Authority",
        "qnb": "QNB Bank",
        "qcb": "Qatar Central Bank",
        "hamad port": "Hamad Port",
        "qatar airways": "Qatar Airways",
        "vision 2030": "Vision 2030",
        "nds": "National Development Strategy",
        "ashghal": "Ashghal",
        "kahramaa": "Kahramaa",
        "ooredoo": "Ooredoo",
        "qatar university": "Qatar University",
        "qatarization": "Qatarization",
        "psa": "Planning and Statistics Authority",
    }
    
    metrics = {
        "institutions_found": [],
        "institution_count": 0,
        "qatar_data_used": False,
        "competitors_mentioned": [],
        "is_qatar_specific": False,
    }
    
    all_content = " ".join([r.get("final_content", "") or "" for r in all_results]).lower()
    
    for key, name in qatar_institutions.items():
        if key in all_content:
            metrics["institutions_found"].append(name)
    
    metrics["institution_count"] = len(metrics["institutions_found"])
    metrics["is_qatar_specific"] = metrics["institution_count"] >= 5
    
    competitors = ["dubai", "uae", "saudi", "singapore", "difc", "adgm", "neom"]
    for comp in competitors:
        if comp in all_content:
            metrics["competitors_mentioned"].append(comp)
    
    metrics["qatar_data_used"] = "qatar gdp" in all_content or "qatari" in all_content
    
    return metrics


def check_cross_validation(engine_a_results: list, engine_b_results: list) -> dict:
    """
    Check agreement between Engine A and Engine B.
    
    FIX 8: Improved parsing to look for explicit RECOMMENDATION sections,
    not just word frequency.
    """
    metrics = {
        "both_recommend_same": False,
        "confidence_difference": 0.0,
        "engine_a_recommendation": "unclear",
        "engine_b_recommendation": "unclear",
        "engine_a_confidence": 0.0,
        "engine_b_confidence": 0.0,
    }
    
    def extract_recommendation(results: list) -> str:
        """
        FIX 8: Extract recommendation from RECOMMENDATION section, not word frequency.
        """
        for r in results:
            content = (r.get("final_content", "") or "").lower()
            
            # Look for explicit recommendation section
            rec_patterns = [
                r'recommendation[:\s]+(?:prioritize\s+)?option\s+([ab])',
                r'recommend[:\s]+(?:prioritize\s+)?option\s+([ab])',
                r'prioritize\s+option\s+([ab])',
                r'verdict[:\s]+option\s+([ab])',
                r'should\s+(?:choose|select|prioritize)\s+option\s+([ab])',
            ]
            
            for pattern in rec_patterns:
                match = re.search(pattern, content)
                if match:
                    option = match.group(1).lower()
                    return 'financial' if option == 'a' else 'logistics'
            
            # Fallback: Look for explicit statements
            if 'recommend' in content or 'prioritize' in content or 'should choose' in content:
                # Find the recommendation context (50 chars before/after keyword)
                for keyword in ['recommend', 'prioritize', 'should choose']:
                    idx = content.find(keyword)
                    if idx >= 0:
                        context = content[max(0, idx-50):min(len(content), idx+100)]
                        if 'financial' in context or 'option a' in context:
                            return 'financial'
                        elif 'logistics' in context or 'option b' in context:
                            return 'logistics'
        
        # Last resort: word frequency
        financial_count = sum(
            (r.get("final_content", "") or "").lower().count("financial hub") +
            (r.get("final_content", "") or "").lower().count("financial centre")
            for r in results
        )
        logistics_count = sum(
            (r.get("final_content", "") or "").lower().count("logistics hub") +
            (r.get("final_content", "") or "").lower().count("logistics centre")
            for r in results
        )
        
        if financial_count > logistics_count:
            return 'financial'
        elif logistics_count > financial_count:
            return 'logistics'
        return 'unclear'
    
    a_rec = extract_recommendation(engine_a_results)
    b_rec = extract_recommendation(engine_b_results)
    
    metrics["engine_a_recommendation"] = a_rec
    metrics["engine_b_recommendation"] = b_rec
    metrics["both_recommend_same"] = a_rec == b_rec and a_rec != "unclear"
    
    a_conf = sum(r.get("confidence", 0) for r in engine_a_results) / max(len(engine_a_results), 1)
    b_conf = sum(r.get("confidence", 0) for r in engine_b_results) / max(len(engine_b_results), 1)
    metrics["confidence_difference"] = abs(a_conf - b_conf)
    metrics["engine_a_confidence"] = a_conf
    metrics["engine_b_confidence"] = b_conf
    
    return metrics


def check_mckinsey_compliance(all_results: list, synthesis: dict) -> Tuple[StageResult, dict]:
    """Evaluate McKinsey-grade compliance."""
    stage = StageResult(stage_name="mckinsey_compliance")
    checklist = {}
    
    all_content = " ".join([r.get("final_content", "") or "" for r in all_results]).lower()
    synth_content = str(synthesis).lower()
    
    # Check 1: NPV present
    has_npv = "npv" in all_content or "net present value" in all_content
    checklist["npv_in_output"] = has_npv
    stage.add_check(CheckResult(
        name="npv_in_output", passed=has_npv,
        score=100 if has_npv else 0, level=ScoreLevel.PASS if has_npv else ScoreLevel.FAIL,
        details="NPV mentioned" if has_npv else "NPV not found"
    ))
    
    # Check 2: IRR present
    has_irr = "irr" in all_content or "internal rate" in all_content
    checklist["irr_in_output"] = has_irr
    stage.add_check(CheckResult(
        name="irr_in_output", passed=has_irr,
        score=100 if has_irr else 0, level=ScoreLevel.PASS if has_irr else ScoreLevel.FAIL,
        details="IRR mentioned" if has_irr else "IRR not found"
    ))
    
    # Check 3: Sensitivity analysis
    has_sensitivity = any(w in all_content for w in ["sensitivity", "scenario", "worst case", "best case"])
    checklist["sensitivity_in_output"] = has_sensitivity
    stage.add_check(CheckResult(
        name="sensitivity_in_output", passed=has_sensitivity,
        score=100 if has_sensitivity else 0, level=ScoreLevel.PASS if has_sensitivity else ScoreLevel.FAIL,
        details="Sensitivity analysis present" if has_sensitivity else "No sensitivity analysis"
    ))
    
    # Check 4: Confidence level stated
    has_confidence = "confidence" in all_content or re.search(r'\d{1,2}%\s*confidence', all_content)
    checklist["confidence_stated"] = has_confidence
    stage.add_check(CheckResult(
        name="confidence_stated", passed=has_confidence,
        score=100 if has_confidence else 50, level=ScoreLevel.PASS if has_confidence else ScoreLevel.WARN,
        details="Confidence level stated" if has_confidence else "No confidence level"
    ))
    
    # Check 5: Tables present
    has_tables = "|" in all_content and "---" in all_content
    checklist["tables_present"] = has_tables
    stage.add_check(CheckResult(
        name="tables_present", passed=has_tables,
        score=100 if has_tables else 30, level=ScoreLevel.PASS if has_tables else ScoreLevel.WARN,
        details="Tables in output" if has_tables else "No tables found"
    ))
    
    # Check 6: No vague estimates
    vague_patterns = [r'\d{1,2}-\d{1,2}%', r'approximately \d+', r'around \d+', r'roughly \d+']
    has_vague = any(re.search(p, all_content) for p in vague_patterns)
    checklist["no_vague_estimates"] = not has_vague
    stage.add_check(CheckResult(
        name="no_vague_estimates", passed=not has_vague,
        score=100 if not has_vague else 50, level=ScoreLevel.PASS if not has_vague else ScoreLevel.WARN,
        details="No vague estimates" if not has_vague else "Contains vague estimates"
    ))
    
    return stage, checklist


def get_grade(overall_score: float, mckinsey_compliant: bool) -> str:
    """Get overall grade based on score."""
    if overall_score >= 90 and mckinsey_compliant:
        return "🏆 LEGENDARY: McKinsey-grade system fully operational!"
    elif overall_score >= 80:
        return "✅ EXCELLENT: System performing at high level"
    elif overall_score >= 70:
        return "👍 GOOD: Core functionality working, some improvements needed"
    elif overall_score >= 50:
        return "⚠️ FAIR: Significant gaps identified, see recommendations"
    else:
        return "❌ NEEDS WORK: Major issues to address"


# =============================================================================
# MAIN E2E TEST FUNCTION
# =============================================================================

async def run_full_e2e_test(query_key: str = "economic_diversification") -> dict:
    """Run complete NSIC end-to-end test with comprehensive evaluation."""
    
    query_info = TEST_QUERIES.get(query_key)
    if not query_info:
        print(f"❌ Unknown query key: {query_key}")
        return {"success": False, "error": f"Unknown query: {query_key}"}
    
    question = query_info["query"]
    query_name = query_info["name"]
    query_domain = query_info["domain"]
    expected_complexity = query_info["complexity"]
    
    print("=" * 70)
    print("NSIC FULL END-TO-END TEST WITH MCKINSEY-GRADE EVALUATION")
    print("=" * 70)
    print()
    print(f"QUERY: {query_name}")
    print(f"DOMAIN: {query_domain}")
    print(f"COMPLEXITY: {expected_complexity}")
    print()
    
    # Initialize stages tracking
    all_stages: Dict[str, StageResult] = {}
    
    # Initialize comprehensive debate logger - logs ALL turns to files
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs", "debates")
    debate_logger = DebateStreamLogger(output_dir, question=question)
    
    # =========================================================================
    # STEP 0: VERIFY DATA FLOW
    # =========================================================================
    data_flow_results = verify_data_flow_services()
    all_stages["data_flow"] = data_flow_results.get("stage_result", StageResult(stage_name="data_flow"))
    
    if not data_flow_results["all_pass"]:
        print("⚠️  WARNING: Some data flow checks failed!")
        print("    Proceeding anyway, but results may be incomplete.")
        print()
    
    # =========================================================================
    # ENGINE INFO
    # =========================================================================
    print("ENGINE A - QNWIS 12-Agent Workflow:")
    print("  • 5 LLM Debating Agents:")
    print("    - Dr. Ahmed (MicroEconomist)")
    print("    - Dr. Sarah (MacroEconomist)")
    print("    - Dr. Mohammed (Nationalization)")
    print("    - Dr. Layla (SkillsAgent)")
    print("    - PatternDetective")
    print()
    print("ENGINE B - ExLlamaV2 on 8 GPUs:")
    print("  • 3 Rotating Agents: Dr. Rashid, Dr. Noor, Dr. Hassan")
    print("  • 24 scenarios across 8 GPUs (3 per GPU)")
    print()
    
    # Import components
    from src.nsic.orchestration import create_dual_engine_orchestrator, reset_timing_logger
    
    reset_timing_logger()
    
    print("[1/5] Creating orchestrator...")
    orchestrator = create_dual_engine_orchestrator()
    
    health = orchestrator.health_check()
    print(f"  Orchestrator: {health['orchestrator']}")
    print(f"  Engine B (DeepSeek): {health['engine_b']['deepseek']['status']}")
    
    if orchestrator.llm_client:
        print(f"  Engine A (Azure): available")
    else:
        print(f"  Engine A (Azure): NOT AVAILABLE")
    print()
    
    print("[2/5] Test Question:")
    print(f"  '{question[:100]}...'")
    print()
    
    # =========================================================================
    # RUN PIPELINE WITH LIVE STREAMING
    # =========================================================================
    print("[3/5] Running process_question() - FULL PIPELINE WITH LIVE OUTPUT...")
    print("=" * 70)
    print()
    print("LIVE DEBATE PROGRESS:")
    print("-" * 50)
    
    start_time = time.time()
    
    try:
        # Connect live streaming callback to orchestrator
        result = await orchestrator.process_question(
            user_question=question,
            max_concurrent=6,
            use_cache=False,
            on_turn_complete=debate_logger.log_turn,  # LIVE STREAMING!
        )
        
        total_time = time.time() - start_time
        
        engine_a_results = result.get("engine_a_results", [])
        engine_b_results = result.get("engine_b_results", [])
        synthesis = result.get("synthesis", {})
        stats = result.get("stats", {})
        
        # =====================================================================
        # TURN COUNT VERIFICATION
        # =====================================================================
        print()
        print("=" * 70)
        print("[4/5] TURN COUNT VERIFICATION")
        print("=" * 70)
        print()
        
        # Engine A verification
        print("ENGINE A TURN VERIFICATION:")
        engine_a_stage = StageResult(stage_name="engine_a_execution")
        engine_a_total_turns = 0
        engine_a_total_time_ms = 0
        
        expected_turns_a = 100 if expected_complexity == "complex" else 50
        
        for i, r in enumerate(engine_a_results):
            turns = r.get("turns_completed", 1)
            time_ms = r.get("total_time_ms", 0)
            scenario_name = r.get("scenario_name", "unknown")
            engine_a_total_turns += turns
            engine_a_total_time_ms += time_ms
            
            turn_ok = turns >= expected_turns_a * 0.8
            status = "✅" if turn_ok else "❌"
            print(f"  Scenario {i+1}: {turns} turns {status} (expected: {expected_turns_a})")
            
            # Log scenario completion for transcripts
            debate_logger.log_scenario_complete(
                "A", r.get("scenario_id", f"a_{i}"), scenario_name,
                turns, expected_turns_a
            )
        
        print(f"  TOTAL: {engine_a_total_turns} turns")
        
        a_turn_score = min(100, engine_a_total_turns / (len(engine_a_results) * expected_turns_a * 0.8) * 100)
        engine_a_stage.add_check(CheckResult(
            name="turn_count", passed=a_turn_score >= 80,
            score=a_turn_score, level=ScoreLevel.PASS if a_turn_score >= 80 else ScoreLevel.WARN,
            details=f"{engine_a_total_turns} total turns across {len(engine_a_results)} scenarios"
        ))
        all_stages["engine_a_execution"] = engine_a_stage
        print()
        
        # Engine B verification
        print("ENGINE B TURN VERIFICATION:")
        engine_b_stage = StageResult(stage_name="engine_b_execution")
        engine_b_total_turns = 0
        engine_b_total_time_ms = 0
        
        expected_turns_b = 25
        
        for i, r in enumerate(engine_b_results):
            eb_result = r.get("engine_b_result", {}) or {}
            
            # FIX: Use turns_count (the actual count) not len(turns) (just samples)
            if isinstance(eb_result, dict):
                turns = eb_result.get("turns_count", 0)
            else:
                turns = len(getattr(eb_result, 'turns', [])) if eb_result else 0
            
            time_ms = r.get("total_time_ms", 0)
            scenario_name = r.get("scenario_name", "unknown")
            engine_b_total_turns += turns
            engine_b_total_time_ms += time_ms
            
            turn_ok = turns >= expected_turns_b * 0.8
            status = "✅" if turn_ok else "❌"
            gpu_id = i % 8
            if i < 10:  # Only show first 10
                print(f"  GPU {gpu_id} - Scenario {i+1}: {turns} turns {status} (expected: {expected_turns_b})")
            
            debate_logger.log_scenario_complete(
                "B", r.get("scenario_id", f"b_{i}"), scenario_name,
                turns, expected_turns_b, gpu_id
            )
        
        if len(engine_b_results) > 10:
            print(f"  ... and {len(engine_b_results) - 10} more scenarios")
        print(f"  TOTAL: {engine_b_total_turns} turns")
        
        b_turn_score = min(100, engine_b_total_turns / (len(engine_b_results) * expected_turns_b * 0.8) * 100) if engine_b_results else 0
        engine_b_stage.add_check(CheckResult(
            name="turn_count", passed=b_turn_score >= 80,
            score=b_turn_score, level=ScoreLevel.PASS if b_turn_score >= 80 else ScoreLevel.WARN,
            details=f"{engine_b_total_turns} total turns across {len(engine_b_results)} scenarios"
        ))
        all_stages["engine_b_execution"] = engine_b_stage
        print()
        
        # Grand total
        grand_total = engine_a_total_turns + engine_b_total_turns
        print(f"GRAND TOTAL: {grand_total} turns")
        print()
        
        # =====================================================================
        # TIMING SANITY CHECK
        # =====================================================================
        print("TIMING SANITY CHECK:")
        print("-" * 50)
        
        a_sec_per_turn = (engine_a_total_time_ms / 1000) / max(engine_a_total_turns, 1)
        b_sec_per_turn = (engine_b_total_time_ms / 1000) / max(engine_b_total_turns, 1)
        
        a_timing_ok = a_sec_per_turn >= 0.5 or engine_a_total_turns == 0
        b_timing_ok = b_sec_per_turn >= 0.3 or engine_b_total_turns == 0  # Parallel is faster
        
        print(f"  Engine A: {engine_a_total_time_ms/1000:.1f}s for {engine_a_total_turns} turns = {a_sec_per_turn:.2f}s/turn {'✅' if a_timing_ok else '⚠️ SUSPICIOUS'}")
        print(f"  Engine B: {engine_b_total_time_ms/1000:.1f}s for {engine_b_total_turns} turns = {b_sec_per_turn:.2f}s/turn {'✅' if b_timing_ok else '⚠️ SUSPICIOUS'}")
        print(f"  Wall clock: {total_time:.1f}s ({total_time/60:.1f} min)")
        print()
        
        if not a_timing_ok or not b_timing_ok:
            print("  ⚠️  TIMING WARNING: Some operations completed suspiciously fast!")
            print("      This could indicate mocked data or skipped turns.")
        print()
        
        # =====================================================================
        # QUALITY EVALUATION
        # =====================================================================
        print("=" * 70)
        print("QUALITY EVALUATION")
        print("=" * 70)
        print()
        
        all_results = engine_a_results + engine_b_results
        
        # Debate Quality
        print("DEBATE QUALITY:")
        print("-" * 50)
        debate_stage = StageResult(stage_name="debate_quality")
        
        total_on_topic = 0
        total_thinking = 0
        total_citations = 0
        total_challenges = 0
        total_data_refs = 0
        total_words = 0
        all_phases = set()
        
        for r in all_results:
            content = r.get("final_content", "") or ""
            m = evaluate_debate_quality(content, r.get("scenario_name", ""))
            if m["on_topic"]:
                total_on_topic += 1
            if m["has_thinking"]:
                total_thinking += 1
            total_citations += m["citation_count"]
            total_challenges += m["challenge_count"]
            total_data_refs += m["data_references"]
            total_words += m["word_count"]
            all_phases.update(m["phase_list"])
        
        on_topic_pct = total_on_topic / max(len(all_results), 1) * 100
        thinking_pct = total_thinking / max(len(all_results), 1) * 100
        
        print(f"  On-topic scenarios: {total_on_topic}/{len(all_results)} ({on_topic_pct:.0f}%)")
        print(f"  Chain-of-thought (<think>): {total_thinking}/{len(all_results)} ({thinking_pct:.0f}%)")
        print(f"  Total citations: {total_citations}")
        print(f"  Challenge instances: {total_challenges}")
        print(f"  Data references: {total_data_refs}")
        print(f"  Total words: {total_words:,}")
        print(f"  Debate phases found: {', '.join(all_phases) if all_phases else 'None'}")
        
        debate_stage.add_check(CheckResult(
            name="on_topic", passed=on_topic_pct >= 70,
            score=on_topic_pct, level=ScoreLevel.PASS if on_topic_pct >= 70 else ScoreLevel.WARN,
            details=f"{on_topic_pct:.0f}% on-topic"
        ))
        debate_stage.add_check(CheckResult(
            name="citations", passed=total_citations >= 10,
            score=min(100, total_citations * 5), level=ScoreLevel.PASS if total_citations >= 10 else ScoreLevel.WARN,
            details=f"{total_citations} citations"
        ))
        debate_stage.add_check(CheckResult(
            name="challenges", passed=total_challenges >= 5,
            score=min(100, total_challenges * 10), level=ScoreLevel.PASS if total_challenges >= 5 else ScoreLevel.WARN,
            details=f"{total_challenges} challenges"
        ))
        debate_stage.add_check(CheckResult(
            name="phases", passed=len(all_phases) >= 3,
            score=len(all_phases) / 4 * 100, level=ScoreLevel.PASS if len(all_phases) >= 3 else ScoreLevel.WARN,
            details=f"Phases: {', '.join(all_phases)}"
        ))
        
        all_stages["debate_quality"] = debate_stage
        print()
        
        # Zero Fabrication
        print("ZERO FABRICATION CHECK:")
        print("-" * 50)
        fab_stage = StageResult(stage_name="zero_fabrication")
        fabrication = check_zero_fabrication(all_results)
        
        print(f"  Citations found: {fabrication['citations_found']}")
        print(f"  Uncited numbers: {fabrication['uncited_numbers']}")
        print(f"  Fabrication rate: {fabrication['fabrication_rate']:.1f}%")
        
        fab_pass = fabrication['fabrication_rate'] < 20
        fab_stage.add_check(CheckResult(
            name="fabrication_rate", passed=fab_pass,
            score=100 - fabrication['fabrication_rate'], level=ScoreLevel.PASS if fab_pass else ScoreLevel.FAIL,
            details=f"{fabrication['fabrication_rate']:.1f}% fabrication rate"
        ))
        all_stages["zero_fabrication"] = fab_stage
        print(f"  Status: {'✅ PASS' if fab_pass else '❌ NEEDS IMPROVEMENT'}")
        print()
        
        # Qatar Specificity
        print("QATAR-SPECIFIC ACCURACY:")
        print("-" * 50)
        qatar_stage = StageResult(stage_name="qatar_specificity")
        qatar = check_qatar_specificity(all_results)
        
        print(f"  Qatar institutions found: {qatar['institution_count']}")
        if qatar['institutions_found']:
            print(f"    {', '.join(qatar['institutions_found'][:8])}")
        print(f"  Competitors mentioned: {', '.join(qatar['competitors_mentioned']) if qatar['competitors_mentioned'] else 'None'}")
        
        qatar_pass = qatar['institution_count'] >= 5
        qatar_stage.add_check(CheckResult(
            name="institution_count", passed=qatar_pass,
            score=min(100, qatar['institution_count'] * 10), level=ScoreLevel.PASS if qatar_pass else ScoreLevel.WARN,
            details=f"{qatar['institution_count']} Qatar institutions"
        ))
        all_stages["qatar_specificity"] = qatar_stage
        print(f"  Status: {'✅ QATAR-SPECIFIC' if qatar_pass else '❌ TOO GENERIC'}")
        print()
        
        # Cross Validation
        print("CROSS-VALIDATION (Engine A vs B):")
        print("-" * 50)
        cross_stage = StageResult(stage_name="cross_validation")
        cross_val = check_cross_validation(engine_a_results, engine_b_results)
        
        print(f"  Engine A recommendation: {cross_val['engine_a_recommendation']}")
        print(f"  Engine B recommendation: {cross_val['engine_b_recommendation']}")
        print(f"  Engines agree: {'✅ YES' if cross_val['both_recommend_same'] else '⚠️ DIVERGENT'}")
        
        cross_stage.add_check(CheckResult(
            name="agreement", passed=cross_val['both_recommend_same'],
            score=100 if cross_val['both_recommend_same'] else 50, 
            level=ScoreLevel.PASS if cross_val['both_recommend_same'] else ScoreLevel.WARN,
            details=f"A={cross_val['engine_a_recommendation']}, B={cross_val['engine_b_recommendation']}"
        ))
        all_stages["cross_validation"] = cross_stage
        print()
        
        # McKinsey Compliance
        print("MCKINSEY COMPLIANCE CHECKLIST:")
        print("-" * 50)
        mckinsey_stage, checklist = check_mckinsey_compliance(all_results, synthesis)
        all_stages["mckinsey_compliance"] = mckinsey_stage
        
        for item, passed in checklist.items():
            icon = "✅" if passed else "❌"
            print(f"  [{icon}] {item.replace('_', ' ').title()}")
        
        mckinsey_score = sum(1 for v in checklist.values() if v) / len(checklist) * 100
        mckinsey_compliant = mckinsey_score >= 70
        print(f"\n  McKinsey compliance: {mckinsey_score:.0f}%")
        print()
        
        # =====================================================================
        # CALCULATE OVERALL SCORE
        # =====================================================================
        print("=" * 70)
        print("OVERALL SCORING")
        print("=" * 70)
        print()
        
        weighted_score = 0.0
        total_weight = 0.0
        
        print(f"  {'Stage':<25} {'Score':<10} {'Level':<10} {'Weight':<10}")
        print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10}")
        
        for stage_name, weight in STAGE_WEIGHTS.items():
            if stage_name in all_stages:
                stage = all_stages[stage_name]
                weighted_score += stage.overall_score * weight
                total_weight += weight
                print(f"  {stage_name:<25} {stage.overall_score:>6.1f}    {stage.overall_level.value:<10} {weight*100:>6.0f}%")
        
        overall_score = weighted_score / total_weight if total_weight > 0 else 0
        
        print(f"\n  {'OVERALL SCORE':<25} {overall_score:>6.1f}")
        print()
        
        grade = get_grade(overall_score, mckinsey_compliant)
        print(f"  {grade}")
        print()
        
        # =====================================================================
        # SAMPLE DEBATE TRANSCRIPTS
        # =====================================================================
        print("=" * 70)
        print("SAMPLE DEBATE TRANSCRIPTS")
        print("=" * 70)
        print()
        
        # Engine A sample
        print("ENGINE A - SAMPLE SCENARIO TRANSCRIPT:")
        print("-" * 50)
        if engine_a_results:
            sample = engine_a_results[0]
            print(f"Scenario: {sample.get('scenario_name', 'unknown')}")
            print(f"Turns: {sample.get('turns_completed', 0)}")
            content = sample.get("final_content", "")
            if content:
                # Show first 1000 chars
                print(f"\nSYNTHESIS:\n{content[:1000]}...")
                if len(content) > 1000:
                    print(f"\n[... {len(content) - 1000} more characters ...]")
            else:
                print("[No synthesis content available]")
            
            # Show debate results if available
            debate = sample.get("engine_a_result", {}) or {}
            if isinstance(debate, dict):
                debate_results = debate.get("debate_results", {})
                if isinstance(debate_results, dict) and debate_results:
                    print(f"\nDebate: {debate_results.get('total_turns', 0)} turns")
        print()
        
        # Engine B sample
        print("ENGINE B - SAMPLE SCENARIO TRANSCRIPT:")
        print("-" * 50)
        if engine_b_results:
            sample = engine_b_results[0]
            print(f"Scenario: {sample.get('scenario_name', 'unknown')}")
            
            # Get content from final_content or fallback to engine_b_result
            content = sample.get("final_content", "")
            eb_result = sample.get("engine_b_result", {}) or {}
            
            if not content and isinstance(eb_result, dict):
                content = eb_result.get("final_synthesis", "")
            
            # Show turn count
            turns_count = 0
            if isinstance(eb_result, dict):
                turns_count = eb_result.get("turns_count", 0)
            print(f"Turns: {turns_count}")
            
            if content:
                print(f"\nSYNTHESIS:\n{content[:1000]}...")
                if len(content) > 1000:
                    print(f"\n[... {len(content) - 1000} more characters ...]")
            else:
                print("[No synthesis content available]")
            
            # Show sample turns if available
            if isinstance(eb_result, dict) and eb_result.get("turns"):
                print("\nSAMPLE TURNS:")
                for turn in eb_result["turns"][:2]:  # First 2 turns
                    if isinstance(turn, dict):
                        print(f"  Turn {turn.get('turn_number', '?')}: {turn.get('response_preview', '')[:200]}...")
        print()
        
        # =====================================================================
        # SAVE FULL REPORT
        # =====================================================================
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"e2e_evaluation_{query_key}_{timestamp}.json")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "query_key": query_key,
            "query_name": query_name,
            "query_domain": query_domain,
            "expected_complexity": expected_complexity,
            "overall_score": overall_score,
            "grade": grade,
            "mckinsey_compliant": mckinsey_compliant,
            "mckinsey_checklist": checklist,
            "stages": {
                name: {
                    "score": stage.overall_score,
                    "level": stage.overall_level.value,
                    "checks": [
                        {"name": c.name, "score": c.score, "level": c.level.value, "details": c.details}
                        for c in stage.checks
                    ]
                }
                for name, stage in all_stages.items()
            },
            "metrics": {
                "engine_a_scenarios": len(engine_a_results),
                "engine_b_scenarios": len(engine_b_results),
                "engine_a_turns": engine_a_total_turns,
                "engine_b_turns": engine_b_total_turns,
                "total_time_seconds": total_time,
                "fabrication_rate": fabrication['fabrication_rate'],
                "qatar_institutions": qatar['institution_count'],
                "cross_validation_agree": cross_val['both_recommend_same'],
            },
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📁 Report saved to: {output_file}")
        print()
        
        # =====================================================================
        # FINALIZE DEBATE LOGS - SAVE MASTER LOG
        # =====================================================================
        print("=" * 70)
        print("DEBATE LOG VERIFICATION")
        print("=" * 70)
        print()
        
        # Finalize debate logger - closes files and creates master log
        master_log = debate_logger.finalize()
        verification = debate_logger.get_verification_summary()
        
        print()
        print("DEBATE LOGGING SUMMARY:")
        print("-" * 50)
        print(f"  Engine A turns logged: {verification['engine_a_turns']}")
        print(f"  Engine B turns logged: {verification['engine_b_turns']}")
        print(f"  Total turns logged: {verification['total_turns']}")
        print(f"  Total words captured: {verification['total_words']:,}")
        print(f"  <think> blocks captured: {verification['think_blocks']}")
        print(f"  Transcript files created: {verification['files_created']}")
        print()
        
        # Verify turn counts match expectations
        expected_a = len(engine_a_results) * 100
        expected_b = len(engine_b_results) * 25
        log_match_a = verification['engine_a_turns'] >= expected_a * 0.8
        log_match_b = verification['engine_b_turns'] >= expected_b * 0.8
        
        print("TURN LOGGING VERIFICATION:")
        print(f"  Engine A: {verification['engine_a_turns']}/{expected_a} expected {'✅' if log_match_a else '❌'}")
        print(f"  Engine B: {verification['engine_b_turns']}/{expected_b} expected {'✅' if log_match_b else '❌'}")
        print()
        
        if master_log.get("verification", {}).get("suspicious_scenarios"):
            print("⚠️ SUSPICIOUS SCENARIOS (too fast):")
            for s in master_log["verification"]["suspicious_scenarios"][:5]:
                print(f"   - {s}")
            print()
        
        # =====================================================================
        # FINAL VERDICT
        # =====================================================================
        print("=" * 70)
        print("FINAL VERDICT")
        print("=" * 70)
        print()
        
        success = overall_score >= 50 and len(engine_a_results) >= 4 and len(engine_b_results) >= 20
        
        if success:
            print(f"  ✅ E2E TEST PASSED - Score: {overall_score:.1f}/100")
            print(f"  {grade}")
        else:
            print(f"  ❌ E2E TEST FAILED - Score: {overall_score:.1f}/100")
            if len(engine_a_results) < 4:
                print(f"     - Engine A: {len(engine_a_results)}/6 (need 4+)")
            if len(engine_b_results) < 20:
                print(f"     - Engine B: {len(engine_b_results)}/24 (need 20+)")
        
        print()
        
        return {
            "success": success,
            "overall_score": overall_score,
            "grade": grade,
            "mckinsey_compliant": mckinsey_compliant,
            "engine_a_completed": len(engine_a_results),
            "engine_b_completed": len(engine_b_results),
            "total_turns": grand_total,
            "turns_logged": verification['total_turns'],
            "words_captured": verification['total_words'],
            "total_time_minutes": total_time / 60,
            "output_file": output_file,
            "debate_log_dir": output_dir,
        }
        
    except Exception as e:
        total_time = time.time() - start_time
        print()
        print("=" * 70)
        print(f"❌ TEST FAILED WITH ERROR: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "error": str(e),
            "total_time_minutes": total_time / 60,
        }


# =============================================================================
# BATCH MODE
# =============================================================================

async def run_batch_diagnostic(query_keys: List[str]) -> Dict[str, Any]:
    """Run diagnostic for multiple queries and compare results."""
    results = {}
    
    print()
    print("=" * 70)
    print(f"BATCH DIAGNOSTIC - Running {len(query_keys)} queries")
    print("=" * 70)
    
    for i, query_key in enumerate(query_keys, 1):
        print()
        print("=" * 70)
        print(f"QUERY {i}/{len(query_keys)}: {query_key}")
        print("=" * 70)
        
        try:
            report = await run_full_e2e_test(query_key)
            results[query_key] = report
        except Exception as e:
            print(f"ERROR: Query '{query_key}' failed: {e}")
            results[query_key] = {"success": False, "error": str(e)}
    
    # Print batch summary
    print()
    print("=" * 70)
    print("BATCH SUMMARY")
    print("=" * 70)
    print()
    print(f"  {'Query':<25} {'Score':<10} {'McKinsey':<12} {'Turns':<10} {'Status':<10}")
    print(f"  {'-'*25} {'-'*10} {'-'*12} {'-'*10} {'-'*10}")
    
    total_score = 0
    successful = 0
    mckinsey_count = 0
    
    for query_key, report in results.items():
        if report.get("success"):
            successful += 1
            score = report.get("overall_score", 0)
            total_score += score
            mckinsey = report.get("mckinsey_compliant", False)
            if mckinsey:
                mckinsey_count += 1
            turns = report.get("total_turns", 0)
            status = "✅ PASS" if score >= 70 else "⚠️ WARN"
            print(f"  {query_key:<25} {score:>6.1f}    {'✅' if mckinsey else '❌':<12} {turns:>6}    {status}")
        else:
            print(f"  {query_key:<25} {'FAILED':<10} {'N/A':<12} {'N/A':<10} ❌ FAIL")
    
    print()
    if successful > 0:
        avg_score = total_score / successful
        print(f"  AVERAGE SCORE: {avg_score:.1f}/100")
        print(f"  McKinsey Compliant: {mckinsey_count}/{successful}")
        print(f"  Success Rate: {successful}/{len(results)}")
    
    print()
    
    return results


# =============================================================================
# CLI
# =============================================================================

def print_available_queries():
    """Print all available test queries."""
    print()
    print("=" * 70)
    print("AVAILABLE TEST QUERIES")
    print("=" * 70)
    print()
    print(f"  {'Key':<25} {'Name':<30} {'Domain':<20} {'Complexity':<10}")
    print(f"  {'-'*25} {'-'*30} {'-'*20} {'-'*10}")
    
    for key, query in TEST_QUERIES.items():
        print(f"  {key:<25} {query['name'][:28]:<30} {query['domain'][:18]:<20} {query['complexity']:<10}")
    
    print()
    print("USAGE:")
    print("  python test_full_e2e.py --query healthcare")
    print("  python test_full_e2e.py --batch")
    print("  python test_full_e2e.py --all-complex")
    print("  python test_full_e2e.py --random")
    print()


async def main():
    """Main entry point with CLI parsing."""
    parser = argparse.ArgumentParser(
        description="NSIC Full E2E Test with McKinsey-Grade Evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --query healthcare          Run healthcare domain test
  %(prog)s --batch                     Run all queries
  %(prog)s --all-complex               Run all complex queries only
  %(prog)s --list                      List available queries
  %(prog)s --random                    Run random query
        """
    )
    
    parser.add_argument("--query", "-q", type=str, default=None,
                       help="Specific query key (e.g., healthcare, education)")
    parser.add_argument("--batch", "-b", action="store_true",
                       help="Run all available queries")
    parser.add_argument("--all-complex", "-c", action="store_true",
                       help="Run all complex queries only")
    parser.add_argument("--list", "-l", action="store_true",
                       help="List all available test queries")
    parser.add_argument("--random", "-r", action="store_true",
                       help="Run a random query")
    
    args = parser.parse_args()
    
    if args.list:
        print_available_queries()
        return
    
    if args.random:
        query_key = random.choice(list(TEST_QUERIES.keys()))
        print(f"\n🎲 Randomly selected: {query_key}\n")
        result = await run_full_e2e_test(query_key)
        return result
    
    if args.batch:
        query_keys = list(TEST_QUERIES.keys())
        return await run_batch_diagnostic(query_keys)
    
    if args.all_complex:
        query_keys = [k for k, v in TEST_QUERIES.items() if v["complexity"] == "complex"]
        return await run_batch_diagnostic(query_keys)
    
    # Single query (default or specified)
    query_key = args.query or "economic_diversification"
    result = await run_full_e2e_test(query_key)
    return result


if __name__ == "__main__":
    print()
    print("Starting NSIC Full E2E Test with McKinsey-Grade Evaluation...")
    print()
    
    result = asyncio.run(main())
    
    if result:
        success = result.get("success", False) if isinstance(result, dict) else False
        if success:
            print("\n🎉 Test completed successfully!")
        else:
            print("\n💥 Test completed with issues - see report above")
        
        sys.exit(0 if success else 1)
