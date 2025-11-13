"""
Qatar Vision 2030 Deep Integration for QNWIS (P6).

Tracks and analyzes progress toward Qatar National Vision 2030 workforce goals.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Vision 2030 Workforce Targets for Qatar
VISION_2030_TARGETS = {
    "qatarization_rate": {
        "target": 50.0,  # 50% Qatari workforce by 2030
        "current": 28.5,  # Example current value
        "unit": "%",
        "pillar": "Human Development"
    },
    "unemployment_rate": {
        "target": 2.0,  # Maximum 2% unemployment
        "current": 3.2,
        "unit": "%",
        "pillar": "Economic Development"
    },
    "knowledge_economy_jobs": {
        "target": 60.0,  # 60% of jobs in knowledge economy
        "current": 42.0,
        "unit": "%",
        "pillar": "Economic Development"
    },
    "skills_alignment": {
        "target": 85.0,  # 85% skills alignment with market
        "current": 68.0,
        "unit": "%",
        "pillar": "Human Development"
    },
    "female_participation": {
        "target": 40.0,  # 40% female workforce participation
        "current": 36.5,
        "unit": "%",
        "pillar": "Social Development"
    },
    "private_sector_qatarization": {
        "target": 40.0,  # 40% Qataris in private sector
        "current": 22.0,
        "unit": "%",
        "pillar": "Economic Development"
    }
}


class Vision2030Tracker:
    """
    Track progress toward Qatar Vision 2030 workforce goals.
    
    Provides:
    - Goal tracking
    - Progress analysis
    - Gap identification
    - Recommendations
    """
    
    def __init__(self):
        """Initialize Vision 2030 tracker."""
        self.targets = VISION_2030_TARGETS.copy()
        logger.info("Vision2030Tracker initialized")
    
    def get_progress(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """
        Get progress for a specific metric.
        
        Args:
            metric_name: Metric name
            
        Returns:
            Progress dictionary
        """
        if metric_name not in self.targets:
            return None
        
        target_data = self.targets[metric_name]
        target = target_data["target"]
        current = target_data["current"]
        
        # Calculate progress percentage
        if target > current:
            # Higher is better
            progress = (current / target) * 100
        else:
            # Lower is better (e.g., unemployment)
            progress = ((target - current) / target) * 100
            progress = max(0, 100 - progress)
        
        gap = abs(target - current)
        years_remaining = 2030 - datetime.now().year
        required_annual_change = gap / years_remaining if years_remaining > 0 else gap
        
        return {
            "metric": metric_name,
            "target": target,
            "current": current,
            "unit": target_data["unit"],
            "pillar": target_data["pillar"],
            "progress_pct": round(progress, 1),
            "gap": round(gap, 2),
            "years_remaining": years_remaining,
            "required_annual_change": round(required_annual_change, 2),
            "on_track": progress >= 70  # 70% progress threshold
        }
    
    def get_all_progress(self) -> List[Dict[str, Any]]:
        """
        Get progress for all Vision 2030 metrics.
        
        Returns:
            List of progress dictionaries
        """
        return [
            self.get_progress(metric_name)
            for metric_name in self.targets.keys()
        ]
    
    def get_dashboard_summary(self) -> str:
        """
        Generate Vision 2030 progress dashboard summary.
        
        Returns:
            Markdown formatted summary
        """
        all_progress = self.get_all_progress()
        
        on_track_count = sum(1 for p in all_progress if p and p["on_track"])
        total_count = len(all_progress)
        
        output = f"## Vision 2030 Workforce Progress Dashboard\n\n"
        output += f"**Overall Status:** {on_track_count}/{total_count} metrics on track\n\n"
        
        # Group by pillar
        pillars = {}
        for progress in all_progress:
            if not progress:
                continue
            pillar = progress["pillar"]
            if pillar not in pillars:
                pillars[pillar] = []
            pillars[pillar].append(progress)
        
        for pillar, metrics in pillars.items():
            output += f"\n### {pillar}\n\n"
            
            for metric in metrics:
                status = "✅" if metric["on_track"] else "⚠️"
                output += f"- {status} **{metric['metric'].replace('_', ' ').title()}**: "
                output += f"{metric['current']}{metric['unit']} / {metric['target']}{metric['unit']} "
                output += f"({metric['progress_pct']}% progress)\n"
                
                if not metric["on_track"]:
                    output += f"  - Gap: {metric['gap']}{metric['unit']}\n"
                    output += f"  - Required annual improvement: {metric['required_annual_change']}{metric['unit']}\n"
        
        return output
    
    def get_recommendations(self) -> List[str]:
        """
        Get recommendations for achieving Vision 2030 goals.
        
        Returns:
            List of recommendations
        """
        all_progress = self.get_all_progress()
        recommendations = []
        
        for progress in all_progress:
            if not progress or progress["on_track"]:
                continue
            
            metric = progress["metric"]
            gap = progress["gap"]
            required = progress["required_annual_change"]
            
            if metric == "qatarization_rate":
                recommendations.append(
                    f"Accelerate Qatarization by {required:.1f}% annually to reach 50% target"
                )
            
            elif metric == "private_sector_qatarization":
                recommendations.append(
                    f"Focus on private sector Qatarization - need {required:.1f}% annual increase"
                )
            
            elif metric == "knowledge_economy_jobs":
                recommendations.append(
                    f"Expand knowledge economy sectors to reach 60% target"
                )
            
            elif metric == "skills_alignment":
                recommendations.append(
                    f"Invest in skills training to close {gap:.1f}% alignment gap"
                )
        
        return recommendations


# Global tracker instance
_tracker: Optional[Vision2030Tracker] = None


def get_vision2030_tracker() -> Vision2030Tracker:
    """Get or create global Vision 2030 tracker."""
    global _tracker
    if _tracker is None:
        _tracker = Vision2030Tracker()
    return _tracker


def get_vision2030_progress() -> List[Dict[str, Any]]:
    """
    Convenience function to get Vision 2030 progress.
    
    Returns:
        List of progress dictionaries
    """
    tracker = get_vision2030_tracker()
    return tracker.get_all_progress()


def get_vision2030_dashboard() -> str:
    """
    Convenience function to get Vision 2030 dashboard.
    
    Returns:
        Markdown formatted dashboard
    """
    tracker = get_vision2030_tracker()
    return tracker.get_dashboard_summary()
