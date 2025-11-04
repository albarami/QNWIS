# CRITICAL ADDITION: Deterministic Data Extraction Layer
## Preventing LLM Hallucination in Data Queries

---

## THE PROBLEM

**LLMs Cannot Be Trusted With Data Extraction:**

### Current Risk (Without This Layer):
```
Agent needs data
  ↓
LLM generates SQL query    ← ❌ HALLUCINATION RISK
  ↓
Execute SQL
  ↓
LLM interprets results     ← ❌ HALLUCINATION RISK
  ↓
Returns fabricated numbers ← ❌ DISASTER
```

**Real Examples of LLM Failures:**
```python
# Agent asked: "How many Qataris left banking in 2023?"

# LLM might generate wrong SQL:
"SELECT COUNT(*) FROM employees WHERE nationality = 'Qatar' AND sector = 'Bank'"
# Wrong: Doesn't check for departures, wrong sector name

# Or worse - LLM might just fabricate:
"Based on the data, 234 Qataris left banking in 2023"
# Complete fabrication - never queried database at all!
```

**Why This is Fatal for QNWIS:**
- Minister makes policy decision based on "234 Qataris"
- Number was hallucinated
- Policy fails, credibility destroyed
- System shut down

---

## THE SOLUTION: Deterministic Data Extraction Layer

### Architecture: Zero-Hallucination Data Access

```
┌─────────────────────────────────────────────────────────────┐
│  AGENT (LLM) - Natural Language Understanding              │
│  "How many Qataris left banking in 2023?"                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
              Structured Request (JSON)
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  DETERMINISTIC DATA LAYER (NO LLM) ⭐                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. Query Registry (Pre-validated SQL templates)    │   │
│  │ 2. Data Access API (Python functions)              │   │
│  │ 3. Validation Engine (Result verification)         │   │
│  │ 4. Audit Logger (Every query tracked)              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          ↓
              Executes ONLY pre-validated queries
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  DATABASE (PostgreSQL / DuckDB)                             │
│  2.3M employee records                                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
              Structured Results + Metadata
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  AGENT (LLM) - Interpretation Only                          │
│  "The data shows 234 Qataris left banking in 2023"         │
│  ← Agent CANNOT fabricate this number                      │
└─────────────────────────────────────────────────────────────┘
```

**Key Principle:** 
**Agents NEVER write SQL. Agents NEVER touch database. Agents ONLY call pre-built functions.**

---

## IMPLEMENTATION: Data Access API

### Component 1: Query Registry (Pre-Validated SQL Templates)

**Purpose:** Library of all possible queries, tested and validated

**Location:** `/qnwis/src/data/query_registry.py`

**Structure:**
```python
from typing import Dict, Any, List
from datetime import date

class QueryRegistry:
    """Registry of all validated SQL queries.
    
    Every query is:
    1. Pre-written by data engineers (not LLMs)
    2. Unit tested against sample data
    3. Performance optimized
    4. Security reviewed (SQL injection proof)
    5. Documented with expected inputs/outputs
    """
    
    # ========================================
    # EMPLOYEE TRANSITIONS
    # ========================================
    
    @staticmethod
    def get_employee_transitions(
        nationality: str,
        from_sector: str,
        to_sector: str = None,
        start_date: date = None,
        end_date: date = None
    ) -> str:
        """Get employees who moved between sectors.
        
        Args:
            nationality: 'Qatari' or 'Non-Qatari'
            from_sector: Source sector (exact match)
            to_sector: Destination sector (None = any exit)
            start_date: Start of period
            end_date: End of period
            
        Returns:
            SQL query string (parameterized, SQL injection safe)
        """
        query = """
        WITH sector_changes AS (
            SELECT 
                e1.person_id,
                e1.name,
                e1.sector as from_sector,
                e2.sector as to_sector,
                e1.end_date as exit_date,
                e2.start_date as entry_date,
                e1.salary as old_salary,
                e2.salary as new_salary
            FROM employees e1
            LEFT JOIN employees e2 
                ON e1.person_id = e2.person_id 
                AND e2.start_date > e1.end_date
                AND e2.start_date <= e1.end_date + INTERVAL '180 days'
            WHERE e1.nationality = %(nationality)s
                AND e1.sector = %(from_sector)s
                AND e1.end_date IS NOT NULL
                AND e1.end_date BETWEEN %(start_date)s AND %(end_date)s
        )
        SELECT 
            person_id,
            name,
            from_sector,
            to_sector,
            exit_date,
            entry_date,
            old_salary,
            new_salary,
            (new_salary - old_salary) as salary_change
        FROM sector_changes
        {to_sector_filter}
        ORDER BY exit_date
        """
        
        to_sector_filter = ""
        if to_sector:
            to_sector_filter = "WHERE to_sector = %(to_sector)s"
        
        return query.format(to_sector_filter=to_sector_filter)
    
    # ========================================
    # RETENTION ANALYSIS
    # ========================================
    
    @staticmethod
    def get_retention_by_company(
        sector: str = None,
        min_employees: int = 50,
        time_period_months: int = 36
    ) -> str:
        """Calculate retention rates by company.
        
        Args:
            sector: Filter by sector (None = all)
            min_employees: Minimum employee count to include
            time_period_months: Months to analyze
            
        Returns:
            SQL query for retention analysis
        """
        query = """
        WITH company_cohorts AS (
            SELECT 
                company_id,
                company_name,
                sector,
                COUNT(DISTINCT person_id) as total_employees,
                COUNT(DISTINCT CASE 
                    WHEN EXTRACT(MONTH FROM AGE(
                        COALESCE(end_date, CURRENT_DATE), 
                        start_date
                    )) >= %(time_period)s 
                    THEN person_id 
                END) as retained_employees
            FROM employees
            WHERE start_date <= CURRENT_DATE - INTERVAL '%(time_period)s months'
            {sector_filter}
            GROUP BY company_id, company_name, sector
            HAVING COUNT(DISTINCT person_id) >= %(min_employees)s
        )
        SELECT 
            company_id,
            company_name,
            sector,
            total_employees,
            retained_employees,
            ROUND(100.0 * retained_employees / total_employees, 2) as retention_rate
        FROM company_cohorts
        ORDER BY retention_rate DESC
        """
        
        sector_filter = "AND sector = %(sector)s" if sector else ""
        return query.format(sector_filter=sector_filter)
    
    # ========================================
    # SALARY ANALYSIS
    # ========================================
    
    @staticmethod
    def get_salary_statistics(
        nationality: str,
        sector: str = None,
        job_title: str = None,
        percentiles: List[float] = [25, 50, 75, 90]
    ) -> str:
        """Get salary distribution statistics.
        
        Args:
            nationality: 'Qatari' or 'Non-Qatari'
            sector: Filter by sector
            job_title: Filter by job title
            percentiles: Which percentiles to calculate
            
        Returns:
            SQL query for salary statistics
        """
        percentile_calcs = ", ".join([
            f"PERCENTILE_CONT({p/100.0}) WITHIN GROUP (ORDER BY salary) as p{int(p)}"
            for p in percentiles
        ])
        
        query = f"""
        SELECT 
            nationality,
            {f"sector," if not sector else ""}
            {f"job_title," if not job_title else ""}
            COUNT(*) as employee_count,
            AVG(salary) as avg_salary,
            {percentile_calcs},
            MIN(salary) as min_salary,
            MAX(salary) as max_salary,
            STDDEV(salary) as salary_stddev
        FROM employees
        WHERE nationality = %(nationality)s
            AND end_date IS NULL  -- Current employees only
            {f"AND sector = %(sector)s" if sector else ""}
            {f"AND job_title ILIKE %(job_title)s" if job_title else ""}
        GROUP BY nationality {f", sector" if not sector else ""} {f", job_title" if not job_title else ""}
        """
        
        return query
    
    # ========================================
    # QATARIZATION ANALYSIS
    # ========================================
    
    @staticmethod
    def get_qatarization_rates(
        sector: str = None,
        company_id: int = None,
        as_of_date: date = None
    ) -> str:
        """Calculate Qatarization rates.
        
        Args:
            sector: Filter by sector
            company_id: Specific company (None = all)
            as_of_date: Calculate as of specific date (None = current)
            
        Returns:
            SQL query for Qatarization rates
        """
        date_filter = (
            "AND (start_date <= %(as_of_date)s) "
            "AND (end_date IS NULL OR end_date > %(as_of_date)s)"
            if as_of_date else 
            "AND end_date IS NULL"
        )
        
        query = f"""
        SELECT 
            {f"sector," if not company_id else ""}
            {f"company_id, company_name," if not company_id else ""}
            COUNT(*) as total_employees,
            COUNT(*) FILTER (WHERE nationality = 'Qatari') as qatari_count,
            COUNT(*) FILTER (WHERE nationality != 'Qatari') as expat_count,
            ROUND(100.0 * COUNT(*) FILTER (WHERE nationality = 'Qatari') 
                  / COUNT(*), 2) as qatarization_rate
        FROM employees
        WHERE 1=1
            {f"AND sector = %(sector)s" if sector else ""}
            {f"AND company_id = %(company_id)s" if company_id else ""}
            {date_filter}
        GROUP BY {f"sector" if not company_id else ""} 
                 {f", company_id, company_name" if not company_id else ""}
        ORDER BY qatarization_rate DESC
        """
        
        return query
    
    # ... Add 50+ more query templates for all operations
```

---

### Component 2: Data Access API (Agent Interface)

**Purpose:** High-level Python API that agents call

**Location:** `/qnwis/src/data/data_access.py`

```python
from typing import Dict, Any, List, Optional
from datetime import date, datetime
from dataclasses import dataclass
import hashlib
import json

from src.data.query_registry import QueryRegistry
from src.data.database import DatabaseExecutor
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class QueryResult:
    """Standardized query result with metadata.
    
    Attributes:
        data: Actual query results (list of dicts)
        query_id: Unique identifier for this query
        executed_at: Timestamp of execution
        row_count: Number of rows returned
        query_params: Parameters used in query
        execution_time_ms: Query execution time
        data_sources: Which tables/APIs were accessed
        freshness: When underlying data was last updated
    """
    data: List[Dict[str, Any]]
    query_id: str
    executed_at: datetime
    row_count: int
    query_params: Dict[str, Any]
    execution_time_ms: float
    data_sources: List[str]
    freshness: Dict[str, datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "data": self.data,
            "metadata": {
                "query_id": self.query_id,
                "executed_at": self.executed_at.isoformat(),
                "row_count": self.row_count,
                "query_params": self.query_params,
                "execution_time_ms": self.execution_time_ms,
                "data_sources": self.data_sources,
                "freshness": {
                    k: v.isoformat() for k, v in self.freshness.items()
                }
            }
        }


class DataAccessAPI:
    """Deterministic data access layer for agents.
    
    CRITICAL: Agents NEVER write SQL. Agents ONLY call these functions.
    
    Every function:
    1. Uses pre-validated SQL from QueryRegistry
    2. Returns QueryResult with full audit trail
    3. Validates results before returning
    4. Logs all access for security audit
    """
    
    def __init__(self, db_executor: DatabaseExecutor):
        self.db = db_executor
        self.query_registry = QueryRegistry()
        
    def _generate_query_id(
        self, 
        operation: str, 
        params: Dict[str, Any]
    ) -> str:
        """Generate unique ID for query reproducibility."""
        param_str = json.dumps(params, sort_keys=True, default=str)
        hash_input = f"{operation}:{param_str}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _execute_and_wrap(
        self,
        operation: str,
        sql: str,
        params: Dict[str, Any],
        data_sources: List[str]
    ) -> QueryResult:
        """Execute query and wrap in QueryResult with metadata."""
        
        query_id = self._generate_query_id(operation, params)
        start_time = datetime.now()
        
        # Log query execution
        logger.info(
            f"Executing query: {operation}",
            extra={
                "query_id": query_id,
                "params": params,
                "operation": operation
            }
        )
        
        # Execute query
        results = self.db.execute_query(sql, params)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds() * 1000
        
        # Get data freshness
        freshness = self.db.get_table_freshness(data_sources)
        
        # Validate results
        self._validate_results(results, operation)
        
        # Wrap in QueryResult
        return QueryResult(
            data=results,
            query_id=query_id,
            executed_at=end_time,
            row_count=len(results),
            query_params=params,
            execution_time_ms=execution_time,
            data_sources=data_sources,
            freshness=freshness
        )
    
    def _validate_results(
        self, 
        results: List[Dict], 
        operation: str
    ) -> None:
        """Validate query results make sense."""
        
        # Check for common issues
        if not isinstance(results, list):
            raise ValueError(f"Query results must be list, got {type(results)}")
        
        # Check row counts are reasonable
        if len(results) > 1_000_000:
            logger.warning(
                f"Query returned {len(results)} rows - possible issue",
                extra={"operation": operation}
            )
        
        # Check for NULL in critical fields
        if results:
            first_row = results[0]
            if "count" in first_row and first_row["count"] is None:
                raise ValueError("Count query returned NULL - data issue")
    
    # ========================================
    # PUBLIC API - AGENTS CALL THESE
    # ========================================
    
    def get_employee_transitions(
        self,
        nationality: str,
        from_sector: str,
        to_sector: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> QueryResult:
        """Get employees who moved between sectors.
        
        Args:
            nationality: 'Qatari' or 'Non-Qatari'
            from_sector: Source sector
            to_sector: Destination sector (None = any exit)
            start_date: Start of period
            end_date: End of period
            
        Returns:
            QueryResult with employee transition data
            
        Example:
            result = api.get_employee_transitions(
                nationality="Qatari",
                from_sector="Banking",
                to_sector="Government",
                start_date=date(2020, 1, 1),
                end_date=date(2024, 12, 31)
            )
            
            print(f"Found {result.row_count} transitions")
            print(f"Query ID: {result.query_id}")
            for employee in result.data:
                print(f"{employee['name']}: {employee['salary_change']}")
        """
        
        # Get validated SQL from registry
        sql = self.query_registry.get_employee_transitions(
            nationality=nationality,
            from_sector=from_sector,
            to_sector=to_sector,
            start_date=start_date,
            end_date=end_date
        )
        
        # Prepare parameters
        params = {
            "nationality": nationality,
            "from_sector": from_sector,
            "to_sector": to_sector,
            "start_date": start_date or date(2017, 1, 1),
            "end_date": end_date or date.today()
        }
        
        # Execute and wrap
        return self._execute_and_wrap(
            operation="get_employee_transitions",
            sql=sql,
            params=params,
            data_sources=["employees"]
        )
    
    def get_retention_by_company(
        self,
        sector: Optional[str] = None,
        min_employees: int = 50,
        time_period_months: int = 36
    ) -> QueryResult:
        """Calculate retention rates by company."""
        
        sql = self.query_registry.get_retention_by_company(
            sector=sector,
            min_employees=min_employees,
            time_period_months=time_period_months
        )
        
        params = {
            "sector": sector,
            "min_employees": min_employees,
            "time_period": time_period_months
        }
        
        return self._execute_and_wrap(
            operation="get_retention_by_company",
            sql=sql,
            params=params,
            data_sources=["employees"]
        )
    
    def get_salary_statistics(
        self,
        nationality: str,
        sector: Optional[str] = None,
        job_title: Optional[str] = None
    ) -> QueryResult:
        """Get salary distribution statistics."""
        
        sql = self.query_registry.get_salary_statistics(
            nationality=nationality,
            sector=sector,
            job_title=job_title
        )
        
        params = {
            "nationality": nationality,
            "sector": sector,
            "job_title": job_title
        }
        
        return self._execute_and_wrap(
            operation="get_salary_statistics",
            sql=sql,
            params=params,
            data_sources=["employees"]
        )
    
    def get_qatarization_rates(
        self,
        sector: Optional[str] = None,
        company_id: Optional[int] = None,
        as_of_date: Optional[date] = None
    ) -> QueryResult:
        """Calculate Qatarization rates."""
        
        sql = self.query_registry.get_qatarization_rates(
            sector=sector,
            company_id=company_id,
            as_of_date=as_of_date
        )
        
        params = {
            "sector": sector,
            "company_id": company_id,
            "as_of_date": as_of_date or date.today()
        }
        
        return self._execute_and_wrap(
            operation="get_qatarization_rates",
            sql=sql,
            params=params,
            data_sources=["employees"]
        )
    
    # ... 50+ more functions for all data operations
```

---

### Component 3: Agent Integration (How Agents Use It)

**Location:** `/qnwis/src/agents/base_agent.py`

```python
from typing import Dict, Any
from src.data.data_access import DataAccessAPI, QueryResult

class BaseAgent:
    """Base class for all agents with deterministic data access."""
    
    def __init__(self, data_api: DataAccessAPI):
        self.data = data_api  # Agents access data through this
    
    def _format_query_result(self, result: QueryResult) -> str:
        """Format QueryResult for LLM consumption.
        
        Returns structured text that LLM can interpret but CANNOT fabricate.
        """
        
        formatted = f"""
DATA QUERY RESULT
═══════════════════════════════════════════════════════════════
Query ID: {result.query_id}
Executed: {result.executed_at.strftime('%Y-%m-%d %H:%M:%S')}
Rows Returned: {result.row_count}
Execution Time: {result.execution_time_ms:.2f}ms

DATA FRESHNESS:
{self._format_freshness(result.freshness)}

QUERY PARAMETERS:
{self._format_params(result.query_params)}

RESULTS (showing top 10):
{self._format_data_table(result.data[:10])}

CRITICAL: These numbers come directly from the database. 
You MUST use these exact numbers. DO NOT round, estimate, or fabricate.
═══════════════════════════════════════════════════════════════
"""
        return formatted


class LabourEconomistAgent(BaseAgent):
    """Example agent using deterministic data access."""
    
    def analyze_sector_transitions(
        self, 
        nationality: str,
        from_sector: str,
        time_range: tuple
    ) -> str:
        """Analyze employee transitions between sectors.
        
        Notice: Agent NEVER writes SQL. Agent CALLS deterministic function.
        """
        
        # Call deterministic data function
        result = self.data.get_employee_transitions(
            nationality=nationality,
            from_sector=from_sector,
            start_date=time_range[0],
            end_date=time_range[1]
        )
        
        # Format for LLM
        data_context = self._format_query_result(result)
        
        # LLM analyzes (but cannot fabricate the numbers)
        prompt = f"""
You are a labour economist. Analyze this employee transition data.

{data_context}

Provide analysis covering:
1. Overall transition patterns
2. Destination sectors
3. Salary changes
4. Timeline patterns

CRITICAL: Use ONLY the numbers from the DATA QUERY RESULT above.
DO NOT estimate, round, or fabricate any numbers.
"""
        
        response = self.llm.invoke(prompt)
        
        # Attach audit trail
        response_with_audit = f"""
{response}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AUDIT TRAIL:
Query ID: {result.query_id}
Data Source: LMIS Database
Rows Analyzed: {result.row_count}
Executed: {result.executed_at}

To reproduce this analysis:
data_api.get_employee_transitions(
    nationality="{nationality}",
    from_sector="{from_sector}",
    start_date={time_range[0]},
    end_date={time_range[1]}
)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        return response_with_audit
```

---

## VERIFICATION LAYER ENHANCEMENT

### Additional Verification: Number Matching

**Purpose:** Ensure LLM didn't fabricate numbers even when given real data

```python
class DataVerificationLayer:
    """Verify LLM responses contain only real data."""
    
    def verify_response(
        self,
        response: str,
        query_results: List[QueryResult]
    ) -> bool:
        """Verify all numbers in response came from query results.
        
        Args:
            response: LLM-generated response
            query_results: All QueryResults used in generating response
            
        Returns:
            True if verification passes
            
        Raises:
            FabricationError if response contains fabricated numbers
        """
        
        # Extract all numbers from response
        numbers_in_response = self._extract_numbers(response)
        
        # Extract all numbers from query results
        numbers_from_data = self._extract_numbers_from_results(query_results)
        
        # Check each number
        for number in numbers_in_response:
            if not self._number_exists_in_data(number, numbers_from_data):
                raise FabricationError(
                    f"Number {number} in response not found in query results. "
                    f"Possible hallucination."
                )
        
        return True
    
    def _extract_numbers(self, text: str) -> List[float]:
        """Extract all numbers from text."""
        import re
        pattern = r'\b\d+(?:,\d{3})*(?:\.\d+)?\b'
        numbers = re.findall(pattern, text)
        return [float(n.replace(',', '')) for n in numbers]
    
    def _number_exists_in_data(
        self,
        number: float,
        data_numbers: List[float],
        tolerance: float = 0.01
    ) -> bool:
        """Check if number exists in data (with rounding tolerance)."""
        for data_num in data_numbers:
            if abs(number - data_num) / max(abs(data_num), 1) < tolerance:
                return True
        return False
```

---

## DEVELOPMENT INTEGRATION

### This Goes in Early Steps (Week 2)

**Step 3: Deterministic Data Layer** (After database setup)

**Deliverables:**
1. Query Registry with 50+ pre-validated queries
2. Data Access API with all operations
3. QueryResult wrapper class
4. Database executor with audit logging
5. Comprehensive tests (>95% coverage)
6. Documentation with usage examples

**Time:** 1.5 days (3 steps in orchestration)

**Critical:** This must be complete before ANY agent development starts.

---

## BENEFITS

### 1. Zero Hallucination Risk
- Agents cannot fabricate data (they only call functions)
- All numbers traceable to database queries
- Reproducible results (query ID system)

### 2. Performance
- Pre-optimized queries (no LLM-generated slow SQL)
- Query caching possible (same params = cached result)
- Database indexes designed for these queries

### 3. Security
- No SQL injection (parameterized queries only)
- Access control at API level
- Audit trail for all data access

### 4. Maintainability
- Queries centralized (easy to fix/optimize)
- Clear separation of concerns
- Testable (mock DataAccessAPI in agent tests)

### 5. Trust
- Every number has audit trail
- Reproducible (query ID + params)
- Transparent (users can see exact queries)

---

## EXAMPLE: COMPLETE WORKFLOW

### User Question: "How many Qataris left banking in 2023?"

**Without Deterministic Layer (RISKY):**
```python
# Agent generates SQL (might be wrong)
sql = llm.generate("SELECT COUNT(*)...")  # ❌ Hallucination risk

# Or agent just makes up number
response = "234 Qataris left banking"  # ❌ Fabricated
```

**With Deterministic Layer (SAFE):**
```python
# Agent calls validated function
result = data_api.get_employee_transitions(
    nationality="Qatari",
    from_sector="Banking",
    start_date=date(2023, 1, 1),
    end_date=date(2023, 12, 31)
)

# Agent sees:
"""
ROWS RETURNED: 234
[List of 234 actual employees with names, dates, destinations]
"""

# Agent responds:
"The data shows 234 Qataris left banking in 2023."
# ✅ This number is REAL (row_count from QueryResult)

# Verification layer checks:
# Does "234" appear in result.row_count? YES ✅
# Response approved
```

---

## TESTING STRATEGY

### Test 1: Query Registry Validation
```python
def test_all_queries_execute():
    """Every query in registry must execute successfully."""
    registry = QueryRegistry()
    
    for query_name in registry.get_all_queries():
        sql = getattr(registry, query_name)(test_params)
        result = db.execute(sql, test_params)
        assert isinstance(result, list)
```

### Test 2: API Completeness
```python
def test_api_covers_all_use_cases():
    """DataAccessAPI must support all agent needs."""
    
    use_cases = [
        "employee_transitions",
        "retention_analysis",
        "salary_statistics",
        "qatarization_rates",
        # ... all 50+ use cases
    ]
    
    api = DataAccessAPI(db)
    for use_case in use_cases:
        assert hasattr(api, use_case)
```

### Test 3: Hallucination Prevention
```python
def test_agent_cannot_fabricate_data():
    """Agent responses must only contain real data."""
    
    # Give agent fake data access (returns empty)
    fake_api = Mock(DataAccessAPI)
    fake_api.get_employee_transitions.return_value = QueryResult(
        data=[],
        row_count=0,
        # ...
    )
    
    agent = LabourEconomistAgent(data_api=fake_api)
    response = agent.analyze_transitions(...)
    
    # Verify agent doesn't fabricate numbers
    numbers_in_response = extract_numbers(response)
    assert len(numbers_in_response) == 0  # Should say "no data"
```

---

## CRITICAL REMINDERS

1. **Agents NEVER write SQL** - Only call DataAccessAPI functions
2. **All queries pre-validated** - Tested, optimized, security-reviewed
3. **Every query logged** - Full audit trail with query ID
4. **Results wrapped** - QueryResult includes metadata + freshness
5. **Verification layer** - Checks responses contain only real numbers
6. **Build this FIRST** - Before any agent development

---

## ADDITION TO PROPOSAL

**Add to Architecture Section:**

```
┌─────────────────────────────────────────────────────────────┐
│  5 SPECIALIST AGENTS (LLMs)                                 │
│  • Natural language understanding                           │
│  • Analysis and synthesis                                   │
│  • NO direct database access ❌                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
              Calls structured functions only
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  DETERMINISTIC DATA LAYER (NO LLM) ⭐ NEW                   │
│  • Query Registry (50+ validated queries)                   │
│  • Data Access API (Python functions)                       │
│  • QueryResult wrapper (audit trail)                        │
│  • Verification engine                                      │
│  └→ Agents CAN'T hallucinate data ✅                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
              Executes pre-validated SQL only
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  DATABASE (PostgreSQL / DuckDB)                             │
│  2.3M employee records                                      │
└─────────────────────────────────────────────────────────────┘
```

**Add to Verification Section:**

**Layer 0 (NEW): Deterministic Data Extraction**
- Prevents hallucination at the source
- Agents never touch SQL
- All queries pre-validated

**Layer 1: Data Isolation** (existing)
**Layer 2: Mandatory Citations** (existing)
**Layer 3: Automated Verification** (existing)
**Layer 4: Audit Trail** (existing)

---

This deterministic layer is **MANDATORY**. Without it, the system will hallucinate numbers and fail catastrophically.
