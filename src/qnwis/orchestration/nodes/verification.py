"""
Verification Node.

Performs GPU-accelerated fact verification across agent reports.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List

from ..state import IntelligenceState
from ...rag import get_fact_verifier

logger = logging.getLogger(__name__)


def _agent_has_citations(report: Dict[str, object]) -> bool:
    """Return True if the agent supplied at least one citation."""

    citations = report.get("citations")
    if isinstance(citations, list) and citations:
        return True
    narrative = report.get("narrative", "")
    return isinstance(narrative, str) and "Per extraction:" in narrative


async def verification_node(state: IntelligenceState) -> IntelligenceState:
    """
    Node 9: GPU-accelerated fact checking.

    Performs two levels of verification:
    1. Citation checks (lightweight)
    2. GPU-powered semantic verification against 70K+ documents
    
    Uses pre-indexed documents on GPU 6 for real-time verification.
    """

    reasoning_chain = state.setdefault("reasoning_chain", [])
    nodes_executed = state.setdefault("nodes_executed", [])
    warnings = state.setdefault("warnings", [])

    issues: List[str] = []
    agent_reports = state.get("agent_reports", [])
    
    # Level 1: Citation checks (backward compatible)
    for bundle in agent_reports:
        agent_name = bundle.get("agent", "unknown")
        report = bundle.get("report", {})
        if not _agent_has_citations(report):
            issues.append(f"{agent_name} missing authoritative citations.")

        confidence = report.get("confidence")
        if isinstance(confidence, (int, float)) and confidence < 0.4:
            issues.append(f"{agent_name} reported low confidence ({confidence:.2f}).")
    
    # Level 2: GPU-accelerated semantic verification
    verifier = get_fact_verifier()
    
    if verifier and verifier.is_indexed:
        try:
            logger.info("🔍 Starting GPU-accelerated fact verification...")
            
            # Verify all agent outputs concurrently
            verification_tasks = []
            for bundle in agent_reports:
                agent_name = bundle.get("agent", "unknown")
                report = bundle.get("report", {})
                narrative = report.get("narrative", "")
                
                if narrative:
                    verification_tasks.append(
                        _verify_agent_narrative(verifier, agent_name, narrative)
                    )
            
            if verification_tasks:
                verification_results = await asyncio.gather(*verification_tasks)
                
                # Aggregate verification metrics
                total_claims = sum(r['total_claims'] for r in verification_results)
                verified_claims = sum(r['verified_claims'] for r in verification_results)
                avg_confidence = (
                    sum(r['avg_confidence'] * r['total_claims'] for r in verification_results if r['total_claims'] > 0)
                    / total_claims if total_claims > 0 else 1.0
                )
                verification_rate = verified_claims / total_claims if total_claims > 0 else 1.0
                
                # Add to state
                gpu_verification = {
                    'total_claims': total_claims,
                    'verified_claims': verified_claims,
                    'verification_rate': verification_rate,
                    'avg_confidence': avg_confidence,
                    'agent_results': verification_results
                }
                
                state['fact_check_results'] = {
                    "status": "PASS" if verification_rate >= 0.70 else "ATTENTION",
                    "issues": issues,
                    "agent_count": len(agent_reports),
                    "gpu_verification": gpu_verification
                }
                
                # Log results
                if verification_rate >= 0.70:
                    logger.info(
                        f"✅ GPU verification: {verification_rate:.0%} "
                        f"({verified_claims}/{total_claims} claims), "
                        f"confidence: {avg_confidence:.2f}"
                    )
                    reasoning_chain.append(
                        f"GPU fact verification: {verification_rate:.0%} verified "
                        f"({verified_claims}/{total_claims} claims), confidence: {avg_confidence:.2f}"
                    )
                else:
                    logger.warning(
                        f"⚠️ Low GPU verification rate: {verification_rate:.0%} "
                        f"({verified_claims}/{total_claims} claims)"
                    )
                    warnings.append(
                        f"GPU verification: only {verification_rate:.0%} of claims verified "
                        f"({verified_claims}/{total_claims})"
                    )
                    issues.append(f"Low fact verification rate: {verification_rate:.0%}")
            else:
                logger.info("No narratives to verify")
                state['fact_check_results'] = {
                    "status": "PASS",
                    "issues": issues,
                    "agent_count": len(agent_reports),
                    "gpu_verification": None
                }
        
        except Exception as e:
            logger.error(f"GPU verification failed: {e}", exc_info=True)
            warnings.append(f"GPU verification error: {str(e)}")
            state['fact_check_results'] = {
                "status": "ERROR",
                "issues": issues + [f"GPU verification error: {str(e)}"],
                "agent_count": len(agent_reports),
                "gpu_verification": None
            }
    else:
        # GPU verification disabled or not initialized
        logger.info("GPU verification not available - using citation checks only")
        state['fact_check_results'] = {
            "status": "ATTENTION" if issues else "PASS",
            "issues": issues,
            "agent_count": len(agent_reports),
            "gpu_verification": None
        }

    fabrication_detected = bool(issues)
    state["fabrication_detected"] = fabrication_detected

    if fabrication_detected:
        warnings.append("Fact check flagged missing citations or low confidence.")
    else:
        reasoning_chain.append("Verification node confirmed citations for all agents.")

    nodes_executed.append("verification")
    return state


async def _verify_agent_narrative(
    verifier,
    agent_name: str,
    narrative: str
) -> Dict:
    """
    Verify an agent's narrative using GPU verifier.
    
    Args:
        verifier: GPUFactVerifier instance
        agent_name: Name of the agent
        narrative: Agent's narrative text
        
    Returns:
        Verification result dictionary
    """
    try:
        result = await verifier.verify_agent_output(narrative)
        result['agent_name'] = agent_name
        return result
    except Exception as e:
        logger.error(f"Failed to verify {agent_name}: {e}")
        return {
            'agent_name': agent_name,
            'total_claims': 0,
            'verified_claims': 0,
            'verification_rate': 0.0,
            'avg_confidence': 0.0,
            'error': str(e)
        }

