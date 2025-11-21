"""
Data Quality and Gap Detection Module.

This module provides functions to calculate data quality scores and identify
missing critical data points based on extracted facts and requirements.
"""

from typing import Any, Dict, List, Set

def calculate_data_quality(facts: List[Dict[str, Any]], required_data: List[str]) -> float:
    """
    Score data quality based on coverage of required data points.
    
    Args:
        facts: List of extracted facts
        required_data: List of required data types
        
    Returns:
        Float score between 0.0 and 1.0
    """
    if not required_data:
        return 0.8  # Default for general queries
    
    # Check how many required data points we have
    found_data_types = set()
    for fact in facts:
        # Check 'data_type' field first, then fallback to checking metric name
        data_type = fact.get("data_type")
        if not data_type and "metric" in fact:
            data_type = fact["metric"]
            
        if data_type and data_type in required_data:
            found_data_types.add(data_type)
    
    coverage = len(found_data_types) / len(required_data)
    
    # Also consider total number of facts
    # 50 facts is considered "full volume"
    volume_score = min(len(facts) / 50, 1.0)
    
    # Weighted average: 70% coverage, 30% volume
    quality_score = (coverage * 0.7) + (volume_score * 0.3)
    
    return round(quality_score, 2)

def identify_missing_data(facts: List[Dict[str, Any]], required_data: List[str]) -> List[str]:
    """
    Identify which required data points are missing from facts.
    
    Args:
        facts: List of extracted facts
        required_data: List of required data types
        
    Returns:
        List of missing data types
    """
    if not required_data:
        return []
        
    found_data_types = set()
    for fact in facts:
        data_type = fact.get("data_type")
        if not data_type and "metric" in fact:
            data_type = fact["metric"]
            
        if data_type:
            found_data_types.add(data_type)
            
    missing = [req for req in required_data if req not in found_data_types]
    return missing
