# Quick Start Guide: Using the AI-Assisted Development Workflow

## Overview

You'll use **OpenAI** as the orchestrator that generates three prompts for each development step:
1. **Cascade** (in Windsurf) - Implements the code
2. **Codex 5** (in Windsurf) - Reviews and enhances
3. **Claude Code** (in Windsurf) - Tests and deploys

---

## Setup Steps

### 1. Create OpenAI Project

1. Go to OpenAI Platform
2. Create new project: **"QNWIS Development"**
3. Upload the meta-instruction document: `OPENAI_PROJECT_META_INSTRUCTION.md`
4. Set project instructions to reference this document

### 2. Prepare Windsurf IDE

1. Open Windsurf IDE
2. Install extensions:
   - Cascade
   - Codex 5
   - Claude Code
3. Create new workspace: `/qnwis`

### 3. Prepare GitHub Repository

```bash
# Create GitHub repo
gh repo create qnwis --private

# Clone locally
git clone https://github.com/[your-username]/qnwis.git
cd qnwis

# Initialize
git branch -M main
```

---

## Workflow: Step-by-Step

### Phase 1: Get Instructions from OpenAI

**In OpenAI Chat (with QNWIS Project selected):**

```
You: BEGIN QNWIS DEVELOPMENT
```

**OpenAI will respond with:**
```
═══════════════════════════════════════════════════════════════
QNWIS DEVELOPMENT - STEP 1: Project Structure & Configuration
═══════════════════════════════════════════════════════════════

📋 PROMPT 1 → CASCADE (IMPLEMENTATION)
[Detailed implementation instructions]

🔍 PROMPT 2 → CODEX 5 (REVIEW & ENHANCEMENT)
[Detailed review instructions]

✅ PROMPT 3 → CLAUDE CODE (TESTING & DEPLOYMENT)
[Detailed testing instructions]
═══════════════════════════════════════════════════════════════
```

### Phase 2: Execute with Cascade (Windsurf)

**Copy PROMPT 1 entirely and paste into Windsurf Cascade:**

```
[Paste entire PROMPT 1 from OpenAI]
```

**Cascade will:**
- Create all required files
- Implement complete functionality
- Generate initial tests

**Your job:** Review output, make sure it looks reasonable

### Phase 3: Review with Codex 5 (Windsurf)

**Copy PROMPT 2 entirely and paste into Windsurf Codex 5:**

```
[Paste entire PROMPT 2 from OpenAI]
```

**Codex 5 will:**
- Review everything Cascade created
- Fix any placeholders
- Enhance code quality
- Optimize performance
- Improve error handling

**Your job:** Review the changes, understand what was improved

### Phase 4: Test with Claude Code (Windsurf)

**Copy PROMPT 3 entirely and paste into Windsurf Claude Code:**

```
[Paste entire PROMPT 3 from OpenAI]
```

**Claude Code will:**
- Write comprehensive tests
- Run all tests
- Check code coverage
- Run security scans
- Run linters
- Git commit and push

**Your job:** Review test results, ensure everything passes

### Phase 5: Confirm and Move to Next Step

**When Claude Code gives final sign-off:**

```
✅ STEP 1 COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
All tests passing
Coverage: 95%
Git: Committed and pushed
Ready for Step 2
```

**Go back to OpenAI and say:**

```
You: NEXT STEP
```

**OpenAI generates Step 2 with three new prompts. Repeat the process.**

---

## Typical Day of Development

### Morning Session (3-4 hours)

**8:00 AM - Get instructions**
```
OpenAI: "BEGIN QNWIS DEVELOPMENT" or "NEXT STEP"
```

**8:05 AM - Cascade implements (Step 1)**
- Copy PROMPT 1 to Cascade
- Review output (~15 minutes)

**8:20 AM - Codex 5 reviews**
- Copy PROMPT 2 to Codex 5
- Review improvements (~15 minutes)

**8:35 AM - Claude Code tests**
- Copy PROMPT 3 to Claude Code
- Review test results (~20 minutes)

**8:55 AM - Confirm completion**
- Verify tests pass
- Check git commit
- Ask OpenAI for "NEXT STEP"

**9:00 AM - Coffee break** ☕

**9:15 AM - Repeat for Step 2**
- Cascade → Codex 5 → Claude Code
- 45-60 minutes per step

**By 12:00 PM:** Complete 3-4 steps

### Afternoon Session (3-4 hours)

**2:00 PM - Continue**
- Complete 3-4 more steps
- Same workflow

**By 6:00 PM:** Complete 6-8 steps total for the day

---

## Example: Complete Workflow for Step 1

### 1. OpenAI Generates Prompts

```
You: BEGIN QNWIS DEVELOPMENT

OpenAI: [Generates Step 1 with three prompts]
```

### 2. Cascade Implementation

**You copy this to Windsurf Cascade:**

```
OBJECTIVE: Set up the complete QNWIS project structure with configuration files.

FILES TO CREATE:
• /qnwis/src/config/settings.py - Configuration management
• /qnwis/src/utils/logger.py - Logging setup
• /qnwis/docker-compose.yml - Docker orchestration
[... full PROMPT 1 content ...]
```

**Cascade creates:**
```
/qnwis/
├── src/
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py ✅ Created
│   └── utils/
│       ├── __init__.py
│       └── logger.py ✅ Created
├── docker-compose.yml ✅ Created
├── Dockerfile ✅ Created
├── requirements.txt ✅ Created
└── README.md ✅ Created
```

**You verify:** Files look good ✅

### 3. Codex 5 Review

**You copy this to Windsurf Codex 5:**

```
YOUR ROLE: Code Reviewer & Quality Enhancer

OBJECTIVE: Review Step 1 implementation

FILES TO REVIEW:
• /qnwis/src/config/settings.py
• /qnwis/src/utils/logger.py
[... full PROMPT 2 content ...]
```

**Codex 5 reports:**
```
REVIEW COMPLETE:

Issues Found and Fixed:
1. Added pydantic validators to settings.py
2. Enhanced logger with JSON formatting
3. Added health checks to docker-compose.yml
4. Improved Dockerfile security (non-root user)
5. Added missing dependencies

All placeholders removed ✅
Code quality improved ✅
Security hardened ✅
```

**You verify:** Improvements make sense ✅

### 4. Claude Code Testing

**You copy this to Windsurf Claude Code:**

```
YOUR ROLE: QA Engineer & Deployment Specialist

OBJECTIVE: Test and validate Step 1

TEST CATEGORIES:
1. Unit tests for configuration
2. Integration tests for Docker
[... full PROMPT 3 content ...]
```

**Claude Code executes:**
```
Running tests...

✅ test_settings_loads_from_env - PASSED
✅ test_settings_validates_required_fields - PASSED
✅ test_logger_initialization - PASSED
✅ test_docker_compose_builds - PASSED
✅ test_postgres_container_starts - PASSED

Coverage: 95%
Security: No vulnerabilities
Linters: All pass

Committing to git...
git commit -m "Step 1: Project Structure & Configuration"
git push origin feature/step-1-project-structure

✅ STEP 1 COMPLETE
Ready for Step 2
```

**You verify:** All tests passed ✅

### 5. Move to Next Step

**Back to OpenAI:**

```
You: NEXT STEP

OpenAI: [Generates Step 2 with three new prompts]
```

**Repeat the process!**

---

## Tips for Success

### Do's ✅

- **Copy entire prompts** (don't edit or summarize)
- **Review AI output** after each stage
- **Verify tests pass** before moving on
- **Keep OpenAI chat organized** (one step per message)
- **Take breaks** between steps (avoid burnout)
- **Commit frequently** (after each step)

### Don'ts ❌

- **Don't skip stages** (Cascade → Codex → Claude sequence is important)
- **Don't move to next step** if current step has failing tests
- **Don't edit prompts** (they're carefully crafted)
- **Don't rush** (quality over speed)
- **Don't work on multiple steps** simultaneously

---

## Troubleshooting

### Issue: Cascade creates placeholders

**Solution:**
- Codex 5 will catch and fix them
- If Codex misses them, Claude Code will catch
- Worst case: Manually review and ask Codex to fix

### Issue: Tests fail in Claude Code

**Solution:**
```
You to Claude Code: "Tests failed. Here are the errors: [paste errors]
Please return to Codex 5 for fixes, then re-test."
```

### Issue: Lost context between steps

**Solution:**
- OpenAI maintains context within project
- Reference previous step numbers
- Each prompt includes dependencies

### Issue: AI gets confused

**Solution:**
```
You to OpenAI: "Reset context. Let's clarify: We just completed Step X.
The files created were: [list files]
Now generate prompts for Step X+1."
```

---

## Progress Tracking

### Daily Log Template

Create a file: `/qnwis/DEVELOPMENT_LOG.md`

```markdown
# QNWIS Development Log

## Week 2

### Monday, [Date]
- ✅ Step 1: Project Structure (8:00-9:00 AM)
- ✅ Step 2: Database Schema (9:15-10:15 AM)
- ✅ Step 3: LMIS Integration (10:30-12:00 PM)
- ✅ Step 4: API Connectors (2:00-3:30 PM)
- ⏸️ Step 5: Caching Layer (started, continue tomorrow)

**Issues:**
- PostgreSQL connection needed retry logic (fixed in Step 3)

**Notes:**
- Step 3 took longer than expected (complex data schema)
- Database indexes identified for Step 6

### Tuesday, [Date]
- ✅ Step 5: Caching Layer (8:00-9:00 AM)
[...]
```

### Step Completion Checklist

After each step, verify:

```
□ Cascade implemented all required files
□ Codex 5 removed all placeholders
□ Codex 5 enhanced code quality
□ Claude Code tests all pass
□ Code coverage >90%
□ No security vulnerabilities
□ Linters pass
□ Git commit successful
□ OpenAI confirmed ready for next step
```

---

## Time Estimates

### Per Step (Average)

- Cascade implementation: 10-15 minutes
- Your review: 5 minutes
- Codex 5 enhancement: 10-15 minutes
- Your review: 5 minutes
- Claude Code testing: 15-20 minutes
- Your review: 5 minutes
- **Total: 50-65 minutes per step**

### Per Day

- Morning session: 3-4 steps (3-4 hours)
- Afternoon session: 3-4 steps (3-4 hours)
- **Total: 6-8 steps per day**

### Full Project

- Total steps: ~35-40 steps
- Days needed: 5-7 days of focused development
- Calendar weeks: 2-3 weeks (accounting for meetings, breaks)

---

## When You're Done

### After 35-40 steps completed:

```
You to OpenAI: "DEVELOPMENT COMPLETE. Generate final validation checklist."

OpenAI will provide:
- Complete system test plan
- Integration verification steps
- Performance benchmark tests
- Security audit checklist
- Documentation review
- Deployment readiness assessment
```

### Final Validation

Run comprehensive system tests:

```bash
# Run all tests
pytest tests/ -v --cov=src

# Security scan
safety check
bandit -r src/

# Performance test
python scripts/benchmark.py

# Documentation check
mkdocs build

# Docker deployment test
docker-compose up --build
```

### Deployment

```bash
# Tag release
git tag -a v1.0.0 -m "QNWIS MVP Release"
git push origin v1.0.0

# Deploy to production
docker-compose -f docker-compose.prod.yml up -d
```

---

## Summary

**Your workflow is:**

1. **OpenAI** - Generates three prompts per step
2. **Cascade** - Implements (Prompt 1)
3. **Codex 5** - Reviews & enhances (Prompt 2)
4. **Claude Code** - Tests & deploys (Prompt 3)
5. **Repeat** - Move to next step

**You are the orchestrator** - copy prompts, review outputs, verify quality, move forward.

**The AI assistants do the coding** - you ensure the system is being built correctly.

---

## Quick Reference Commands

### OpenAI Commands

```
"BEGIN QNWIS DEVELOPMENT" - Start from Step 1
"NEXT STEP" - Generate next step's prompts
"SHOW DEVELOPMENT ROADMAP" - See all planned steps
"CLARIFY STEP X" - Get more details on a step
```

### Verification Commands

```bash
# After each step
pytest tests/unit/ -v --cov
flake8 src/
mypy src/
docker-compose build

# Check git status
git status
git log --oneline -5
```

---

**You're ready to start! Go to OpenAI and say: "BEGIN QNWIS DEVELOPMENT"** 🚀
