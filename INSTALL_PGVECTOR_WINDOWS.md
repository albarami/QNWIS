# Installing pgvector on Windows PostgreSQL 15

## PROPER INSTALLATION STEPS

### Option 1: Download Pre-built Binary (FASTEST)

1. **Download pgvector for PostgreSQL 15 (Windows)**
   ```
   https://github.com/pgvector/pgvector/releases
   ```
   Download: `pgvector-v0.5.1-pg15-windows-x64.zip` (or latest version)

2. **Extract and Install**
   ```powershell
   # Extract to PostgreSQL extension directory
   # Typically: C:\Program Files\PostgreSQL\15\
   
   # Copy files:
   # - vector.dll -> C:\Program Files\PostgreSQL\15\lib\
   # - vector.control -> C:\Program Files\PostgreSQL\15\share\extension\
   # - vector--*.sql -> C:\Program Files\PostgreSQL\15\share\extension\
   ```

3. **Restart PostgreSQL Service**
   ```powershell
   # As Administrator
   Restart-Service postgresql-x64-15
   ```

4. **Enable in Database**
   ```sql
   CREATE EXTENSION vector;
   ```

### Option 2: Build from Source (If no binary available)

1. **Install Prerequisites**
   - Visual Studio 2019 or later with C++ support
   - PostgreSQL 15 development files

2. **Clone and Build**
   ```powershell
   git clone https://github.com/pgvector/pgvector.git
   cd pgvector
   
   # Use nmake with MSVC
   nmake /F Makefile.win
   nmake /F Makefile.win install
   ```

### Option 3: Use pgvector-compatible Alternative

If pgvector installation fails, use PostgreSQL's built-in features:

**Create table with BYTEA instead of vector type:**
```sql
CREATE TABLE document_embeddings (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(100) UNIQUE,
    source VARCHAR(50),
    chunk_text TEXT,
    embedding BYTEA,  -- Store as binary instead of vector
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create GiST index for similarity search
CREATE INDEX document_embeddings_embedding_idx 
ON document_embeddings 
USING gist (embedding);
```

## VERIFICATION

After installation:
```sql
-- Connect to database
\c qnwis

-- Check if extension is available
SELECT * FROM pg_available_extensions WHERE name = 'vector';

-- Create extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
```

## CURRENT STATUS

**pgvector NOT installed** - Need to install before proceeding with embeddings.

**Action Required:**
1. Download pgvector binary for PostgreSQL 15 Windows
2. Install to PostgreSQL directory
3. Restart PostgreSQL service
4. Run: CREATE EXTENSION vector;
