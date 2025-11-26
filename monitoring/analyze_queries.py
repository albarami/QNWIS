# Query Performance Tracker
# Analyzes query logs for performance metrics

import re
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta

def analyze_query_logs():
    """Analyze query logs for performance metrics."""
    log_file = Path("logs/production.log")
    
    if not log_file.exists():
        print("No log file found")
        return
    
    query_times = []
    error_count = 0
    verification_rates = []
    
    with open(log_file, "r") as f:
        for line in f:
            try:
                log_entry = json.loads(line)
                
                # Track query completion times
                if "query completed" in log_entry.get("message", "").lower():
                    # Extract time from message if available
                    pass
                
                # Track errors
                if log_entry.get("level") == "ERROR":
                    error_count += 1
                
                # Track verification rates
                if "verification rate" in log_entry.get("message", "").lower():
                    # Extract verification rate
                    pass
                    
            except json.JSONDecodeError:
                continue
    
    # Generate report
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_queries": len(query_times),
        "total_errors": error_count,
        "error_rate": error_count / max(len(query_times), 1),
        "avg_query_time_s": sum(query_times) / len(query_times) if query_times else 0,
        "avg_verification_rate": sum(verification_rates) / len(verification_rates) if verification_rates else 0
    }
    
    print(json.dumps(report, indent=2))
    
    # Write report
    with open("monitoring/query_performance.json", "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    analyze_query_logs()
