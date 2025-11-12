# QNWIS User Guide

**Version:** 1.0.0  
**Audience:** Ministry of Labour analysts, policy makers, and end users  
**Last Updated:** 2025-01-12

## Overview

The Qatar National Workforce Intelligence System (QNWIS) is a production-grade analytical platform that provides real-time insights into Qatar's labour market dynamics. This guide will help you effectively use the system to answer complex workforce questions.

## Getting Started

### Accessing QNWIS

1. **Chainlit Interface**: Navigate to your deployment URL (e.g., `https://qnwis.mol.gov.qa`)
2. **Authentication**: Log in with your Ministry credentials
3. **Dashboard**: Access the operations console at `/ops` (requires appropriate permissions)

### System Capabilities

QNWIS can answer questions about:

- **Labour Market Trends**: Employment rates, workforce composition, sector growth
- **Economic Indicators**: GDP correlation, productivity metrics, wage trends
- **Infrastructure Impact**: Project effects on employment, regional development
- **Policy Scenarios**: "What-if" analysis for policy changes
- **Predictive Analytics**: Forecasting workforce needs, skill gaps

## How to Ask Questions

### Question Patterns

QNWIS uses a sophisticated multi-agent system that routes your questions to specialized agents. Use these patterns for best results:

#### Simple Queries (< 10 seconds)
```
"What is the current unemployment rate?"
"How many workers are employed in construction?"
"Show me the latest GDP figures"
```

#### Medium Complexity (< 30 seconds)
```
"Compare employment trends in healthcare vs. technology over the past 5 years"
"What is the correlation between infrastructure spending and job creation?"
"Analyze wage growth by sector for Qatari nationals"
```

#### Complex Analysis (< 90 seconds)
```
"Predict the impact of a 20% increase in renewable energy investment on job creation across all sectors"
"Analyze historical patterns of workforce retention in hospitality and forecast next quarter"
"What would happen if we increased minimum wage by 15% while maintaining current visa policies?"
```

### Best Practices

1. **Be Specific**: Include time ranges, sectors, or demographics
   - ❌ "Tell me about jobs"
   - ✅ "Show employment trends in healthcare for Q3 2024"

2. **Use Natural Language**: The system understands conversational queries
   - "How has the construction sector performed since 2022?"
   - "What's driving the increase in tech jobs?"

3. **Request Citations**: Ask for sources to verify data
   - "Show me employment data with sources"
   - "What's the evidence for this trend?"

4. **Iterate**: Refine your questions based on initial results
   - Start broad, then drill down into specific areas

## Understanding Results

### Response Structure

Every QNWIS response includes:

1. **Direct Answer**: Clear, concise response to your question
2. **Supporting Data**: Relevant statistics, trends, or visualizations
3. **Citations**: Source references with timestamps and confidence scores
4. **Confidence Score**: System confidence in the answer (0.0-1.0)
5. **Audit Trail**: Unique query ID for tracking

### Confidence Scores

- **0.90-1.00**: High confidence, verified from multiple authoritative sources
- **0.70-0.89**: Good confidence, supported by primary data sources
- **0.50-0.69**: Moderate confidence, may require additional verification
- **< 0.50**: Low confidence, treat as preliminary or exploratory

### Citations and Verification

All answers include citations in this format:

```
[Source: LMIS Employment Database, Table: qtr_employment_stats, 
 Timestamp: 2024-Q3, Confidence: 0.95]
```

**Deterministic Data Layer Guarantee**: All data comes from verified LMIS tables. The system never fabricates data or uses unverified sources. Every statistic can be traced back to its source table and timestamp.

## Using the Audit Trail

### Viewing Your Query History

1. Navigate to the Chainlit interface
2. Click "History" in the sidebar
3. Each query shows:
   - Question asked
   - Timestamp
   - Agents involved
   - Response time
   - Confidence score
   - Full audit trail

### Audit Trail Details

Each query generates a complete audit trail stored in the database:

```sql
-- View your recent queries
SELECT query_id, question, confidence_score, response_time_ms, created_at
FROM audit.query_log
WHERE user_id = 'your_user_id'
ORDER BY created_at DESC
LIMIT 20;
```

Audit records include:
- **Query routing**: Which agents processed your question
- **Data sources**: Exact tables and rows accessed
- **Verification steps**: Confidence calculation details
- **Performance metrics**: Response time breakdown by stage
- **User context**: Session, permissions, rate limit status

### Exporting Audit Data

For compliance or analysis:

1. Go to `/ops/audit` (requires audit viewer role)
2. Filter by date range, user, or query type
3. Export to CSV or JSON
4. All exports are logged for security compliance

## Dashboard Features

### Operations Console (`/ops`)

**Access Level**: Operations team, administrators

Features:
- **Real-time Metrics**: Query volume, response times, error rates
- **System Health**: Database connections, cache hit rates, agent status
- **SLO Monitoring**: Performance against targets (simple <10s, medium <30s, complex <90s)
- **Alert Center**: Active incidents, warnings, and notifications
- **Audit Viewer**: System-wide query logs and access patterns

### Performance Metrics

Key metrics displayed:
- **Query Throughput**: Queries per minute/hour
- **Response Time Percentiles**: p50, p95, p99
- **Cache Hit Rate**: Percentage of cached responses
- **Agent Utilization**: Load distribution across agents
- **Error Rate**: 4xx/5xx responses per endpoint

## Advanced Features

### Scenario Analysis

Run "what-if" scenarios to model policy impacts:

```
"What would happen if we increased construction permits by 30% 
while maintaining current safety standards?"
```

The system will:
1. Identify relevant historical patterns
2. Apply predictive models
3. Generate forecasts with confidence intervals
4. Provide supporting evidence and assumptions

### Time Machine Queries

Analyze historical data at specific points in time:

```
"What was the employment situation in hospitality as of June 2023?"
"Compare Q1 2024 predictions made in Q4 2023 vs. actual outcomes"
```

### Pattern Mining

Discover hidden correlations:

```
"Find patterns between infrastructure investment and employment growth"
"What factors correlate most strongly with workforce retention?"
```

## Troubleshooting

### Common Issues

**"Query timed out"**
- Your question may be too complex
- Try breaking it into smaller questions
- Check system status at `/health`

**"Insufficient data"**
- The requested time period may not have complete data
- Try a different date range
- Check data availability in the data dictionary

**"Access denied"**
- You may not have permissions for certain data
- Contact your administrator
- Check your role assignments

**"Rate limit exceeded"**
- You've exceeded the query limit (default: 100/hour)
- Wait for the rate limit window to reset
- Contact ops team for limit increase if needed

### Getting Help

1. **In-App Help**: Click the "?" icon in Chainlit
2. **Operations Team**: Contact via `/ops/support`
3. **Documentation**: Full docs at `/docs`
4. **Audit Trail**: Reference your query ID when reporting issues

## Security and Privacy

### Data Classification

QNWIS handles sensitive workforce data:

- **Public**: Aggregated statistics, published reports
- **Internal**: Detailed analytics, trend analysis
- **Confidential**: Individual employer data, sensitive metrics
- **Restricted**: Personally identifiable information (not accessible via QNWIS)

### Your Responsibilities

1. **Access Control**: Don't share credentials
2. **Data Handling**: Follow Ministry data policies
3. **Query Logging**: All queries are audited
4. **Export Restrictions**: Respect data classification when exporting

### Security Features

- **HTTPS Only**: All traffic encrypted (TLS 1.2+)
- **CSRF Protection**: Automatic token validation
- **Rate Limiting**: Prevents abuse and overload
- **Audit Logging**: Complete activity trail
- **Role-Based Access**: Granular permission control

## Performance Expectations

### Response Time SLOs

- **Simple Queries**: < 10 seconds (95th percentile)
- **Medium Queries**: < 30 seconds (95th percentile)
- **Complex Queries**: < 90 seconds (95th percentile)
- **Dashboard Load**: < 3 seconds (95th percentile)

### System Availability

- **Uptime Target**: 99.5% (excluding planned maintenance)
- **Planned Maintenance**: Announced 48 hours in advance
- **Incident Response**: < 15 minutes acknowledgment, < 4 hours resolution

## Best Practices Summary

1. ✅ **Start Simple**: Test with basic queries before complex analysis
2. ✅ **Verify Sources**: Always check citations and confidence scores
3. ✅ **Use Audit Trail**: Track your analysis for reproducibility
4. ✅ **Respect Limits**: Stay within rate limits and data access policies
5. ✅ **Report Issues**: Use query IDs when reporting problems
6. ✅ **Iterate**: Refine questions based on initial results
7. ✅ **Document**: Save important queries and results for future reference

## Appendix: Question Templates

### Employment Analysis
```
"Show employment trends in [sector] from [start_date] to [end_date]"
"Compare employment rates between [sector1] and [sector2]"
"What is the current workforce composition in [sector]?"
```

### Economic Impact
```
"Analyze the correlation between [economic_indicator] and [employment_metric]"
"How has [policy_change] affected [sector] employment?"
"Predict employment impact of [scenario]"
```

### Forecasting
```
"Forecast [metric] for [sector] over the next [time_period]"
"What are the predicted skill gaps in [sector] for [year]?"
"Project workforce needs for [infrastructure_project]"
```

### Historical Analysis
```
"What was [metric] as of [specific_date]?"
"Compare [current_metric] to historical patterns"
"Show year-over-year trends for [metric]"
```

---

**For technical documentation, see**: [DEVELOPER_ONBOARDING.md](./DEVELOPER_ONBOARDING.md)  
**For operations procedures, see**: [OPERATIONS_RUNBOOK.md](./OPERATIONS_RUNBOOK.md)  
**For troubleshooting, see**: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
