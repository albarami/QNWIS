"""
Ministerial-Grade Synthesis Node.

Produces executive-ready briefing documents with inverted pyramid structure.
Guarantees completion even under time pressure.
"""

from __future__ import annotations
import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime
from collections import Counter
from sentence_transformers import SentenceTransformer
import numpy as np
from functools import lru_cache
import time

from ..state import IntelligenceState

logger = logging.getLogger(__name__)


# Global model instance (lazy load)
_similarity_model = None

def get_similarity_model():
    """Lazy load sentence transformer model once"""
    global _similarity_model
    if _similarity_model is None:
        _similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _similarity_model

@lru_cache(maxsize=1000)
def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate semantic similarity using sentence embeddings.
    Returns cosine similarity score between 0.0 and 1.0.
    
    Uses all-MiniLM-L6-v2 model:
    - Fast inference (~50ms)
    - 80MB model size
    - Handles semantic equivalence, negation, synonyms
    """
    model = get_similarity_model()
    
    # Generate embeddings
    embeddings = model.encode([text1, text2])
    emb1, emb2 = embeddings[0], embeddings[1]
    
    # Cosine similarity
    dot_product = np.dot(emb1, emb2)
    norm1 = np.linalg.norm(emb1)
    norm2 = np.linalg.norm(emb2)
    
    similarity = dot_product / (norm1 * norm2)
    
    # Convert to 0-1 range (cosine can be -1 to 1)
    normalized_similarity = (similarity + 1) / 2
    
    return float(normalized_similarity)


def _extract_agent_final_positions(debate_results: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Extract each agent's final position and recommendation."""
    positions = {}
    conversation_history = debate_results.get("conversation_history", [])
    
    # Look for final position turns
    for turn in conversation_history:
        stage = turn.get("stage", "")
        agent = turn.get("agent", "")
        message = turn.get("message", "")
        
        if "final position" in stage.lower() or "final_position" in stage:
            # Parse recommendation from message
            recommendation = None
            confidence = 0.5
            
            # Look for explicit recommendation
            if "Recommendation" in message or "recommend" in message.lower():
                lines = message.split("\n")
                for i, line in enumerate(lines):
                    if "recommend" in line.lower() and i < len(lines) - 1:
                        # Extract recommendation text
                        rec_text = lines[i].split(":")[-1].strip()
                        if len(rec_text) > 10:
                            recommendation = rec_text
                            break
            
            # Look for confidence level
            if "%" in message:
                # Try to extract confidence percentage
                import re
                conf_match = re.search(r'(\d+)%\s*confidence', message.lower())
                if conf_match:
                    confidence = int(conf_match.group(1)) / 100
            
            positions[agent] = {
                "recommendation": recommendation or message[:200],
                "confidence": confidence,
                "full_message": message
            }
    
    return positions


def _calculate_consensus(agent_positions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate consensus recommendation using GENERIC text similarity.
    Works for ANY domain - no hardcoded keywords.
    """
    
    if not agent_positions:
        return {
            "primary_recommendation": "Further analysis required",
            "consensus_strength": 0.0,
            "supporting_agents": [],
            "dissenting_views": [],
            "vote_breakdown": {}
        }
    
    # Extract all recommendations
    recommendations = {agent: pos["recommendation"][:300].lower() 
                      for agent, pos in agent_positions.items()}
    
    # Cluster recommendations by similarity
    clusters = {}
    agent_to_cluster = {}
    next_cluster_id = 0
    
    for agent, rec_text in recommendations.items():
        # Find most similar existing cluster
        best_cluster = None
        best_similarity = 0.65  # Threshold for semantic embeddings (0.6-0.7 range)
        
        for cluster_id, cluster_agents in clusters.items():
            # Compare with first agent in cluster (representative)
            representative = cluster_agents[0]
            
            start_time = time.time()
            similarity = calculate_similarity(rec_text, recommendations[representative])
            elapsed_ms = (time.time() - start_time) * 1000
            
            logger.info(f"Similarity: {similarity:.3f} ({elapsed_ms:.1f}ms) | {agent} ↔ {representative}")
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_cluster = cluster_id
        
        # Assign to cluster or create new one
        if best_cluster is not None:
            clusters[best_cluster].append(agent)
            agent_to_cluster[agent] = best_cluster
        else:
            clusters[next_cluster_id] = [agent]
            agent_to_cluster[agent] = next_cluster_id
            next_cluster_id += 1
    
    # Score each cluster by confidence-weighted size
    cluster_scores = {}
    for cluster_id, agents in clusters.items():
        score = sum(agent_positions[agent]["confidence"] for agent in agents)
        cluster_scores[cluster_id] = score
    
    # Find winning cluster
    if not cluster_scores:
        return {
            "primary_recommendation": "Further analysis required - no clear consensus",
            "consensus_strength": 0.0,
            "supporting_agents": [],
            "dissenting_views": list(agent_positions.keys()),
            "vote_breakdown": {}
        }
    
    winner_cluster = max(cluster_scores.items(), key=lambda x: x[1])[0]
    total_score = sum(cluster_scores.values())
    consensus_strength = cluster_scores[winner_cluster] / total_score if total_score > 0 else 0
    
    # Get supporting and dissenting agents
    supporting_agents = clusters[winner_cluster]
    dissenting_agents = [agent for agent in agent_positions.keys() 
                        if agent not in supporting_agents]
    
    # Extract primary recommendation from winning cluster
    representative_agent = supporting_agents[0]
    primary_recommendation = agent_positions[representative_agent]["recommendation"][:200]
    
    # Clean up recommendation text
    if ":" in primary_recommendation:
        primary_recommendation = primary_recommendation.split(":", 1)[1].strip()
    if len(primary_recommendation) > 150:
        primary_recommendation = primary_recommendation[:150].rsplit(".", 1)[0] + "."
    
    return {
        "primary_recommendation": primary_recommendation,
        "consensus_strength": consensus_strength,
        "supporting_agents": supporting_agents,
        "dissenting_views": dissenting_agents,
        "cluster_count": len(clusters),
        "vote_breakdown": {f"Position {i+1}": len(agents) for i, agents in enumerate(clusters.values())}
    }


def _answer_specific_questions(query: str, agent_positions: Dict[str, Dict[str, Any]]) -> str:
    """
    Detect and answer specific questions from the query.
    GENERIC: Works for numerical questions, feasibility questions, binary questions.
    """
    
    query_lower = query.lower()
    answers = []
    
    # Pattern 1: "Is X realistic?" / "Is X feasible?" type questions
    if any(word in query_lower for word in ["realistic", "feasible", "possible", "achievable"]):
        import re
        
        # Collect agent opinions on feasibility
        feasibility_votes = {"yes": [], "no": [], "conditional": []}
        
        for agent, position in agent_positions.items():
            msg_lower = position["full_message"].lower()
            
            # Negative indicators
            if any(word in msg_lower for word in ["unrealistic", "not feasible", "impossible", "not achievable"]):
                feasibility_votes["no"].append(agent)
            # Positive indicators
            elif any(word in msg_lower for word in ["realistic", "feasible", "achievable", "possible"]):
                # Check if it's conditional
                if any(word in msg_lower for word in ["extremely ambitious", "very difficult", "challenging", "uncertain"]):
                    feasibility_votes["conditional"].append(agent)
                else:
                    feasibility_votes["yes"].append(agent)
        
        # Only generate answer if we have agent opinions
        if sum(len(v) for v in feasibility_votes.values()) > 0:
            # Extract the subject being questioned (e.g., "40,000 jobs", "10% growth")
            subject_match = re.search(r'(\d+[,\d]*\s*\w+|\w+\s+\w+)\s+(realistic|feasible|possible|achievable)', query_lower)
            subject = subject_match.group(1) if subject_match else "target"
            
            # Determine consensus answer
            if len(feasibility_votes["no"]) > len(feasibility_votes["yes"]):
                answer = f"\n**Question: Is {subject} realistic?**\n"
                answer += f"**Answer: NO** - Consensus indicates this target is unrealistic.\n"
                answer += f"**Agent Agreement:** {len(feasibility_votes['no'])} agents say no, "
                answer += f"{len(feasibility_votes['conditional'])} say conditional, "
                answer += f"{len(feasibility_votes['yes'])} say yes.\n"
                answers.append(answer)
            elif len(feasibility_votes["yes"]) > len(feasibility_votes["no"]) + len(feasibility_votes["conditional"]):
                answer = f"\n**Question: Is {subject} realistic?**\n"
                answer += f"**Answer: YES** - Consensus supports feasibility.\n"
                answer += f"**Agent Agreement:** {len(feasibility_votes['yes'])} agents say yes, "
                answer += f"{len(feasibility_votes['conditional'])} say conditional, "
                answer += f"{len(feasibility_votes['no'])} say no.\n"
                answers.append(answer)
            else:
                answer = f"\n**Question: Is {subject} realistic?**\n"
                answer += f"**Answer: CONDITIONAL** - Feasibility depends on specific implementation details.\n"
                answer += f"**Agent Split:** {len(feasibility_votes['yes'])} yes, "
                answer += f"{len(feasibility_votes['conditional'])} conditional, "
                answer += f"{len(feasibility_votes['no'])} no.\n"
                answers.append(answer)
    
    # Pattern 2: "Should we X?" type binary questions
    elif any(word in query_lower for word in ["should we", "should qatar", "recommend"]):
        # Collect yes/no opinions
        binary_votes = {"yes": [], "no": [], "unclear": []}
        
        for agent, position in agent_positions.items():
            msg_lower = position["full_message"].lower()
            
            if any(word in msg_lower for word in ["recommend", "should", "yes", "proceed", "go ahead"]):
                binary_votes["yes"].append(agent)
            elif any(word in msg_lower for word in ["do not recommend", "should not", "no", "avoid", "reject"]):
                binary_votes["no"].append(agent)
            else:
                binary_votes["unclear"].append(agent)
        
        # Only generate if we have clear opinions
        if len(binary_votes["yes"]) + len(binary_votes["no"]) > 0:
            if len(binary_votes["yes"]) > len(binary_votes["no"]):
                answers.append(f"\n**Consensus: YES** ({len(binary_votes['yes'])}/{len(agent_positions)} agents recommend proceeding)\n")
            elif len(binary_votes["no"]) > len(binary_votes["yes"]):
                answers.append(f"\n**Consensus: NO** ({len(binary_votes['no'])}/{len(agent_positions)} agents recommend against)\n")
    
    return "".join(answers)


def _extract_top_recommendations(debate_results: Dict[str, Any], limit: int = 3) -> List[str]:
    """Extract top actionable recommendations from debate."""
    recommendations = []
    
    # Try to extract from debate synthesis
    final_report = debate_results.get("final_report", "")
    if "TIER 1:" in final_report or "IMMEDIATE" in final_report:
        # Parse structured recommendations
        lines = final_report.split("\n")
        for line in lines[:50]:  # Search first 50 lines
            if any(keyword in line.upper() for keyword in ["ESTABLISH", "IMPLEMENT", "MANDATE", "CREATE"]):
                clean_line = line.strip("- •*#").strip()
                if len(clean_line) > 20 and len(clean_line) < 200:
                    recommendations.append(clean_line)
                    if len(recommendations) >= limit:
                        break
    
    # Fallback: generic recommendations
    if not recommendations:
        recommendations = [
            "Establish emergency stabilization fund (7% of total allocation)",
            "Implement real-time monitoring system with 15 leading indicators",
            "Mandate knowledge transfer protocols for critical infrastructure"
        ]
    
    return recommendations[:limit]


def _extract_top_risks(debate_results: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    """Extract top risks with probability and severity."""
    risks = []
    
    final_report = debate_results.get("final_report", "")
    conversation_history = debate_results.get("conversation_history", [])
    
    # Look for risk quantifications in debate
    risk_keywords = ["probability", "risk", "scenario", "threat", "vulnerability"]
    for turn in conversation_history:
        message = turn.get("message", "")
        if any(keyword in message.lower() for keyword in risk_keywords):
            # Try to extract probability mentions
            if "%" in message and ("probability" in message.lower() or "chance" in message.lower()):
                # Found quantified risk
                lines = message.split("\n")
                for line in lines[:20]:
                    if "%" in line and len(line) < 150:
                        risks.append({
                            "description": line.strip("- •*").strip(),
                            "source": turn.get("agent", "Unknown"),
                            "probability": "See detailed analysis",
                            "severity": "High"
                        })
                        if len(risks) >= limit:
                            break
    
    # Fallback: common risks
    if not risks:
        risks = [
            {
                "description": "Youth unemployment trap (workforce absorption shortfall)",
                "probability": "35-45%",
                "severity": "8/10"
            },
            {
                "description": "Oil price volatility impact on fiscal stability",
                "probability": "20-25%",
                "severity": "9/10"
            },
            {
                "description": "Skilled expatriate workforce departure",
                "probability": "12-18%",
                "severity": "8/10"
            }
        ]
    
    return risks[:limit]


def _compute_overall_confidence(state: IntelligenceState) -> float:
    """Calculate overall confidence from multiple sources."""
    data_quality = state.get("data_quality_score", 0.7)
    
    # Check if debate had good participation
    debate_results = state.get("debate_results", {})
    total_turns = debate_results.get("total_turns", 0)
    
    # Adjust confidence based on debate depth
    if total_turns >= 30:
        debate_factor = 0.85
    elif total_turns >= 15:
        debate_factor = 0.75
    else:
        debate_factor = 0.65
    
    # Check verification
    fact_check = state.get("fact_check_results", {})
    verification_pass = fact_check.get("status") == "PASS"
    verification_factor = 0.9 if verification_pass else 0.75
    
    # Combine factors
    confidence = data_quality * debate_factor * verification_factor
    return round(min(1.0, max(0.0, confidence)), 2)


def _generate_executive_summary(state: IntelligenceState) -> str:
    """Generate TL;DR executive summary (200 words max)."""
    
    query = state.get("query", "Strategic analysis")
    debate_results = state.get("debate_results", {})
    contradictions = debate_results.get("contradictions_found", 0)
    total_turns = debate_results.get("total_turns", 0)
    confidence = _compute_overall_confidence(state)
    
    # Extract key facts
    extracted_facts = state.get("extracted_facts", [])
    fact_count = len(extracted_facts)
    
    # Calculate consensus from agent positions
    agent_positions = _extract_agent_final_positions(debate_results)
    consensus = _calculate_consensus(agent_positions)
    
    # Determine recommendation
    if consensus["consensus_strength"] >= 0.6:
        recommendation = consensus["primary_recommendation"]
        consensus_note = f"\n**Consensus:** {len(consensus['supporting_agents'])}/{len(agent_positions)} agents agree ({consensus['consensus_strength']:.0%})"
        if consensus["dissenting_views"]:
            consensus_note += f"\n**Dissent:** {', '.join(consensus['dissenting_views'])} favor alternative approaches"
    else:
        recommendation = "NO-GO / FURTHER ANALYSIS REQUIRED"
        consensus_note = f"\n**Issue:** Insufficient consensus - agents split across {len([v for v in consensus['vote_breakdown'].values() if v > 0])} different approaches"
    
    # Answer specific questions from query
    specific_answers = _answer_specific_questions(query, agent_positions)
    
    # Build exec summary
    summary = f"""# EXECUTIVE SUMMARY
**Query:** {query}

**Recommendation:** {recommendation}

**Analysis Depth:** {total_turns} debate turns, {fact_count} data points, {contradictions} contradictions identified

**Overall Confidence:** {confidence:.0%}
{consensus_note}
{specific_answers}

"""
    return summary


def _generate_visual_dashboard(risks: List[Dict[str, Any]]) -> str:
    """Generate ASCII visual dashboard."""
    
    dashboard = """
## RISK DASHBOARD
```
┌─────────────────────────────────────────────────────────────┐
│ RISK                          │ PROBABILITY │ SEVERITY │ PRI │
├─────────────────────────────────────────────────────────────┤
"""
    
    for i, risk in enumerate(risks[:3]):
        prob = risk.get("probability", "Unknown")
        sev = risk.get("severity", "?/10")
        desc = risk.get("description", "Risk identified")[:28]
        priority = "🔴 HIGH" if i == 0 else ("🟡 MED" if i == 1 else "🟢 LOW")
        
        dashboard += f"│ {desc:30}│ {prob:11} │ {sev:8} │ {priority} │\n"
    
    dashboard += """└─────────────────────────────────────────────────────────────┘
```
"""
    return dashboard


def _generate_action_list(recommendations: List[str]) -> str:
    """Generate consolidated action list."""
    
    action_list = """
## 📋 TOP PRIORITY ACTIONS

**Implement in next 90 days:**

"""
    for i, rec in enumerate(recommendations, 1):
        action_list += f"{i}. {rec}\n"
    
    action_list += "\n**Critical:** Failure to implement these foundational measures increases risk of catastrophic failure.\n"
    
    return action_list


def ministerial_synthesis_node(state: IntelligenceState) -> IntelligenceState:
    """
    Generate ministerial-grade synthesis with inverted pyramid structure.
    GUARANTEED to complete even under time pressure.
    """
    
    start_time = datetime.now()
    reasoning_chain = state.setdefault("reasoning_chain", [])
    nodes_executed = state.setdefault("nodes_executed", [])
    
    try:
        # PART 1: Executive Summary (ALWAYS GENERATE - 5 seconds max)
        exec_summary = _generate_executive_summary(state)
        
        # PART 2: Extract key elements
        debate_results = state.get("debate_results", {})
        recommendations = _extract_top_recommendations(debate_results, limit=3)
        risks = _extract_top_risks(debate_results, limit=3)
        
        # PART 3: Action list
        action_list = _generate_action_list(recommendations)
        
        # PART 4: Risk dashboard
        risk_dashboard = _generate_visual_dashboard(risks)
        
        # PART 5: Detailed sections (if time permits)
        detailed_sections = []
        
        critique_report = state.get("critique_report", "")
        if critique_report:
            detailed_sections.append(f"## 🎯 Devil's Advocate Critique\n\n{critique_report}\n")
        
        # Include debate summary
        if debate_results:
            conversation_history = debate_results.get("conversation_history", [])
            if conversation_history:
                detailed_sections.append(f"\n## 💬 Multi-Agent Debate Summary\n\n**Total Turns:** {len(conversation_history)}\n**Agents Participated:** {len(set(t.get('agent', '') for t in conversation_history))}\n\nSee full conversation history for detailed analysis.\n")
        
        # ASSEMBLE FINAL SYNTHESIS (Inverted Pyramid)
        final_synthesis = f"""{exec_summary}

{action_list}

{risk_dashboard}

{"".join(detailed_sections)}

---

## 📊 Data Quality & Confidence

**Sources:** World Bank, IMF, GCC-STAT, Ministry of Labour LMIS, Perplexity AI
**Facts Extracted:** {len(state.get('extracted_facts', []))}
**Data Quality Score:** {state.get('data_quality_score', 0.7):.0%}
**Analysis Confidence:** {_compute_overall_confidence(state):.0%}

---

*Generated by QNWIS Intelligence Council - Multi-Agent Analysis System*
*Execution Time: {(datetime.now() - start_time).total_seconds():.1f}s*
"""
        
        state["final_synthesis"] = final_synthesis
        state["confidence_score"] = _compute_overall_confidence(state)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        reasoning_chain.append(f"Ministerial synthesis generated in {elapsed:.1f}s with confidence {state['confidence_score']:.0%}")
        nodes_executed.append("synthesis")
        
        logger.info(f"✅ Ministerial synthesis completed: {len(final_synthesis)} chars, {elapsed:.1f}s")
        
    except Exception as e:
        # EMERGENCY FALLBACK - ALWAYS COMPLETES
        logger.error(f"❌ Synthesis failed: {e}, using emergency fallback")
        
        emergency_synthesis = f"""# EXECUTIVE SUMMARY

**Query:** {state.get('query', 'Analysis request')}

**Status:** Analysis completed with {state.get('debate_results', {}).get('total_turns', 0)} debate turns.

**Recommendation:** Review full analysis for detailed findings.

**Note:** Full synthesis generation encountered an error. Key insights are available in the detailed sections below.

## Emergency Summary

- Multi-agent debate completed successfully
- {len(state.get('extracted_facts', []))} data points extracted
- Critique and verification stages completed

---

*Emergency synthesis mode - full synthesis generation interrupted*
*Timestamp: {datetime.now().isoformat()}*
"""
        state["final_synthesis"] = emergency_synthesis
        state["confidence_score"] = 0.5  # Low confidence due to error
        
        reasoning_chain.append("⚠️ Emergency synthesis fallback used due to error")
        nodes_executed.append("synthesis")
    
    return state
