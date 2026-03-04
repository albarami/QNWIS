"""
Debate verdict extraction for the Legendary Synthesis pipeline.

Extracts structured verdicts (quantified assessments, recommendations,
confidence levels) from debate conversation turns.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from ...state import IntelligenceState

logger = logging.getLogger(__name__)


def _parse_probability_from_text(text: str) -> Optional[float]:
    """
    Parse probability from various formats:
    - "≈62%" -> 0.62
    - "60-62%" -> 0.61 (midpoint)
    - "Option A: 46%, Option B: 58%" -> 0.58 (take higher for forecast)
    """
    if not text:
        return None
    text = str(text)

    if 'Option' in text or ' vs' in text.lower():
        matches = re.findall(r'(\d+(?:\.\d+)?)\s*%', text)
        if matches:
            return max(float(m) for m in matches) / 100

    range_match = re.search(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*%', text)
    if range_match:
        low, high = float(range_match.group(1)), float(range_match.group(2))
        return (low + high) / 200

    single_match = re.search(r'[≈~]?\s*(\d+(?:\.\d+)?)\s*%', text)
    if single_match:
        return float(single_match.group(1)) / 100

    return None


def try_extract_verdict_from_message(message: str, turn: Dict) -> Optional[Dict[str, Any]]:
    """
    FIX RUN 53: Helper to extract verdict from a single turn's message.
    Used to prioritize Moderator synthesis extraction.
    """
    verdict: Dict[str, Any] = {
        "direct_answer": None,
        "quantified_assessment": None,
        "assessment_type": None,
        "recommendation": None,
        "confidence_level": None,
        "decision": None,
        "key_findings": [],
        "areas_of_consensus": [],
        "remaining_disagreements": [],
        "risks_and_mitigations": [],
        "next_steps": [],
        "source": f"turn_{turn.get('turn', 'unknown')}",
    }

    if not message:
        logger.warning("⚠️ FIX RUN 55: Empty message passed to try_extract_verdict_from_message")
        return None

    # FIX RUN 55: First try to parse the ENTIRE message as JSON
    try:
        data = json.loads(message)
        logger.info(f"📊 FIX RUN 55: Successfully parsed entire message as JSON, keys: {list(data.keys())[:5]}")

        verdict["direct_answer"] = data.get("direct_answer", data.get("answer", data.get("conclusion")))

        if "quantified_assessment" in data:
            qa = data["quantified_assessment"]
            if isinstance(qa, dict):
                verdict["quantified_assessment"] = qa.get("value", qa.get("score", "N/A"))
                verdict["assessment_type"] = qa.get("metric_type", "probability")
                logger.info(f"📊 FIX RUN 55: Found quantified_assessment.value = {verdict['quantified_assessment']}")
            elif isinstance(qa, str):
                verdict["quantified_assessment"] = qa
                logger.info(f"📊 FIX RUN 55: Found quantified_assessment (string) = {qa}")

        verdict["recommendation"] = data.get("recommendation")
        verdict["decision"] = data.get("go_no_go_decision", data.get("decision"))

        conf = data.get("confidence_level", data.get("confidence"))
        if conf is not None:
            if isinstance(conf, str):
                conf_str = conf.replace('≈', '').replace('%', '').strip()
                try:
                    conf = float(conf_str)
                except ValueError:
                    conf = None
            verdict["confidence_level"] = conf if isinstance(conf, (int, float)) else None

        for key in ["areas_of_consensus", "remaining_disagreements",
                     "risks_and_mitigations", "next_steps", "key_findings"]:
            items = data.get(key, [])
            if isinstance(items, list) and items:
                verdict[key] = items[:6]

        if verdict["quantified_assessment"] or verdict["direct_answer"]:
            logger.info("📊 FIX RUN 55: Extraction SUCCESS from full JSON parse")
            return verdict
        else:
            logger.warning("⚠️ FIX RUN 55: JSON parsed but no quantified_assessment or direct_answer found")
    except json.JSONDecodeError as e:
        logger.info(f"📊 FIX RUN 55: Could not parse entire message as JSON ({e}), trying embedded JSON extraction...")

    # FALLBACK: Try to find JSON blocks within the message
    json_candidates = _extract_json_candidates(message)
    logger.info(f"📊 FIX RUN 55: Found {len(json_candidates)} JSON candidates in message")

    for json_str in json_candidates:
        try:
            data = json.loads(json_str)

            verdict["direct_answer"] = data.get("direct_answer", data.get("answer", data.get("conclusion")))

            for key in ["quantified_assessment", "primary_metric", "success_probability",
                        "assessment", "probability", "confidence", "impact", "risk_level"]:
                if key in data:
                    val = data[key]
                    if isinstance(val, dict):
                        verdict["quantified_assessment"] = f"{val.get('value', val.get('score', 'N/A'))}"
                        verdict["assessment_type"] = val.get('metric_type', 'probability')
                    elif isinstance(val, (int, float)):
                        verdict["quantified_assessment"] = f"{val}%"
                        verdict["assessment_type"] = "probability"
                    elif isinstance(val, str):
                        verdict["quantified_assessment"] = val
                        verdict["assessment_type"] = "qualitative"
                    break

            verdict["recommendation"] = data.get(
                "recommendation", data.get("recommended", data.get("direct_answer", data.get("action")))
            )
            verdict["decision"] = data.get("go_no_go_decision", data.get("decision"))

            conf = data.get("confidence_level", data.get("confidence"))
            if conf is not None:
                if isinstance(conf, str):
                    conf_str = conf.replace('≈', '').replace('%', '').strip()
                    try:
                        conf = float(conf_str)
                    except ValueError:
                        conf = None
                verdict["confidence_level"] = conf if isinstance(conf, (int, float)) else None

            for key, field in [("areas_of_consensus", "areas_of_consensus"),
                               ("remaining_disagreements", "remaining_disagreements"),
                               ("risks_and_mitigations", "risks_and_mitigations"),
                               ("next_steps", "next_steps"),
                               ("key_findings", "key_findings")]:
                items = data.get(key, [])
                if isinstance(items, list) and items:
                    verdict[field] = items[:6]

            if verdict["quantified_assessment"] or verdict["direct_answer"]:
                return verdict

        except json.JSONDecodeError:
            continue

    # Fallback: regex for probability ranges like "58-60%" or "≈58–60%"
    range_match = re.search(r'(?:≈|~)?(\d{1,2})\s*[-–]\s*(\d{1,2})\s*%', message)
    if range_match:
        low, high = int(range_match.group(1)), int(range_match.group(2))
        avg = (low + high) / 2
        verdict["quantified_assessment"] = f"{avg:.0f}%"
        verdict["assessment_type"] = "probability"
        logger.info(f"📊 FIX RUN 53: Extracted range {low}-{high}% → {avg:.0f}%")
        return verdict

    # Fallback: single percentage
    single_match = re.search(
        r'(\d{1,2}(?:\.\d+)?)\s*%\s*(?:probability|chance|likelihood|success|confidence)',
        message, re.IGNORECASE
    )
    if single_match:
        verdict["quantified_assessment"] = f"{single_match.group(1)}%"
        verdict["assessment_type"] = "probability"
        return verdict

    # FIX RUN 56: Handle corrupted Option A/B format
    option_matches = re.findall(
        r'Option\s*[AB]\s*\([^)]+\)\s*[—–-]\s*(\d+(?:\.\d+)?)\s*%',
        message, re.IGNORECASE
    )
    if option_matches:
        probs = [float(m) for m in option_matches]
        best_prob = max(probs)
        logger.warning("⚠️ FIX RUN 56: Found corrupted Option A/B format in FORECAST question")
        logger.warning(f"   Extracted probabilities: {probs}, using best: {best_prob}%")
        verdict["quantified_assessment"] = f"{best_prob}%"
        verdict["assessment_type"] = "probability"
        return verdict

    # Last resort
    prob = _parse_probability_from_text(message)
    if prob:
        verdict["quantified_assessment"] = f"{prob*100:.0f}%"
        verdict["assessment_type"] = "probability"
        logger.info(f"📊 FIX RUN 56: Extracted probability {prob*100:.0f}% from text")
        return verdict

    return None


def _extract_json_candidates(text: str) -> List[str]:
    """Extract potential JSON object strings from text using brace matching."""
    candidates: List[str] = []
    brace_depth = 0
    start_idx: Optional[int] = None
    for i, char in enumerate(text):
        if char == '{':
            if brace_depth == 0:
                start_idx = i
            brace_depth += 1
        elif char == '}':
            brace_depth -= 1
            if brace_depth == 0 and start_idx is not None:
                candidates.append(text[start_idx:i + 1])
                start_idx = None

    if not candidates:
        candidates = re.findall(r'\{[^{}]+\}', text, re.DOTALL)

    return candidates


def extract_final_debate_verdict(state: IntelligenceState) -> Dict[str, Any]:
    """
    Extract the final debate verdict with quantified assessments.

    FULLY DOMAIN AGNOSTIC: Works for ANY question type.

    CRITICAL FIX (Run 53): Prioritize the FINAL Moderator synthesis turn,
    not early agent opening positions.
    """
    conversation = state.get("conversation_history", []) or []
    debate_synthesis = state.get("debate_synthesis", "")

    verdict: Dict[str, Any] = {
        "direct_answer": None,
        "quantified_assessment": None,
        "assessment_type": None,
        "recommendation": None,
        "confidence_level": None,
        "decision": None,
        "key_findings": [],
        "areas_of_consensus": [],
        "remaining_disagreements": [],
        "risks_and_mitigations": [],
        "next_steps": [],
        "source": None,
    }

    # FIX RUN 53: FIRST look for Moderator's FINAL synthesis turn
    logger.info(f"📊 FIX RUN 53: Searching {len(conversation)} turns for Moderator synthesis...")
    moderator_synthesis_turn = None
    for turn in reversed(conversation):
        if isinstance(turn, dict):
            agent = turn.get("agent", "").lower()
            turn_type = turn.get("type", "").lower()
            phase = turn.get("phase", "").lower()

            if "moderator" in agent:
                logger.info(f"📊 FIX RUN 53: Moderator turn found - type='{turn_type}', phase='{phase}'")

            if "moderator" in agent and any(
                kw in turn_type or kw in phase
                for kw in ["synthesis", "consensus", "final", "conclusion", "verdict"]
            ):
                moderator_synthesis_turn = turn
                logger.info(f"📊 FIX RUN 53: ✅ Found Moderator synthesis at turn {turn.get('turn', '?')}, type='{turn_type}'")
                break

    if not moderator_synthesis_turn:
        logger.warning(f"⚠️ FIX RUN 53: No Moderator synthesis turn found in {len(conversation)} turns")

    if moderator_synthesis_turn:
        message = moderator_synthesis_turn.get("message", "")
        logger.info(f"📊 FIX RUN 55: Moderator message length: {len(message)} chars")
        logger.info(f"📊 FIX RUN 55: Moderator message preview: {message[:300]}...")

        extracted = try_extract_verdict_from_message(message, moderator_synthesis_turn)

        if extracted:
            logger.info(
                f"📊 FIX RUN 55: Extracted result: quantified_assessment="
                f"{extracted.get('quantified_assessment')}, direct_answer="
                f"{str(extracted.get('direct_answer', ''))[:50]}"
            )
        else:
            logger.warning("⚠️ FIX RUN 55: try_extract_verdict_from_message returned None")

        if extracted and (extracted.get("quantified_assessment") or extracted.get("direct_answer")):
            logger.info(
                f"📊 FIX RUN 53: Using Moderator synthesis: "
                f"{extracted.get('quantified_assessment', extracted.get('direct_answer', '')[:50])}"
            )
            return extracted
        else:
            logger.warning("⚠️ FIX RUN 55: Moderator synthesis found but extraction failed - falling back")

    # FALLBACK: Look for structured JSON in last 10 turns
    for turn in reversed(conversation[-10:]):
        message = turn.get("message", "") if isinstance(turn, dict) else ""

        json_candidates = _extract_json_candidates(message)

        for json_str in json_candidates:
            try:
                data = json.loads(json_str)

                verdict["direct_answer"] = data.get("direct_answer", data.get("answer", data.get("conclusion")))

                for key in ["quantified_assessment", "primary_metric", "success_probability",
                            "assessment", "probability", "confidence", "impact", "risk_level"]:
                    if key in data:
                        val = data[key]
                        if isinstance(val, dict):
                            verdict["quantified_assessment"] = f"{val.get('value', val.get('score', 'N/A'))}"
                            verdict["assessment_type"] = val.get('metric_type', 'probability')
                        elif isinstance(val, (int, float)):
                            verdict["quantified_assessment"] = f"{val}%"
                            verdict["assessment_type"] = "probability"
                        elif isinstance(val, str):
                            verdict["quantified_assessment"] = val
                            verdict["assessment_type"] = "qualitative"
                        break

                findings = data.get("key_findings", data.get("findings", []))
                if isinstance(findings, list):
                    verdict["key_findings"] = findings[:5]

                verdict["recommendation"] = data.get(
                    "recommendation", data.get("recommended", data.get("direct_answer", data.get("action")))
                )
                verdict["decision"] = data.get(
                    "go_no_go_decision", data.get("decision", data.get("go_no_go", data.get("verdict")))
                )

                conf = data.get("confidence_level", data.get("confidence"))
                if conf is not None:
                    if isinstance(conf, str):
                        conf_str = conf.replace('≈', '').replace('%', '').strip()
                        try:
                            conf = float(conf_str)
                        except ValueError:
                            conf = None
                    verdict["confidence_level"] = conf if isinstance(conf, (int, float)) else None

                consensus = data.get("areas_of_consensus", [])
                if isinstance(consensus, list) and consensus:
                    verdict["areas_of_consensus"] = consensus[:6]
                disagreements = data.get("remaining_disagreements", [])
                if isinstance(disagreements, list) and disagreements:
                    verdict["remaining_disagreements"] = disagreements[:4]
                risks = data.get("risks_and_mitigations", [])
                if isinstance(risks, list) and risks:
                    verdict["risks_and_mitigations"] = risks[:6]
                next_steps = data.get("next_steps", [])
                if isinstance(next_steps, list) and next_steps:
                    verdict["next_steps"] = next_steps[:5]

                verdict["source"] = f"turn_{turn.get('turn', 'unknown')}"

                if verdict["quantified_assessment"] or verdict["direct_answer"]:
                    logger.info(
                        f"📊 Extracted debate verdict: "
                        f"{verdict.get('quantified_assessment') or str(verdict.get('direct_answer', ''))[:50]}"
                    )
                    return verdict

            except json.JSONDecodeError:
                continue

        # Strategy 2: Regex extraction
        percentage_matches = re.findall(r'([A-Za-z][A-Za-z\s]+?):\s*(\d+(?:\.\d+)?)\s*%', message)
        if percentage_matches:
            for label, value in percentage_matches:
                if any(kw in label.lower() for kw in [
                    "success", "probability", "confidence", "score",
                    "rate", "likelihood", "chance", "assessment"
                ]):
                    verdict["quantified_assessment"] = f"{value}%"
                    verdict["assessment_type"] = "probability"
                    verdict["source"] = f"turn_{turn.get('turn', 'unknown')}"

            if verdict["quantified_assessment"]:
                logger.info(f"📊 Extracted verdict via regex: {verdict['quantified_assessment']}")
                return verdict

        qualitative_matches = re.findall(
            r'(risk|impact|severity|priority):\s*(HIGH|MEDIUM|LOW|CRITICAL)',
            message, re.IGNORECASE
        )
        if qualitative_matches:
            verdict["quantified_assessment"] = qualitative_matches[0][1].upper()
            verdict["assessment_type"] = qualitative_matches[0][0].lower()
            verdict["source"] = f"turn_{turn.get('turn', 'unknown')}"
            logger.info(
                f"📊 Extracted qualitative verdict: "
                f"{verdict['assessment_type']}={verdict['quantified_assessment']}"
            )
            return verdict

    # Strategy 3: Look in debate_synthesis
    if debate_synthesis:
        percentage_matches = re.findall(
            r'(\d+(?:\.\d+)?)\s*%\s*(?:success|probability|confidence|likely)',
            debate_synthesis, re.IGNORECASE
        )
        if percentage_matches:
            verdict["quantified_assessment"] = f"{percentage_matches[0]}%"
            verdict["assessment_type"] = "probability"
            verdict["source"] = "debate_synthesis"
            logger.info(f"📊 Extracted verdict from synthesis: {verdict['quantified_assessment']}")
            return verdict

    logger.warning("⚠️ Could not extract structured verdict - using scenario averages")
    return verdict
