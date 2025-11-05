# 🔧 Vertex AI Implementation Guide

**Practical Step-by-Step Guide for Integration**

---

## 📋 Prerequisites

### 1. Google Cloud Setup

```bash
# Install Google Cloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Initialize and authenticate
gcloud init
gcloud auth application-default login

# Create project (or use existing)
gcloud projects create neurosurgery-kb-prod --name="Neurosurgery KB Production"

# Set project
gcloud config set project neurosurgery-kb-prod

# Enable required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable discoveryengine.googleapis.com  # For grounding

# Create service account
gcloud iam service-accounts create neurosurgery-kb-sa \
    --display-name="Neurosurgery KB Service Account"

# Grant necessary permissions
gcloud projects add-iam-policy-binding neurosurgery-kb-prod \
    --member="serviceAccount:neurosurgery-kb-sa@neurosurgery-kb-prod.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding neurosurgery-kb-prod \
    --member="serviceAccount:neurosurgery-kb-sa@neurosurgery-kb-prod.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Download service account key
gcloud iam service-accounts keys create ./gcp-credentials.json \
    --iam-account=neurosurgery-kb-sa@neurosurgery-kb-prod.iam.gserviceaccount.com
```

### 2. Update Requirements

```bash
# Add to requirements.txt
echo "google-cloud-aiplatform>=1.60.0" >> requirements.txt
echo "google-cloud-storage>=2.10.0" >> requirements.txt

# Install
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
# Add to .env
cat >> .env << EOF

# ==================== Vertex AI Configuration ====================
# Enable Vertex AI (set to true for production)
VERTEX_AI_ENABLED=false

# GCP Project Configuration
VERTEX_AI_PROJECT=neurosurgery-kb-prod
VERTEX_AI_LOCATION=us-central1

# Service Account (set path to credentials JSON)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp-credentials.json

# Feature Flags
VERTEX_AI_USE_CONTEXT_CACHING=true
VERTEX_AI_USE_GROUNDING=false
VERTEX_AI_CACHE_TTL=3600  # 1 hour

# Model Configuration
VERTEX_AI_MODEL=gemini-2.0-flash-001
VERTEX_AI_TEMPERATURE=0.7
VERTEX_AI_MAX_OUTPUT_TOKENS=8192

# Cost Controls
VERTEX_AI_DAILY_BUDGET_USD=100
VERTEX_AI_ALERT_THRESHOLD_USD=80
EOF
```

---

## 🔨 Implementation

### Step 1: Update Settings

```python
# backend/config/settings.py

class Settings(BaseSettings):
    # ... existing settings ...
    
    # ==================== Vertex AI Configuration ====================
    VERTEX_AI_ENABLED: bool = False
    VERTEX_AI_PROJECT: Optional[str] = None
    VERTEX_AI_LOCATION: str = "us-central1"
    
    # Feature Flags
    VERTEX_AI_USE_CONTEXT_CACHING: bool = False
    VERTEX_AI_USE_GROUNDING: bool = False
    VERTEX_AI_CACHE_TTL: int = 3600
    
    # Model Configuration
    VERTEX_AI_MODEL: str = "gemini-2.0-flash-001"
    VERTEX_AI_TEMPERATURE: float = 0.7
    VERTEX_AI_MAX_OUTPUT_TOKENS: int = 8192
    
    # Cost Controls
    VERTEX_AI_DAILY_BUDGET_USD: float = 100.0
    VERTEX_AI_ALERT_THRESHOLD_USD: float = 80.0
    
    # Pricing (Gemini 2.0 Flash on Vertex AI)
    VERTEX_AI_INPUT_COST_PER_1K: float = 0.000075
    VERTEX_AI_OUTPUT_COST_PER_1K: float = 0.0003
    VERTEX_AI_CACHED_INPUT_COST_PER_1K: float = 0.0000075  # 90% discount
    VERTEX_AI_CACHE_STORAGE_PER_GB_HOUR: float = 0.00125
    
    @validator("VERTEX_AI_ENABLED")
    def validate_vertex_ai_config(cls, v, values):
        """Validate Vertex AI configuration"""
        if v:
            if not values.get("VERTEX_AI_PROJECT"):
                raise ValueError("VERTEX_AI_PROJECT required when VERTEX_AI_ENABLED=true")
            
            import os
            if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                raise ValueError("GOOGLE_APPLICATION_CREDENTIALS required when VERTEX_AI_ENABLED=true")
        
        return v
    
    class Config:
        env_file = ".env"
```

### Step 2: Create Vertex AI Service

```python
# backend/services/vertex_ai_service.py
"""
Vertex AI Service - Enterprise Google AI integration
Provides context caching, grounding, and advanced monitoring
"""

from google.cloud import aiplatform
from google.cloud.aiplatform_v1beta1 import CachedContent
from typing import Optional, Dict, Any, List
import hashlib
from datetime import datetime, timedelta

from backend.config import settings
from backend.utils import get_logger

logger = get_logger(__name__)


class VertexAIService:
    """
    Vertex AI integration with enterprise features
    
    Features:
    - Context caching (90% cost reduction)
    - Grounding with Vertex AI Search
    - Multi-region deployment
    - Full monitoring and logging
    """
    
    def __init__(self):
        """Initialize Vertex AI client"""
        if not settings.VERTEX_AI_ENABLED:
            logger.warning("Vertex AI not enabled, using fallback")
            return
        
        # Initialize Vertex AI
        aiplatform.init(
            project=settings.VERTEX_AI_PROJECT,
            location=settings.VERTEX_AI_LOCATION,
        )
        
        # Track cached contents
        self._cached_contents: Dict[str, CachedContent] = {}
        
        logger.info(
            f"Vertex AI initialized: project={settings.VERTEX_AI_PROJECT}, "
            f"location={settings.VERTEX_AI_LOCATION}"
        )
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = None,
        temperature: float = None,
        use_cache: bool = True,
        use_grounding: bool = False
    ) -> Dict[str, Any]:
        """
        Generate text with optional caching and grounding
        
        Args:
            prompt: User prompt
            system_prompt: System instructions (can be cached)
            max_tokens: Max output tokens
            temperature: Sampling temperature
            use_cache: Whether to use context caching
            use_grounding: Whether to ground in search results
        
        Returns:
            dict with text, tokens, cost, and metadata
        """
        max_tokens = max_tokens or settings.VERTEX_AI_MAX_OUTPUT_TOKENS
        temperature = temperature or settings.VERTEX_AI_TEMPERATURE
        
        # Build generation config
        generation_config = aiplatform.generative_models.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature
        )
        
        # Handle context caching
        cached_content = None
        if use_cache and system_prompt and settings.VERTEX_AI_USE_CONTEXT_CACHING:
            cached_content = await self._get_or_create_cache(system_prompt)
        
        # Handle grounding
        tools = None
        if use_grounding and settings.VERTEX_AI_USE_GROUNDING:
            tools = [self._get_grounding_tool()]
        
        # Create model
        if cached_content:
            model = aiplatform.generative_models.GenerativeModel.from_cached_content(
                cached_content=cached_content
            )
        else:
            model = aiplatform.generative_models.GenerativeModel(
                model_name=settings.VERTEX_AI_MODEL,
                system_instruction=system_prompt
            )
        
        # Generate
        start_time = datetime.now()
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            tools=tools
        )
        
        latency_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Extract text
        text = response.text if response.text else ""
        
        # Calculate costs
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count
        output_tokens = usage.candidates_token_count
        cached_tokens = usage.cached_content_token_count if cached_content else 0
        
        # Calculate cost with caching discount
        cost_input = (input_tokens - cached_tokens) * settings.VERTEX_AI_INPUT_COST_PER_1K / 1000
        cost_cached = cached_tokens * settings.VERTEX_AI_CACHED_INPUT_COST_PER_1K / 1000
        cost_output = output_tokens * settings.VERTEX_AI_OUTPUT_COST_PER_1K / 1000
        cost_total = cost_input + cost_cached + cost_output
        
        # Extract grounding metadata
        grounding_metadata = None
        if use_grounding and hasattr(response, 'grounding_metadata'):
            grounding_metadata = {
                "grounding_score": response.grounding_metadata.grounding_score,
                "citations": [
                    {
                        "source": citation.source,
                        "start_index": citation.start_index,
                        "end_index": citation.end_index
                    }
                    for citation in response.grounding_metadata.citations
                ]
            }
        
        logger.info(
            f"Vertex AI generation: {input_tokens} input ({cached_tokens} cached) + "
            f"{output_tokens} output tokens, ${cost_total:.4f}, {latency_ms:.0f}ms"
        )
        
        return {
            "text": text,
            "provider": "vertex_ai",
            "model": settings.VERTEX_AI_MODEL,
            "tokens_used": input_tokens + output_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
            "cost_usd": cost_total,
            "cost_breakdown": {
                "input": cost_input,
                "cached": cost_cached,
                "output": cost_output
            },
            "latency_ms": latency_ms,
            "grounding_metadata": grounding_metadata,
            "cache_hit": cached_tokens > 0
        }
    
    async def _get_or_create_cache(self, system_prompt: str) -> CachedContent:
        """
        Get or create cached content for system prompt
        
        Args:
            system_prompt: System instruction to cache
        
        Returns:
            CachedContent object
        """
        # Generate cache key
        cache_key = hashlib.md5(system_prompt.encode()).hexdigest()
        
        # Check if already cached
        if cache_key in self._cached_contents:
            cached = self._cached_contents[cache_key]
            
            # Check if expired
            if cached.expire_time > datetime.now():
                logger.debug(f"Using existing cache: {cache_key}")
                return cached
            else:
                logger.debug(f"Cache expired: {cache_key}")
                del self._cached_contents[cache_key]
        
        # Create new cache
        logger.info(f"Creating new context cache: {cache_key}")
        
        cached_content = aiplatform.caching.CachedContent.create(
            model_name=settings.VERTEX_AI_MODEL,
            system_instruction=system_prompt,
            ttl=timedelta(seconds=settings.VERTEX_AI_CACHE_TTL)
        )
        
        self._cached_contents[cache_key] = cached_content
        
        return cached_content
    
    def _get_grounding_tool(self):
        """Get grounding tool configuration"""
        from google.cloud.aiplatform_v1beta1.types import Tool, GoogleSearchRetrieval
        
        return Tool(
            google_search_retrieval=GoogleSearchRetrieval()
        )
    
    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str = "Analyze this medical image in detail.",
        use_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze medical image with Gemini Vision
        
        Args:
            image_bytes: Image data
            prompt: Analysis prompt
            use_cache: Whether to cache system prompt
        
        Returns:
            dict with analysis, tokens, and cost
        """
        import base64
        
        # Encode image
        image_b64 = base64.b64encode(image_bytes).decode()
        
        # Create model
        model = aiplatform.generative_models.GenerativeModel(
            settings.VERTEX_AI_MODEL
        )
        
        # Create multimodal prompt
        image_part = aiplatform.generative_models.Part.from_data(
            data=image_bytes,
            mime_type="image/jpeg"
        )
        
        # Generate
        start_time = datetime.now()
        
        response = model.generate_content(
            [prompt, image_part],
            generation_config=aiplatform.generative_models.GenerationConfig(
                max_output_tokens=settings.VERTEX_AI_MAX_OUTPUT_TOKENS,
                temperature=0.4  # Lower temp for factual medical analysis
            )
        )
        
        latency_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Calculate cost
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count
        output_tokens = usage.candidates_token_count
        
        cost_usd = (
            (input_tokens * settings.VERTEX_AI_INPUT_COST_PER_1K / 1000) +
            (output_tokens * settings.VERTEX_AI_OUTPUT_COST_PER_1K / 1000)
        )
        
        logger.info(
            f"Vertex AI vision: {input_tokens} input + {output_tokens} output tokens, "
            f"${cost_usd:.4f}, {latency_ms:.0f}ms"
        )
        
        return {
            "text": response.text,
            "provider": "vertex_ai_vision",
            "model": settings.VERTEX_AI_MODEL,
            "tokens_used": input_tokens + output_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        active_caches = len(self._cached_contents)
        
        return {
            "active_caches": active_caches,
            "cache_keys": list(self._cached_contents.keys())
        }
```

### Step 3: Update AI Provider Service

```python
# backend/services/ai_provider_service.py

class AIProviderService:
    def __init__(self):
        # ... existing initialization ...
        
        # Add Vertex AI
        if settings.VERTEX_AI_ENABLED:
            from backend.services.vertex_ai_service import VertexAIService
            self.vertex_ai_service = VertexAIService()
            logger.info("Vertex AI service initialized")
        else:
            self.vertex_ai_service = None
    
    def get_preferred_provider(self, task: AITask) -> AIProvider:
        """Get preferred provider with Vertex AI support"""
        # If Vertex AI enabled, prefer it for Gemini tasks
        if settings.VERTEX_AI_ENABLED and task in [
            AITask.CHAPTER_GENERATION,
            AITask.SUMMARIZATION,
            AITask.IMAGE_ANALYSIS
        ]:
            return AIProvider.VERTEX_AI  # New enum value
        
        # ... existing logic ...
    
    async def generate_text(
        self,
        prompt: str,
        task: AITask,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        provider: Optional[AIProvider] = None
    ) -> Dict[str, Any]:
        """Generate text with Vertex AI support"""
        if provider is None:
            provider = self.get_preferred_provider(task)
        
        try:
            if provider == AIProvider.VERTEX_AI:
                return await self.vertex_ai_service.generate_text(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    use_cache=True,  # Enable caching
                    use_grounding=False  # Can be enabled per task
                )
            elif provider == AIProvider.CLAUDE:
                return await self._generate_claude(...)
            # ... existing providers ...
        
        except Exception as e:
            logger.error(f"Generation failed with {provider}: {e}")
            # Fallback logic...
```

### Step 4: Add Enum Value

```python
# backend/services/ai_provider_service.py

class AIProvider(str, Enum):
    """Available AI providers"""
    CLAUDE = "claude"
    GPT4 = "gpt4"
    GEMINI = "gemini"
    VERTEX_AI = "vertex_ai"  # New
```

---

## 🧪 Testing

### Test 1: Basic Generation

```python
# test_vertex_ai_basic.py
"""Test basic Vertex AI text generation"""

import asyncio
import os
from backend.services.vertex_ai_service import VertexAIService
from backend.config import settings

async def test_basic_generation():
    """Test basic text generation"""
    
    # Enable Vertex AI temporarily
    settings.VERTEX_AI_ENABLED = True
    settings.VERTEX_AI_USE_CONTEXT_CACHING = False
    
    service = VertexAIService()
    
    result = await service.generate_text(
        prompt="Explain traumatic brain injury in 100 words.",
        system_prompt="You are a neurosurgery expert.",
        max_tokens=200
    )
    
    print("\n✅ Basic Generation Test")
    print(f"Provider: {result['provider']}")
    print(f"Model: {result['model']}")
    print(f"Tokens: {result['input_tokens']} input + {result['output_tokens']} output")
    print(f"Cost: ${result['cost_usd']:.6f}")
    print(f"Latency: {result['latency_ms']:.0f}ms")
    print(f"\nResponse:\n{result['text'][:200]}...")
    
    assert result['provider'] == 'vertex_ai'
    assert result['text']
    assert result['cost_usd'] > 0

if __name__ == "__main__":
    asyncio.run(test_basic_generation())
```

### Test 2: Context Caching

```python
# test_vertex_ai_caching.py
"""Test Vertex AI context caching"""

import asyncio
from backend.services.vertex_ai_service import VertexAIService
from backend.config import settings

async def test_context_caching():
    """Test that context caching reduces costs"""
    
    settings.VERTEX_AI_ENABLED = True
    settings.VERTEX_AI_USE_CONTEXT_CACHING = True
    
    service = VertexAIService()
    
    # Large system prompt (would be medical guidelines in production)
    system_prompt = """
    You are a neurosurgery expert. Follow these detailed guidelines:
    
    1. Always cite recent peer-reviewed literature
    2. Use evidence-based medicine principles
    3. Consider patient safety first
    4. Follow standard surgical protocols
    5. Discuss complications and contraindications
    
    [Imagine 5000+ more tokens of guidelines here...]
    """ * 50  # Simulate large prompt
    
    # First request: No cache
    result1 = await service.generate_text(
        prompt="Explain craniotomy procedure.",
        system_prompt=system_prompt,
        max_tokens=100
    )
    
    print("\n✅ First Request (No Cache)")
    print(f"Input tokens: {result1['input_tokens']}")
    print(f"Cached tokens: {result1['cached_tokens']}")
    print(f"Cost: ${result1['cost_usd']:.6f}")
    
    # Second request: Should hit cache
    result2 = await service.generate_text(
        prompt="Explain ventriculostomy procedure.",
        system_prompt=system_prompt,  # Same system prompt
        max_tokens=100
    )
    
    print("\n✅ Second Request (With Cache)")
    print(f"Input tokens: {result2['input_tokens']}")
    print(f"Cached tokens: {result2['cached_tokens']}")
    print(f"Cost: ${result2['cost_usd']:.6f}")
    
    # Calculate savings
    savings = result1['cost_usd'] - result2['cost_usd']
    savings_pct = (savings / result1['cost_usd']) * 100
    
    print(f"\n💰 Savings: ${savings:.6f} ({savings_pct:.1f}%)")
    
    assert result2['cache_hit'] == True
    assert result2['cached_tokens'] > 0
    assert result2['cost_usd'] < result1['cost_usd']

if __name__ == "__main__":
    asyncio.run(test_context_caching())
```

### Test 3: Image Analysis

```python
# test_vertex_ai_vision.py
"""Test Vertex AI vision analysis"""

import asyncio
from backend.services.vertex_ai_service import VertexAIService
from backend.config import settings

async def test_vision_analysis():
    """Test medical image analysis"""
    
    settings.VERTEX_AI_ENABLED = True
    
    service = VertexAIService()
    
    # Load test image
    with open("tests/fixtures/brain_mri.jpg", "rb") as f:
        image_bytes = f.read()
    
    result = await service.analyze_image(
        image_bytes=image_bytes,
        prompt="""
        Analyze this brain MRI image:
        1. Identify anatomical structures
        2. Note any abnormalities
        3. Suggest imaging modality
        """
    )
    
    print("\n✅ Vision Analysis Test")
    print(f"Provider: {result['provider']}")
    print(f"Tokens: {result['input_tokens']} input + {result['output_tokens']} output")
    print(f"Cost: ${result['cost_usd']:.6f}")
    print(f"\nAnalysis:\n{result['text']}")
    
    assert result['provider'] == 'vertex_ai_vision'
    assert 'brain' in result['text'].lower() or 'mri' in result['text'].lower()

if __name__ == "__main__":
    asyncio.run(test_vision_analysis())
```

---

## 🚀 Deployment

### Docker Compose Update

```yaml
# docker-compose.yml (add to existing)
services:
  neurocore-api:
    environment:
      # Vertex AI Configuration
      VERTEX_AI_ENABLED: ${VERTEX_AI_ENABLED:-false}
      VERTEX_AI_PROJECT: ${VERTEX_AI_PROJECT:-}
      VERTEX_AI_LOCATION: ${VERTEX_AI_LOCATION:-us-central1}
      VERTEX_AI_USE_CONTEXT_CACHING: ${VERTEX_AI_USE_CONTEXT_CACHING:-true}
      VERTEX_AI_USE_GROUNDING: ${VERTEX_AI_USE_GROUNDING:-false}
      GOOGLE_APPLICATION_CREDENTIALS: ${GOOGLE_APPLICATION_CREDENTIALS:-}
    
    volumes:
      # Mount GCP credentials if using Vertex AI
      - ${GCP_CREDENTIALS_PATH:-./gcp-credentials.json}:/app/gcp-credentials.json:ro
```

### Production .env

```bash
# .env.production
VERTEX_AI_ENABLED=true
VERTEX_AI_PROJECT=neurosurgery-kb-prod
VERTEX_AI_LOCATION=us-central1
VERTEX_AI_USE_CONTEXT_CACHING=true
VERTEX_AI_USE_GROUNDING=true
GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-credentials.json
GCP_CREDENTIALS_PATH=./secrets/gcp-credentials.json

# Keep AI Studio as fallback
GOOGLE_API_KEY=your-api-key-here
```

---

## 📊 Monitoring

### Add Monitoring Endpoint

```python
# backend/api/monitoring_routes.py
from fastapi import APIRouter, Depends
from backend.services.vertex_ai_service import VertexAIService
from backend.utils.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])

@router.get("/vertex-ai/cache-stats")
async def get_cache_stats(
    current_user = Depends(get_current_user)
):
    """Get Vertex AI cache statistics"""
    service = VertexAIService()
    return service.get_cache_stats()

@router.get("/vertex-ai/cost-summary")
async def get_cost_summary(
    current_user = Depends(get_current_user)
):
    """Get cost summary from Cloud Monitoring"""
    # Query Cloud Monitoring API
    # Return daily/weekly/monthly costs
    pass
```

---

## ✅ Checklist

### Pre-Deployment
- [ ] GCP project created
- [ ] APIs enabled (Vertex AI, Storage, Discovery Engine)
- [ ] Service account created with proper permissions
- [ ] Credentials downloaded and secured
- [ ] Environment variables configured
- [ ] Dependencies installed
- [ ] Tests passing

### Implementation
- [ ] Settings updated
- [ ] VertexAIService created
- [ ] AIProviderService updated
- [ ] Tests written and passing
- [ ] Documentation complete

### Deployment
- [ ] Staging environment tested
- [ ] Cost monitoring enabled
- [ ] Alerts configured
- [ ] Gradual rollout plan ready
- [ ] Rollback plan documented

### Post-Deployment
- [ ] Monitor costs daily
- [ ] Track cache hit rates
- [ ] Measure latency improvements
- [ ] Validate grounding quality
- [ ] Collect user feedback

---

## 🆘 Troubleshooting

### Issue: "Permission denied"
```bash
# Solution: Grant service account proper roles
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:SA_EMAIL" \
    --role="roles/aiplatform.user"
```

### Issue: "Quota exceeded"
```bash
# Solution: Request quota increase
gcloud alpha services quota list --service=aiplatform.googleapis.com
# Then request increase via Cloud Console
```

### Issue: "Cache not working"
```python
# Check cache TTL and size
# Minimum cacheable content: 32,768 tokens
# Ensure system prompt is large enough
```

### Issue: "High costs"
```bash
# Enable cost monitoring
gcloud beta billing budgets create \
    --billing-account=BILLING_ACCOUNT_ID \
    --display-name="Vertex AI Daily Budget" \
    --budget-amount=100USD \
    --threshold-rule=percent=80
```

---

## 📚 Next Steps

1. **Test in Development**
   ```bash
   pytest tests/unit/test_vertex_ai*.py -v
   ```

2. **Deploy to Staging**
   ```bash
   VERTEX_AI_ENABLED=true docker-compose up -d
   ```

3. **Monitor Costs**
   ```bash
   gcloud billing accounts list
   gcloud billing accounts get-iam-policy BILLING_ACCOUNT_ID
   ```

4. **Gradual Rollout**
   - Start with 10% of traffic
   - Monitor for 1 week
   - Increase to 50%
   - Monitor for 1 week
   - Full rollout

---

**Document Version**: 1.0
**Last Updated**: November 2, 2025
