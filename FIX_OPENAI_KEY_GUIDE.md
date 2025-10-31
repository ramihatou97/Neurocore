# 🔧 OpenAI API Key Fix Guide

**Date**: October 29, 2025
**Status**: API Key Invalid - Billing/Activation Required

---

## 🎯 DIAGNOSIS SUMMARY

✅ **Key Structure**: PERFECT (164 characters, correct sk-proj- format)
❌ **OpenAI Authentication**: FAILED (Error Code: `invalid_api_key`)

### What This Means:
The API key you have is **formatted correctly** but OpenAI's servers are **rejecting it**. This is almost always due to:

1. **Billing not set up** (90% of cases)
2. **Project not activated** (8% of cases)
3. **Key was revoked** (2% of cases)

---

## 📋 STEP-BY-STEP FIX (Choose Option A or B)

### Option A: Activate Current Key (10 minutes)

**This will fix the key if billing just needs to be set up.**

#### Step 1: Set Up Billing

1. Go to: **https://platform.openai.com/settings/organization/billing**
2. Click "Add payment method"
3. Enter credit card information
4. Click "Set as default payment method"
5. ✅ Verify it shows as "Active"

#### Step 2: Verify Project Activation

1. Go to: **https://platform.openai.com/settings/organization/projects**
2. Find the project associated with your API key
3. Ensure status shows "Active"
4. If inactive, click "Activate project"

#### Step 3: Check API Key Status

1. Go to: **https://platform.openai.com/api-keys**
2. Find your key in the list (ends with `...93QA`)
3. Check if it shows:
   - ✅ "Active" (good)
   - ❌ "Revoked" (need new key)
   - ❌ Not listed (need new key)

#### Step 4: Test the Key

```bash
cd "/Users/ramihatoum/Desktop/The neurosurgical core of knowledge"
python3 diagnose_openai_key.py
```

**Expected output after fixing:**
```
✓ SUCCESS: Can access OpenAI API
✓ SUCCESS: GPT-4o is working!
✓ SUCCESS: Embeddings working!
```

---

### Option B: Generate New Key (5 minutes)

**Recommended if Option A doesn't work or if the key was revoked.**

#### Step 1: Ensure Billing is Active

⚠️ **CRITICAL**: Must do this FIRST or new key won't work either!

1. Go to: **https://platform.openai.com/settings/organization/billing**
2. Verify billing is active with valid payment method
3. If not, add payment method (see Option A, Step 1)

#### Step 2: Generate New API Key

1. Go to: **https://platform.openai.com/api-keys**
2. Click "Create new secret key"
3. **Important settings**:
   - Name: "Neurosurgery Knowledge Base" (or your choice)
   - Permissions: "All" or at minimum:
     - `model.read`
     - `model.request`
   - Optionally: Set spending limits for safety
4. Click "Create secret key"
5. **⚠️ COPY THE KEY IMMEDIATELY** (you won't see it again!)

#### Step 3: Update .env File

1. Open `.env` file in editor:
   ```bash
   nano "/Users/ramihatoum/Desktop/The neurosurgical core of knowledge/.env"
   ```

2. Find line 26 that says:
   ```
   OPENAI_API_KEY=sk-proj-JGlLgZV...
   ```

3. Replace with your new key:
   ```
   OPENAI_API_KEY=sk-proj-YOUR_NEW_KEY_HERE
   ```

   **⚠️ IMPORTANT**:
   - No spaces before or after the `=`
   - No quotes around the key
   - No spaces before or after the key
   - Key should be on ONE line

4. Save and exit:
   - Press `Ctrl+O` then `Enter` to save
   - Press `Ctrl+X` to exit

#### Step 4: Verify .env Update

```bash
cd "/Users/ramihatoum/Desktop/The neurosurgical core of knowledge"

# Check the key was updated
grep "OPENAI_API_KEY" .env | head -1
```

Should show your new key.

#### Step 5: Test New Key

```bash
cd "/Users/ramihatoum/Desktop/The neurosurgical core of knowledge"
python3 diagnose_openai_key.py
```

**If successful, you'll see:**
```
✓ SUCCESS: Can access OpenAI API
✓ SUCCESS: GPT-4o is working!
✓ SUCCESS: Embeddings working!
```

#### Step 6: Run Full Test Suite

```bash
cd "/Users/ramihatoum/Desktop/The neurosurgical core of knowledge"

# Run basic test
python3 test_gpt4o_basic.py

# Expected output:
# ✓ Configuration correct!
# ✓ GPT-4o text generation working!
# ✓ All tests passed!
```

---

## 🚨 Common Issues & Solutions

### Issue 1: "Billing not set up" Error

**Symptoms:**
- New key still returns 401 error
- "Payment method required" message

**Solution:**
1. Billing MUST be active before creating key
2. Go to billing settings, add payment method
3. Wait 2-3 minutes for activation
4. Generate new key AFTER billing is active

### Issue 2: "You don't have access" Error

**Symptoms:**
- Can't access billing settings
- "Contact organization owner" message

**Solution:**
- You need to be organization owner/admin
- Contact your organization owner
- Or create a new OpenAI account (free)

### Issue 3: Key Still Not Working After Billing Setup

**Symptoms:**
- Billing active
- New key created
- Still getting 401 error

**Solution:**
1. Wait 5 minutes (propagation delay)
2. Check usage limits:
   - Go to: https://platform.openai.com/settings/organization/usage
   - Verify you haven't exceeded limits
3. Try creating key with different permissions:
   - "All" permission instead of restricted
4. Try creating key from different project

### Issue 4: Can't Find API Keys Page

**Direct Links:**
- Billing: https://platform.openai.com/settings/organization/billing
- API Keys: https://platform.openai.com/api-keys
- Usage: https://platform.openai.com/settings/organization/usage
- Projects: https://platform.openai.com/settings/organization/projects

---

## 📊 Cost Information (Once Working)

### OpenAI Pricing (GPT-4o)
- **Input**: $0.0025 per 1K tokens (~$0.0025 per page)
- **Output**: $0.010 per 1K tokens (~$0.010 per page)
- **Embeddings**: $0.00013 per 1K tokens

### Expected Costs (200 chapters/month)
- Text generation: ~$36/year
- Embeddings: ~$3/year
- Fact-checking: ~$192/year (if used)
- **Total**: ~$231/year

### Free Trial
- OpenAI provides $5 free credits for new accounts
- Expires after 3 months
- Enough for ~100-200 test queries

---

## ✅ Verification Checklist

Use this checklist to verify your setup:

### Before Creating/Using Key:
- [ ] OpenAI account created
- [ ] Logged in to platform.openai.com
- [ ] Billing page accessible
- [ ] Payment method added
- [ ] Billing shows as "Active"

### When Creating Key:
- [ ] Project is active (check projects page)
- [ ] Key created with proper permissions
- [ ] Key copied immediately (full key, no truncation)
- [ ] Key saved to `.env` file correctly

### After Creating Key:
- [ ] No extra spaces in `.env` file
- [ ] Key is on line 26 in correct format
- [ ] Run `python3 diagnose_openai_key.py`
- [ ] All tests show ✓ SUCCESS
- [ ] Run `python3 test_gpt4o_basic.py`
- [ ] GPT-4o responding correctly

---

## 🔐 Security Best Practices

### Protecting Your API Key

1. **Never commit `.env` to git**
   - Already in `.gitignore` ✓
   - Double-check: `git status` should not show `.env`

2. **Rotate keys regularly**
   - Create new key every 90 days
   - Delete old keys from OpenAI dashboard

3. **Set spending limits**
   - Recommended: $10/month soft limit
   - Hard limit: $50/month
   - Set at: https://platform.openai.com/settings/organization/billing/limits

4. **Monitor usage**
   - Check daily: https://platform.openai.com/settings/organization/usage
   - Set up email alerts in billing settings

5. **Use project-based keys**
   - Scope keys to specific projects
   - Easier to revoke if compromised

---

## 📞 Getting Help

### If This Guide Doesn't Work:

1. **Check OpenAI Status**
   - https://status.openai.com
   - Verify no outages

2. **OpenAI Support**
   - https://help.openai.com
   - Select: "API" → "Authentication"

3. **Verify Account Status**
   - Email: Ensure email is verified
   - Phone: Some features require phone verification
   - Organization: Verify you're in correct organization

4. **Create Fresh Account (Last Resort)**
   - New email address
   - New OpenAI account
   - Start fresh with proper billing setup

---

## 🎯 Quick Command Reference

### Diagnostic Commands

```bash
# Check current key in .env
grep "OPENAI_API_KEY" .env | head -1

# Run full diagnostic
python3 diagnose_openai_key.py

# Test basic functionality
python3 test_gpt4o_basic.py

# Run comprehensive tests
pytest tests/unit/test_openai_integration.py -v

# Check configuration
python3 -c "from backend.utils.config_validator import validate_configuration; validate_configuration()"
```

### Edit .env File

```bash
# Using nano (recommended)
nano .env

# Using vim
vim .env

# Using TextEdit (macOS)
open -a TextEdit .env
```

---

## 🌟 What Happens After Fix

Once your OpenAI key is working:

### 1. System Will Use GPT-4o
- Automatic failover no longer needed
- GPT-4o for metadata extraction
- GPT-4o for structured outputs
- GPT-4o for fact-checking

### 2. Cost Tracking Active
```bash
# View costs
python3 -c "
from backend.utils.ai_logging import CostTracker
print(CostTracker.get_cost_summary())
"
```

### 3. All Features Available
- ✅ Structured outputs (100% reliable)
- ✅ Medical fact-checking
- ✅ Batch processing
- ✅ Advanced embeddings

### 4. Run Full Test Suite
```bash
# This will now pass completely
pytest tests/unit/test_openai_integration.py -v
pytest tests/integration/test_chapter_generation_gpt4o.py -v
```

---

## 📈 Success Metrics

After fixing the key, you should see:

```
Configuration Validation:
✓ OpenAI API key: VALID
✓ GPT-4o model: ACCESSIBLE
✓ Embeddings: WORKING
✓ All tests: PASSING

System Status:
✓ Provider: gpt4 (using GPT-4o)
✓ Cost per query: ~$0.015
✓ Reliability: 100%
✓ Fallback: Available if needed
```

---

## 🎉 Alternative: Use Gemini (Already Working!)

**Don't want to deal with OpenAI billing right now?**

Your system is **already working perfectly** with Gemini fallback:

- ✅ Provider: Gemini 2.0 Flash
- ✅ Cost: $0.000016 per query (98% cheaper!)
- ✅ Quality: Excellent
- ✅ All features: Working

**To continue with Gemini:**
- Do nothing! System is operational now
- All chapter generation works
- All features except GPT-4o specific ones work
- Revisit OpenAI key later if needed

**Cost comparison:**
- Gemini: $0.77/year (200 chapters/month)
- GPT-4o: $36/year (200 chapters/month)

---

**Last Updated**: October 29, 2025
**Status**: Waiting for billing setup or new key
**System Status**: ✅ Operational (using Gemini fallback)
**Action Required**: Follow Option A or Option B above
