"""
Legendary Synthesis Node.

Generates a Strategic Intelligence Briefing that makes consultants obsolete.
This is the crown jewel of QNWIS – crystallizing extraordinary analytical depth
into actionable ministerial intelligence.

FIX RUN 36: Added question type detection to handle DIAGNOSTIC questions
without forcing A/B framework.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import os
import re
from datetime import datetime
from typing import Optional

from ....llm.client import LLMClient
from ...confidence_calibration import (
    ConfidenceCalibrator,
    generate_honest_uncertainty_section,
)
from ...ground_truth import (
    determine_verdict,
    extract_ground_truth,
    validate_no_fabrication,
)
from ...scenario_aware_synthesis import ScenarioAwareSynthesis
from ...state import IntelligenceState
from .extractors import (
    extract_agent_final_positions,
    extract_debate_highlights,
    extract_stats,
)
from .formatters import (
    add_data_integrity_note,
    apply_hedge_removal,
    apply_section_override,
    build_programmatic_head_comparative,
    build_programmatic_head_diagnostic,
    correct_body_rates,
    correct_deflated_rates,
    enforce_calibrated_confidence,
    fix_confidence_mentions,
    fix_rate_ranges,
    inject_consensus_header,
)
from .ground_truth import (
    aggregate_agent_estimates,
    calculate_calibrated_confidence,
    cap_unrealistic_rates,
    classify_question_type,
    validate_output_consistency,
)
from .prompts import build_legendary_prompt
from .sections import (
    calculate_robustness_ratio,
    extract_edge_cases,
    extract_risks,
    extract_scenario_summaries,
)
from .services import (
    fetch_case_studies,
    run_financial_modeling,
    run_implementation_plan,
    run_risk_register,
    run_stakeholder_analysis,
)
from .verdict import extract_final_debate_verdict

logger = logging.getLogger(__name__)


async def legendary_synthesis_node(state: IntelligenceState) -> IntelligenceState:
    """
    Generate the Legendary Strategic Intelligence Briefing.

    This synthesis makes consultants obsolete by crystallizing extraordinary
    analytical depth into actionable ministerial intelligence.
    """
    start_time = datetime.now()
    reasoning_chain = state.get("reasoning_chain") or []
    state["reasoning_chain"] = reasoning_chain
    nodes_executed = state.get("nodes_executed") or []
    state["nodes_executed"] = nodes_executed

    query = state.get("query", "")
    question_type = state.get("question_type", "COMPARATIVE")
    logger.info(f"📋 Synthesis question_type: {question_type}")

    if question_type in ("DIAGNOSTIC", "FORECAST", "HYBRID"):
        logger.warning(f"⚠️ {question_type} question - will aggregate agent probability estimates")

    if state.get("target_infeasible"):
        return _handle_infeasible(state, query, reasoning_chain, nodes_executed)

    # ── Extract all statistics and data ──────────────────────────────────────
    stats = _safe(extract_stats, state, {})
    debate_highlights = _safe(extract_debate_highlights, state, {})
    scenario_summaries = _safe(extract_scenario_summaries, state, [])
    risks = _safe(extract_risks, state, [])
    edge_cases = _safe(extract_edge_cases, state, [])
    facts = state.get("extracted_facts", [])
    research_analysis = state.get("research_analysis", "")

    # ── Debate verdict ───────────────────────────────────────────────────────
    debate_verdict = _safe(extract_final_debate_verdict, state, {})
    _enrich_stats_with_verdict(stats, debate_verdict, debate_highlights)

    engine_b = state.get("engine_b_aggregate", {})
    stats["engine_b_scenarios"] = engine_b.get("scenarios_with_compute", 0)
    stats["avg_success_probability"] = engine_b.get("avg_success_probability", 0) * 100
    stats["sensitivity_drivers"] = engine_b.get("sensitivity_drivers", [])
    if stats["engine_b_scenarios"] == 0:
        logger.warning("⚠️ NO ENGINE B DATA AVAILABLE FOR SYNTHESIS")

    robustness = calculate_robustness_ratio(scenario_summaries)
    stats["robustness_ratio"] = robustness["ratio_str"]
    stats["robustness_pct"] = robustness["ratio_pct"]
    _apply_debate_override(stats, debate_verdict, robustness)

    logger.info(
        f"🏛️ Generating Legendary Briefing: {stats['n_facts']} facts, "
        f"{stats['n_turns']} turns, {stats['n_scenarios']} scenarios"
    )

    # ── Supplementary services ───────────────────────────────────────────────
    case_studies_text = await fetch_case_studies(state, query)
    financial_text = run_financial_modeling(query, scenario_summaries, facts)
    stakeholder_text = run_stakeholder_analysis(query, scenario_summaries, facts)
    risk_register_text = run_risk_register(query, scenario_summaries)
    implementation_text = run_implementation_plan(query, scenario_summaries)

    # ── Build constraint for DIAGNOSTIC questions ────────────────────────────
    brief_constraint = _build_diagnostic_constraint(state, question_type)

    # ── Build prompt & call LLM ──────────────────────────────────────────────
    prompt = build_legendary_prompt(
        query=query, stats=stats, debate_highlights=debate_highlights,
        scenario_summaries=scenario_summaries, risks=risks, facts=facts,
        edge_cases=edge_cases, case_studies_text=case_studies_text,
        financial_analysis_text=financial_text,
        implementation_plan_text=implementation_text,
        stakeholder_analysis_text=stakeholder_text,
        risk_register_text=risk_register_text,
        research_analysis_text=research_analysis,
    )
    if brief_constraint:
        prompt = brief_constraint + "\n" + prompt

    provider = os.getenv("QNWIS_LLM_PROVIDER", "azure")
    model = os.getenv("QNWIS_LANGGRAPH_LLM_MODEL", "gpt-4o")
    llm_client = LLMClient(provider=provider, model=model)

    try:
        briefing = await llm_client.generate_with_routing(
            prompt=prompt, task_type="final_synthesis",
            temperature=0.4, max_tokens=8000,
        )

        agent_positions = extract_agent_final_positions(state)
        briefing, state = _post_process(
            briefing, state, stats, debate_highlights, scenario_summaries,
            agent_positions, debate_verdict, query,
        )

        state["final_synthesis"] = briefing
        state["meta_synthesis"] = briefing

        elapsed = (datetime.now() - start_time).total_seconds()
        reasoning_chain.append(f"🏛️ Legendary Strategic Briefing generated: {len(briefing):,} chars in {elapsed:.1f}s")
        nodes_executed.append("synthesis")
        logger.info(f"✅ Legendary Briefing complete: {len(briefing):,} chars, {elapsed:.1f}s")

    except Exception as e:
        logger.error(f"❌ Legendary synthesis failed: {e}", exc_info=True)
        state["final_synthesis"] = _emergency_fallback(stats, str(e))
        state["confidence_score"] = 0.3
        reasoning_chain.append(f"❌ Synthesis failed: {e}")

    _run_final_validation(state)
    return state


def legendary_synthesis_node_sync(state: IntelligenceState) -> IntelligenceState:
    """Synchronous wrapper for the legendary synthesis node.

    Handles both sync and async calling contexts correctly.
    When called from an existing async loop (e.g. LangGraph), runs
    the coroutine in a new thread to avoid blocking the event loop.
    """
    try:
        loop = asyncio.get_running_loop()
        logger.info("legendary_synthesis called from async context — bridging via thread")
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, legendary_synthesis_node(state))
            return future.result()
    except RuntimeError:
        ...

    return asyncio.run(legendary_synthesis_node(state))


# ═══════════════════════════════════════════════════════════════════════════════
# Small helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _safe(fn, state, default):
    try:
        return fn(state)
    except Exception as e:
        logger.warning(f"Extraction error in {fn.__name__}: {e}")
        return default


def _handle_infeasible(state, query, reasoning_chain, nodes_executed):
    logger.info("🛑 INFEASIBLE TARGET - Generating explanation briefing...")
    reason = state.get("infeasibility_reason", "Target is arithmetically impossible")
    alternative = state.get("feasible_alternative", "Consider more realistic targets")
    fc = state.get("feasibility_check", {})
    state["final_synthesis"] = (
        f"## ⛔ FEASIBILITY ANALYSIS: TARGET NOT ACHIEVABLE\n\n**Query:** {query}\n\n"
        f"### First-Principles Assessment\n\n**Verdict: INFEASIBLE**\n\n{reason}\n\n"
        f"### Arithmetic Analysis\n{fc.get('explanation', reason)}\n\n"
        f"### Recommended Alternative\n{alternative}\n\n**Confidence: 99%** (arithmetic certainty)\n"
    )
    state["meta_synthesis"] = state["final_synthesis"]
    state["confidence_score"] = 0.99
    reasoning_chain.append("⛔ Synthesis: Generated infeasibility explanation")
    nodes_executed.append("synthesis")
    return state


def _enrich_stats_with_verdict(stats, debate_verdict, debate_highlights):
    if not debate_verdict or not (debate_verdict.get("quantified_assessment") or debate_verdict.get("direct_answer")):
        return
    logger.info(f"📊 DEBATE VERDICT: {debate_verdict.get('quantified_assessment', str(debate_verdict.get('direct_answer',''))[:50])}")
    debate_highlights["final_verdict"] = debate_verdict
    if debate_verdict.get("quantified_assessment"):
        assessment = debate_verdict["quantified_assessment"]
        m = re.search(r'(\d+(?:\.\d+)?)', str(assessment))
        if m:
            stats["debate_assessment_value"] = float(m.group(1))
            stats["debate_assessment_type"] = debate_verdict.get("assessment_type", "score")
        else:
            stats["debate_assessment_value"] = assessment
            stats["debate_assessment_type"] = "qualitative"
        stats["debate_recommendation"] = debate_verdict.get("recommendation", "See verdict")


def _apply_debate_override(stats, debate_verdict, robustness):
    if not (debate_verdict.get("quantified_assessment") or debate_verdict.get("direct_answer")):
        return
    assessment = stats.get("debate_assessment_value", debate_verdict.get("quantified_assessment"))
    rec = stats.get("debate_recommendation", "See verdict")
    at = stats.get("debate_assessment_type", "assessment")
    stats["debate_summary"] = f"{rec}: {assessment:.0f}% {at}" if isinstance(assessment, (int, float)) else f"{rec}: {assessment} {at}"

    dp = stats.get("debate_assessment_value")
    if robustness["passed"] == 0 and isinstance(dp, (int, float)) and dp > 0:
        n = max(robustness["total"], stats.get("n_scenarios", 6), 6)
        passed = n if dp >= 50 else max(1, int(n * dp / 100))
        stats["robustness_ratio"] = f"{passed}/{n}"
        stats["robustness_pct"] = (passed / n) * 100
        stats["avg_success_probability"] = dp
        stats["debate_override_applied"] = True
        logger.info(f"📊 OVERRIDE: debate verdict ({dp}%) → {passed}/{n} scenarios pass")


def _build_diagnostic_constraint(state, question_type):
    if question_type not in ("DIAGNOSTIC", "FORECAST", "HYBRID"):
        return ""
    cp = state.get('consensus_probability', 0.45)
    cc = state.get('consensus_confidence', 0.55)
    n = len(state.get('agent_estimates', []))
    logger.warning(f"⚠️ PHASE 6: Injecting brief constraint for {question_type} (prob={cp*100:.0f}%)")
    return (
        f"\n═══════════════════════════════════════════════════════════════════════════════\n"
        f"⚠️ BINDING CONSTRAINT - YOU MUST USE THESE VALUES\n"
        f"═══════════════════════════════════════════════════════════════════════════════\n\n"
        f"QUESTION TYPE: {question_type}\nDo NOT frame as \"Option A vs Option B\".\n\n"
        f"EXPERT CONSENSUS (MANDATORY):\n• Probability: {cp*100:.0f}%\n• Confidence: {cc*100:.0f}%\n"
        f"• Source: {n} expert analysts\n\n"
        f"═══════════════════════════════════════════════════════════════════════════════\n"
    )


def _emergency_fallback(stats, error_msg):
    return (
        f"\n═══════════════════════════════════════════════════════════════════════════════\n"
        f"                    NSIC STRATEGIC INTELLIGENCE BRIEFING\n"
        f"═══════════════════════════════════════════════════════════════════════════════\n\n"
        f"## I. STRATEGIC VERDICT\n\n**VERDICT: ANALYSIS IN PROGRESS**\n\n"
        f"Synthesis error. Analysis completed with:\n"
        f"- {stats.get('n_facts',0)} facts, {stats.get('n_scenarios',0)} scenarios, {stats.get('n_turns',0)} debate turns\n\n"
        f"Error: {error_msg[:200]}\n"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Post-processing pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def _post_process(briefing, state, stats, debate_highlights, scenario_summaries,
                  agent_positions, debate_verdict, query):
    qt = state.get("question_type", "COMPARATIVE")

    # Phase 4: Aggregate agent estimates for DIAGNOSTIC/FORECAST
    if qt in ("DIAGNOSTIC", "FORECAST", "HYBRID"):
        _aggregate_diagnostic_estimates(state, agent_positions)

    # Scenario-aware synthesis
    synthesizer = ScenarioAwareSynthesis()
    sr = synthesizer.synthesize(
        scenarios=scenario_summaries, agent_positions=agent_positions,
        original_question=query, debate_summary=debate_highlights.get("synthesis_summary", ""),
    )
    if sr is None:
        from dataclasses import dataclass
        @dataclass
        class _D:
            recommendation: str = "Analysis Complete"
            confidence: float = 45.0
            scenario_agent_aligned: bool = True
            agent_recommendation: str = "Analysis Complete"
            reconciliation_note: str = ""
            decision: str = "CONDITIONAL"
        sr = _D()

    sgt = synthesizer._scenario_ground_truth or {
        'best_option': sr.recommendation, 'best_rate': sr.confidence,
        'worst_option': 'Unknown', 'worst_rate': 0.0, 'gap': 0.0,
    }

    calibrator = ConfidenceCalibrator()
    cal = calibrator.calibrate_from_scenarios(
        scenarios=scenario_summaries, agent_positions=agent_positions, original_question=query,
    )

    best_rate = cap_unrealistic_rates(sgt.get('best_rate', 0.0))
    worst_rate = cap_unrealistic_rates(sgt.get('worst_rate', 0.0))
    gap = best_rate - worst_rate
    question_type = classify_question_type(query)
    state['question_type'] = question_type

    if question_type in ("DIAGNOSTIC", "FORECAST", "HYBRID"):
        _extract_debate_probability(state)

    cc, ta = _count_consensus(agent_positions, sgt.get('best_option', ''), gap)
    calibrated = calculate_calibrated_confidence(gap=gap, consensus_count=cc, total_agents=ta)
    state["calibrated_confidence"] = calibrated
    state["confidence_inputs"] = {"gap": gap, "consensus_count": cc, "total_agents": ta}

    dw = _clean_name(sgt.get('best_option', 'Strategic Initiative'))
    dl = _clean_name(sgt.get('worst_option', 'Alternative'))

    vr = determine_verdict(calibrated / 100.0, 'COMPARATIVE')
    va = {'GO': 'APPROVE', 'CONDITIONAL GO': 'CONDITIONAL', 'RECONSIDER': 'RECONSIDER', 'NO GO': 'REJECT'}.get(vr['short_verdict'], vr['short_verdict'])

    inv_m = re.search(r'\$?([\d.]+)\s*(billion|million|B|M|k)', query, re.IGNORECASE)
    inv_str = f"${inv_m.group(1)}{inv_m.group(2).upper()}" if inv_m else "allocated budget"
    is_tied = gap < 5.0

    # Build & apply programmatic head
    qts = state.get("question_type", "COMPARATIVE")
    if qts in ("DIAGNOSTIC", "FORECAST", "HYBRID"):
        cp = state.get('consensus_probability', 0.45)
        ccf = state.get('consensus_confidence', 0.55)
        ests = state.get('agent_estimates', [])
        ne = len(ests) if ests else stats.get('n_experts', 7)
        ar = f"{min(ests)*100:.0f}% - {max(ests)*100:.0f}%" if ests else f"{max(0,cp*100-15):.0f}% - {min(100,cp*100+15):.0f}%"
        dvr = determine_verdict(cp, qts)
        head = build_programmatic_head_diagnostic(
            verdict_action=dvr['verdict'], consensus_prob=cp, consensus_conf=ccf,
            n_estimates=ne, agent_range=ar, question_type=qts, verdict_recommendation=dvr['recommendation'],
        )
    else:
        head = build_programmatic_head_comparative(
            verdict_action=va, display_winner=dw, display_loser=dl, best_rate=best_rate,
            worst_rate=worst_rate, gap=gap, is_tied=is_tied, consensus_count=cc,
            total_agents=ta, calibrated_conf=calibrated, inv_str=inv_str,
        )

    briefing = apply_section_override(briefing, head)
    briefing = correct_body_rates(briefing, best_rate, worst_rate)

    uncertainty = generate_honest_uncertainty_section(cal)
    if not sr.scenario_agent_aligned or cal.is_close_call:
        s2 = briefing.find("## II.")
        if s2 > 0:
            briefing = briefing[:s2] + "\n" + uncertainty + "\n\n" + briefing[s2:]

    _store_verdict(state, sr, cal, calibrated, sgt, gap, best_rate, worst_rate, question_type)

    if qts in ("DIAGNOSTIC", "FORECAST", "HYBRID"):
        _override_diagnostic_verdict(state, sr)

    # Summary-brief alignment
    gtr = sgt.get('best_rate', 50.0)
    gtg = sgt.get('gap', 0)
    is_tied_gt = gtg < 5.0
    dc = _derive_confidence(gtr, gtg, is_tied_gt)

    vrf = determine_verdict(dc / 100.0, state.get('question_type', 'COMPARATIVE'))
    ad = vrf['short_verdict']
    if is_tied_gt and ad == 'GO':
        ad = 'CONDITIONAL GO'

    ccf_final = state.get("calibrated_confidence", dc)
    state.setdefault("debate_verdict", {}).update({
        "aligned_verdict": vrf['verdict'], "aligned_decision": ad,
        "probability": ccf_final, "confidence": ccf_final,
        "recommendation": sgt.get('best_option', sr.recommendation),
        "is_tied": is_tied_gt, "scenario_gap": gtg,
        "best_rate": sgt.get('best_rate', 0), "worst_rate": sgt.get('worst_rate', 0),
    })

    old_conf = stats.get("confidence", 75)
    new_conf = int(round(dc))
    briefing = fix_confidence_mentions(briefing, old_conf, new_conf)
    briefing = enforce_calibrated_confidence(briefing, state.get("calibrated_confidence", 70))

    ar_name = sr.recommendation if hasattr(sr, 'recommendation') else sgt.get('best_option', '')
    briefing = apply_hedge_removal(briefing, ar_name)

    adt = "GO" if dc >= 60 else "CONDITIONAL GO" if dc >= 45 else "RECONSIDER" if dc >= 30 else "NO GO"
    briefing = inject_consensus_header(
        briefing, ar_name, best_rate, sgt.get('worst_rate', worst_rate),
        sgt.get('worst_option', 'Alternative'), sgt.get('gap', gtg),
        sgt.get('gap', gtg) >= 5.0, cc, ta, new_conf, adt,
    )
    briefing = fix_rate_ranges(briefing, sgt.get('best_rate', 0), sgt.get('worst_rate', 0))
    briefing = correct_deflated_rates(briefing, sgt.get('worst_rate', 0), sgt.get('gap', 0))
    briefing = add_data_integrity_note(
        briefing, sgt.get('gap', 0), sgt.get('best_rate', 0),
        sgt.get('worst_rate', 0), state.get("question_type", "COMPARATIVE"),
    )
    state["confidence_score"] = calibrated / 100
    return briefing, state


def _aggregate_diagnostic_estimates(state, agent_positions):
    conversation = state.get("conversation_history", [])
    final_out, open_out = [], []
    for t in conversation:
        if not isinstance(t, dict):
            continue
        c = t.get("message", t.get("content", ""))
        ph = t.get("phase", "").lower()
        tt = t.get("type", "").lower()
        if not c:
            continue
        if "final" in ph or "final" in tt or "consensus" in ph:
            final_out.append(c)
        else:
            open_out.append(c)
    for pos in agent_positions:
        c = pos.get('rationale', pos.get('position', str(pos))) if isinstance(pos, dict) else str(pos)
        final_out.append(c)

    outputs = final_out or open_out
    result = aggregate_agent_estimates(outputs)
    if result.get('estimates'):
        state['agent_estimates'] = [e['central'] for e in result['estimates']]
    state['consensus_probability'] = result['consensus_probability']
    state['consensus_confidence'] = result['consensus_confidence']
    state['consensus_spread'] = result['spread']
    state['monte_carlo_valid'] = False


def _extract_debate_probability(state):
    fv = extract_final_debate_verdict(state)
    fp, fc = None, None
    if fv and fv.get('quantified_assessment'):
        a = fv['quantified_assessment']
        rm = re.search(r'(\d+)\s*[-–]\s*(\d+)', a)
        sm = re.search(r'(\d+(?:\.\d+)?)', a)
        if rm:
            fp = (int(rm.group(1)) + int(rm.group(2))) / 2 / 100
        elif sm:
            fp = float(sm.group(1)) / 100
        if fv.get('confidence_level'):
            fc = fv['confidence_level']
            if fc > 1:
                fc /= 100

    if fp and fp > 0:
        state['consensus_probability'] = fp
        state['consensus_confidence'] = fc if fc else min(0.65, fp + 0.1)
        return

    ds = state.get("debate_synthesis", "")
    for pat in [r'~?\s*(\d{1,2}(?:\.\d+)?)\s*%\s*(?:probability|chance|likelihood|success)',
                r'(?:probability|chance)\s*(?:of|at)?\s*~?\s*(\d{1,2}(?:\.\d+)?)\s*%']:
        m = re.search(pat, ds, re.IGNORECASE)
        if m:
            state['consensus_probability'] = float(m.group(1)) / 100
            state['consensus_confidence'] = min(0.65, float(m.group(1)) / 100 + 0.1)
            return
    f = state.get('feasibility_check') or {}
    state['consensus_probability'] = f.get('ratio', 0.45) if isinstance(f, dict) else 0.45
    state['consensus_confidence'] = 0.55


def _count_consensus(positions, best_opt, gap):
    total = len(positions) if positions else 5
    wl = best_opt.lower()
    count = sum(
        1 for p in positions
        if any(w in str(p.get('recommendation', '') if isinstance(p, dict) else p).lower()
               for w in [w2 for w2 in wl.split() if len(w2) > 3] or [wl])
    )
    if count == 0 and gap >= 5:
        count = total
    return count, total


def _clean_name(name):
    if ' - ' in name:
        name = name.split(' - ')[-1]
    elif 'Option ' in name and len(name) > 10:
        m = re.search(r'\((.*?)\)', name)
        if m:
            name = m.group(1)
    return name[:60] + "..." if len(name) > 60 else name


def _store_verdict(state, sr, cal, calibrated, sgt, gap, best_rate, worst_rate, qt):
    state["debate_verdict"] = {
        "recommendation": sr.recommendation,
        "probability": state.get("calibrated_confidence", cal.recommended_confidence),
        "confidence": state.get("calibrated_confidence", cal.recommended_confidence),
        "decision": getattr(sr, 'decision', 'CONDITIONAL'),
        "scenario_agent_aligned": sr.scenario_agent_aligned,
        "reconciliation_applied": not sr.scenario_agent_aligned,
        "is_close_call": cal.is_close_call,
        "scenario_gap": gap,
        "ground_truth_winner": sgt['best_option'],
        "ground_truth_rate": best_rate,
        "ground_truth_loser": sgt['worst_option'],
        "ground_truth_loser_rate": worst_rate,
        "ground_truth_gap": gap,
        "question_type": qt,
        "model_reliable": sgt.get('model_reliable', True),
        "reliability_reason": sgt.get('reliability_reason') if not sgt.get('model_reliable', True) else None,
    }
    state["confidence_score"] = state.get("calibrated_confidence", cal.recommended_confidence) / 100


def _override_diagnostic_verdict(state, sr):
    qt = state.get("question_type", "COMPARATIVE")
    cp = state.get('consensus_probability', 0.45)
    cc = state.get('consensus_confidence', 0.55)
    state["debate_verdict"] = {
        "recommendation": sr.recommendation,
        "probability": cp * 100, "confidence": cc * 100,
        "decision": getattr(sr, 'decision', 'CONDITIONAL'),
        "scenario_agent_aligned": False, "reconciliation_applied": False,
        "is_close_call": state.get('consensus_spread', 0) > 0.15,
        "scenario_gap": state.get('consensus_spread', 0) * 100,
        "source": "agent_consensus", "monte_carlo_valid": False,
        "question_type": qt,
        "n_agent_estimates": len(state.get('agent_estimates', [])),
        "consensus_spread": state.get('consensus_spread', 0) * 100,
    }
    state["confidence_score"] = cc
    state["calibrated_confidence"] = cc * 100


def _derive_confidence(rate, gap, is_tied):
    if is_tied:
        return min(rate, 60.0)
    if gap < 10:
        return min(rate, 70.0)
    if gap < 20:
        return min(rate, 80.0)
    return rate


def _run_final_validation(state):
    qt = state.get("question_type", "COMPARATIVE")
    if qt in ("DIAGNOSTIC", "FORECAST", "HYBRID"):
        validate_output_consistency(state, qt)

    final = state.get('final_synthesis', '')
    bp = _extract_brief_probability(final)
    if bp and bp < 85:
        state.setdefault('debate_verdict', {}).update({
            'probability': bp, 'confidence': min(bp + 15, 70),
            'source': 'brief_extraction', 'brief_aligned': True,
        })

    try:
        gt = extract_ground_truth(state)
        state['ground_truth'] = gt.to_dict()
        if bp and bp < 85:
            state['ground_truth']['probability'] = bp / 100
            state['ground_truth']['probability_percent'] = bp
            state['ground_truth']['source'] = 'brief_extraction'
        if final:
            w = validate_no_fabrication(final, gt)
            if w:
                state['fabrication_warnings'] = w
        logger.info(f"✅ GROUND TRUTH: type={gt.question_type.value}, prob={gt.probability*100:.1f}%")
    except Exception as e:
        logger.error(f"❌ Ground truth extraction failed: {e}")


def _extract_brief_probability(text: str) -> Optional[float]:
    if not text:
        return None
    for pat in [
        r'(?:probability|likelihood|chances?).*?(\d{1,2})\s*[-–]\s*(\d{1,2})\s*%',
        r'(\d{1,2})\s*[-–]\s*(\d{1,2})\s*%\s*(?:probability|likelihood|chances?)',
        r'estimated at\s*(\d{1,2})\s*[-–]\s*(\d{1,2})\s*%',
        r'success.*?(\d{1,2})\s*[-–]\s*(\d{1,2})\s*%',
        r'~(\d{1,2})\s*%\s*(?:probability|likelihood|success)',
        r'(\d{1,2})\s*%\s*(?:to|[-–])\s*(\d{1,2})\s*%',
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return (float(m.group(1)) + float(m.group(2))) / 2 if len(m.groups()) == 2 and m.group(2) else float(m.group(1))
    v = re.search(r'STRATEGIC VERDICT.*?(?=##|\Z)', text, re.DOTALL | re.IGNORECASE)
    if v:
        pcts = [float(p) for p in re.findall(r'(\d{1,2})\s*%', v.group(0)) if 20 <= float(p) <= 80]
        if pcts:
            return pcts[0]
    return None
