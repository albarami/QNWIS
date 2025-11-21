# QNWIS Scripts

## Production Scripts

### ETL (Extract, Transform, Load)

**World Bank Data**
```bash
python scripts/etl_world_bank_to_postgres.py
```
Loads 128 World Bank indicators for Qatar (2010-2024).  
GDP growth, sector breakdown, unemployment, etc.  
Writes to: `world_bank_indicators` table  
Runtime: ~30 seconds  
Output: 128 rows

**ILO Labor Data**
```bash
python scripts/etl_ilo_to_postgres.py
```
Loads ILO labor data for 6 GCC countries.  
Employment, unemployment by country  
Writes to: `ilo_labour_data` table  
Runtime: ~20 seconds  
Output: 6 rows

**FAO Food Security**
```bash
python scripts/etl_fao_to_postgres.py
```
Loads FAO food security data for Qatar.  
Food supply, import dependency, self-sufficiency  
Writes to: `fao_data` table  
Runtime: ~15 seconds  
Output: 1+ rows

**Qatar Open Data**
```bash
python scripts/etl_qatar_api_to_database.py
```
Loads Qatar national statistics from Open Data portal.  
Labor force, employment by sector, nationality  
Writes to multiple tables  
Runtime: ~45 seconds  
Output: Varies by dataset

### Database Setup

**Embeddings Table**
```bash
python scripts/create_embeddings_table_basic.py
```
Creates `document_embeddings` table with proper indexes.  
Uses JSONB for embeddings (upgradeable to pgvector)  
One-time setup  
Required before using RAG system

**Embeddings Migration**
```bash
python scripts/migrate_embeddings_to_postgres.py
```
Migrates in-memory embeddings to PostgreSQL.  
Moves existing RAG documents to database  
Run after creating embeddings table  
Idempotent (safe to re-run)

**pgvector Setup**
```bash
python scripts/setup_pgvector.py
```
Installs and configures pgvector extension.  
Enables vector similarity search  
Required for advanced RAG features  
One-time setup

### Verification

**Database Verification**
```bash
python scripts/verify_postgres_population.py
```
Checks all tables are populated correctly.  
Shows row counts for all tables  
Displays sample data  
Verifies data quality

---

## Initial Setup

Run these scripts in order:

```bash
# 1. Create embeddings table
python scripts/create_embeddings_table_basic.py

# 2. Load external data
python scripts/etl_world_bank_to_postgres.py
python scripts/etl_ilo_to_postgres.py
python scripts/etl_fao_to_postgres.py
python scripts/etl_qatar_api_to_database.py

# 3. Verify
python scripts/verify_postgres_population.py
```

**Expected output:**
- ✅ World Bank indicators: 128 rows
- ✅ ILO labour data: 6 rows
- ✅ FAO data: 1+ rows
- ✅ Qatar Open Data: Multiple datasets
- ✅ Document embeddings: Table ready

---

## Maintenance

**Weekly:** Re-run ETL scripts to refresh data
```bash
python scripts/etl_world_bank_to_postgres.py
python scripts/etl_ilo_to_postgres.py
python scripts/etl_fao_to_postgres.py
python scripts/etl_qatar_api_to_database.py
```

**Monthly:** Verify data quality
```bash
python scripts/verify_postgres_population.py
```

---

## Archived Scripts

See `scripts/archive/` for historical scripts kept for reference:

- **archive/seeding/** - Legacy database seeding scripts
- **archive/demos/** - Demo and example scripts
- **archive/dev-tools/** - Development and testing utilities

---

## Troubleshooting

**Error: DATABASE_URL not set**
```bash
export DATABASE_URL="postgresql://postgres:1234@localhost:5432/qnwis"
```

**Error: API key missing**  
Check `.env` file has all required keys.

**Error: Table doesn't exist**  
Run database schema first:
```bash
psql -d qnwis -f data/schema/lmis_schema.sql
```

**Error: Permission denied**  
Ensure PostgreSQL user has CREATE privileges:
```sql
GRANT ALL PRIVILEGES ON DATABASE qnwis TO postgres;
```

---

## Script Descriptions

| Script | Purpose | Frequency | Output |
|--------|---------|-----------|--------|
| `etl_world_bank_to_postgres.py` | Load World Bank indicators | Weekly | 128 rows |
| `etl_ilo_to_postgres.py` | Load ILO labor data | Weekly | 6 rows |
| `etl_fao_to_postgres.py` | Load FAO food security | Weekly | 1+ rows |
| `etl_qatar_api_to_database.py` | Load Qatar national statistics | Weekly | Multiple |
| `create_embeddings_table_basic.py` | Create embeddings table | Once | Table created |
| `migrate_embeddings_to_postgres.py` | Migrate RAG documents | Once | Documents migrated |
| `setup_pgvector.py` | Install pgvector extension | Once | Extension enabled |
| `verify_postgres_population.py` | Verify database | As needed | Report |

---

## Environment Requirements

- Python 3.11+
- PostgreSQL 15+
- DATABASE_URL configured in `.env`
- API keys (optional, for external APIs)

---

## Support

For issues or questions:
1. Check documentation in `docs/`
2. Review error logs
3. Verify environment configuration
4. Contact system administrator

---

**Last Updated:** November 2025  
**Status:** Production-ready  
**Quality:** Enterprise-grade
