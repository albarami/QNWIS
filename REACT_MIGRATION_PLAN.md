# 🚀 Complete React + Vite Migration Plan
## Kill Chainlit Forever - Build It RIGHT

**Project**: QNWIS Multi-Agent Intelligence System  
**Goal**: Replace Chainlit with production-grade React + Vite frontend  
**Timeline**: 5 phases over 3-5 days

---

## Quick Navigation
- [Phase 1A: Minimal Setup (3h)](#phase-1a)
- [Phase 1B: Components (6h)](#phase-1b)
- [Phase 1C: Backend (4h)](#phase-1c)
- [Phase 2: Remove Chainlit (2h)](#phase-2)
- [Phase 3: Production (3h)](#phase-3)
- [Phase 4: Testing (4h)](#phase-4)
- [Phase 5: Docs (2h)](#phase-5)

---

## Phase 1A: Minimal React Setup (3 hours) {#phase-1a}

### Step 1.1: Initialize Project
```bash
cd d:\lmis_int
npm create vite@latest qnwis-ui -- --template react-ts
cd qnwis-ui
npm install
npm install axios @microsoft/fetch-event-source date-fns lucide-react
npm install -D @types/node tailwindcss postcss autoprefixer
```

**Commit:**
```bash
git add qnwis-ui/
git commit -m "feat(frontend): initialize React + Vite with TypeScript"
git push origin main
```

### Step 1.2: Configure Vite
Create `vite.config.ts` with API proxy

**Commit:**
```bash
git add qnwis-ui/vite.config.ts
git commit -m "config(frontend): add Vite proxy for API"
git push origin main
```

### Step 1.3: TypeScript Types
Create `src/types/workflow.ts`

**Commit:**
```bash
git add qnwis-ui/src/types/
git commit -m "feat(frontend): define TypeScript types for LangGraph"
git push origin main
```

### Step 1.4: SSE Hook
Create `src/hooks/useWorkflowStream.ts`

**Commit:**
```bash
git add qnwis-ui/src/hooks/
git commit -m "feat(frontend): implement SSE streaming hook"
git push origin main
```

### Step 1.5: MVP Component
Update `src/App.tsx`

**Commit:**
```bash
git add qnwis-ui/src/App.tsx
git commit -m "feat(frontend): build MVP application component"
git push origin main
```

### Step 1.6: Tailwind Setup
```bash
npx tailwindcss init -p
```

**Commit:**
```bash
git add qnwis-ui/tailwind.config.js qnwis-ui/src/index.css
git commit -m "style(frontend): configure Tailwind CSS"
git push origin main
```

---

## Phase 1B: Component Architecture (6 hours) {#phase-1b}

### Step 2.1: Component Structure
Create directory structure

**Commit:**
```bash
git add qnwis-ui/src/components/
git commit -m "refactor(frontend): create component structure"
git push origin main
```

### Step 2.2: Layout Components
Build Header, Footer, Layout

**Commit:**
```bash
git add qnwis-ui/src/components/layout/
git commit -m "feat(frontend): implement layout components"
git push origin main
```

### Step 2.3: Workflow Components
Build StageIndicator, QueryInput, etc.

**Commit:**
```bash
git add qnwis-ui/src/components/workflow/
git commit -m "feat(frontend): build workflow components"
git push origin main
```

### Step 2.4: Analysis Components
Build ExtractedFacts, AgentCard, etc.

**Commit:**
```bash
git add qnwis-ui/src/components/analysis/
git commit -m "feat(frontend): implement analysis components"
git push origin main
```

### Step 2.5: Common Components
Build Button, Card, Badge, etc.

**Commit:**
```bash
git add qnwis-ui/src/components/common/
git commit -m "feat(frontend): create reusable components"
git push origin main
```

### Step 2.6: Advanced Features
Query history, PDF export, comparison view

**Commit:**
```bash
git add qnwis-ui/src/features/
git commit -m "feat(frontend): add advanced features"
git push origin main
```

---

## Phase 1C: Backend Integration (4 hours) {#phase-1c}

### Step 3.1: CORS Setup
Update `src/qnwis/api/main.py`

**Commit:**
```bash
git add src/qnwis/api/main.py
git commit -m "config(backend): add CORS for React"
git push origin main
```

### Step 3.2: SSE Enhancement
Update `src/qnwis/api/routes/council.py`

**Commit:**
```bash
git add src/qnwis/api/routes/council.py
git commit -m "feat(backend): enhance SSE streaming"
git push origin main
```

### Step 3.3: Response Validation
Add Pydantic models

**Commit:**
```bash
git add src/qnwis/api/models/
git commit -m "feat(backend): add response validation"
git push origin main
```

---

## Phase 2: Chainlit Removal (2 hours) {#phase-2}

### Step 4.1: Audit
Create `CHAINLIT_AUDIT.md`

**Commit:**
```bash
git add CHAINLIT_AUDIT.md
git commit -m "docs(migration): audit Chainlit usage"
git push origin main
```

### Step 4.2: Remove App
```bash
git rm -rf apps/chainlit/
```

**Commit:**
```bash
git add pyproject.toml
git commit -m "remove(chainlit): delete Chainlit app"
git push origin main
```

### Step 4.3: Update Configs
Clean `.env`, `docker-compose`, `Makefile`

**Commit:**
```bash
git add .env.example ops/ Makefile
git commit -m "config: remove Chainlit configs"
git push origin main
```

### Step 4.4: Update Docs
Remove references

**Commit:**
```bash
git add README.md docs/
git commit -m "docs: remove Chainlit references"
git push origin main
```

---

## Phase 3: Production Deployment (3 hours) {#phase-3}

### Step 5.1: Build Config
Production `vite.config.ts`

**Commit:**
```bash
git add qnwis-ui/vite.config.ts
git commit -m "config(frontend): production build setup"
git push origin main
```

### Step 5.2: Docker
Create `Dockerfile` and update compose

**Commit:**
```bash
git add qnwis-ui/Dockerfile ops/docker/
git commit -m "docker(frontend): add production config"
git push origin main
```

### Step 5.3: Nginx
Configure nginx

**Commit:**
```bash
git add ops/nginx/
git commit -m "config(nginx): configure for React SPA"
git push origin main
```

### Step 5.4: CI/CD
Create `.github/workflows/frontend-ci.yml`

**Commit:**
```bash
git add .github/workflows/
git commit -m "ci(frontend): add CI/CD pipeline"
git push origin main
```

---

## Phase 4: Testing (4 hours) {#phase-4}

### Step 6.1: Unit Tests
**Commit:**
```bash
git add qnwis-ui/src/__tests__/
git commit -m "test(frontend): add unit tests"
git push origin main
```

### Step 6.2: Integration Tests
**Commit:**
```bash
git add qnwis-ui/src/__tests__/integration/
git commit -m "test(frontend): add integration tests"
git push origin main
```

### Step 6.3: E2E Tests
**Commit:**
```bash
git add qnwis-ui/e2e/
git commit -m "test(frontend): add E2E tests"
git push origin main
```

---

## Phase 5: Documentation (2 hours) {#phase-5}

### Step 7.1: Frontend Docs
**Commit:**
```bash
git add qnwis-ui/README.md
git commit -m "docs(frontend): add comprehensive docs"
git push origin main
```

### Step 7.2: Architecture
**Commit:**
```bash
git add docs/architecture/
git commit -m "docs(architecture): document frontend"
git push origin main
```

### Step 7.3: Deployment Guide
**Commit:**
```bash
git add docs/deployment/
git commit -m "docs(deployment): add frontend guide"
git push origin main
```

### Step 7.4: Migration Summary
**Commit:**
```bash
git add CHAINLIT_TO_REACT_MIGRATION_COMPLETE.md
git commit -m "docs(migration): create completion summary"
git push origin main
```

---

## 🎯 Success Criteria

**Phase 1A:** React app running, SSE working, basic UI complete  
**Phase 1B:** Component architecture, advanced features  
**Phase 1C:** Backend integration complete  
**Phase 2:** Chainlit completely removed  
**Phase 3:** Production-ready deployment  
**Phase 4:** 80%+ test coverage  
**Phase 5:** Complete documentation

---

## 🚨 Common Issues

### CORS Errors
Add to FastAPI:
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"])
```

### SSE Not Working
Check backend format:
```python
yield f"data: {json.dumps(event)}\n\n"
```

### Build Errors
Clear cache:
```bash
rm -rf node_modules package-lock.json
npm install
```

---

## Next Steps
1. Run Step 1.1 commands
2. Copy provided code files
3. Test basic functionality
4. Report any errors
5. Proceed to next phase

Ready to execute! 🚀
