"""
Animated Visualizations for QNWIS (P1).

Creates engaging animated charts for executive dashboards.
"""

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class AnimatedChart:
    """
    Base class for animated chart generation.
    
    Generates interactive HTML/JavaScript charts with animations.
    """
    
    def __init__(self, title: str, chart_type: str = "line"):
        """
        Initialize animated chart.
        
        Args:
            title: Chart title
            chart_type: Chart type (line, bar, pie, area)
        """
        self.title = title
        self.chart_type = chart_type
        self.data: List[Dict[str, Any]] = []
    
    def add_data_point(self, label: str, value: float, **kwargs) -> None:
        """
        Add data point to chart.
        
        Args:
            label: Data point label
            value: Data point value
            **kwargs: Additional data (color, icon, etc.)
        """
        self.data.append({
            "label": label,
            "value": value,
            **kwargs
        })
    
    def render_plotly(self) -> str:
        """
        Render chart using Plotly.
        
        Returns:
            HTML with Plotly chart
        """
        # Generate Plotly configuration
        plotly_data = {
            "x": [d["label"] for d in self.data],
            "y": [d["value"] for d in self.data],
            "type": self.chart_type,
            "name": self.title
        }
        
        layout = {
            "title": self.title,
            "xaxis": {"title": ""},
            "yaxis": {"title": "Value"},
            "transition": {
                "duration": 500,
                "easing": "cubic-in-out"
            }
        }
        
        config = {
            "data": [plotly_data],
            "layout": layout
        }
        
        html = f"""
<div id="chart_{id(self)}">
    <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
    <script>
        var config = {json.dumps(config)};
        Plotly.newPlot('chart_{id(self)}', config.data, config.layout);
    </script>
</div>
"""
        return html
    
    def render_chartjs(self) -> str:
        """
        Render chart using Chart.js.
        
        Returns:
            HTML with Chart.js chart
        """
        labels = [d["label"] for d in self.data]
        values = [d["value"] for d in self.data]
        
        html = f"""
<div>
    <canvas id="chart_{id(self)}"></canvas>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script>
        new Chart(document.getElementById('chart_{id(self)}'), {{
            type: '{self.chart_type}',
            data: {{
                labels: {json.dumps(labels)},
                datasets: [{{
                    label: '{self.title}',
                    data: {json.dumps(values)},
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                animation: {{
                    duration: 1000,
                    easing: 'easeInOutQuart'
                }},
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});
    </script>
</div>
"""
        return html


def create_trend_chart(
    title: str,
    data_points: List[Dict[str, Any]],
    animated: bool = True
) -> AnimatedChart:
    """
    Create animated trend chart.
    
    Args:
        title: Chart title
        data_points: List of {label, value} dicts
        animated: Whether to animate
        
    Returns:
        AnimatedChart instance
    """
    chart = AnimatedChart(title=title, chart_type="line")
    
    for point in data_points:
        chart.add_data_point(
            label=point.get("label", ""),
            value=point.get("value", 0)
        )
    
    return chart


def create_comparison_chart(
    title: str,
    categories: List[str],
    values: List[float]
) -> AnimatedChart:
    """
    Create animated comparison bar chart.
    
    Args:
        title: Chart title
        categories: Category labels
        values: Category values
        
    Returns:
        AnimatedChart instance
    """
    chart = AnimatedChart(title=title, chart_type="bar")
    
    for category, value in zip(categories, values):
        chart.add_data_point(label=category, value=value)
    
    return chart
