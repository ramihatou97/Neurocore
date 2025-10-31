# Gemini 2.0 Flash - Quick Reference Card

## ⚡ Quick Start

```bash
# Verify Gemini is working
python3 test_gemini_basic.py

# Expected output:
# ✓ Gemini configuration validated successfully
# Cost: $0.000015
# Reduction: 98.1%
```

## 🔑 Configuration

### API Key Location
```bash
# File: .env
GOOGLE_API_KEY=AIzaSyDB2jl7-Kd5OifBMgoT1rTaP3Ip87nXt9Y
```

### Model Settings
```python
# File: backend/config/settings.py
GOOGLE_MODEL = "gemini-2.0-flash-exp"  # Latest, fastest
# Alternative: "gemini-1.5-flash" (stable)
```

## 💻 Common Usage Patterns

### Auto-Routing (Recommended)
```python
# Gemini automatically used for summarization
result = await service.generate_text(
    prompt="Summarize this research paper...",
    task=AITask.SUMMARIZATION  # Auto-routes to Gemini
)
```

### Force Gemini
```python
result = await service.generate_text(
    prompt="Your prompt here",
    task=AITask.SUMMARIZATION,
    provider=AIProvider.GEMINI  # Force Gemini
)
```

### Image Analysis
```python
with open("brain_scan.png", "rb") as f:
    image_data = f.read()

result = await service._generate_google_vision(
    image_data=image_data,
    prompt="Analyze this medical image"
)
```

### Streaming
```python
async for chunk in service._generate_gemini_streaming(
    prompt="Generate long content...",
    max_tokens=1000
):
    print(chunk['chunk'], end='')
```

## 📊 Cost Savings

| Task | Claude | Gemini | Savings |
|------|--------|--------|---------|
| 100 tokens | $0.0016 | $0.00003 | **98.1%** |
| Image analysis | $0.0024 | $0.00011 | **95.3%** |
| 200 chapters/mo | $130 | $41.50 | **68%** |

## 🎯 When to Use Gemini

✅ **Use Gemini:**
- Summarization
- Research analysis
- Image analysis (non-critical)
- Draft generation
- Bulk processing

❌ **Use Claude:**
- Final medical content
- Critical diagnosis
- Complex clinical reasoning

## 🔧 Troubleshooting

### Issue: Tests failing
```bash
# Check API key
echo $GOOGLE_API_KEY

# Verify model name
grep GOOGLE_MODEL backend/config/settings.py
```

### Issue: Wrong model error
```bash
# Should be: gemini-2.0-flash-exp
# NOT: gemini-pro-2.5 (doesn't exist)
```

### Issue: Safety filters blocking
```python
# All categories set to BLOCK_NONE for medical content
# See: backend/services/ai_provider_service.py line 279
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `backend/config/settings.py` | Configuration |
| `backend/services/ai_provider_service.py` | Implementation |
| `docs/GEMINI_INTEGRATION.md` | Full documentation |
| `test_gemini_basic.py` | Quick test |
| `GEMINI_IMPLEMENTATION_COMPLETE.md` | Summary |

## 🧪 Testing

```bash
# Basic test (30 seconds)
python3 test_gemini_basic.py

# Vision test (30 seconds)
python3 test_gemini_vision.py

# Full suite (2 minutes)
pytest tests/unit/test_gemini_integration.py -v
```

## 📈 Monitoring

### Check Logs
```bash
# Look for lines like:
# Gemini generation: 16 input + 46 output tokens, $0.000015
```

### Cost Tracking
All Gemini calls automatically log:
- Input/output tokens
- Exact cost (USD)
- Model used
- Latency

## 🚨 Emergency Rollback

If issues occur:
```bash
# 1. Disable Gemini
echo 'GOOGLE_API_KEY=""' >> .env

# 2. System auto-falls back to Claude

# 3. Verify
python3 test_gemini_basic.py
```

## 💡 Pro Tips

1. **Batch Processing**: Process multiple items in one call
2. **Lower Temperature**: Use 0.3-0.5 for factual content
3. **Context Caching**: Reuse large contexts for 90% discount
4. **Streaming**: Better UX for long responses
5. **Monitor Quality**: Track metrics vs Claude

## 📞 Support

- **Docs**: `docs/GEMINI_INTEGRATION.md`
- **Tests**: `tests/unit/test_gemini_integration.py`
- **Logs**: Check `backend/logs/` directory

---

**Status**: ✅ Production Ready
**Version**: Gemini 2.0 Flash (Experimental)
**Last Updated**: October 29, 2025
