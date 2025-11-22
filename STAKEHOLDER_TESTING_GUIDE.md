# QNWIS Stakeholder Testing Guide

**Purpose:** Guide stakeholders through testing the system with REAL ministerial queries  
**Duration:** 1-2 weeks  
**Goal:** Validate system with actual use cases, gather feedback

---

## What to Test

### Test YOUR Real Questions

**Don't use scripted queries. Ask what you actually need to know:**

Examples of good test queries:
- "Should we approve QAR 5B budget for [specific initiative]?"
- "Compare Qatar's [sector] performance to regional competitors"
- "What are the risks of [specific policy decision]?"
- "Analyze impact of [recent event] on [sector]"
- "Recommend strategy for [actual ministerial priority]"

**The system is domain-agnostic - test ANY ministerial topic.**

---

## How to Evaluate Results

### 1. Data Depth
**Question:** Did the system provide enough facts to make a decision?  
**Target:** 80+ facts for complex queries  
**Evaluate:** Are there gaps? What data is missing?

### 2. Analysis Quality
**Question:** Is the analysis ministerial-grade?  
**Target:** Multi-perspective, evidence-based, actionable  
**Evaluate:** Could you brief the minister with this?

### 3. Confidence Calibration
**Question:** Are uncertainty levels appropriate?  
**Target:** 0.5-0.8 confidence for most queries  
**Evaluate:** Does high confidence = high quality? Low confidence = appropriate caution?

### 4. Source Diversity
**Question:** Are multiple authoritative sources used?  
**Target:** 5-10 sources for complex queries  
**Evaluate:** Are sources appropriate for the query?

### 5. Actionability
**Question:** Can you act on the recommendations?  
**Target:** Clear, specific, justified recommendations  
**Evaluate:** What would you need to add to make this actionable?

---

## Feedback Template

For each query tested, provide:

```
Query: [Your actual question]

✅ Strengths:
- What worked well?
- What impressed you?

⚠️ Gaps:
- What data was missing?
- What analysis was shallow?

💡 Suggestions:
- What would make this more useful?
- What additional sources needed?

⭐ Overall Rating: [1-5]

Would you use this for real ministerial briefings? [Yes/No/Maybe]
```

---

## Focus Areas

### Week 1: Breadth Testing
Test queries across different domains:
- Economic policy
- Social development
- Infrastructure
- Energy/environment
- Labor market
- Food security
- Healthcare
- Education
- Tourism
- Manufacturing

**Goal:** Validate domain-agnostic capability

### Week 2: Depth Testing
Pick 3-5 critical domains and go deep:
- Multiple queries per domain
- Follow-up questions
- Challenge the system
- Test edge cases

**Goal:** Validate analysis depth

---

## Success Criteria

**System is ready for production if:**
- [ ] 80%+ of queries rated 4-5 stars
- [ ] Stakeholders would use for real briefings
- [ ] Data gaps are identified and addressable
- [ ] No critical failures or errors
- [ ] Confidence scores make sense

**System needs more work if:**
- [ ] <60% of queries rated 4-5 stars
- [ ] Major data gaps across multiple domains
- [ ] Analysis quality inconsistent
- [ ] System errors or crashes

---

## What Happens Next

**If testing successful:**
1. Address minor feedback
2. Production deployment (Week 4)
3. Training for ministerial staff
4. Gradual rollout

**If testing reveals issues:**
1. Prioritize critical fixes
2. Re-test affected areas
3. Iterate until ready
4. Delayed production deployment

---

## Contact

**Questions during testing:** [Contact info]  
**Report issues:** [GitHub issues or email]  
**Emergency support:** [Contact info]

---

**Remember:** This is YOUR system. Test it like you'll use it. Ask REAL questions, not hypothetical ones. The goal is to validate this will actually help you do your job better.
