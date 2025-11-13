"""
KPI Cards for Executive Dashboard (H2).

Renders Key Performance Indicators as visually appealing cards with:
- Metric value and unit
- Trend indicators (up/down/stable)
- Percentage change from baseline
- Benchmark comparisons
- Color coding for status

Optimized for ministerial briefings and executive reviews.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class KPICard:
    """
    Represents a single KPI metric card.
    
    Displays key workforce metrics with visual indicators for
    quick ministerial comprehension.
    """

    def __init__(
        self,
        title: str,
        value: Any,
        unit: str = "",
        trend: str = "stable",
        change: Optional[float] = None,
        benchmark: Optional[Any] = None,
        benchmark_label: str = "Target",
        status: str = "normal",
        description: Optional[str] = None
    ):
        """
        Initialize KPI card.

        Args:
            title: KPI title (e.g., "Unemployment Rate")
            value: Current value
            unit: Unit of measurement (%, QAR, K, etc.)
            trend: Trend direction (up, down, stable, improving, worsening)
            change: Percentage change from previous period
            benchmark: Benchmark/target value for comparison
            benchmark_label: Label for benchmark (Target, GCC Average, etc.)
            status: Status indicator (normal, warning, critical, good)
            description: Optional description text
        """
        self.title = title
        self.value = value
        self.unit = unit
        self.trend = trend.lower()
        self.change = change
        self.benchmark = benchmark
        self.benchmark_label = benchmark_label
        self.status = status.lower()
        self.description = description

    def render_markdown(self) -> str:
        """
        Render KPI card as markdown.

        Returns:
            Markdown-formatted KPI card
        """
        # Status emoji
        status_emoji = self._get_status_emoji()
        
        # Trend emoji
        trend_emoji = self._get_trend_emoji()
        
        # Format value
        value_str = self._format_value(self.value)
        
        # Build card
        card = f"### {status_emoji} {self.title}\n\n"
        card += f"**{value_str}{self.unit}**"
        
        # Add change indicator
        if self.change is not None:
            change_emoji = "📈" if self.change > 0 else "📉" if self.change < 0 else "➡️"
            card += f" {change_emoji} {self.change:+.1f}%"
        
        card += f" {trend_emoji}\n\n"
        
        # Add benchmark comparison
        if self.benchmark is not None:
            benchmark_str = self._format_value(self.benchmark)
            comparison = self._compare_to_benchmark()
            card += f"*{self.benchmark_label}: {benchmark_str}{self.unit}* {comparison}\n\n"
        
        # Add description
        if self.description:
            card += f"_{self.description}_\n\n"
        
        return card

    def _get_status_emoji(self) -> str:
        """Get emoji for status."""
        status_map = {
            "good": "✅",
            "normal": "📊",
            "warning": "⚠️",
            "critical": "🔴",
            "excellent": "🌟"
        }
        return status_map.get(self.status, "📊")

    def _get_trend_emoji(self) -> str:
        """Get emoji for trend."""
        trend_map = {
            "up": "↗️",
            "down": "↘️",
            "stable": "→",
            "improving": "✅",
            "worsening": "⚠️",
            "volatile": "〰️"
        }
        return trend_map.get(self.trend, "→")

    def _format_value(self, value: Any) -> str:
        """Format value for display."""
        if isinstance(value, float):
            # Round to 1 decimal place
            return f"{value:.1f}"
        elif isinstance(value, int):
            # Add thousand separators
            return f"{value:,}"
        else:
            return str(value)

    def _compare_to_benchmark(self) -> str:
        """Compare current value to benchmark."""
        if self.benchmark is None:
            return ""
        
        try:
            current = float(self.value)
            target = float(self.benchmark)
            
            if current == target:
                return "✅ On target"
            elif current > target:
                diff = ((current - target) / target) * 100
                return f"📈 {diff:+.1f}% vs target"
            else:
                diff = ((current - target) / target) * 100
                return f"📉 {diff:.1f}% vs target"
        except (ValueError, TypeError):
            return ""


class KPICardGrid:
    """
    Manages a grid of KPI cards for dashboard display.
    
    Organizes multiple KPIs into categories and renders them
    in a structured layout.
    """

    def __init__(self):
        """Initialize KPI card grid."""
        self.cards: List[KPICard] = []
        self.categories: Dict[str, List[KPICard]] = {}

    def add_card(self, card: KPICard, category: str = "general") -> None:
        """
        Add a KPI card to the grid.

        Args:
            card: KPICard instance
            category: Category for organization
        """
        self.cards.append(card)
        
        if category not in self.categories:
            self.categories[category] = []
        self.categories[category].append(card)
        
        logger.debug(f"Added KPI card: {card.title} (category: {category})")

    def render_all(self, max_per_row: int = 3) -> str:
        """
        Render all KPI cards.

        Args:
            max_per_row: Maximum cards per row

        Returns:
            Markdown-formatted KPI grid
        """
        if not self.cards:
            return "No KPI cards available."

        output = "## 📊 Key Performance Indicators\n\n"
        
        # Render by category
        category_order = [
            "unemployment",
            "qatarization",
            "gcc_comparison",
            "skills",
            "workforce",
            "general"
        ]
        
        category_titles = {
            "unemployment": "📉 Unemployment Metrics",
            "qatarization": "🇶🇦 Qatarization Progress",
            "gcc_comparison": "🌍 GCC Benchmarks",
            "skills": "🎓 Skills & Education",
            "workforce": "👥 Workforce Composition",
            "general": "📊 General Metrics"
        }
        
        for category in category_order:
            if category in self.categories:
                cards = self.categories[category]
                output += f"### {category_titles.get(category, category.title())}\n\n"
                
                for card in cards:
                    output += card.render_markdown()
                
                output += "---\n\n"
        
        # Render uncategorized cards
        uncategorized = [c for c in self.categories.keys() if c not in category_order]
        for category in uncategorized:
            cards = self.categories[category]
            output += f"### {category.title()}\n\n"
            for card in cards:
                output += card.render_markdown()
            output += "---\n\n"
        
        return output

    def get_card(self, title: str) -> Optional[KPICard]:
        """
        Get a specific card by title.

        Args:
            title: Card title

        Returns:
            KPICard if found, None otherwise
        """
        for card in self.cards:
            if card.title.lower() == title.lower():
                return card
        return None

    def get_category_cards(self, category: str) -> List[KPICard]:
        """
        Get all cards in a category.

        Args:
            category: Category name

        Returns:
            List of KPICard instances
        """
        return self.categories.get(category, [])


def create_standard_kpi_cards(metrics: Dict[str, Any]) -> KPICardGrid:
    """
    Create standard KPI cards from metrics dictionary.

    Args:
        metrics: Dictionary of metric name -> value/details

    Returns:
        KPICardGrid with standard cards populated
    """
    grid = KPICardGrid()
    
    # Unemployment metrics
    if "unemployment_rate" in metrics:
        grid.add_card(
            KPICard(
                title="Unemployment Rate",
                value=metrics["unemployment_rate"],
                unit="%",
                trend=metrics.get("unemployment_trend", "stable"),
                change=metrics.get("unemployment_change"),
                benchmark=metrics.get("unemployment_target"),
                benchmark_label="National Target",
                status="warning" if metrics["unemployment_rate"] > 5.0 else "normal",
                description="National unemployment rate"
            ),
            category="unemployment"
        )
    
    # Qatarization metrics
    if "qatarization_rate" in metrics:
        grid.add_card(
            KPICard(
                title="Qatarization Rate",
                value=metrics["qatarization_rate"],
                unit="%",
                trend=metrics.get("qatarization_trend", "stable"),
                change=metrics.get("qatarization_change"),
                benchmark=metrics.get("qatarization_target"),
                benchmark_label="Vision 2030 Target",
                status="good" if metrics["qatarization_rate"] >= metrics.get("qatarization_target", 0) else "normal",
                description="Percentage of Qatari nationals in workforce"
            ),
            category="qatarization"
        )
    
    # Labor force participation
    if "labour_force_participation" in metrics:
        grid.add_card(
            KPICard(
                title="Labour Force Participation",
                value=metrics["labour_force_participation"],
                unit="%",
                trend=metrics.get("participation_trend", "stable"),
                change=metrics.get("participation_change"),
                description="Share of population in labour force"
            ),
            category="workforce"
        )
    
    # Gender gap
    if "gender_gap" in metrics:
        grid.add_card(
            KPICard(
                title="Gender Employment Gap",
                value=metrics["gender_gap"],
                unit=" pp",
                trend=metrics.get("gender_gap_trend", "stable"),
                change=metrics.get("gender_gap_change"),
                benchmark=0,
                benchmark_label="Parity Target",
                status="warning" if abs(metrics["gender_gap"]) > 10 else "normal",
                description="Difference in male vs female employment rates"
            ),
            category="workforce"
        )
    
    # Skills gap
    if "skills_gap_score" in metrics:
        grid.add_card(
            KPICard(
                title="Skills Gap Index",
                value=metrics["skills_gap_score"],
                unit="/10",
                trend=metrics.get("skills_gap_trend", "stable"),
                status="critical" if metrics["skills_gap_score"] > 7 else "warning" if metrics["skills_gap_score"] > 5 else "good",
                description="Higher score indicates larger skills gap"
            ),
            category="skills"
        )
    
    return grid
