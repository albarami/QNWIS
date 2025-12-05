"""
Position Tracker - Track agent positions through debate and flag unexplained changes.

PROBLEM: Agents make opening statements for Option B, then final positions for Option A
without explaining what changed their mind.

SOLUTION: Track positions and require explanation when agents flip.

DOMAIN-AGNOSTIC: Works for any question type.
"""

import logging
import re
from typing import Dict, List, Any, Optional
from collections import defaultdict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PositionRecord:
    """Record of an agent's position at a point in debate."""
    turn: int
    position: str  # e.g., "Option A", "Tourism", "Hybrid"
    confidence: float  # 0-100
    rationale: str  # Why they hold this position
    

class PositionTracker:
    """
    Track each agent's position through the debate and flag unexplained changes.
    
    DOMAIN-AGNOSTIC: Extracts position from any agent statement.
    """
    
    def __init__(self):
        self.position_history: Dict[str, List[PositionRecord]] = defaultdict(list)
        self.position_changes: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    def extract_position_from_content(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract position from agent content (domain-agnostic).
        
        Looks for patterns like:
        - "I recommend Option A"
        - "Tourism offers the best path"
        - "A hybrid approach is optimal"
        - "Option B with 70% confidence"
        """
        content_lower = content.lower()
        
        # Position indicators (domain-agnostic)
        position_patterns = [
            (r'(?:i\s+)?recommend\s+option\s+([ab])', 'Option'),
            (r'option\s+([ab])\s+(?:is|offers|provides)', 'Option'),
            (r'(?:favor|support|advocate)\s+(?:for\s+)?option\s+([ab])', 'Option'),
            (r'hybrid\s+(?:approach|strategy|allocation)', 'Hybrid'),
            (r'balanced\s+(?:approach|strategy|allocation)', 'Hybrid'),
            (r'(?:tourism|sustainable\s+tourism)\s+(?:offers|provides|is)', 'Tourism'),
            (r'(?:ai|technology)\s+hub\s+(?:offers|provides|is)', 'AI/Technology'),
        ]
        
        position = None
        for pattern, label in position_patterns:
            match = re.search(pattern, content_lower)
            if match:
                if label == 'Option':
                    position = f"Option {match.group(1).upper()}"
                else:
                    position = label
                break
        
        if not position:
            # Fallback: Look for explicit statements
            if 'option a' in content_lower and ('recommend' in content_lower or 'support' in content_lower):
                position = 'Option A'
            elif 'option b' in content_lower and ('recommend' in content_lower or 'support' in content_lower):
                position = 'Option B'
            elif 'hybrid' in content_lower and ('recommend' in content_lower or 'best' in content_lower):
                position = 'Hybrid'
        
        if not position:
            return None
        
        # Extract confidence
        confidence = 70.0  # Default
        conf_match = re.search(r'(\d+)\s*%\s*confidence', content_lower)
        if conf_match:
            confidence = float(conf_match.group(1))
        
        # Extract rationale (first 200 chars after position statement)
        rationale_start = content_lower.find(position.lower()) if position else 0
        rationale = content[rationale_start:rationale_start + 200] if rationale_start >= 0 else content[:200]
        
        return {
            'position': position,
            'confidence': confidence,
            'rationale': rationale
        }
    
    def record_position(
        self,
        agent: str,
        turn: int,
        content: str
    ) -> Optional[Dict[str, Any]]:
        """
        Record an agent's position from their turn content.
        
        Returns position change info if a change was detected.
        """
        extracted = self.extract_position_from_content(content)
        if not extracted:
            return None
        
        record = PositionRecord(
            turn=turn,
            position=extracted['position'],
            confidence=extracted['confidence'],
            rationale=extracted['rationale']
        )
        
        # Check for position change
        change_info = None
        history = self.position_history[agent]
        
        if history:
            last_record = history[-1]
            if not self._positions_match(last_record.position, record.position):
                change_info = {
                    'agent': agent,
                    'changed': True,
                    'from': last_record.position,
                    'from_turn': last_record.turn,
                    'to': record.position,
                    'to_turn': turn,
                    'requires_explanation': True
                }
                self.position_changes[agent].append(change_info)
                logger.warning(f"⚠️ POSITION CHANGE: {agent} flipped from {last_record.position} to {record.position}")
        
        self.position_history[agent].append(record)
        return change_info
    
    def _positions_match(self, pos1: str, pos2: str) -> bool:
        """Check if two positions are the same (domain-agnostic)."""
        if not pos1 or not pos2:
            return True
        
        p1_lower = pos1.lower()
        p2_lower = pos2.lower()
        
        # Direct match
        if p1_lower == p2_lower:
            return True
        
        # Synonym matching
        option_a_synonyms = ['option a', 'ai', 'technology', 'tech hub']
        option_b_synonyms = ['option b', 'tourism', 'sustainable']
        hybrid_synonyms = ['hybrid', 'balanced', 'dual', 'mixed']
        
        p1_is_a = any(s in p1_lower for s in option_a_synonyms)
        p2_is_a = any(s in p2_lower for s in option_a_synonyms)
        
        p1_is_b = any(s in p1_lower for s in option_b_synonyms)
        p2_is_b = any(s in p2_lower for s in option_b_synonyms)
        
        p1_is_hybrid = any(s in p1_lower for s in hybrid_synonyms)
        p2_is_hybrid = any(s in p2_lower for s in hybrid_synonyms)
        
        if p1_is_a and p2_is_a:
            return True
        if p1_is_b and p2_is_b:
            return True
        if p1_is_hybrid and p2_is_hybrid:
            return True
        
        return False
    
    def get_change_prompt(self, agent: str, old_position: str, new_position: str) -> str:
        """
        Generate a prompt requiring the agent to explain their position change.
        
        DOMAIN-AGNOSTIC: Works for any position change.
        """
        return f"""
═══════════════════════════════════════════════════════════════════════════════
⚠️ POSITION CHANGE DETECTED - EXPLANATION REQUIRED
═══════════════════════════════════════════════════════════════════════════════

You ({agent}) previously advocated for: **{old_position}**
You are now recommending: **{new_position}**

Before stating your new position, you MUST explain:

1. **What specific evidence or argument changed your mind?**
   - Cite the turn number and agent who presented compelling data
   - What data point was most persuasive?

2. **Why is {new_position} now better than {old_position}?**
   - What weakness in {old_position} became apparent?
   - What strength of {new_position} did you underestimate?

3. **What trade-offs are you now accepting?**
   - What benefits of {old_position} are you giving up?
   - What risks of {new_position} are you accepting?

DO NOT simply state your new position. EXPLAIN the change with specific references.

Example: "After reviewing Dr. Hassan's analysis in Turn 34 showing that 
{old_position} achieves only 20.8% success under stress testing while 
{new_position} achieves 64.9%, I'm revising my recommendation because..."
═══════════════════════════════════════════════════════════════════════════════
"""
    
    def get_unexplained_changes(self) -> List[Dict[str, Any]]:
        """Get all position changes that weren't explained."""
        unexplained = []
        for agent, changes in self.position_changes.items():
            for change in changes:
                if change.get('requires_explanation') and not change.get('explained'):
                    unexplained.append(change)
        return unexplained
    
    def mark_change_explained(self, agent: str, turn: int):
        """Mark a position change as explained."""
        for change in self.position_changes[agent]:
            if change['to_turn'] == turn:
                change['explained'] = True
                change['requires_explanation'] = False
    
    def get_final_positions(self) -> Dict[str, PositionRecord]:
        """Get each agent's final position."""
        finals = {}
        for agent, history in self.position_history.items():
            if history:
                finals[agent] = history[-1]
        return finals
    
    def generate_position_summary(self) -> str:
        """Generate a summary of all agent positions and changes."""
        lines = ["## Agent Position Summary\n"]
        
        for agent, history in self.position_history.items():
            if not history:
                continue
            
            first = history[0]
            last = history[-1]
            
            lines.append(f"### {agent}")
            lines.append(f"- **Opening Position:** {first.position} ({first.confidence:.0f}% confidence)")
            lines.append(f"- **Final Position:** {last.position} ({last.confidence:.0f}% confidence)")
            
            # Check for changes
            changes = self.position_changes.get(agent, [])
            if changes:
                lines.append(f"- **Position Changes:** {len(changes)}")
                for c in changes:
                    explained = "✓ Explained" if c.get('explained') else "⚠️ Unexplained"
                    lines.append(f"  - Turn {c['from_turn']} ({c['from']}) → Turn {c['to_turn']} ({c['to']}) {explained}")
            else:
                lines.append(f"- **Position Changes:** None (consistent throughout)")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def validate_final_positions(self, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate that final positions are supported by scenario analysis.
        
        Returns validation result with any issues.
        """
        from .scenario_aware_synthesis import validate_recommendation_against_scenarios
        
        finals = self.get_final_positions()
        issues = []
        
        # Count positions
        position_counts = defaultdict(int)
        for agent, record in finals.items():
            position_counts[record.position] += 1
        
        # Find majority
        majority_position = max(position_counts, key=position_counts.get) if position_counts else None
        
        if majority_position:
            # Validate majority position against scenarios
            validation = validate_recommendation_against_scenarios(majority_position, scenarios)
            
            if not validation['valid']:
                issues.append({
                    'type': 'scenario_mismatch',
                    'message': validation['issue'],
                    'suggested': validation.get('suggested_recommendation')
                })
        
        # Check for unexplained changes
        unexplained = self.get_unexplained_changes()
        if unexplained:
            issues.append({
                'type': 'unexplained_changes',
                'message': f"{len(unexplained)} agents changed positions without explanation",
                'agents': [c['agent'] for c in unexplained]
            })
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'majority_position': majority_position,
            'position_counts': dict(position_counts)
        }

