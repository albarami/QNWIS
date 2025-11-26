#!/usr/bin/env python3
"""
Analyze debate turns for diminishing returns.
Find the optimal cutoff point where additional turns add minimal value.
"""
import json
from collections import defaultdict
import re

def calculate_content_similarity(text1, text2):
    """Simple word-overlap similarity between two texts."""
    if not text1 or not text2:
        return 0.0
    
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    overlap = words1.intersection(words2)
    return len(overlap) / max(len(words1), len(words2))

def extract_key_concepts(text):
    """Extract key economic/strategic concepts from text."""
    concepts = {
        'cost_concepts': ['cost', 'npv', 'roi', 'expense', 'price', 'budget', 'capital'],
        'benefit_concepts': ['benefit', 'value', 'return', 'gain', 'profit'],
        'strategic_concepts': ['strategic', 'security', 'resilience', 'sovereignty', 'independence'],
        'risk_concepts': ['risk', 'uncertainty', 'failure', 'challenge', 'threat'],
        'quantitative': ['billion', 'million', 'percent', '%', '$']
    }
    
    text_lower = text.lower()
    found_concepts = defaultdict(int)
    
    for category, keywords in concepts.items():
        for keyword in keywords:
            if keyword in text_lower:
                found_concepts[category] += text_lower.count(keyword)
    
    return dict(found_concepts)

def calculate_novelty_score(current_turn, previous_turns):
    """
    Calculate how much new content a turn adds vs previous turns.
    Returns a novelty score from 0 (fully redundant) to 1 (completely new).
    """
    if not previous_turns:
        return 1.0  # First turn is always novel
    
    current_text = current_turn.get('message', '')
    
    # Check similarity with recent turns (last 5)
    recent_turns = previous_turns[-5:] if len(previous_turns) > 5 else previous_turns
    similarities = []
    
    for prev_turn in recent_turns:
        prev_text = prev_turn.get('message', '')
        similarity = calculate_content_similarity(current_text, prev_text)
        similarities.append(similarity)
    
    # Novelty is inverse of average similarity
    avg_similarity = sum(similarities) / len(similarities) if similarities else 0
    novelty = 1.0 - avg_similarity
    
    return novelty

def analyze_debate_value_over_time(results_file='phase8_full_test_results.json'):
    """
    Analyze debate turns to identify point of diminishing returns.
    """
    
    try:
        with open(results_file, 'r') as f:
            results = json.load(f)
    except FileNotFoundError:
        print(f"❌ Results file not found: {results_file}")
        print("   Test may still be running. Wait for completion.")
        return
    
    debate_turns = results.get('debate_turns', [])
    
    if not debate_turns:
        print("❌ No debate turns found in results")
        return
    
    print("="*80)
    print("DEBATE DIMINISHING RETURNS ANALYSIS")
    print("="*80)
    print(f"Total turns: {len(debate_turns)}")
    
    # Analyze each turn
    turn_analysis = []
    previous_turns = []
    
    for i, turn in enumerate(debate_turns):
        turn_num = i + 1
        agent = turn.get('agent', 'Unknown')
        turn_type = turn.get('type', 'unknown')
        message = turn.get('message', '')
        
        # Calculate metrics
        word_count = len(message.split())
        concepts = extract_key_concepts(message)
        novelty = calculate_novelty_score(turn, previous_turns)
        
        analysis = {
            'turn': turn_num,
            'agent': agent,
            'type': turn_type,
            'word_count': word_count,
            'concepts': concepts,
            'novelty_score': novelty,
            'concept_diversity': len(concepts)
        }
        
        turn_analysis.append(analysis)
        previous_turns.append(turn)
    
    # Calculate moving averages for novelty
    window_size = 5
    novelty_trends = []
    
    for i in range(len(turn_analysis)):
        start_idx = max(0, i - window_size + 1)
        window = turn_analysis[start_idx:i+1]
        avg_novelty = sum(t['novelty_score'] for t in window) / len(window)
        novelty_trends.append(avg_novelty)
    
    # Identify key thresholds
    print(f"\n{'='*80}")
    print("NOVELTY ANALYSIS BY TURN RANGES")
    print(f"{'='*80}")
    
    ranges = [
        (1, 10, "Opening Statements"),
        (11, 20, "Early Debate"),
        (21, 30, "Mid Debate"),
        (31, 40, "Late Debate"),
        (41, 50, "Extended Debate"),
        (51, 100, "Very Extended")
    ]
    
    for start, end, label in ranges:
        range_turns = [t for t in turn_analysis if start <= t['turn'] <= end]
        if not range_turns:
            continue
        
        avg_novelty = sum(t['novelty_score'] for t in range_turns) / len(range_turns)
        avg_concepts = sum(t['concept_diversity'] for t in range_turns) / len(range_turns)
        avg_words = sum(t['word_count'] for t in range_turns) / len(range_turns)
        
        print(f"\nTurns {start}-{end} ({label}):")
        print(f"  Avg Novelty: {avg_novelty:.2f} (1.0 = novel, 0.0 = redundant)")
        print(f"  Avg Concept Diversity: {avg_concepts:.1f} concept types")
        print(f"  Avg Word Count: {avg_words:.0f} words")
        print(f"  Turn Count: {len(range_turns)}")
    
    # Find diminishing returns point
    print(f"\n{'='*80}")
    print("DIMINISHING RETURNS ANALYSIS")
    print(f"{'='*80}")
    
    # Look for where novelty drops below threshold
    novelty_threshold = 0.3  # Below this is considered low novelty
    
    low_novelty_start = None
    consecutive_low = 0
    
    for i, analysis in enumerate(turn_analysis):
        if analysis['novelty_score'] < novelty_threshold:
            consecutive_low += 1
            if consecutive_low >= 3 and low_novelty_start is None:
                low_novelty_start = analysis['turn']
        else:
            consecutive_low = 0
    
    if low_novelty_start:
        print(f"\n⚠️  DIMINISHING RETURNS DETECTED at Turn {low_novelty_start}")
        print(f"   (3+ consecutive turns with novelty < {novelty_threshold})")
    else:
        print(f"\n✅ NO SIGNIFICANT DIMINISHING RETURNS DETECTED")
        print(f"   All turns maintained novelty > {novelty_threshold}")
    
    # Compare specific ranges
    print(f"\n{'='*80}")
    print("VALUE COMPARISON: Early vs Late Debate")
    print(f"{'='*80}")
    
    early_turns = [t for t in turn_analysis if 1 <= t['turn'] <= 20]
    mid_turns = [t for t in turn_analysis if 21 <= t['turn'] <= 40]
    late_turns = [t for t in turn_analysis if 41 <= t['turn'] <= 60]
    
    if early_turns:
        early_novelty = sum(t['novelty_score'] for t in early_turns) / len(early_turns)
        print(f"Turns 1-20 (Early): Avg Novelty = {early_novelty:.2f}")
    
    if mid_turns:
        mid_novelty = sum(t['novelty_score'] for t in mid_turns) / len(mid_turns)
        print(f"Turns 21-40 (Mid): Avg Novelty = {mid_novelty:.2f}")
        
        if early_turns:
            drop = ((early_novelty - mid_novelty) / early_novelty * 100) if early_novelty > 0 else 0
            print(f"  → {drop:.1f}% drop from early debate")
    
    if late_turns:
        late_novelty = sum(t['novelty_score'] for t in late_turns) / len(late_turns)
        print(f"Turns 41-60 (Late): Avg Novelty = {late_novelty:.2f}")
        
        if mid_turns:
            drop = ((mid_novelty - late_novelty) / mid_novelty * 100) if mid_novelty > 0 else 0
            print(f"  → {drop:.1f}% drop from mid debate")
    
    # Recommendation
    print(f"\n{'='*80}")
    print("RECOMMENDATION")
    print(f"{'='*80}")
    
    if low_novelty_start and low_novelty_start < 40:
        print(f"\n💡 OPTIMAL CUTOFF: ~{low_novelty_start} turns")
        print(f"   Rationale: Novelty drops significantly after turn {low_novelty_start}")
        print(f"   Recommendation: Set MAX_TURNS for COMPLEX queries to {low_novelty_start + 5}")
    elif len(debate_turns) > 50:
        # If we ran 50+ turns without significant drop, check if still valuable
        late_novelty = sum(t['novelty_score'] for t in turn_analysis[-10:]) / 10
        if late_novelty > 0.5:
            print(f"\n✅ EXTENDED DEBATE STILL VALUABLE")
            print(f"   Last 10 turns maintained {late_novelty:.2f} novelty")
            print(f"   Current {len(debate_turns)} turn limit is appropriate")
        else:
            print(f"\n⚠️  EXTENDED DEBATE SHOWS REDUCED VALUE")
            print(f"   Last 10 turns averaged {late_novelty:.2f} novelty")
            print(f"   Consider reducing to 40-50 turns for efficiency")
    else:
        print(f"\n✅ CURRENT DEBATE LENGTH APPROPRIATE")
        print(f"   {len(debate_turns)} turns maintained good novelty throughout")
    
    return turn_analysis

if __name__ == "__main__":
    analyze_debate_value_over_time()
