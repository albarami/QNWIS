#!/usr/bin/env python3
"""
Ultimate Strategic Council - Maximum Quality
Uses Latest Models (Nov 2025):
- Claude Opus 4.1 for expert agent analyses
- Claude Sonnet 4.5 Thinking for deep strategic reasoning
- GPT-5 for final synthesis
- Claude Haiku 4.5 for fast classification
"""

if __name__ != "__main__":
    # These are reference examples; not for import.
    raise ImportError(
        "references.orchestration_reference is a reference script and must not be imported."
    )

import asyncio
import os
from pathlib import Path
from typing import Any

import anthropic
import openai
from dotenv import load_dotenv

# Load environment variables from .env file
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

# Model configuration - LATEST & GREATEST (Nov 2025)
ULTIMATE_MODEL_CONFIG = {
    # Agent Analysis - Most powerful reasoning
    'agents': {
        'model': 'claude-opus-4-1',  # Correct format: dashes not dots
        'temperature': 0.3,
        'max_tokens': 8000
    },

    # Deep Thinking - Extended reasoning
    'strategic_thinking': {
        'model': 'claude-sonnet-4-5',  # Smartest model for complex reasoning
        'temperature': 0.3,
        'max_tokens': 32000  # Long-form reasoning
    },

    # Final Synthesis - Best reasoning available
    'synthesis': {
        'model': 'gpt-5',
        'temperature': 0.3,
        'max_tokens': 16000
    },

    # Quick classification/routing
    'classification': {
        'model': 'claude-haiku-4-5',  # Fastest with near-frontier intelligence
        'temperature': 0.0,
        'max_tokens': 500
    },

    # Embeddings
    'embeddings': {
        'model': 'text-embedding-3-large',
        'dimensions': 3072
    }
}


class UltimateStrategicCouncil:
    """
    Maximum quality multi-agent system
    No compromises on quality

    Architecture:
    1. Retrieve comprehensive data (30+ datasets)
    2. Run 4 expert agents in parallel (Claude Opus 4.1)
    3. Deep strategic reasoning (Sonnet 4.5 Thinking)
    4. Identify expert debates and contradictions
    5. Final synthesis (GPT-5)
    6. Generate CEO Decision Sheet
    """

    def __init__(self):
        """Initialize with API clients"""
        # Anthropic client for Claude models
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_key:
            # Extended timeout for Sonnet 4.5 Thinking (deep reasoning can take 5-10 min)
            self.anthropic = anthropic.Anthropic(
                api_key=anthropic_key,
                timeout=600.0  # 10 minutes
            )
            self.anthropic_available = True
        else:
            self.anthropic = None
            self.anthropic_available = False
            print("⚠️  ANTHROPIC_API_KEY not found - Claude models unavailable")

        # OpenAI client for GPT-5
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            self.openai_client = openai.OpenAI(api_key=openai_key)
            self.openai_available = True
        else:
            self.openai_client = None
            self.openai_available = False
            print("⚠️  OPENAI_API_KEY not found - GPT-5 unavailable")

        # Import agents and RAG system
        try:
            # Using enhanced adaptive prompts (Phase 2.6)
            from agent_prompts import AGENT_PROMPTS, ORCHESTRATOR_PROMPT
            from agents import dr_fatima, dr_james, dr_omar, dr_sarah
            from rag_system import retrieve_datasets

            self.agents = {
                'dr_omar': dr_omar,
                'dr_fatima': dr_fatima,
                'dr_james': dr_james,
                'dr_sarah': dr_sarah
            }
            self.agent_prompts = AGENT_PROMPTS
            self.orchestrator_prompt = ORCHESTRATOR_PROMPT
            self.retrieve_datasets = retrieve_datasets

        except ImportError as e:
            print(f"⚠️  Error importing dependencies: {e}")
            self.agents = {}
            self.retrieve_datasets = None

    async def analyze_ceo_question(self, query: str) -> dict[str, Any]:
        """
        Complete analysis pipeline for CEO question

        6-Stage Process:
        1. Retrieve comprehensive context (30+ datasets)
        2. Run 4 expert analyses (Opus 4.1) in parallel
        3. Deep strategic reasoning (Sonnet 4.5 Thinking)
        4. Identify expert debates
        5. Final synthesis (GPT-5)
        6. Generate CEO Decision Sheet
        """

        print("="*100)
        print("🚀 ULTIMATE STRATEGIC COUNCIL - MAXIMUM QUALITY ANALYSIS")
        print("="*100)
        print(f"\nCEO Question: {query}\n")

        # STAGE 1: Retrieve comprehensive data
        print("[1/6] Retrieving comprehensive context from ChromaDB...")
        context = self._retrieve_comprehensive_context(query, n_results=30)
        print(f"      ✓ Retrieved {len(context)} relevant datasets")

        # STAGE 2: Run 4 expert agents in parallel (Opus 4.1)
        print("\n[2/6] Running 4 expert analyses (Claude Opus 4.1)...")
        agent_analyses = await self._run_expert_agents(query, context)
        print(f"      ✓ {len(agent_analyses)} expert analyses complete")

        # STAGE 3: Deep strategic reasoning (Sonnet 4.5 Thinking)
        print("\n[3/6] Deep strategic reasoning (Sonnet 4.5 Thinking)...")
        strategic_thinking = await self._deep_strategic_analysis(
            query, agent_analyses, context
        )
        print(f"      ✓ Strategic reasoning complete ({len(strategic_thinking.get('thinking_process', ''))} chars)")

        # STAGE 4: Identify expert debates
        print("\n[4/6] Identifying expert disagreements...")
        debates = self._identify_debates(agent_analyses)
        print(f"      ✓ Found {len(debates)} areas of expert debate")

        # STAGE 5: Final synthesis (GPT-5)
        print("\n[5/6] Final synthesis (GPT-5)...")
        final_recommendation = await self._synthesize_with_gpt5(
            query, agent_analyses, strategic_thinking, debates
        )
        print(f"      ✓ Synthesis complete ({len(final_recommendation.get('synthesis', ''))} chars)")

        # STAGE 6: Generate CEO Decision Sheet
        print("\n[6/6] Generating CEO Decision Sheet...")
        decision_sheet = self._generate_decision_sheet(
            query, agent_analyses, strategic_thinking,
            debates, final_recommendation, context
        )
        print("      ✓ Decision Sheet generated")

        print("\n" + "="*100)
        print("✅ ANALYSIS COMPLETE - CEO DECISION SHEET READY")
        print("="*100)

        return decision_sheet

    def _retrieve_comprehensive_context(self, query: str, n_results: int = 30) -> list[dict]:
        """Retrieve comprehensive data from ChromaDB"""

        # Retrieve from all categories (no filtering for comprehensive view)
        retrieval_result = self.retrieve_datasets(
            query=query,
            category=None,  # All categories
            top_k=n_results
        )

        return retrieval_result.get('results', [])

    async def _run_expert_agents(self, query: str, context: list[dict]) -> list[dict]:
        """Run all 4 expert agents in parallel with Claude Opus 4.1"""

        if not self.anthropic_available:
            # Fallback to existing agent system
            print("      ⚠️  Anthropic unavailable, using fallback agents")
            return self._run_fallback_agents(query, context)

        # Run all 4 agents in parallel
        tasks = [
            self._run_single_agent("dr_omar", query, context),
            self._run_single_agent("dr_fatima", query, context),
            self._run_single_agent("dr_james", query, context),
            self._run_single_agent("dr_sarah", query, context)
        ]

        return await asyncio.gather(*tasks)

    async def _run_single_agent(self, agent_key: str, query: str,
                                context: list[dict]) -> dict:
        """Run single agent with Claude Opus 4.1"""

        agent = self.agents.get(agent_key)
        if not agent:
            return {"error": f"Agent {agent_key} not found"}

        # Get expert prompt
        prompt = self.agent_prompts.get(agent_key, "")

        # Format context
        context_str = self._format_context(context)

        # Build full prompt
        full_prompt = f"""{prompt}

═══════════════════════════════════════════════════════════
UDC CONTEXT
═══════════════════════════════════════════════════════════
United Development Company (UDC) is Qatar's master developer, operating:
- The Pearl-Qatar: Luxury waterfront development
- Lusail: Smart city development
- UDC Tower: Premium commercial real estate
- Various hospitality and retail assets

═══════════════════════════════════════════════════════════
AVAILABLE DATA SOURCES
═══════════════════════════════════════════════════════════
{context_str}

═══════════════════════════════════════════════════════════
CEO'S STRATEGIC QUESTION
═══════════════════════════════════════════════════════════
{query}

═══════════════════════════════════════════════════════════
YOUR EXPERT ANALYSIS (Use the 5-section structure)
═══════════════════════════════════════════════════════════
"""

        # Call Claude Opus 4.1
        try:
            message = self.anthropic.messages.create(
                model=ULTIMATE_MODEL_CONFIG['agents']['model'],
                max_tokens=ULTIMATE_MODEL_CONFIG['agents']['max_tokens'],
                temperature=ULTIMATE_MODEL_CONFIG['agents']['temperature'],
                messages=[{
                    "role": "user",
                    "content": full_prompt
                }]
            )

            return {
                "agent": agent.name,
                "title": agent.title,
                "domain": agent.category,
                "analysis": message.content[0].text,
                "model": ULTIMATE_MODEL_CONFIG['agents']['model']
            }

        except Exception as e:
            return {
                "agent": agent.name,
                "error": str(e),
                "fallback": "Opus 4.1 unavailable"
            }

    def _run_fallback_agents(self, query: str, context: list[dict]) -> list[dict]:
        """Fallback to existing agent system if Claude unavailable"""

        analyses = []
        for _agent_key, agent in self.agents.items():
            result = agent.analyze(query, top_k=10)
            analyses.append({
                "agent": agent.name,
                "title": agent.title,
                "domain": agent.category,
                "analysis": result.get('analysis', ''),
                "model": "fallback"
            })

        return analyses

    async def _deep_strategic_analysis(self, query: str, agent_analyses: list[dict],
                                      context: list[dict]) -> dict:
        """Use Claude Sonnet 4.5 Thinking for deep reasoning"""

        if not self.anthropic_available:
            return {
                "thinking_process": "Claude unavailable - skipping deep thinking stage",
                "model": "skipped"
            }

        # Format agent analyses
        analyses_str = self._format_agent_analyses(agent_analyses)

        # Deep thinking prompt
        thinking_prompt = f"""You are conducting deep strategic analysis for UDC's CEO.

CEO QUESTION: {query}

EXPERT ANALYSES FROM 4 DOMAIN EXPERTS:
{analyses_str}

CONDUCT DEEP STRATEGIC REASONING:

1. Second-Order Effects
   → What consequences are not mentioned by the experts?
   → What ripple effects will this decision create?
   → What long-term implications are being overlooked?

2. Expert Disagreements
   → Where do experts disagree and why?
   → What underlying assumptions differ?
   → Which perspective is most valid and why?

3. Missing Strategic Considerations
   → What critical factors weren't addressed?
   → What would a world-class strategist add?
   → What would Warren Buffett or Jeff Bezos consider?

4. Game Theory & Competitive Dynamics
   → How will competitors respond?
   → What strategic moves become available/blocked?
   → What Nash equilibria exist?

5. Hidden Risks & Black Swans
   → What low-probability, high-impact risks exist?
   → What could make this decision catastrophic?
   → What early warning signals should we monitor?

6. CEO's Unstated Questions
   → What does the CEO really want to know?
   → What keeps them up at night?
   → What political/board dynamics matter?

THINK STEP BY STEP. SHOW YOUR REASONING PROCESS.
Take as much space as needed to reason thoroughly."""

        try:
            # Deep thinking with extended timeout (Sonnet 4.5 can take 5-10 minutes)
            message = self.anthropic.messages.create(
                model=ULTIMATE_MODEL_CONFIG['strategic_thinking']['model'],
                max_tokens=ULTIMATE_MODEL_CONFIG['strategic_thinking']['max_tokens'],
                temperature=ULTIMATE_MODEL_CONFIG['strategic_thinking']['temperature'],
                timeout=600.0,  # 10 minutes for deep reasoning
                messages=[{
                    "role": "user",
                    "content": thinking_prompt
                }]
            )

            return {
                "thinking_process": message.content[0].text,
                "model": ULTIMATE_MODEL_CONFIG['strategic_thinking']['model']
            }

        except Exception as e:
            return {
                "thinking_process": f"Error in deep thinking: {str(e)}",
                "model": "error"
            }

    def _identify_debates(self, agent_analyses: list[dict]) -> list[dict]:
        """Identify areas where experts disagree"""

        debates = []

        # Simple heuristic: look for contrasting recommendations
        recommendations = []
        for analysis in agent_analyses:
            text = analysis.get('analysis', '').lower()

            # Extract key sentiment
            if 'recommend' in text or 'should' in text:
                recommendations.append({
                    'agent': analysis.get('agent', 'Unknown'),
                    'stance': 'positive' if 'recommend' in text else 'neutral'
                })

        # If we have varying stances, that's a debate
        if len({r['stance'] for r in recommendations}) > 1:
            debates.append({
                'topic': 'Strategic Recommendation',
                'positions': recommendations,
                'type': 'recommendation_divergence'
            })

        return debates

    async def _synthesize_with_gpt5(self, query: str, agent_analyses: list[dict],
                                   strategic_thinking: dict, debates: list[dict]) -> dict:
        """Use GPT-5 for ultimate synthesis"""

        if not self.openai_available:
            return {
                "synthesis": "GPT-5 unavailable - synthesis skipped",
                "model": "skipped"
            }

        # Format inputs
        analyses_str = self._format_agent_analyses(agent_analyses)
        thinking_str = strategic_thinking.get('thinking_process', '')
        debates_str = self._format_debates(debates)

        # Synthesis prompt
        system_prompt = """You are synthesizing strategic advice for UDC's CEO.

Your analysis will guide multi-million dollar decisions.

Be:
- Definitive (clear GO/NO-GO/CONDITIONAL)
- Specific (quantify everything)
- Actionable (concrete next steps)
- Honest (acknowledge uncertainties)"""

        user_prompt = f"""CEO QUESTION: {query}

═══════════════════════════════════════════════════════════
EXPERT ANALYSES (4 Domain Experts)
═══════════════════════════════════════════════════════════
{analyses_str}

═══════════════════════════════════════════════════════════
DEEP STRATEGIC THINKING
═══════════════════════════════════════════════════════════
{thinking_str}

═══════════════════════════════════════════════════════════
EXPERT DEBATES
═══════════════════════════════════════════════════════════
{debates_str if debates else "No major disagreements identified."}

═══════════════════════════════════════════════════════════
SYNTHESIZE INTO CEO DECISION SHEET
═══════════════════════════════════════════════════════════

Structure your synthesis as follows:

# EXECUTIVE SUMMARY
[2-3 paragraphs]
- Bottom line: What should the CEO do?
- Why: The compelling rationale
- Expected outcome: Quantified results

# STRATEGIC RATIONALE
[4-5 paragraphs]
- Why this is the right move
- What the data definitively shows
- How experts converge/diverge
- Second-order strategic considerations
- Competitive dynamics

# EXECUTION PLAN
[5-7 specific, sequenced steps]
- Each step: What, Who, When, Resources needed
- Timeline and milestones
- Success metrics for each phase
- Dependencies and critical path

# RISK MITIGATION
[3-4 key risks]
- Risk description
- Probability × Impact
- Mitigation strategy
- Kill criteria (when to exit)

# DECISION RECOMMENDATION
[Clear, unambiguous recommendation]
- GO / NO-GO / CONDITIONAL
- If GO: Immediate next 3 actions
- If NO-GO: What would need to change
- If CONDITIONAL: Specific conditions that must be met

Be specific. Quantify. This CEO makes $100M+ decisions."""

        try:
            # GPT-5 uses max_completion_tokens and doesn't support custom temperature
            response = self.openai_client.chat.completions.create(
                model=ULTIMATE_MODEL_CONFIG['synthesis']['model'],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_completion_tokens=ULTIMATE_MODEL_CONFIG['synthesis']['max_tokens']
                # Note: GPT-5 only supports temperature=1 (default)
            )

            return {
                "synthesis": response.choices[0].message.content,
                "model": ULTIMATE_MODEL_CONFIG['synthesis']['model']
            }

        except Exception as e:
            return {
                "synthesis": f"Error in GPT-5 synthesis: {str(e)}",
                "model": "error"
            }

    def _generate_decision_sheet(self, query: str, agent_analyses: list[dict],
                                strategic_thinking: dict, debates: list[dict],
                                final_recommendation: dict, context: list[dict]) -> dict:
        """Generate complete CEO Decision Sheet"""

        return {
            "question": query,
            "executive_summary": self._extract_executive_summary(final_recommendation),
            "expert_analyses": agent_analyses,
            "strategic_reasoning": strategic_thinking,
            "expert_debates": debates,
            "final_recommendation": final_recommendation,
            "data_sources": context,
            "models_used": {
                "agents": ULTIMATE_MODEL_CONFIG['agents']['model'],
                "deep_thinking": ULTIMATE_MODEL_CONFIG['strategic_thinking']['model'],
                "synthesis": ULTIMATE_MODEL_CONFIG['synthesis']['model'],
                "embeddings": ULTIMATE_MODEL_CONFIG['embeddings']['model']
            },
            "metadata": {
                "total_data_sources": len(context),
                "num_agents": len(agent_analyses),
                "has_debates": len(debates) > 0,
                "analysis_date": "2025-11-01"
            }
        }

    def _format_context(self, context: list[dict]) -> str:
        """Format context for prompts"""
        formatted = []
        for i, item in enumerate(context[:15], 1):  # Limit to top 15
            formatted.append(
                f"[{i}] {item.get('title', 'Untitled')}\n"
                f"    Category: {item.get('category', 'Unknown')}\n"
                f"    Relevance: {item.get('similarity', 0):.1%}"
            )
        return "\n\n".join(formatted)

    def _format_agent_analyses(self, analyses: list[dict]) -> str:
        """Format agent analyses for synthesis"""
        formatted = []
        for analysis in analyses:
            formatted.append(
                f"═══ {analysis.get('agent', 'Unknown')} ({analysis.get('title', '')} ═══\n"
                f"{analysis.get('analysis', 'No analysis available')}\n"
            )
        return "\n\n".join(formatted)

    def _format_debates(self, debates: list[dict]) -> str:
        """Format debates for synthesis"""
        if not debates:
            return "No significant expert disagreements identified."

        formatted = []
        for i, debate in enumerate(debates, 1):
            formatted.append(
                f"Debate {i}: {debate.get('topic', 'Unknown')}\n"
                f"Type: {debate.get('type', 'Unknown')}\n"
                f"Positions: {len(debate.get('positions', []))} different views"
            )
        return "\n\n".join(formatted)

    def _extract_executive_summary(self, final_recommendation: dict) -> str:
        """Extract executive summary from final recommendation"""
        synthesis = final_recommendation.get('synthesis', '')

        # Try to extract first section (Executive Summary)
        if '# EXECUTIVE SUMMARY' in synthesis:
            parts = synthesis.split('# STRATEGIC RATIONALE')
            if len(parts) > 0:
                return parts[0].replace('# EXECUTIVE SUMMARY', '').strip()

        # Fallback: first 500 characters
        return synthesis[:500] + "..." if len(synthesis) > 500 else synthesis


# ============================================================================
# Convenience Functions
# ============================================================================

async def ask_ultimate_council(query: str) -> dict[str, Any]:
    """
    Ask the Ultimate Strategic Council a question

    Returns complete CEO Decision Sheet
    """
    council = UltimateStrategicCouncil()
    return await council.analyze_ceo_question(query)


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def test_ultimate_council():
        query = "Should UDC invest in luxury residential development at Lusail or affordable housing at The Pearl?"

        result = await ask_ultimate_council(query)

        print("\n" + "="*100)
        print("CEO DECISION SHEET")
        print("="*100)
        print(f"\nQuestion: {result['question']}")
        print("\nModels Used:")
        for component, model in result['models_used'].items():
            print(f"  - {component}: {model}")
        print(f"\nData Sources: {result['metadata']['total_data_sources']}")
        print(f"Expert Agents: {result['metadata']['num_agents']}")
        print(f"Debates Identified: {result['metadata']['has_debates']}")

        print("\n" + "="*100)
        print("FINAL RECOMMENDATION")
        print("="*100)
        print(result['final_recommendation'].get('synthesis', 'No synthesis available')[:1000])
        print("\n...")

    asyncio.run(test_ultimate_council())
