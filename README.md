# QNWIS - Qatar National Workforce Intelligence System

**Status:** ✅ PILOT VALIDATED - Ready for Development Deployment  
**Version:** Week 3  
**Success Rate:** 10/10 queries (100%)

---

## What is QNWIS?

A domain-agnostic ministerial intelligence system that provides PhD-level policy analysis across ANY topic Qatar's economic committee might discuss.

**Not just labor. Not just food. ANYTHING:**
- Economic diversification strategy
- Energy sector decisions
- Tourism development
- Healthcare infrastructure
- Digital transformation
- Manufacturing competitiveness
- Food security
- Workforce nationalization
- Infrastructure investment
- And more...

---

## System Architecture

**Backend:**
- Python 3.11+ with LangGraph orchestration
- FastAPI server (port 8000)
- PostgreSQL database (128 cached World Bank indicators)
- Anthropic Claude Sonnet 4.5

**Frontend:**
- React 19.0 with concurrent rendering
- TypeScript 5.9 (strict mode)
- Vite 7.2 (lightning-fast dev server)
- TailwindCSS 3.4 (utility-first styling)
- Lucide React (icons)
- @microsoft/fetch-event-source (SSE streaming)
- Port 3000

**Integration:**
- Real-time SSE streaming from backend to frontend
- Live multi-agent workflow visualization
- 12-agent debate displayed in real-time

---

## Key Features

✅ **Domain-Agnostic:** Works across 15+ ministerial domains  
✅ **Multi-Source:** Integrates 15+ authoritative APIs  
✅ **Real-Time:** Perplexity + Brave for current data  
✅ **Research-Backed:** Semantic Scholar (6+ papers per query)  
✅ **Evidence-Based:** Every fact cited to source  
✅ **Multi-Perspective:** 4 specialist agents debate each query  
✅ **Transparent:** Full reasoning chains visible  
✅ **High-Quality:** 154 facts avg, 0.67 confidence  
✅ **Live Streaming:** Real-time workflow updates via SSE

---

## Pilot Validation Results

**10/10 queries passing (100% success rate)**

| Domain | Facts | Sources | Confidence |
|--------|-------|---------|------------|
| Economic | 175 | 11 | 0.67 ✅ |
| Energy | 168 | 9 | 0.68 ✅ |
| Tourism | 141 | 3 | 0.67 ✅ |
| Food | 163 | 7 | 0.64 ✅ |
| Healthcare | 141 | 3 | 0.67 ✅ |
| Digital/AI | 157 | 9 | 0.74 ✅ |
| Manufacturing | 141 | 3 | 0.67 ✅ |
| Workforce | 157 | 9 | 0.64 ✅ |
| Infrastructure | 141 | 3 | 0.62 ✅ |
| Cross-Domain | 156 | 8 | 0.70 ✅ |

**Average: 154 facts, 0.67 confidence, 7 sources per query**

---

## Quick Start

### Backend Setup

```bash
# Clone and setup
git clone https://github.com/albarami/QNWIS.git
cd QNWIS

# Python environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate    # Linux/Mac

pip install -r requirements.txt

# Configure
cp .env.example .env
# Add your ANTHROPIC_API_KEY=sk-ant-...

# Initialize database
python scripts/init_db.py
python scripts/load_wb_cache.py

# Validate
python validate_langgraph_refactor.py

# Start backend (port 8000)
python -m qnwis.main
```

### Frontend Setup

```bash
# Navigate to frontend
cd qnwis-frontend

# Install dependencies
npm install

# Start dev server (port 3000)
npm run dev

# Build for production
npm run build
```

### Access

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

---

## Frontend Features

### Live Workflow Visualization:
- 12-agent grid with real-time status updates
- Multi-agent debate panel with live conversations
- Stage progress timeline
- Critique & verification panels
- Executive summary with confidence scores

### SSE Streaming:
- Real-time updates as agents work
- Live debate turns streamed to UI
- Extraction progress visible
- Final synthesis streams incrementally

### Components:
```
qnwis-frontend/src/
├── components/
│   ├── agents/      # AgentCard, AgentGrid
│   ├── debate/      # DebatePanel, DebateConversation  
│   ├── critique/    # CritiquePanel
│   ├── results/     # ExecutiveSummary, VerificationPanel
│   └── workflow/    # StageProgress, StageTimeline
├── hooks/
│   └── useWorkflowStream.ts  # SSE streaming logic
└── types/
    └── workflow.ts  # TypeScript definitions
```

---

## Data Sources (15+)

**International Organizations:**
World Bank, IMF, ILO, FAO, UNCTAD, UNWTO, IEA, UN Comtrade, FRED

**Regional & Local:**
GCC-STAT, MoL LMIS, Qatar Open Data

**Research & Intelligence:**
Semantic Scholar (200M+ papers), Brave Search, Perplexity AI

---

## Technology Stack

### Backend:
- Python 3.11+ (async)
- LangGraph (orchestration)
- FastAPI (API server)
- PostgreSQL (data cache)
- Anthropic Claude Sonnet 4.5 (LLM)

### Frontend:
- React 19.0 (concurrent rendering)
- TypeScript 5.9 (strict mode)
- Vite 7.2 (build tool)
- TailwindCSS 3.4 (styling)
- @microsoft/fetch-event-source (SSE)

### Infrastructure:
- Docker (containerization)
- GitHub (version control)
- SSE (real-time streaming)

---

## Documentation

- **Week 3 Pilot Report** - Complete validation results
- **Deployment Guide** - Full setup instructions
- **Architecture** - System design
- **Stakeholder Testing** - Testing framework
- **Frontend README** - Frontend-specific docs

---

## API Documentation

FastAPI auto-generated docs:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI spec:** http://localhost:8000/openapi.json

**Main endpoints:**
- `POST /api/v1/council/stream` - SSE streaming workflow
- `GET /health` - Health check
- `GET /api/v1/sources` - List data sources

---

## Status

- **Current:** Development deployment ready
- **Next:** Stakeholder testing (1-2 weeks)
- **Target:** Production deployment (Week 4)
- **Last validated:** November 22, 2025
- **Pilot success rate:** 100% (10/10)
- **Production readiness:** ✅ APPROVED

---

## Contributing

See CONTRIBUTING.md for development workflow.

## License

[Your license]

## Contact

[Your contact info]
