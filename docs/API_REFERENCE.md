# QNWIS API Reference

**Version:** 1.0.0  
**Base URL**: `https://api.qnwis.mol.gov.qa` (production)  
**OpenAPI Specification**: [openapi.json](./api/openapi.json)  
**Last Updated:** 2025-01-12

## Overview

The QNWIS API provides programmatic access to Qatar's workforce intelligence system. All endpoints require authentication and follow RESTful conventions.

## Full API Documentation

**Complete OpenAPI specification**: See [api/openapi.json](./api/openapi.json)  
**Human-readable endpoint index**: See [api/openapi.md](./api/openapi.md)

These files are auto-generated from the FastAPI application using:
```bash
python scripts/export_openapi.py
```

## Authentication

All API requests require a valid JWT token:

```http
Authorization: Bearer <your_jwt_token>
```

Obtain tokens via the authentication endpoint or your Ministry SSO integration.

## Core Endpoints

### Query Submission

#### POST `/api/v1/query`

Submit a natural language query to the QNWIS system.

**Request:**
```json
{
  "question": "What is the current unemployment rate in construction?",
  "context": {
    "user_id": "analyst_123",
    "session_id": "sess_abc",
    "priority": "normal"
  },
  "options": {
    "include_citations": true,
    "max_response_time": 30,
    "confidence_threshold": 0.7
  }
}
```

**Response (200 OK):**
```json
{
  "query_id": "q_2024_001234",
  "answer": "The current unemployment rate in the construction sector is 3.2% as of Q3 2024.",
  "confidence_score": 0.94,
  "response_time_ms": 1847,
  "citations": [
    {
      "source": "LMIS Employment Database",
      "table": "qtr_employment_stats",
      "timestamp": "2024-Q3",
      "confidence": 0.95,
      "row_ids": [12345, 12346]
    }
  ],
  "metadata": {
    "agents_used": ["router", "simple_query", "verifier"],
    "cache_hit": false,
    "data_freshness": "2024-10-15T14:30:00Z"
  },
  "audit_trail_id": "audit_2024_001234"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid query format
- `401 Unauthorized`: Missing or invalid token
- `429 Too Many Requests`: Rate limit exceeded
- `503 Service Unavailable`: System overload or maintenance

**Rate Limits:**
- Default: 100 requests/hour per user
- Burst: 10 requests/minute
- Headers: `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### Query Status

#### GET `/api/v1/query/{query_id}`

Retrieve results for a previously submitted query.

**Response (200 OK):**
```json
{
  "query_id": "q_2024_001234",
  "status": "completed",
  "answer": "...",
  "confidence_score": 0.94,
  "created_at": "2024-11-12T05:03:00Z",
  "completed_at": "2024-11-12T05:03:02Z"
}
```

**Status Values:**
- `pending`: Query queued
- `processing`: Agents working
- `completed`: Results available
- `failed`: Error occurred
- `timeout`: Exceeded max response time

### Data Retrieval

#### GET `/api/v1/data/{table_name}`

Direct access to LMIS data tables (requires elevated permissions).

**Query Parameters:**
- `filters`: JSON-encoded filter conditions
- `limit`: Maximum rows (default: 100, max: 1000)
- `offset`: Pagination offset
- `fields`: Comma-separated field list

**Example:**
```http
GET /api/v1/data/qtr_employment_stats?filters={"quarter":"2024-Q3"}&limit=50
```

**Response (200 OK):**
```json
{
  "table": "qtr_employment_stats",
  "rows": [
    {
      "id": 12345,
      "quarter": "2024-Q3",
      "sector": "construction",
      "employment_count": 125000,
      "unemployment_rate": 0.032
    }
  ],
  "total_count": 1,
  "metadata": {
    "data_classification": "internal",
    "last_updated": "2024-10-15T14:30:00Z",
    "source": "LMIS_PROD"
  }
}
```

**Deterministic Data Layer**: All data comes from verified LMIS tables. No synthetic or inferred data is returned. Every row includes source metadata and timestamps.

### Scenario Analysis

#### POST `/api/v1/scenario`

Run predictive "what-if" scenarios.

**Request:**
```json
{
  "scenario_type": "policy_impact",
  "parameters": {
    "policy": "minimum_wage_increase",
    "change_percent": 15,
    "sectors": ["hospitality", "retail"],
    "timeframe": "12_months"
  },
  "options": {
    "include_confidence_intervals": true,
    "historical_comparison": true
  }
}
```

**Response (200 OK):**
```json
{
  "scenario_id": "scen_2024_001",
  "predictions": {
    "employment_impact": {
      "hospitality": {
        "change_percent": -2.3,
        "confidence_interval": [-4.1, -0.5],
        "confidence": 0.78
      },
      "retail": {
        "change_percent": -1.8,
        "confidence_interval": [-3.2, -0.4],
        "confidence": 0.81
      }
    }
  },
  "supporting_evidence": [
    {
      "historical_scenario": "2019_wage_adjustment",
      "similarity_score": 0.87,
      "outcome": "Employment decreased by 2.1% over 12 months"
    }
  ],
  "assumptions": [
    "Current economic conditions remain stable",
    "No major policy changes in other areas",
    "Historical patterns continue to apply"
  ],
  "audit_trail_id": "audit_2024_001235"
}
```

### Health and Status

#### GET `/health`

System health check (no authentication required).

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-11-12T05:03:00Z",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "agents": "healthy"
  },
  "performance": {
    "avg_response_time_ms": 1250,
    "queries_per_minute": 45,
    "cache_hit_rate": 0.68
  }
}
```

#### GET `/metrics`

Prometheus-compatible metrics (requires ops role).

**Response (200 OK):**
```
# HELP qnwis_queries_total Total number of queries processed
# TYPE qnwis_queries_total counter
qnwis_queries_total{status="success"} 12847
qnwis_queries_total{status="error"} 23

# HELP qnwis_response_time_seconds Query response time
# TYPE qnwis_response_time_seconds histogram
qnwis_response_time_seconds_bucket{le="1.0"} 8234
qnwis_response_time_seconds_bucket{le="5.0"} 11456
qnwis_response_time_seconds_bucket{le="10.0"} 12654
...
```

**Security Note**: The `/metrics` endpoint is restricted to operations team and should not be publicly exposed. Access is logged and monitored.

## Request/Response Examples

### Example 1: Simple Employment Query

**Request:**
```bash
curl -X POST https://api.qnwis.mol.gov.qa/api/v1/query \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How many people work in healthcare?",
    "options": {"include_citations": true}
  }'
```

**Response:**
```json
{
  "query_id": "q_2024_001236",
  "answer": "As of Q3 2024, there are 87,450 people employed in the healthcare sector in Qatar.",
  "confidence_score": 0.96,
  "response_time_ms": 892,
  "citations": [
    {
      "source": "LMIS Employment Database",
      "table": "sector_employment",
      "timestamp": "2024-Q3",
      "confidence": 0.96
    }
  ]
}
```

### Example 2: Complex Trend Analysis

**Request:**
```bash
curl -X POST https://api.qnwis.mol.gov.qa/api/v1/query \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Compare employment growth in tech vs. construction over the past 3 years",
    "options": {
      "include_citations": true,
      "max_response_time": 30
    }
  }'
```

**Response:**
```json
{
  "query_id": "q_2024_001237",
  "answer": "Over the past 3 years (Q4 2021 - Q3 2024), technology sector employment grew by 42% (from 12,300 to 17,466), while construction grew by 18% (from 106,000 to 125,080). Technology showed stronger growth but from a smaller base.",
  "confidence_score": 0.89,
  "response_time_ms": 4521,
  "citations": [
    {
      "source": "LMIS Employment Database",
      "table": "qtr_employment_stats",
      "timestamp": "2021-Q4 to 2024-Q3",
      "confidence": 0.92
    },
    {
      "source": "LMIS Sector Analysis",
      "table": "sector_trends",
      "timestamp": "2024-Q3",
      "confidence": 0.87
    }
  ],
  "metadata": {
    "agents_used": ["router", "medium_query", "time_machine", "verifier"],
    "data_points_analyzed": 24
  }
}
```

### Example 3: Data Table Access

**Request:**
```bash
curl -X GET "https://api.qnwis.mol.gov.qa/api/v1/data/qtr_employment_stats?filters=%7B%22quarter%22%3A%222024-Q3%22%7D&limit=5" \
  -H "Authorization: Bearer ${TOKEN}"
```

**Response:**
```json
{
  "table": "qtr_employment_stats",
  "rows": [
    {
      "id": 12345,
      "quarter": "2024-Q3",
      "sector": "construction",
      "employment_count": 125080,
      "unemployment_rate": 0.032,
      "avg_wage_qar": 8500
    },
    {
      "id": 12346,
      "quarter": "2024-Q3",
      "sector": "healthcare",
      "employment_count": 87450,
      "unemployment_rate": 0.018,
      "avg_wage_qar": 12300
    }
  ],
  "total_count": 2,
  "metadata": {
    "data_classification": "internal",
    "last_updated": "2024-10-15T14:30:00Z"
  }
}
```

## Error Handling

All errors follow this format:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "You have exceeded the rate limit of 100 requests per hour",
    "details": {
      "limit": 100,
      "window": "1h",
      "reset_at": "2024-11-12T06:00:00Z"
    },
    "request_id": "req_2024_001238"
  }
}
```

**Common Error Codes:**
- `INVALID_REQUEST`: Malformed request body
- `UNAUTHORIZED`: Missing or invalid authentication
- `FORBIDDEN`: Insufficient permissions
- `NOT_FOUND`: Resource does not exist
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `QUERY_TIMEOUT`: Query exceeded max response time
- `INTERNAL_ERROR`: Server error (logged and monitored)

## Rate Limiting

**Default Limits:**
- 100 requests/hour per user
- 10 requests/minute burst
- 1000 requests/day for service accounts

**Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1699776000
```

**Exceeding Limits:**
- Returns `429 Too Many Requests`
- Includes `Retry-After` header
- Contact ops team for limit increases

## Security

### HTTPS Only
All API traffic must use HTTPS (TLS 1.2+). HTTP requests are rejected.

### CSRF Protection
POST/PUT/DELETE requests require CSRF tokens when using cookie-based authentication.

### CORS
Allowed origins are configured per environment. Default: Ministry domains only.

### Audit Logging
All API requests are logged with:
- User ID and session
- Request/response details
- IP address and user agent
- Performance metrics

## Performance SLOs

**Response Time Targets (95th percentile):**
- Simple queries: < 10 seconds
- Medium queries: < 30 seconds
- Complex queries: < 90 seconds
- Data retrieval: < 5 seconds
- Health checks: < 1 second

**Availability:**
- Uptime: 99.5%
- Incident response: < 15 minutes
- Resolution: < 4 hours

## Versioning

API version is included in the URL path: `/api/v1/...`

**Current Version:** v1.0.0  
**Deprecation Policy:** 6 months notice for breaking changes  
**Backward Compatibility:** Maintained within major versions

## Support

**Documentation**: https://docs.qnwis.mol.gov.qa  
**Status Page**: https://status.qnwis.mol.gov.qa  
**Operations Team**: ops@qnwis.mol.gov.qa  
**Issue Tracking**: Include `request_id` from error responses

---

**See also:**
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Common API issues
- [SECURITY.md](./SECURITY.md) - Security controls and best practices
- [OPERATIONS_RUNBOOK.md](./OPERATIONS_RUNBOOK.md) - Ops procedures
