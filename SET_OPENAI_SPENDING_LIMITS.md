# Set OpenAI Spending Limits - Quick Guide

**Date**: October 29, 2025
**Purpose**: Protect against unexpected OpenAI costs

---

## 🎯 Recommended Limits

Based on balanced hybrid configuration (200 chapters/month):

| Limit Type | Amount | Purpose |
|------------|--------|---------|
| **Soft Limit** | $50/month | Alert when approaching budget |
| **Hard Limit** | $100/month | Stop API calls if exceeded |
| **Initial Testing** | $10/month | First week of testing |

---

## 📋 Step-by-Step Setup (5 minutes)

### Step 1: Go to OpenAI Billing Limits

**URL**: https://platform.openai.com/settings/organization/billing/limits

Or navigate:
1. Go to: https://platform.openai.com
2. Click your profile (top-right)
3. Select "Settings"
4. Click "Billing" → "Limits"

### Step 2: Set Soft Limit

1. Find "Usage limits" section
2. Click "Set soft limit"
3. Enter: **$50** (or $10 for testing)
4. Enable "Send email alert"
5. Click "Save"

**What happens**: You'll get email when you hit $50, but API continues working

### Step 3: Set Hard Limit

1. Find "Hard usage limit" section
2. Click "Set hard limit"
3. Enter: **$100** (or $20 for testing)
4. **Important**: Check "Disable API access when limit reached"
5. Click "Save"

**What happens**: API stops working at $100 to prevent overspending

### Step 4: Enable Notifications

1. Go to "Notification settings"
2. Enable:
   - ✓ Daily usage summary
   - ✓ Approaching limit warning (at 80%)
   - ✓ Limit reached alert
3. Add email address
4. Click "Save"

---

## 💰 Cost Expectations

### With Balanced Hybrid Config:

**Per Day** (200 chapters/month = ~7 chapters/day):
- Metadata extraction: 14 queries x $0.015 = $0.21
- Fact-checking: 35 queries x $0.015 = $0.525
- Embeddings: 35 queries x $0.000002 = $0.00007
- **Daily total**: ~$0.74

**Per Week**: ~$5
**Per Month**: ~$22
**Per Year**: ~$264

**Well under $50/month soft limit!**

### If Using Full GPT-4o (not hybrid):

**Per Day**: ~$12
**Per Month**: ~$360
**Would exceed soft limit** → Need to increase or optimize

---

## 🔔 Alert Recommendations

### Email Alerts Setup:

1. **Daily digest**: Review usage patterns
2. **80% warning**: Check if usage is normal
3. **100% hard limit**: Investigate immediately

### What to do when alerted:

**If usage is higher than expected**:
1. Check analytics: `backend/utils/ai_logging.py`
2. Review CostTracker summary
3. Identify high-cost operations
4. Optimize or increase limit

**If limit is too low**:
1. Verify costs are legitimate
2. Increase soft limit (e.g., $75)
3. Keep hard limit as safety net

---

## 🧪 Testing Period Recommendations

### Week 1: Conservative Testing

**Limits**:
- Soft: $10
- Hard: $20

**Why**: Test with low limits to ensure config is correct

**Expected**: ~$5 for week 1

### Week 2-4: Normal Operation

**Limits**:
- Soft: $50
- Hard: $100

**Why**: Comfortable buffer for 200 chapters/month

**Expected**: ~$22/month

### After Month 1: Optimize

**Review**:
- Actual costs vs. expected
- Usage patterns
- Quality metrics

**Adjust**:
- Limits based on actual usage
- Provider allocation if needed
- Increase limits for scale

---

## 📊 Cost Monitoring

### Daily Check (1 minute):

```bash
cd "/Users/ramihatoum/Desktop/The neurosurgical core of knowledge"

# View cost summary
python3 -c "
from backend.utils.ai_logging import CostTracker
print(CostTracker.get_cost_summary())
"
```

### Weekly Review (5 minutes):

1. Check OpenAI usage: https://platform.openai.com/settings/organization/usage
2. Compare with budget
3. Review cost tracking logs
4. Verify spend is on-track

### Monthly Analysis (15 minutes):

1. Full cost breakdown by task
2. Quality vs. cost analysis
3. Optimization opportunities
4. Plan adjustments if needed

---

## ⚠️ Emergency Procedures

### If Hard Limit Reached:

**Symptoms**: API calls return error, system falls back to Gemini/Claude

**Actions**:
1. Check if legitimate usage (analytics dashboard)
2. If legitimate: Increase hard limit temporarily
3. If unexpected: Investigate for bugs/loops
4. Review and optimize

### If Costs Are Too High:

**Options**:
1. **Increase Gemini usage**: Move more tasks to Gemini
2. **Reduce GPT-4o usage**: Only for critical tasks
3. **Optimize prompts**: Shorter prompts = lower costs
4. **Batch operations**: More efficient processing

### If Quality Suffers:

**Options**:
1. **Move back to Claude**: For specific tasks
2. **Hybrid approach**: Critical tasks = GPT-4o/Claude
3. **Increase budget**: Accept higher costs for quality

---

## 🎯 Quick Actions Checklist

**Right now (5 minutes)**:

- [ ] Go to: https://platform.openai.com/settings/organization/billing/limits
- [ ] Set soft limit: $50/month
- [ ] Set hard limit: $100/month
- [ ] Enable email notifications
- [ ] Add email address for alerts

**This week**:

- [ ] Monitor daily costs
- [ ] Verify limits are appropriate
- [ ] Adjust if needed

**Monthly**:

- [ ] Review total spend
- [ ] Compare quality vs. cost
- [ ] Optimize configuration
- [ ] Update limits based on scale

---

## 💡 Pro Tips

1. **Start conservative**: Lower limits for first week
2. **Monitor daily**: Catch issues early
3. **Use alerts**: Don't rely on manual checking
4. **Track by task**: Know what's expensive
5. **Optimize iteratively**: Small improvements add up

---

## 📞 Resources

### OpenAI Links:
- Limits: https://platform.openai.com/settings/organization/billing/limits
- Usage: https://platform.openai.com/settings/organization/usage
- Billing: https://platform.openai.com/settings/organization/billing

### System Tools:
- Cost tracking: `backend/utils/ai_logging.py`
- Analytics: Analytics dashboard
- Config: `backend/config/settings.py`

---

**Created**: October 29, 2025
**Status**: ✅ Action required - Set limits now!
**Estimated Monthly Cost**: $22 (with balanced hybrid)
**Recommended Limits**: $50 soft, $100 hard
