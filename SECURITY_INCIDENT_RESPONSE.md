# Security Incident Response - Exposed API Key

**Date**: November 4, 2025  
**Severity**: HIGH  
**Status**: MITIGATION IN PROGRESS

---

## 🚨 Incident Summary

**Exposed Secret**: Semantic Scholar API Key  
**Key Value**: `SAYzpCnxTxgayxysRRQM1wwrE7NslFn9uPKT2xy4`  
**Location**: `src/data/apis/semantic_scholar.py` (line 14)  
**Git Commit**: `1de2b58f52f4e3356164027ac4c21160d8333a01`  
**Repository**: https://github.com/albarami/QNWIS.git (PUBLIC)  
**Exposure Duration**: Unknown (until code sanitization on Nov 4, 2025)

---

## ✅ Immediate Actions Completed

1. **Code Sanitized** (✅ DONE)
   - Removed hardcoded key from `semantic_scholar.py`
   - Refactored to use `SEMANTIC_SCHOLAR_API_KEY` environment variable
   - Added input validation and error handling
   - Created comprehensive unit tests

2. **Secret Scanning** (✅ DONE)
   - Created `scripts/secret_scan.ps1` for CI/CD
   - No other hardcoded secrets found
   - `.gitignore` updated to prevent future `.env` commits

3. **Documentation** (✅ DONE)
   - Updated `.env.example` with required variables
   - Created `STEP_2A_COMPLETE.md` with security summary

---

## ⚠️ Actions Required IMMEDIATELY

### 1. Rotate Semantic Scholar API Key (URGENT)

**DO THIS NOW**:
```bash
# 1. Go to Semantic Scholar API portal
https://www.semanticscholar.org/product/api

# 2. Log in and revoke the compromised key:
SAYzpCnxTxgayxysRRQM1wwrE7NslFn9uPKT2xy4

# 3. Generate new key

# 4. Add to .env (NOT .env.example)
echo "SEMANTIC_SCHOLAR_API_KEY=your_new_key_here" >> .env

# 5. Test new key
.venv\Scripts\activate
pytest tests/unit/test_apis_semantic_scholar.py -v
```

**If you don't have account access**:
- Contact Semantic Scholar support immediately
- Request key invalidation for security incident
- Reference: exposed in public GitHub repository

---

### 2. Purge Key from Git History (REQUIRED)

**CRITICAL**: The old key is still in git history and visible on GitHub.

#### Option A: Automated Script (Recommended)
```powershell
# Run the prepared script
.\scripts\purge_secrets_from_history.ps1
```

The script will:
- ✅ Verify key rotation completed
- ✅ Create automatic backup
- ✅ Purge secrets from history
- ✅ Provide force-push instructions

#### Option B: Manual Cleanup
```bash
# 1. Create backup
git clone --mirror https://github.com/albarami/QNWIS.git ../QNWIS-backup

# 2. Install git-filter-repo
pip install git-filter-repo

# 3. Remove file with secrets from history
cd d:\lmis_int
git filter-repo --force --invert-paths --path src/data/apis/semantic_scholar.py

# 4. Re-add clean version
git add src/data/apis/semantic_scholar.py
git commit -m "Add sanitized semantic_scholar.py (no secrets)"

# 5. Force-push to GitHub
git push --force --all origin
git push --force --tags origin
```

---

### 3. Team Coordination

**BEFORE force-push, notify all team members**:

```
⚠️ SECURITY ALERT: Git history rewrite required

An API key was accidentally committed. We're purging git history.

ACTION REQUIRED:
1. Commit and push any pending work NOW
2. After force-push notification, delete your local copy
3. Fresh clone: git clone https://github.com/albarami/QNWIS.git

Timeline: [Specify when force-push will occur]
```

**AFTER force-push**:
- All team members must delete local clones
- Fresh `git clone` required
- Old clones will have merge conflicts

---

## 🔍 Impact Assessment

### Exposed Key Capabilities
Semantic Scholar API key allows:
- ✅ Search academic papers
- ✅ Get paper recommendations
- ✅ Retrieve paper metadata
- ❌ No write access
- ❌ No user data access
- ❌ No payment methods

### Risk Level: **MEDIUM**
- **Data Breach**: None (read-only API)
- **Financial Impact**: Potential quota exhaustion
- **Reputation**: Exposed in public repo
- **Compliance**: N/A (no PII/PCI involved)

### Potential Abuse Scenarios
1. ⚠️ **Quota Exhaustion**: Attacker uses key until rate limited
2. ⚠️ **Service Denial**: Key gets banned due to abuse
3. ⚠️ **Data Mining**: Unauthorized research data collection

---

## 📊 Monitoring & Verification

### Post-Rotation Checklist

- [ ] Old key revoked on Semantic Scholar portal
- [ ] New key generated and added to `.env`
- [ ] New key tested (tests pass)
- [ ] Git history purged (old key not in `git log`)
- [ ] Force-pushed to GitHub
- [ ] GitHub commit history verified clean
- [ ] Team members notified and re-cloned
- [ ] Monitor API usage for 7 days for anomalies

### Semantic Scholar API Monitoring
Check for unexpected activity:
```bash
# If Semantic Scholar provides usage dashboard
# Monitor for:
# - Unusual request volumes
# - Unexpected geographic origins
# - Abnormal query patterns
```

---

## 🛡️ Prevention Measures Implemented

1. **Secret Scanning** (✅)
   - `scripts/secret_scan.ps1` scans for hardcoded secrets
   - Run before every commit
   - Add to CI/CD pipeline

2. **Environment Variables** (✅)
   - All API credentials via environment
   - `.env` in `.gitignore`
   - `.env.example` with placeholders only

3. **Code Review** (✅)
   - No secrets in code reviews
   - Unit tests verify env-based auth

4. **Documentation** (✅)
   - Security guidelines in README
   - Incident response procedures

---

## 📝 Lessons Learned

### What Went Wrong
- API key hardcoded during initial development
- Committed to public GitHub repository
- No pre-commit secret scanning

### What Went Right
- Detected and fixed same day
- Comprehensive sanitization
- Automated tools created

### Process Improvements
1. **Add pre-commit hooks**:
   ```bash
   # .git/hooks/pre-commit
   .\scripts\secret_scan.ps1
   ```

2. **CI/CD Secret Scanning**:
   - Run `secret_scan.ps1` on every pull request
   - Block merges if secrets detected

3. **Developer Training**:
   - Never commit credentials
   - Always use environment variables
   - Review `.gitignore` before first commit

---

## 📞 Contacts

**Security Team**: [Add contact]  
**Semantic Scholar Support**: https://www.semanticscholar.org/product/api#api-support  
**GitHub Security**: https://github.com/albarami/QNWIS/security

---

## 🔄 Incident Timeline

| Time | Event | Action |
|------|-------|--------|
| Unknown | Key hardcoded in `semantic_scholar.py` | N/A |
| Unknown | Committed to public GitHub repo | N/A |
| Nov 4, 2025 | Detected during code review | Immediate sanitization |
| Nov 4, 2025 | Code refactored to use env vars | Completed |
| Nov 4, 2025 | Unit tests created | Completed |
| Nov 4, 2025 | Secret scanning script created | Completed |
| **PENDING** | **Key rotation** | **IN PROGRESS** |
| **PENDING** | **Git history purge** | **IN PROGRESS** |
| **PENDING** | **Force-push to GitHub** | **AWAITING** |
| **PENDING** | **Team re-clone coordination** | **AWAITING** |

---

## ✅ Incident Closure Criteria

- [x] Code sanitized (no hardcoded secrets)
- [x] Secret scanning implemented
- [x] Unit tests verify env-based auth
- [ ] **Old key revoked**
- [ ] **New key generated and tested**
- [ ] **Git history purged**
- [ ] **Force-pushed to GitHub**
- [ ] **GitHub history verified clean**
- [ ] **Team re-cloned**
- [ ] **7-day monitoring period completed**

---

**Status**: AWAITING KEY ROTATION AND HISTORY PURGE  
**Next Action**: Run `.\scripts\purge_secrets_from_history.ps1`  
**Owner**: Repository Administrator
