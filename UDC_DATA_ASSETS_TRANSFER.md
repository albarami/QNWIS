# UDC Data Assets & API Code - Ready to Transfer

**What UDC Actually Has (Working Code + Data)**

---

## 📊 ACTUAL DATA ASSETS IN UDC

### 1. Qatar Open Data Portal - **1,152 CSV Files Downloaded** ✅

**Location:** `D:\udc\qatar_data\clean_unique_datasets\`

**What UDC Has:**
- ✅ **1,152 unique CSV datasets** (deduplicated from 1,496)
- ✅ **135 Employment & Labor datasets** (DIRECTLY USEFUL for QNWIS!)
- ✅ **314 Demographics datasets** (population, age, nationality)
- ✅ **54 GDP & Economic datasets** (sector analysis)
- ✅ **Dataset IDs catalog** in JSON format

**Employment & Labor Datasets (Top Priority for QNWIS):**
```
employed-population-by-economic-activity-and-nationality-in-2020-census.csv
average-wages-and-salaries-by-economic-activity-at-national-level.csv
employed-persons-15-years-and-above-and-average-work-hours-by-gender.csv
estimates-of-compensations-of-employees-by-sex-and-occupation.csv
```

**TRANSFER ACTION:**
1. Copy entire folder: `D:\udc\qatar_data\clean_unique_datasets\` → `D:\lmis_int\external_data\qatar_open_data\`
2. You instantly get 135 labor datasets to complement LMIS data
3. No download needed - **files are already there!**

---

## 🔧 WORKING API INTEGRATION CODE

### 2. Semantic Scholar API - **Production Code** ✅

**Location:** `D:\udc\scripts\test_semantic_scholar.py`

**What UDC Has:**
```python
# WORKING CODE - Lines 1-247
API_KEY = "SAYzpCnxTxgayxysRRQM1wwrE7NslFn9uPKT2xy4"  # REAL API KEY!
BASE_URL = "https://api.semanticscholar.org/graph/v1"

def search_papers(query, fields="title,year,abstract,citationCount,authors,url", year_filter="2020-"):
    """Search for papers using Semantic Scholar API."""
    url = f"{BASE_URL}/paper/search/bulk"
    
    params = {
        "query": query,
        "fields": fields,
        "year": year_filter
    }
    
    headers = {"x-api-key": API_KEY}
    
    response = requests.get(url, params=params, headers=headers)
    # ... handles response, returns papers
```

**QNWIS Use Cases:**
```python
# Search for Qatar labour market research
papers = search_papers(
    query='"qatar labour market" OR "gcc employment" OR "qatarization"',
    year_filter="2019-"
)

# Search for nationalization policies
papers = search_papers(
    query='"nationalization policies" OR "workforce localization" OR "gulf employment"',
    year_filter="2018-"
)

# Search for skills gap research
papers = search_papers(
    query='"skills gap" OR "workforce development" OR "vocational training"',
    year_filter="2020-"
)
```

**TRANSFER ACTION:**
```bash
# Copy the working code
copy D:\udc\scripts\test_semantic_scholar.py D:\lmis_int\src\data\apis\semantic_scholar.py

# Adapt for QNWIS queries:
# - Change query topics to labour market
# - Integrate with your agents
```

**VALUE:** Instant access to 200M+ research papers on labour topics!

---

### 3. World Bank API - **Production Code** ✅

**Location:** `D:\udc\scripts\integrate_global_data_sources.py`

**What UDC Has:**
```python
# WORKING CODE - Lines 103-150
class UDCGlobalDataIntegrator:
    def _integrate_world_bank_data(self):
        """Integrate World Bank data for GCC economic benchmarking."""
        
        # Strategic indicators already configured
        strategic_indicators = {
            "qatar_economic": [
                "NY.GDP.MKTP.CD",      # GDP (current US$)
                "NY.GDP.MKTP.KD.ZG",   # GDP growth (annual %)
                "BX.KLT.DINV.CD.WD",   # Foreign direct investment
                "NE.CON.TOTL.ZS",      # Consumption
                "NV.IND.TOTL.ZS"       # Industry value added
            ],
            "gcc_comparison": ["QAT", "SAU", "ARE", "KWT", "BHR", "OMN"],
            "tourism_indicators": [
                "ST.INT.ARVL",         # Tourist arrivals
                "ST.INT.RCPT.CD",      # Tourism receipts
                "ST.INT.RCPT.XP.ZS"    # Tourism % of exports
            ]
        }
        
        # Download and process automatically
        qatar_data = self._download_wb_country_data("QAT", indicators)
        gcc_data = self._download_wb_gcc_comparison()
```

**QNWIS-Specific Indicators to Add:**
```python
# Labour market indicators from World Bank
labour_indicators = [
    "SL.UEM.TOTL.ZS",        # Unemployment rate, total (% of labor force)
    "SL.UEM.1524.ZS",        # Youth unemployment (ages 15-24)
    "SL.TLF.TOTL.IN",        # Labor force, total
    "SL.TLF.CACT.ZS",        # Labor force participation rate
    "SL.EMP.WORK.ZS",        # Wage and salaried workers (% of employed)
    "SL.UEM.LTRM.ZS",        # Long-term unemployment
    "SL.TLF.ADVN.ZS",        # Labor force with advanced education
    "SL.UEM.ADVN.ZS",        # Unemployment with advanced education
    "SP.POP.TOTL",           # Population, total
    "NY.GDP.PCAP.CD"         # GDP per capita
]

# QNWIS Usage:
gcc_labour_data = query_world_bank_labour_indicators(
    countries=["QA", "SA", "AE", "KW", "BH", "OM"],  # GCC
    indicators=labour_indicators,
    years="2015:2024"
)

# Now your agents can compare Qatar labour metrics vs GCC peers!
```

**TRANSFER ACTION:**
```bash
# Copy working World Bank integration
copy D:\udc\scripts\integrate_global_data_sources.py D:\lmis_int\src\data\apis\world_bank_integration.py

# Adapt indicators for labour market (above)
```

**VALUE:** Real-time GCC labour market comparisons for your agents!

---

### 4. Qatar Open Data API - **Production Code** ✅

**Location:** `D:\udc\scripts\qatar_data_scraper_v2.py`

**What UDC Has:**
```python
# WORKING QATAR API INTEGRATION
BASE_URL = "https://www.data.gov.qa/api/explore/v2.1/catalog/datasets/"

def download_dataset_csv(dataset_id):
    """Download dataset from Qatar Open Data Portal."""
    url = f"{BASE_URL}{dataset_id}/exports/csv"
    response = requests.get(url)
    
    if response.status_code == 200:
        # Qatar uses semicolon delimiter!
        df = pd.read_csv(io.StringIO(response.text), sep=';')
        return df
    else:
        return None

def query_dataset_records(dataset_id, limit=100, where=None):
    """Query specific records with filtering."""
    url = f"{BASE_URL}{dataset_id}/records"
    params = {
        'limit': limit,
        'where': where if where else None
    }
    response = requests.get(url, params=params)
    return response.json()
```

**Labour-Specific Datasets (Ready to Use):**
```python
# Employment datasets
employment_datasets = {
    "employed_by_activity": "employed-population-by-economic-activity-and-nationality-in-2020-census",
    "wages_by_sector": "average-wages-and-salaries-by-economic-activity-at-national-level",
    "compensation_by_occupation": "estimates-of-compensations-of-employees-by-sex-and-occupation",
    "work_hours": "employed-persons-15-years-and-above-and-average-work-hours-by-gender",
    "labour_force": "economically-active-population-15-years-and-above-by-gender",
    "unemployment": "unemployed-population-by-gender-and-age-groups"
}

# QNWIS Usage:
for name, dataset_id in employment_datasets.items():
    df = download_dataset_csv(dataset_id)
    # Now you have Qatar labour data to compare with LMIS!
    print(f"Downloaded {name}: {len(df)} records")
```

**TRANSFER ACTION:**
```bash
# Copy Qatar API integration
copy D:\udc\scripts\qatar_data_scraper_v2.py D:\lmis_int\src\data\apis\qatar_opendata.py

# Use with your agents for external validation
```

**VALUE:** Compare your LMIS data against official Qatar statistics!

---

## 📋 DATA CATALOG FILES TO COPY

### 5. Dataset Catalogs (JSON) ✅

**What UDC Has:**
- `qatar_actual_dataset_ids.json` - Complete catalog of 1,496 datasets
- `qatar_priority_datasets_for_udc.json` - Curated by category
- Dataset metadata with:
  - Dataset IDs
  - Titles
  - Descriptions
  - Categories
  - Update frequency

**TRANSFER ACTION:**
```bash
# Copy catalog files
copy D:\udc\qatar_actual_dataset_ids.json D:\lmis_int\metadata\
copy D:\udc\qatar_priority_datasets_for_udc.json D:\lmis_int\metadata\

# Use in your agents to discover relevant datasets dynamically
```

---

## 🚀 PRACTICAL TRANSFER PLAN

### Week 1: Data Transfer

**Day 1: Copy Qatar Open Data**
```bash
# Copy 1,152 CSV files (already downloaded!)
robocopy D:\udc\qatar_data\clean_unique_datasets D:\lmis_int\external_data\qatar_open_data /E

# Result: Instant access to 135 employment datasets
```

**Day 2: Copy API Integration Code**
```bash
# Copy working API scripts
copy D:\udc\scripts\test_semantic_scholar.py D:\lmis_int\src\data\apis\semantic_scholar.py
copy D:\udc\scripts\integrate_global_data_sources.py D:\lmis_int\src\data\apis\world_bank.py
copy D:\udc\scripts\qatar_data_scraper_v2.py D:\lmis_int\src\data\apis\qatar_opendata.py

# Copy catalog files
copy D:\udc\*.json D:\lmis_int\metadata\
```

**Day 3: Test Integration**
```python
# Test Semantic Scholar
from src.data.apis.semantic_scholar import search_papers
papers = search_papers('"qatar employment" OR "gcc labour market"')
print(f"Found {len(papers)} research papers")

# Test World Bank
from src.data.apis.world_bank import query_world_bank_labour_indicators
data = query_world_bank_labour_indicators(["QA", "SA", "AE"], "2019:2024")
print(f"Downloaded GCC labour data: {len(data)} indicators")

# Test Qatar Open Data
from src.data.apis.qatar_opendata import download_dataset_csv
df = download_dataset_csv("average-wages-and-salaries-by-economic-activity")
print(f"Qatar wage data: {len(df)} records")
```

---

## 💡 HOW QNWIS AGENTS USE THIS DATA

### Agent 1: Labour Economist
```python
# Use World Bank for GCC comparison
gcc_unemployment = world_bank.get_unemployment_rates(["QA", "SA", "AE"])

# Use Qatar Open Data for validation
qatar_employment = qatar_api.get_employment_by_sector()

# Compare LMIS vs Qatar Open Data
discrepancies = compare_lmis_vs_qatar_data()
```

### Agent 2: Nationalization Strategist
```python
# Use Semantic Scholar for best practices
research = semantic_scholar.search('"nationalization policies" OR "workforce localization"')

# Extract successful strategies from research
strategies = analyze_successful_nationalization_policies(research)
```

### Agent 3: Pattern Detective
```python
# Compare multiple data sources
lmis_salary = get_from_lmis("average_salary_by_sector")
qatar_salary = qatar_api.get_wages_by_sector()
world_bank_salary = world_bank.get_wage_indicators("QA")

# Identify discrepancies (fraud detection)
anomalies = detect_data_anomalies([lmis_salary, qatar_salary, world_bank_salary])
```

### Agent 5: National Strategy
```python
# GCC competitive analysis
gcc_labour_force = world_bank.get_labour_force_gcc()
gcc_wages = world_bank.get_wage_data_gcc()

# Research on regional competition
gcc_research = semantic_scholar.search('"gcc talent competition" OR "gulf brain drain"')

# Strategic positioning
qatar_position = analyze_qatar_competitive_position(gcc_labour_force, gcc_wages, gcc_research)
```

---

## ✅ SUMMARY: WHAT YOU'RE GETTING

### Data Assets
- ✅ **1,152 Qatar datasets** (already downloaded)
- ✅ **135 employment datasets** (directly useful)
- ✅ **314 demographics datasets**
- ✅ **54 GDP datasets**

### Working API Code
- ✅ **Semantic Scholar integration** (200M papers, real API key)
- ✅ **World Bank integration** (GCC labour indicators)
- ✅ **Qatar Open Data integration** (1,496 datasets)
- ✅ **Dataset catalogs** (JSON metadata)

### Time Savings
- **Data collection:** 0 hours (already downloaded!)
- **API integration:** 2-3 days (copy & adapt)
- **Testing:** 1 day
- **Total:** ~1 week vs 4-6 weeks from scratch

### Value
- **Instant external validation** for LMIS data
- **GCC competitive intelligence** (compare Qatar vs neighbors)
- **Academic research** (200M papers on labour topics)
- **Government statistics** (official Qatar data)

---

## 🎯 NEXT STEPS

1. **Copy data** (Day 1):
   ```bash
   robocopy D:\udc\qatar_data\clean_unique_datasets D:\lmis_int\external_data\qatar_open_data /E
   ```

2. **Copy API code** (Day 2):
   ```bash
   copy D:\udc\scripts\test_semantic_scholar.py D:\lmis_int\src\data\apis\
   copy D:\udc\scripts\integrate_global_data_sources.py D:\lmis_int\src\data\apis\
   ```

3. **Test integration** (Day 3):
   - Run semantic scholar search
   - Query World Bank GCC data
   - Download Qatar labour datasets

4. **Integrate with agents** (Week 2):
   - Add external data to agent context
   - Enable GCC comparisons
   - Validate LMIS against Qatar data

Ready to transfer? Let me know which component to start with!
