# Step 19: Citation Enforcement System

## Overview

The Citation Enforcement System is a production-grade verification layer that ensures all numeric claims in agent narratives are properly cited with source prefixes and query IDs. This system provides deterministic, regex-based validation to maintain data integrity and traceability.

## Architecture

### Components

1. **citation_patterns.py** - Compiled regex patterns for detecting:
   - Numeric claims (integers, decimals, percentages, currencies)
   - Year patterns (for exclusion)
   - Query ID patterns (QID:xxx or query_id=xxx)
   - Source prefixes (Per LMIS:, According to GCC-STAT:, etc.)
   - Ignorable tokens (codes, identifiers)

2. **citation_enforcer.py** - Core enforcement engine:
   - Extracts numeric spans from text
   - Validates citation context
   - Maps sources to QueryResults
   - Produces CitationReport

3. **citation.yml** - Configuration:
   - Allowed source prefixes
   - Query ID requirements
   - Ignore lists (years, tokens, thresholds)
   - Source mapping rules

4. **schemas.py** - Data models:
   - `CitationRules` - Configuration schema
   - `CitationIssue` - Individual violation
   - `CitationReport` - Enforcement summary

## Workflow Integration

The citation enforcer is integrated into the verification pipeline:

```
verify.py
  ↓
VerificationEngine (engine.py)
  ↓
1. Citation Enforcement (FIRST)
   - Extract numeric claims
   - Validate source prefixes
   - Check query IDs
   - Map to QueryResults
   ↓
2. Layer 2: Cross-checks
   ↓
3. Layer 4: Sanity checks
   ↓
4. Layer 3: Privacy redaction
   ↓
VerificationSummary (includes CitationReport)
  ↓
verify.py checks: if ERROR issues → FAIL workflow
  ↓
format.py adds "Citations Summary" section
```

## Citation Rules

### Allowed Prefixes

Citations must use one of these prefixes (case-insensitive):

- `Per LMIS:`
- `According to GCC-STAT:`
- `According to World Bank:`

### Query ID Requirement

When `require_query_id: true`, citations must include a query ID in one of these formats:

- `QID: abc123def`
- `QID=abc123def`
- `query_id = abc123def`

### Ignore Rules

The enforcer automatically ignores:

1. **Years** (e.g., 2023, 2024) - configurable via `ignore_years: true`
2. **Small numbers** - below `ignore_numbers_below` threshold (default: 1.0)
3. **Tokens** - configured in `ignore_tokens` list:
   - ISO-3166 (country codes)
   - NOC (National Olympic Committee codes)
   - PO Box
   - RFC (document codes)
   - ID (generic identifiers)

## Error Codes

### UNCITED_NUMBER

**Severity**: ERROR

**Description**: Numeric claim lacks required citation source

**Example**:
```
The retention rate is 87.5% in Q3.
```

**Fix**: Add source prefix and QID:
```
Per LMIS: The retention rate is 87.5% in Q3 (QID: lmis_ret_001).
```

### MISSING_QID

**Severity**: ERROR

**Description**: Citation has source prefix but missing query ID

**Example**:
```
Per LMIS: The retention rate is 87.5% in Q3.
```

**Fix**: Add query ID:
```
Per LMIS: The retention rate is 87.5% in Q3 (QID: lmis_ret_001).
```

### UNKNOWN_SOURCE

**Severity**: ERROR

**Description**: Citation source not found in available QueryResults

**Example**:
```
According to External DB: The rate is 75% (QID: ext_001).
```

**Fix**: Use a valid source that matches QueryResult data_sources:
```
Per LMIS: The rate is 75% (QID: lmis_rate_001).
```

### MALFORMED_CITATION

**Severity**: ERROR

**Description**: Citation syntax is incorrect or unrecognized

**Example**:
```
From LMIS database: The count is 1,234.
```

**Fix**: Use correct prefix format:
```
Per LMIS: The count is 1,234 (QID: lmis_count_001).
```

## Configuration

### citation.yml

```yaml
# Allowed citation source prefixes
allowed_prefixes:
  - "Per LMIS:"
  - "According to GCC-STAT:"
  - "According to World Bank:"

# Whether query IDs are required in citations
require_query_id: true

# Query ID patterns (regex)
query_id_patterns:
  - '\bQID[:=]\s*[A-Za-z0-9_-]{8,}\b'
  - '\bquery_id\s*=\s*[A-Za-z0-9_-]{8,}\b'

# Ignore years in citation checks
ignore_years: true

# Ignore numbers below this threshold
ignore_numbers_below: 1.0

# Tokens to ignore (not considered numeric claims)
ignore_tokens:
  - "ISO-3166"
  - "NOC"
  - "PO Box"
  - "RFC"
  - "ID"

# Source mapping for validation
source_mapping:
  "Per LMIS:":
    - "LMIS"
    - "lmis"
  "According to GCC-STAT:":
    - "GCC-STAT"
    - "gcc_stat"
  "According to World Bank:":
    - "WorldBank"
    - "world_bank"
    - "WB"
```

### verification.yml

```yaml
# Enable/disable citation enforcement
citation_enforcement_enabled: true
```

## Usage Examples

### Valid Citation Patterns

```markdown
Per LMIS: The qatarization rate increased to 58.3% in Q2 2024 (QID: lmis_qat_2024q2).

According to GCC-STAT: Regional employment grew by 12,500 positions (QID: gcc_emp_reg_001).

According to World Bank: Qatar's GDP growth is projected at 2.8% for 2024 (QID: wb_gdp_qat_2024).
```

### Invalid Patterns (Will Fail)

```markdown
# Missing source prefix
The qatarization rate increased to 58.3% in Q2 2024.

# Missing QID
Per LMIS: The qatarization rate increased to 58.3% in Q2 2024.

# Unrecognized source
From internal analysis: The rate is 58.3% (QID: int_001).

# Malformed QID
Per LMIS: The rate is 58.3% (ID: short).
```

## Performance

The citation enforcer is designed for O(n) performance on text length:

- Regex scanning: Single pass through text
- Context extraction: Fixed window size (200 chars)
- Source mapping: Dictionary lookups
- **Target**: <10ms for typical agent narratives (1-5KB)

## Testing Strategy

### Unit Tests

Test file: `tests/unit/verification/test_citation_enforcer.py`

Coverage areas:
1. **Pattern matching**:
   - Numeric extraction (integers, decimals, percentages)
   - Year detection
   - QID patterns
   - Source prefixes

2. **Context validation**:
   - Sentence boundary detection
   - Window sizing
   - Multi-line contexts

3. **Source mapping**:
   - Prefix matching
   - QueryResult validation
   - Case-insensitivity

4. **Ignore rules**:
   - Year filtering
   - Threshold filtering
   - Token exclusions

### Integration Tests

Test file: `tests/integration/verification/test_citation_integration.py`

Coverage areas:
1. **End-to-end workflow**:
   - verify.py → engine.py → citation_enforcer.py
   - Error propagation
   - Workflow failure on citation errors

2. **Report formatting**:
   - Citations summary section
   - Issue counts
   - Example snippets

3. **Configuration loading**:
   - YAML parsing
   - Schema validation
   - Default fallbacks

## Troubleshooting

### Issue: Too Many False Positives

**Symptom**: Years or codes flagged as uncited numbers

**Solution**: Add to `ignore_tokens` in citation.yml:
```yaml
ignore_tokens:
  - "ISO-3166"
  - "RFC"
  - "NOC"
  - "PO Box"
  - "ID"
  - "YOUR_TOKEN_HERE"  # Add custom tokens
```

### Issue: Valid Citations Rejected

**Symptom**: Citations fail with UNKNOWN_SOURCE

**Solution**: Update `source_mapping` in citation.yml:
```yaml
source_mapping:
  "Per LMIS:":
    - "LMIS"
    - "lmis"
    - "your_dataset_prefix"  # Add your dataset prefix
```

### Issue: Performance Degradation

**Symptom**: Citation enforcement takes >100ms

**Investigation**:
1. Check narrative length (should be <10KB)
2. Review regex complexity
3. Reduce context window if needed

**Solution**: Consider chunking large narratives or caching results.

### Issue: QID Patterns Not Matching

**Symptom**: Valid QIDs flagged as MISSING_QID

**Solution**: Update `query_id_patterns` in citation.yml:
```yaml
query_id_patterns:
  - '\bQID[:=]\s*[A-Za-z0-9_-]{8,}\b'
  - '\bquery_id\s*=\s*[A-Za-z0-9_-]{8,}\b'
  - 'YOUR_CUSTOM_PATTERN'  # Add custom pattern
```

## Maintenance

### Adding New Citation Sources

1. Update `citation.yml`:
```yaml
allowed_prefixes:
  - "Per LMIS:"
  - "According to YOUR-SOURCE:"

source_mapping:
  "According to YOUR-SOURCE:":
    - "your_source"
    - "your_source_alt"
```

2. Update tests in `test_citation_enforcer.py`
3. Update documentation

### Modifying Ignore Rules

1. Update `citation.yml`:
```yaml
ignore_years: true  # or false
ignore_numbers_below: 1.0  # adjust threshold
ignore_tokens:
  - "NEW_TOKEN"
```

2. Add test cases
3. Document changes

### Adjusting Strictness

**Disable QID requirement** (not recommended):
```yaml
require_query_id: false
```

**Lower numeric threshold** (more strict):
```yaml
ignore_numbers_below: 0.0  # Catch all numbers
```

**Disable citation enforcement** (emergency only):
```yaml
# In verification.yml
citation_enforcement_enabled: false
```

## Security & Privacy

### PII Safety

The citation enforcer:
- ✓ Only captures numeric tokens and non-PII context
- ✓ Does not store full narrative text in issues
- ✓ Limits span information to character positions
- ✓ Integrates with Layer 3 privacy redaction

### No External Calls

The enforcer is 100% deterministic:
- ✓ Pure Python regex operations
- ✓ No network requests
- ✓ No database queries
- ✓ No file I/O (except config loading)

## Metrics & Monitoring

The citation enforcer logs:

- **Info**: Enforcement start/completion with counts
- **Debug**: Individual claim validation details
- **Error**: Configuration or pattern matching failures

Key metrics to monitor:
- `citation.total_numbers` - Claims detected
- `citation.cited_numbers` - Properly cited
- `citation.uncited_count` - Missing citations
- `citation.enforcement_time_ms` - Performance

## Future Enhancements

Potential improvements:

1. **Fuzzy source matching** - Handle minor typos in prefixes
2. **Citation clustering** - Group nearby claims under one citation
3. **Auto-suggestion** - Recommend QIDs from available QueryResults
4. **Batch processing** - Parallel validation for multiple reports
5. **Citation graphs** - Visualize citation coverage

## References

- **Step 18**: Verification Layers 2-4 implementation
- **Complete_Testing_Strategy_and_Validation.md**: Testing requirements
- **Complete_API_Specification.md**: API contracts
- **verification.yml**: Layer 2-4 configuration
- **citation.yml**: Citation rules configuration

## Contact

For issues or questions about citation enforcement, see:
- Implementation: `src/qnwis/verification/citation_enforcer.py`
- Tests: `tests/unit/verification/test_citation_enforcer.py`
- Config: `src/qnwis/config/citation.yml`
