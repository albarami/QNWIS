"""
Post-processing and formatting helpers for the Legendary Synthesis pipeline.

Handles programmatic executive summary override, confidence enforcement,
fabricated rate correction, hedge removal, and other brief post-processing.
"""

from __future__ import annotations

import logging
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# PROGRAMMATIC EXECUTIVE SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

def build_programmatic_head_diagnostic(
    verdict_action: str,
    consensus_prob: float,
    consensus_conf: float,
    n_estimates: int,
    agent_range: str,
    question_type: str,
    verdict_recommendation: str,
) -> str:
    """Build the programmatic executive summary for DIAGNOSTIC/FORECAST questions."""
    return f"""## I. STRATEGIC VERDICT

**VERDICT: {verdict_action}**

**Direct Answer to Your Question:**
- **Probability of Success:** {consensus_prob*100:.0f}%
- **Confidence Level:** {consensus_conf*100:.0f}%

**Expert Consensus:**
- Based on analysis from {n_estimates} domain experts
- Expert estimate range: {agent_range}
- Source: Agent consensus (NOT Monte Carlo simulation)

**⚠️ IMPORTANT NOTE:** This is a {question_type.lower()} question, not a comparative A/B analysis. The probability estimate reflects expert judgment about a single outcome, not a comparison between options.

**BOTTOM LINE FOR DECISION-MAKERS:**
• **Assessment:** {consensus_prob*100:.0f}% probability of achieving stated objectives
• **Confidence:** {"Moderate" if consensus_conf < 0.65 else "High"} - based on expert agreement
• **Recommendation:** {verdict_recommendation}
"""


def build_programmatic_head_comparative(
    verdict_action: str,
    display_winner: str,
    display_loser: str,
    best_rate: float,
    worst_rate: float,
    gap: float,
    is_tied: bool,
    consensus_count: int,
    total_agents: int,
    calibrated_conf: int,
    inv_str: str,
) -> str:
    """Build the programmatic executive summary for COMPARATIVE questions."""
    tied_disclaimer = ""
    if is_tied:
        tied_disclaimer = f"""
**⚠️ TIED SCENARIO NOTICE:** The {gap:.1f}pp difference between options is within statistical margin of error. This recommendation is based on **secondary factors** (strategic alignment, execution risk, workforce absorption) rather than probability advantage alone. A hybrid 60/40 approach may be appropriate.
"""

    return f"""## I. STRATEGIC VERDICT

**VERDICT: {verdict_action}**

**RECOMMENDATION: {display_winner.upper()}**

**Scenario Analysis (Monte Carlo - EXACT VALUES):**
- **{display_winner}:** {best_rate:.1f}% success probability
- **{display_loser}:** {worst_rate:.1f}% success probability
- **Gap:** {gap:.1f}pp {"(TIED - within statistical margin)" if is_tied else "(DECISIVE)" if gap >= 15 else "(CLEAR WINNER)"}
{tied_disclaimer}
**Expert Consensus:** {consensus_count}/{total_agents} analysts recommend {display_winner}

**Confidence: {calibrated_conf}%** {"(CAPPED - tied scenario uncertainty)" if is_tied else "(High - Clear Winner)" if calibrated_conf >= 70 else "(Moderate)"}

**BOTTOM LINE FOR DECISION-MAKERS:**
• **Primary Action:** {"Consider " + inv_str + " allocation weighted toward " + display_winner + " (60/40 acceptable for tied scenario)" if is_tied else "Allocate full " + inv_str + " to " + display_winner}
• **Critical Warning:** {"For tied scenarios, a balanced approach may be appropriate" if is_tied else "Avoid 'balanced' or 'dual-track' hedging which dilutes strategic impact"}
• **Expected Outcome:** {best_rate:.1f}% probability of achieving strategic targets
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION OVERRIDE
# ═══════════════════════════════════════════════════════════════════════════════

def apply_section_override(briefing: str, programmatic_head: str) -> str:
    """Replace Section I of the briefing with the programmatic head."""
    header_patterns = [
        r'## I\. STRATEGIC VERDICT.*?(?=## II\.)',
        r'## I\. EXECUTIVE SUMMARY.*?(?=## II\.)',
        r'##\s*STRATEGIC VERDICT.*?(?=## II\.)',
        r'##\s*EXECUTIVE SUMMARY.*?(?=## II\.)',
        r'#\s*STRATEGIC VERDICT.*?(?=## II\.)',
        r'#\s*I\.\s*.*?(?=## II\.)',
    ]

    for pattern in header_patterns:
        if re.search(pattern, briefing, flags=re.DOTALL | re.IGNORECASE):
            briefing = re.sub(
                pattern,
                programmatic_head + '\n\n',
                briefing,
                flags=re.DOTALL | re.IGNORECASE
            )
            logger.info(f"✅ PROGRAMMATIC OVERRIDE matched pattern: {pattern[:30]}...")
            return briefing

    logger.warning("⚠️ No header pattern matched - prepending programmatic head")
    return programmatic_head + "\n\n" + briefing


# ═══════════════════════════════════════════════════════════════════════════════
# RATE CORRECTION
# ═══════════════════════════════════════════════════════════════════════════════

def replace_fabricated_rates(text: str, actual_best: float, actual_worst: float) -> str:
    """Replace fabricated rates with actual rates from scenario data."""
    tolerance = 10

    def rate_replacer(match: re.Match) -> str:
        rate_val = float(match.group(1))
        if abs(rate_val - actual_best) <= tolerance or abs(rate_val - actual_worst) <= tolerance:
            return match.group(0)
        if rate_val in [10, 15, 20, 25, 30, 35, 100]:
            return match.group(0)
        if 40 <= rate_val <= 99:
            if rate_val > (actual_best + actual_worst) / 2:
                logger.info(f"📝 Correcting fabricated rate: {rate_val}% → {actual_best:.1f}%")
                return f"{actual_best:.1f}%"
            else:
                logger.info(f"📝 Correcting fabricated rate: {rate_val}% → {actual_worst:.1f}%")
                return f"{actual_worst:.1f}%"
        return match.group(0)

    return re.sub(r'\b(\d{2,3})%', rate_replacer, text)


def correct_body_rates(briefing: str, best_rate: float, worst_rate: float) -> str:
    """Correct fabricated rates in the Brief body (after Section I)."""
    section_ii_idx = briefing.find('## II.')
    if section_ii_idx > 0:
        brief_body = briefing[section_ii_idx:]
        corrected_body = replace_fabricated_rates(brief_body, best_rate, worst_rate)
        if corrected_body != brief_body:
            briefing = briefing[:section_ii_idx] + corrected_body
            logger.info("✅ RATE FABRICATION CORRECTED in Brief body")
    return briefing


def fix_rate_ranges(briefing: str, actual_best: float, actual_worst: float) -> str:
    """Replace common range patterns the LLM generates with exact values."""
    range_patterns = [
        (r'6[0-9][-–]7[0-9]%', f'{actual_best:.0f}%'),
        (r'6[0-9][-–]6[0-9]%', f'{actual_best:.0f}%'),
        (r'4[0-9][-–]5[0-9]%', f'{actual_worst:.0f}%'),
        (r'5[0-9][-–]6[0-9]%', f'{actual_worst:.0f}%' if actual_worst > 50 else f'{actual_best:.0f}%'),
        (r'(?:approximately|about|roughly|around)\s+6[0-9]%', f'{actual_best:.0f}%'),
        (r'(?:approximately|about|roughly|around)\s+[45][0-9]%', f'{actual_worst:.0f}%'),
    ]

    replacements = 0
    for pattern, replacement in range_patterns:
        new_briefing = re.sub(pattern, replacement, briefing, flags=re.IGNORECASE)
        if new_briefing != briefing:
            replacements += 1
            briefing = new_briefing

    if replacements > 0:
        logger.info(f"✅ RATE RANGES FIXED: {replacements} ranges replaced with exact values")
        logger.info(f"   Best rate: {actual_best:.1f}%, Worst rate: {actual_worst:.1f}%")
    return briefing


def correct_deflated_rates(briefing: str, actual_worst: float, actual_gap: float) -> str:
    """Fix deflated loser rates in tied scenarios."""
    is_tied = actual_gap < 5.0
    if not (is_tied and actual_worst > 40):
        return briefing

    deflation_threshold = actual_worst - 8

    def corrector(match: re.Match) -> str:
        rate_val = float(match.group(1))
        if 40 <= rate_val < deflation_threshold:
            logger.warning(f"⚠️ DEFLATED RATE DETECTED: {rate_val}% (should be ~{actual_worst:.0f}%)")
            return f"{actual_worst:.0f}%"
        return match.group(0)

    section_ii_start = briefing.find('## II.')
    if section_ii_start > 0:
        brief_body = briefing[section_ii_start:]
        corrected_body = re.sub(r'\b(\d{2})%', corrector, brief_body)
        if corrected_body != brief_body:
            briefing = briefing[:section_ii_start] + corrected_body
            logger.info("✅ CORRECTED DEFLATED RATES in Brief body for tied scenario")
    return briefing


# ═══════════════════════════════════════════════════════════════════════════════
# HEDGE REMOVAL
# ═══════════════════════════════════════════════════════════════════════════════

def get_hedged_patterns(agent_recommendation: str) -> List[Tuple[str, str]]:
    """Return domain-agnostic (pattern, replacement) pairs for hedge removal."""
    r = agent_recommendation
    return [
        (r'dual[- ]track\s+(?:capital\s+)?(?:allocation|diversification|approach|strategy)', f'{r} strategy'),
        (r'calibrated\s+dual[- ]track', f'{r}'),
        (r'dual[- ]track', f'{r}'),
        (r'balanced\s+(?:pathway|approach|allocation|strategy)', f'{r} as primary pathway'),
        (r'hybrid\s+(?:approach|strategy|allocation)', f'{r} strategy'),
        (r'hedge\s+(?:sectoral\s+)?risk', f'prioritize {r} based on expert consensus'),
        (r'50%\s+(?:to\s+)?(?:\w+)\s+(?:and|&)\s+50%\s+(?:to\s+)?(?:\w+)', f'primary allocation to {r}'),
        (r'\d+%\s+(?:to\s+)?(?:\w+)\s+(?:and|&)\s+\d+%\s+(?:to\s+)?(?:\w+)', f'primary allocation to {r}'),
        (r'\d+/\d+\s+(?:\w+[- ])?(?:investment|allocation)\s+mix', f'{r} focused investment'),
        (r'(?:maintain|adopt|pursue)\s+\d+/\d+\s+(?:\w+[- ])?(?:investment|allocation)', f'focus on {r}'),
        (r'moderate\s+strategic\s+resilience', f'strong support for {r}'),
        (r'neither\s+option\s+(?:clearly\s+)?dominates', f'{r} is recommended based on secondary factors'),
        (r'(?:optimal|best)\s+(?:approach|strategy)\s+(?:combines|integrates|balances)', f'{r} is the optimal strategy'),
        (r'(?:accelerated\s+)?integration\s+of\s+(?:\w+)\s+(?:into|with)\s+(?:\w+)', f'{r} development'),
        (r'combine\s+(?:steady\s+)?(?:\w+\s+)?(?:revenues?|investments?)\s+with\s+(?:\w+)', f'prioritize {r}'),
        (r'most\s+resilient\s+pathways?\s+combine', f'{r} offers the most resilient pathway'),
        (r'pathways?\s+(?:that\s+)?combine\s+(?:\w+\s+)+with', f'{r} pathway'),
        (r'integrated\s+investment\s+in\s+(?:both|\w+)', f'focused investment in {r}'),
        (r'neither\s+pure\s+Option\s+[A-Z]\s+nor\s+pure\s+Option\s+[A-Z]', f'{r}'),
        (r'neither\s+(?:\w+)\s+alone\s+nor\s+(?:\w+)\s+alone', f'{r}'),
        (r'combination\s+of\s+both(?:\s+options?)?', f'{r}'),
        (r'blend\s+(?:of\s+)?(?:both|the\s+two)\s+(?:options?|approaches?)', f'{r}'),
        (r'\([^)]*50%[^)]*50%[^)]*\)', f'(primary allocation to {r})'),
        (r'\([^)]*balanced[^)]*investment[^)]*\)', f'(prioritize {r})'),
        (r'Maintain\s+balanced\s+investment', f'Prioritize {r}'),
        (r'balanced\s+investment\s*\([^)]*\)', f'{r} investment'),
        (r'pivot\s+between\s+(?:\w+)\s+and\s+(?:\w+)', f'focus on {r}'),
        (r'build\s+adaptive\s+capacity', f'execute {r} strategy'),
    ]


def apply_hedge_removal(briefing: str, agent_recommendation: str) -> str:
    """Remove hedged language and replace with agent consensus recommendation."""
    patterns = get_hedged_patterns(agent_recommendation)
    for pattern, replacement in patterns:
        briefing = re.sub(pattern, replacement, briefing, flags=re.IGNORECASE)

    hedge_indicators = [
        'combine', 'integration', 'dual-track', 'dual track', 'balanced',
        '50%', '/50', '60/', '40/', 'mix of', 'hybrid'
    ]
    exec_start = briefing.find('## I.')
    exec_end = briefing.find('## II.') if briefing.find('## II.') > 0 else len(briefing)
    exec_summary = briefing[exec_start:exec_end] if exec_start > 0 else ""
    remaining = [h for h in hedge_indicators if h in exec_summary.lower()]
    if remaining:
        logger.warning(f"⚠️ FIX RUN 27: Executive Summary still contains hedging: {remaining}")

    return briefing


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIDENCE ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def fix_confidence_mentions(briefing: str, old_conf: int, new_conf: int) -> str:
    """Replace LLM-generated confidence with derived confidence throughout."""
    briefing = re.sub(rf'\b{old_conf}%\s*Confidence\b', f'{new_conf}% Confidence', briefing, flags=re.IGNORECASE)
    briefing = re.sub(rf'confidence[:\s]+{old_conf}%', f'confidence: {new_conf}%', briefing, flags=re.IGNORECASE)
    briefing = re.sub(rf'Confidence\s+Level[:\s]+{old_conf}%', f'Confidence Level: {new_conf}%', briefing, flags=re.IGNORECASE)
    briefing = re.sub(rf'\b{old_conf}%\s*(confidence|certain)', rf'{new_conf}% \1', briefing, flags=re.IGNORECASE)
    briefing = re.sub(r'High\s*\([~≈]?\s*\d+%\)', f'Moderate ({new_conf}%)', briefing, flags=re.IGNORECASE)
    briefing = re.sub(r'\([~≈]\s*\d+%\)', f'({new_conf}%)', briefing)
    briefing = re.sub(rf'[~≈]\s*{old_conf}%', f'{new_conf}%', briefing)

    if new_conf < 65:
        briefing = re.sub(r'\b(7[0-9]|8[0-5])%', f'{new_conf}%', briefing)

    return briefing


def enforce_calibrated_confidence(briefing: str, calibrated_conf: float) -> str:
    """Replace any LLM-generated confidence with calibrated value throughout."""
    conf_int = int(calibrated_conf)
    patterns = [
        (r'(?i)confidence\s*level[:\s]+\d{1,3}%', f'Confidence Level: {conf_int}%'),
        (r'(?i)confidence[:\s]+\d{1,3}%', f'Confidence: {conf_int}%'),
        (r'(?i)confidence\s+(?:level\s+)?of\s+\d{1,3}%', f'confidence of {conf_int}%'),
        (r'(?i)\b\d{1,3}%\s+confidence\b', f'{conf_int}% confidence'),
    ]
    for pattern, replacement in patterns:
        briefing = re.sub(pattern, replacement, briefing)

    calibrated_decimal = calibrated_conf / 100
    if calibrated_conf < 70:
        decimal_patterns = [
            (r'\b0\.8[0-9]\b', f'{calibrated_decimal:.2f}'),
            (r'\b0\.7[5-9]\b', f'{calibrated_decimal:.2f}'),
            (r'\b0\.9[0-9]\b', f'{calibrated_decimal:.2f}'),
        ]
        for pattern, replacement in decimal_patterns:
            briefing = re.sub(pattern, replacement, briefing)
        logger.info(f"✅ DECIMAL CONFIDENCE ENFORCED: {calibrated_decimal:.2f} applied")

    logger.info(f"✅ CONFIDENCE ENFORCED: {conf_int}% applied throughout Brief")
    return briefing


# ═══════════════════════════════════════════════════════════════════════════════
# CONSENSUS HEADER INJECTION & DATA INTEGRITY NOTES
# ═══════════════════════════════════════════════════════════════════════════════

def inject_consensus_header(
    briefing: str,
    agent_recommendation: str,
    best_rate: float,
    worst_rate: float,
    loser_option: str,
    gap_pp: float,
    is_clear_winner: bool,
    consensus_count: int,
    total_agents: int,
    new_conf_int: int,
    aligned_decision_text: str,
) -> str:
    """Inject the consensus recommendation header into Section I."""
    if consensus_count < total_agents - 1:
        return briefing

    exec_marker = "## I. EXECUTIVE SUMMARY"
    if exec_marker not in briefing:
        return briefing

    if is_clear_winner:
        insert = f"""
**🎯 DECISIVE RECOMMENDATION: {agent_recommendation.upper()}**

- **Success Probability:** {best_rate:.1f}% vs {worst_rate:.1f}% ({loser_option})
- **Advantage:** {gap_pp:.1f} percentage points (CLEAR WINNER ≥5pp threshold)
- **Expert Consensus:** {consensus_count}/{total_agents} analysts recommend {agent_recommendation}
- **Confidence:** {new_conf_int}%
- **Decision:** {aligned_decision_text}

"""
    else:
        insert = f"""
**🎯 RECOMMENDATION: {agent_recommendation.upper()}** (Tied Scenario Resolution)

- **Success Probability:** {best_rate:.1f}% vs {worst_rate:.1f}% ({loser_option})
- **Scenario Gap:** {gap_pp:.1f}pp (statistically tied, <5pp threshold)
- **Expert Consensus:** {consensus_count}/{total_agents} analysts recommend {agent_recommendation}
- **Decision Basis:** Secondary factors (implementation risk, strategic alignment, workforce absorption)
- **Confidence:** {new_conf_int}% (capped for tied scenarios)
- **Decision:** {aligned_decision_text}

**Why {agent_recommendation} wins despite tied scenarios:** When quantitative analysis shows near-identical success rates, experts evaluated qualitative factors including execution feasibility, strategic fit with national priorities, and competitive positioning.

"""

    briefing = briefing.replace(exec_marker, exec_marker + insert)
    logger.info(
        f"📊 INJECTED CONSENSUS RECOMMENDATION: {agent_recommendation} "
        f"({'CLEAR WINNER' if is_clear_winner else 'TIED + secondary factors'})"
    )
    return briefing


def add_data_integrity_note(
    briefing: str,
    actual_gap: float,
    actual_best: float,
    actual_worst: float,
    question_type: str,
) -> str:
    """Add a data integrity note for tied scenarios (COMPARATIVE questions only)."""
    is_tied = actual_gap < 5.0

    if question_type != "COMPARATIVE":
        if is_tied:
            logger.info(f"📊 FIX RUN 55: Skipping Monte Carlo gap note for {question_type} question")
        return briefing

    if not is_tied:
        return briefing

    section_i_end = briefing.find('## II.')
    if section_i_end <= 0:
        return briefing

    if "DATA INTEGRITY" in briefing[:section_i_end]:
        return briefing

    note = (
        f"\n\n**DATA INTEGRITY NOTE:** The scenario analysis shows a "
        f"**{actual_gap:.1f}pp gap** ({actual_best:.1f}% vs {actual_worst:.1f}%), "
        f"which is within statistical margin of error. The recommendation is based on "
        f"secondary qualitative factors, not probability advantage.\n\n"
    )
    briefing = briefing[:section_i_end] + note + briefing[section_i_end:]
    logger.info("✅ Added data integrity note for tied scenario")
    return briefing
