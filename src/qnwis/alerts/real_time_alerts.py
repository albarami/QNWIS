"""
Real-time Alerting System for QNWIS (M4).

Monitors key workforce metrics and sends alerts when thresholds are breached.
"""

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class Alert:
    """Represents a workforce metric alert."""
    
    def __init__(
        self,
        alert_id: str,
        metric_name: str,
        threshold_value: float,
        current_value: float,
        severity: str = "medium",
        message: str = ""
    ):
        """
        Initialize alert.
        
        Args:
            alert_id: Unique alert identifier
            metric_name: Name of metric (e.g., "unemployment_rate")
            threshold_value: Threshold that was breached
            current_value: Current metric value
            severity: Alert severity (low, medium, high, critical)
            message: Alert message
        """
        self.alert_id = alert_id
        self.metric_name = metric_name
        self.threshold_value = threshold_value
        self.current_value = current_value
        self.severity = severity
        self.message = message
        self.timestamp = datetime.utcnow().isoformat() + "Z"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "metric_name": self.metric_name,
            "threshold_value": self.threshold_value,
            "current_value": self.current_value,
            "severity": self.severity,
            "message": self.message,
            "timestamp": self.timestamp
        }


class RealTimeAlertSystem:
    """
    Real-time monitoring and alerting for workforce metrics.
    
    Features:
    - Threshold-based alerting
    - Trend detection
    - Multi-channel notifications
    - Alert history
    """
    
    def __init__(self):
        """Initialize real-time alert system."""
        self.thresholds: Dict[str, Dict[str, float]] = {}
        self.alert_handlers: List[Callable[[Alert], None]] = []
        self.active_alerts: List[Alert] = []
        logger.info("RealTimeAlertSystem initialized")
    
    def set_threshold(
        self,
        metric_name: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> None:
        """
        Set alert threshold for a metric.
        
        Args:
            metric_name: Metric name
            min_value: Minimum acceptable value (alert if below)
            max_value: Maximum acceptable value (alert if above)
        """
        self.thresholds[metric_name] = {
            "min": min_value,
            "max": max_value
        }
        logger.info(f"Threshold set for {metric_name}: min={min_value}, max={max_value}")
    
    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """
        Add alert handler function.
        
        Args:
            handler: Function to call when alert is triggered
        """
        self.alert_handlers.append(handler)
        logger.info(f"Alert handler added: {handler.__name__}")
    
    def check_metric(
        self,
        metric_name: str,
        current_value: float
    ) -> Optional[Alert]:
        """
        Check metric against thresholds.
        
        Args:
            metric_name: Metric name
            current_value: Current value
            
        Returns:
            Alert if threshold breached, None otherwise
        """
        if metric_name not in self.thresholds:
            return None
        
        threshold = self.thresholds[metric_name]
        min_val = threshold.get("min")
        max_val = threshold.get("max")
        
        alert = None
        
        if min_val is not None and current_value < min_val:
            alert = Alert(
                alert_id=f"{metric_name}_{int(datetime.now().timestamp())}",
                metric_name=metric_name,
                threshold_value=min_val,
                current_value=current_value,
                severity="high",
                message=f"{metric_name} fell below minimum threshold: {current_value} < {min_val}"
            )
        
        elif max_val is not None and current_value > max_val:
            alert = Alert(
                alert_id=f"{metric_name}_{int(datetime.now().timestamp())}",
                metric_name=metric_name,
                threshold_value=max_val,
                current_value=current_value,
                severity="high",
                message=f"{metric_name} exceeded maximum threshold: {current_value} > {max_val}"
            )
        
        if alert:
            self._trigger_alert(alert)
        
        return alert
    
    def _trigger_alert(self, alert: Alert) -> None:
        """
        Trigger alert and notify handlers.
        
        Args:
            alert: Alert to trigger
        """
        self.active_alerts.append(alert)
        logger.warning(f"Alert triggered: {alert.message}")
        
        # Notify all handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Get list of active alerts."""
        return self.active_alerts.copy()
    
    def clear_alert(self, alert_id: str) -> bool:
        """
        Clear/acknowledge an alert.
        
        Args:
            alert_id: Alert ID to clear
            
        Returns:
            True if cleared, False if not found
        """
        for i, alert in enumerate(self.active_alerts):
            if alert.alert_id == alert_id:
                self.active_alerts.pop(i)
                logger.info(f"Alert cleared: {alert_id}")
                return True
        return False


# Predefined alert thresholds for Qatar
QATAR_ALERT_THRESHOLDS = {
    "unemployment_rate": {"min": None, "max": 5.0},  # Alert if > 5%
    "qatarization_rate": {"min": 25.0, "max": None},  # Alert if < 25%
    "skills_gap_index": {"min": None, "max": 7.5},  # Alert if > 7.5/10
    "attrition_rate": {"min": None, "max": 15.0},  # Alert if > 15%
}


def create_default_alert_system() -> RealTimeAlertSystem:
    """
    Create alert system with Qatar-specific defaults.
    
    Returns:
        Configured RealTimeAlertSystem
    """
    system = RealTimeAlertSystem()
    
    # Set default thresholds
    for metric_name, thresholds in QATAR_ALERT_THRESHOLDS.items():
        system.set_threshold(
            metric_name,
            min_value=thresholds.get("min"),
            max_value=thresholds.get("max")
        )
    
    # Add default log handler
    def log_alert_handler(alert: Alert):
        logger.warning(f"ALERT: {alert.message}")
    
    system.add_alert_handler(log_alert_handler)
    
    return system


# Global alert system instance
_alert_system: Optional[RealTimeAlertSystem] = None


def get_alert_system() -> RealTimeAlertSystem:
    """Get or create global alert system."""
    global _alert_system
    if _alert_system is None:
        _alert_system = create_default_alert_system()
    return _alert_system
