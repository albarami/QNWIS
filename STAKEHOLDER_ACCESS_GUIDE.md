# QNWIS Development Access Guide

**For Stakeholders:** How to access and test the system

---

## Quick Access

**System URL:** http://localhost:3000  
**Status:** Development environment (Week 3 validated)  
**Available:** [Date/time when deployed]

---

## What You'll See

### Homepage
- Query input field
- 12-agent visualization grid
- Real-time workflow display

### When You Submit a Query

**Phase 1: Data Extraction**
- Watch as system fetches from 15+ data sources
- Progress bar shows extraction status
- Sources appear as they complete

**Phase 2: Multi-Agent Analysis**
- 4 specialist agents analyze in parallel:
  - Financial Economist
  - Market Analyst
  - Operations Expert
  - Research Scientist
- Each agent card shows live status

**Phase 3: Multi-Agent Debate**
- Agents discuss findings
- Debate panel shows conversation in real-time
- Watch perspectives emerge

**Phase 4: Critique & Verification**
- Devil's advocate challenges conclusions
- Fact checker verifies all claims
- Confidence scores displayed

**Phase 5: Final Synthesis**
- Executive summary generated
- Confidence score shown
- All sources cited

**Total time: 1-3 minutes** (depending on query complexity)

---

## How to Test

### Your First Query

**Try this:**
```
What is Qatar's GDP growth trend over the last 5 years?
```

**What to expect:**
- 80-150 facts extracted
- Data from World Bank, IMF, GCC-STAT
- Analysis from all 4 agents
- Confidence score: 0.6-0.8
- Clear executive summary

### Test Different Domains

**The system is domain-agnostic. Try queries like:**

**Economic:**
- "Analyze Qatar's non-oil GDP diversification progress"
- "Compare Qatar's fiscal position to GCC countries"

**Energy:**
- "Should Qatar invest QAR 30B in renewable energy by 2030?"
- "Evaluate Qatar's LNG export competitiveness"

**Tourism:**
- "Compare Qatar's tourism performance to Dubai"
- "Assess World Cup legacy impact on tourism sector"

**Food Security:**
- "What is Qatar's food self-sufficiency by category?"
- "Analyze Qatar's agricultural sector potential"

**Healthcare:**
- "Evaluate Qatar's healthcare infrastructure capacity"
- "Compare Qatar's health outcomes to regional peers"

**Digital/AI:**
- "Should Qatar invest QAR 20B in AI sector by 2030?"
- "Assess Qatar's digital transformation readiness"

**Workforce:**
- "Evaluate feasibility of 60% Qatarization by 2030"
- "Analyze Qatar's labor force participation trends"

**Infrastructure:**
- "Should Qatar invest QAR 15B in metro expansion?"
- "Evaluate Qatar's infrastructure quality gaps"

**Cross-Domain:**
- "Recommend top 3 sectors for QAR 50B investment fund"
- "What are biggest economic risks facing Qatar?"

---

## What to Look For

### Data Quality
- [ ] Are 80+ facts extracted?
- [ ] Are sources diverse (5-10 sources)?
- [ ] Are citations present for all claims?
- [ ] Is data current (2023-2024)?

### Analysis Quality
- [ ] Do agents show different perspectives?
- [ ] Is debate substantive (not generic)?
- [ ] Are recommendations specific and actionable?
- [ ] Is synthesis coherent and clear?

### Confidence Calibration
- [ ] High confidence (0.7-0.8) when data is strong?
- [ ] Low confidence (0.4-0.5) when uncertain?
- [ ] Does confidence match your assessment?

### User Experience
- [ ] Is the interface clear and intuitive?
- [ ] Are live updates smooth and informative?
- [ ] Is the final report easy to understand?
- [ ] Would you use this for real briefings?

---

## Providing Feedback

### For Each Query You Test

**Use this template:**

```
Query: [What you asked]

Rating: ⭐⭐⭐⭐⭐ (1-5 stars)

✅ Strengths:
- [What worked well?]
- [What impressed you?]

⚠️ Gaps:
- [What data was missing?]
- [What analysis was shallow?]

💡 Suggestions:
- [What would improve this?]
- [What features would help?]

Would you use this for ministerial briefings? [Yes / No / Maybe - explain]
```

**Send feedback to:** [Your contact method]

---

## Known Limitations

**The system currently:**
- ✅ Works across 15+ ministerial domains
- ✅ Provides 80-150 facts per query
- ✅ Includes real-time data (Perplexity, Brave)
- ✅ Cites all sources
- ⚠️ Takes 1-3 minutes per query (appropriate for depth)
- ⚠️ Some data sources require API keys (UN Comtrade, FRED, MoL LMIS)
- ⚠️ Best for strategic queries, not simple factual lookups

---

## Troubleshooting

**Issue: "Cannot connect to server"**
→ Backend may not be running. Contact admin.

**Issue: Query takes very long (>5 minutes)**
→ May be food security query with UN Comtrade rate limiting. This is known.

**Issue: Low confidence score (<0.4)**
→ May indicate insufficient data for that specific query. Try rephrasing.

**Issue: Few facts extracted (<50)**
→ Topic may have limited data coverage. Try broader query.

---

## Questions?

**Technical support:** [Contact]  
**Feedback:** [Contact]  
**System issues:** [Contact]

---

**Remember:** This is YOUR system. Test it with YOUR real questions. The goal is to validate it will help you do your job better.

**Thank you for testing QNWIS!**
