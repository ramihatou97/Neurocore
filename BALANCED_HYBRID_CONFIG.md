# Balanced Hybrid AI Provider Configuration

**Date**: October 29, 2025
**Status**: ✅ GPT-4o Working | Configuring Cost-Optimized Hybrid System

---

## 🎯 Optimization Strategy

### Goal: Balance Cost vs. Features

**Principle**: Use the cheapest provider that can reliably perform each task.

**Providers Available**:
1. **Gemini 2.0 Flash**: $0.000016/query (ultra-cheap, fast)
2. **GPT-4o**: ~$0.015/query (structured outputs, embeddings)
3. **Claude Sonnet 4.5**: ~$0.05/query (medical accuracy, reasoning)

---

## 📊 Current Task Allocation

### As-Is (Line 91-100 in `ai_provider_service.py`):

| Task | Current Provider | Cost/Query | Rationale |
|------|------------------|------------|-----------|
| `CHAPTER_GENERATION` | Claude | $0.05 | Medical accuracy |
| `SECTION_WRITING` | Claude | $0.05 | Medical accuracy |
| `IMAGE_ANALYSIS` | Claude | $0.05 | Vision capability |
| `FACT_CHECKING` | Claude | $0.05 | Medical accuracy critical |
| `METADATA_EXTRACTION` | GPT-4 | $0.015 | Structured output |
| `SUMMARIZATION` | Gemini | $0.000016 | Fast & cheap |
| `EMBEDDING` | GPT-4 | $0.000002 | text-embedding-3-large |

### Estimated Cost (200 chapters/month):

**Per Chapter Breakdown**:
- Stage 1-2 (Metadata): 2 x GPT-4o = $0.030
- Stage 3-9 (Generation): 30 x Claude = $1.50
- Stage 10 (Fact-check): 5 x Claude = $0.25
- Summaries: 10 x Gemini = $0.00016
- Embeddings: 5 x GPT-4o = $0.00001

**Per Chapter**: ~$1.78
**Per Month (200 chapters)**: ~$356
**Per Year**: ~$4,272

---

## 💡 BALANCED HYBRID PROPOSAL

### Optimized Task Allocation:

| Task | Optimized Provider | Cost/Query | Change | Rationale |
|------|-------------------|------------|---------|-----------|
| `CHAPTER_GENERATION` | **Gemini** | $0.000016 | ✓ Changed | 99.97% cheaper, good quality for drafts |
| `SECTION_WRITING` | **Gemini** | $0.000016 | ✓ Changed | Fast drafting, human review anyway |
| `IMAGE_ANALYSIS` | Claude | $0.05 | No change | Vision critical for medical images |
| `FACT_CHECKING` | GPT-4o | $0.015 | ✓ Changed | Structured output + medical accuracy |
| `METADATA_EXTRACTION` | GPT-4o | $0.015 | No change | Structured output essential |
| `SUMMARIZATION` | Gemini | $0.000016 | No change | Already optimal |
| `EMBEDDING` | GPT-4o | $0.000002 | No change | Best embeddings |

### New Estimated Cost (200 chapters/month):

**Per Chapter Breakdown**:
- Stage 1-2 (Metadata): 2 x GPT-4o = $0.030
- Stage 3-9 (Generation): 30 x **Gemini** = $0.00048
- Stage 10 (Fact-check): 5 x **GPT-4o** = $0.075
- Summaries: 10 x Gemini = $0.00016
- Embeddings: 5 x GPT-4o = $0.00001
- Image analysis (if used): 2 x Claude = $0.10

**Per Chapter**: ~$0.20
**Per Month (200 chapters)**: ~$40
**Per Year**: ~$480

**💰 SAVINGS: $3,792/year (89% reduction!)**

---

## 🔧 Implementation Plan

### Step 1: Update Provider Priority (Code Change)

**File**: `backend/services/ai_provider_service.py`
**Lines**: 91-100

**Change**:
```python
task_to_provider = {
    AITask.CHAPTER_GENERATION: AIProvider.GEMINI,  # Changed: Gemini for drafting
    AITask.SECTION_WRITING: AIProvider.GEMINI,     # Changed: Gemini for sections
    AITask.IMAGE_ANALYSIS: AIProvider.CLAUDE,      # Keep: Claude for vision
    AITask.FACT_CHECKING: AIProvider.GPT4,         # Changed: GPT-4o for structured fact-check
    AITask.METADATA_EXTRACTION: AIProvider.GPT4,   # Keep: GPT-4o for structured output
    AITask.SUMMARIZATION: AIProvider.GEMINI,       # Keep: Gemini already optimal
    AITask.EMBEDDING: AIProvider.GPT4,             # Keep: GPT-4o embeddings best
}
```

### Step 2: Enable GPT-4o for Fact-Checking

**File**: `backend/services/fact_checking_service.py`

**Current**: Uses Claude for fact-checking
**Change**: Use GPT-4o with structured output schema

**Benefits**:
- 70% cost reduction vs Claude
- Structured output (JSON schema validation)
- Still excellent medical accuracy

### Step 3: Set Up Cost Monitoring

**OpenAI Spending Limits**:
1. Go to: https://platform.openai.com/settings/organization/billing/limits
2. Set soft limit: $50/month
3. Set hard limit: $100/month
4. Enable email notifications

**Cost Tracking**:
- Monitor daily via: `backend/utils/ai_logging.py` (CostTracker)
- Weekly reports from analytics

### Step 4: A/B Testing Period (2 weeks)

**Week 1**: Run 50 chapters with new config
- Track quality metrics
- Monitor costs
- Collect user feedback

**Week 2**: Compare with baseline
- Quality comparison
- Cost verification
- Adjust if needed

---

## 📈 Quality Safeguards

### Human Review Points:
1. **After Gemini generation**: Review Stage 3-9 outputs
2. **After GPT-4o fact-check**: Verify medical accuracy
3. **Final review**: Before publication

### Automatic Quality Checks:
1. **Schema validation**: All structured outputs validated
2. **Confidence scores**: Fact-checking confidence tracked
3. **Fallback**: Automatic Claude fallback if Gemini fails

### Rollback Plan:
If quality suffers:
1. Revert critical stages back to Claude
2. Keep Gemini for non-critical tasks
3. Monitor incrementally

---

## 🎯 Conservative Alternative (If Worried About Quality)

### Hybrid Approach - Phase In Gradually:

**Phase 1** (Month 1): Test Gemini on non-critical tasks only
- Summarization: Gemini ✓ (already using)
- Draft generation: Gemini (testing)
- Keep Claude for: Final writing, fact-checking, critical sections

**Phase 2** (Month 2): Expand if Phase 1 succeeds
- All generation: Gemini
- Fact-checking: GPT-4o
- Keep Claude for: Complex medical scenarios

**Phase 3** (Month 3): Full optimization
- Implement full balanced config
- Claude only for edge cases

**Cost Trajectory**:
- Month 1: ~$300/month (30% reduction)
- Month 2: ~$100/month (77% reduction)
- Month 3: ~$40/month (91% reduction)

---

## 💰 Cost Comparison Summary

| Configuration | Cost/Chapter | Cost/Year (200ch/mo) | Quality | Recommendation |
|--------------|--------------|---------------------|---------|----------------|
| **Current** (mostly Claude) | $1.78 | $4,272 | Excellent | Too expensive |
| **Balanced Hybrid** (proposed) | $0.20 | $480 | Very Good | ✅ **Recommended** |
| **Conservative Hybrid** (gradual) | $0.50 | $1,200 | Excellent | Safe option |
| **All Gemini** (extreme savings) | $0.01 | $24 | Good | Too risky |

---

## 🚀 Immediate Actions

### Option A: Implement Full Balanced Config (Aggressive)

**What to do**:
1. Update `ai_provider_service.py` (5 minutes)
2. Update `fact_checking_service.py` (10 minutes)
3. Set OpenAI spending limits (5 minutes)
4. Test on 10 sample chapters (30 minutes)
5. Deploy if quality is acceptable

**Timeline**: 1 hour
**Risk**: Medium (might need quality adjustments)
**Savings**: 89% immediately

### Option B: Gradual Phase-In (Conservative)

**What to do**:
1. Start with Gemini for drafts only (5 minutes)
2. Keep everything else as-is
3. Monitor for 1 week
4. Expand if successful

**Timeline**: 3 weeks to full optimization
**Risk**: Low
**Savings**: 30% → 77% → 89% over 3 months

### Option C: Test First, Decide Later (Cautious)

**What to do**:
1. Create test branch
2. Run 50 chapters with new config
3. Compare quality vs. current
4. Decide based on data

**Timeline**: 1-2 weeks for testing
**Risk**: Very low
**Savings**: Delayed but data-driven

---

## 🎯 My Recommendation: Option B (Gradual Phase-In)

**Why**:
1. **Low risk**: Test incrementally
2. **Data-driven**: Make decisions based on real results
3. **Reversible**: Easy to rollback
4. **Cost-effective**: Still 30% savings immediately

**Implementation**:
1. **Today**: Update Gemini for `CHAPTER_GENERATION` only
2. **Week 1**: Monitor 50 chapters, collect feedback
3. **Week 2**: Add `SECTION_WRITING` if successful
4. **Week 3**: Add GPT-4o fact-checking
5. **Week 4**: Full optimization if all successful

---

## 📋 Next Steps (Awaiting Your Choice)

**Which option do you prefer?**

1. **Option A** (Aggressive): Implement full balanced config now
2. **Option B** (Conservative): Gradual phase-in over 3 weeks
3. **Option C** (Cautious): Test thoroughly first

**Or customize**: Tell me your priorities and I'll create a custom plan!

---

**Created**: October 29, 2025
**Status**: ✅ GPT-4o working | Ready to implement hybrid config
**Estimated Savings**: 89% cost reduction ($3,792/year)
**Quality Impact**: Minimal (with human review safeguards)
