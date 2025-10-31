"""
Application settings and configuration management
Uses pydantic-settings for environment variable validation
"""

from pydantic_settings import BaseSettings
from typing import Optional
import secrets


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # ==================== Application ====================
    APP_NAME: str = "Neurosurgery Knowledge Base"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ==================== Database ====================
    DB_HOST: str = "postgres"
    DB_PORT: int = 5432
    DB_NAME: str = "neurosurgery_kb"
    DB_USER: str = "nsurg_admin"
    DB_PASSWORD: str

    # Connection pool settings (optimized for parallel operations)
    DB_POOL_SIZE: int = 30  # Increased from 20 for better parallel support
    DB_MAX_OVERFLOW: int = 50  # Increased from 40 for peak load handling
    DB_POOL_TIMEOUT: int = 10  # Decreased from 30 (fail fast, not accumulate delays)
    DB_POOL_RECYCLE: int = 1800  # Decreased from 3600 (30min, prevent stale connections)

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def async_database_url(self) -> str:
        """Construct async PostgreSQL connection URL"""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # ==================== Redis Cache ====================
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_MAX_CONNECTIONS: int = 50

    # Cache TTL settings (in seconds)
    CACHE_HOT_TTL: int = 3600  # 1 hour for hot cache (in-memory)
    CACHE_COLD_TTL: int = 86400  # 24 hours for cold cache (Redis)
    CACHE_PATTERN_TTL: int = 604800  # 7 days for pattern recognition

    @property
    def redis_url(self) -> str:
        """Construct Redis connection URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ==================== Authentication ====================
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # Password requirements
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True

    # ==================== AI Providers ====================

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"  # 3072 dims, better quality
    OPENAI_EMBEDDING_DIMENSIONS: int = 3072  # text-embedding-3-large dimensions
    OPENAI_CHAT_MODEL: str = "gpt-4o"  # Latest GPT-4o, 75% cheaper than turbo
    OPENAI_MAX_TOKENS: int = 4096
    OPENAI_TEMPERATURE: float = 0.7

    # Anthropic Claude
    ANTHROPIC_API_KEY: str
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5-20250929"
    ANTHROPIC_MAX_TOKENS: int = 8192
    ANTHROPIC_TEMPERATURE: float = 0.7

    # Google Gemini
    GOOGLE_API_KEY: str
    GOOGLE_MODEL: str = "gemini-2.0-flash-exp"  # Gemini 2.0 Flash (experimental, latest)
    GOOGLE_MAX_TOKENS: int = 8192
    GOOGLE_TEMPERATURE: float = 0.7

    # AI Provider Hierarchy for different tasks
    # Medical/Synthesis: Claude Sonnet 4.5 → GPT-4/5 → Claude Opus
    PRIMARY_SYNTHESIS_PROVIDER: str = "anthropic"
    SECONDARY_SYNTHESIS_PROVIDER: str = "openai"
    FALLBACK_SYNTHESIS_PROVIDER: str = "anthropic"

    # External Research: Gemini Pro 2.5 → Perplexity → OpenAI
    PRIMARY_RESEARCH_PROVIDER: str = "google"
    SECONDARY_RESEARCH_PROVIDER: str = "openai"

    # ==================== File Storage ====================
    PDF_STORAGE_PATH: str = "/data/pdfs"
    IMAGE_STORAGE_PATH: str = "/data/images"
    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_PDF_EXTENSIONS: list = [".pdf"]
    ALLOWED_IMAGE_EXTENSIONS: list = [".png", ".jpg", ".jpeg", ".gif", ".webp"]

    # ==================== PDF Processing ====================
    PDF_MAX_PAGES: int = 1000
    PDF_EXTRACT_IMAGES: bool = True
    PDF_EXTRACT_TABLES: bool = True
    PDF_OCR_ENABLED: bool = True

    # ==================== Vector Search ====================
    VECTOR_DIMENSIONS: int = 1536  # OpenAI ada-002
    VECTOR_SEARCH_LIMIT: int = 50
    VECTOR_SIMILARITY_THRESHOLD: float = 0.7

    # ==================== Chapter Generation ====================

    # Chapter types and section counts
    SURGICAL_DISEASE_SECTIONS: int = 97
    PURE_ANATOMY_SECTIONS: int = 48
    SURGICAL_TECHNIQUE_SECTIONS: int = 65

    # Quality thresholds
    MIN_DEPTH_SCORE: float = 0.7
    MIN_COVERAGE_SCORE: float = 0.75
    MIN_CURRENCY_SCORE: float = 0.6
    MIN_EVIDENCE_SCORE: float = 0.8

    # Gap detection thresholds
    GAP_SEVERITY_HIGH: float = 0.8
    GAP_SEVERITY_MEDIUM: float = 0.5
    GAP_SEVERITY_LOW: float = 0.3

    # ==================== WebSocket ====================
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30  # seconds
    WEBSOCKET_MESSAGE_QUEUE_SIZE: int = 100

    # ==================== Rate Limiting ====================
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds

    # ==================== External APIs ====================

    # PubMed
    PUBMED_API_URL: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    PUBMED_BASE_URL: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    PUBMED_EFETCH_URL: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    PUBMED_EMAIL: Optional[str] = None
    PUBMED_API_KEY: Optional[str] = None
    PUBMED_MAX_RESULTS: int = 100

    # Google Scholar (via SerpAPI or similar)
    SCHOLAR_API_KEY: Optional[str] = None
    SCHOLAR_MAX_RESULTS: int = 50

    # arXiv
    ARXIV_API_URL: str = "http://export.arxiv.org/api/query"
    ARXIV_MAX_RESULTS: int = 50

    # ==================== File Storage ====================
    # Container path that matches Docker volume mounts (pdf_storage:/data/pdfs, image_storage:/data/images)
    STORAGE_BASE_PATH: str = "/data"
    MAX_PDF_SIZE_MB: int = 100
    MAX_IMAGE_SIZE_MB: int = 50
    THUMBNAIL_SIZE: tuple = (300, 300)
    ALLOWED_PDF_EXTENSIONS: list = [".pdf"]
    ALLOWED_IMAGE_EXTENSIONS: list = [".png", ".jpg", ".jpeg", ".gif", ".bmp"]

    # ==================== Monitoring & Observability ====================
    ENABLE_METRICS: bool = True
    ENABLE_CACHE_ANALYTICS: bool = True
    METRICS_EXPORT_INTERVAL: int = 60  # seconds

    # Cost tracking
    # OpenAI Embeddings
    OPENAI_EMBEDDING_ADA_002_COST_PER_1K: float = 0.0001  # $0.10 per 1M (legacy)
    OPENAI_EMBEDDING_3_SMALL_COST_PER_1K: float = 0.00002  # $0.02 per 1M
    OPENAI_EMBEDDING_3_LARGE_COST_PER_1K: float = 0.00013  # $0.13 per 1M (current)
    OPENAI_EMBEDDING_COST_PER_1K: float = 0.00013  # Default to 3-large

    # OpenAI GPT-4o (latest, recommended)
    OPENAI_GPT4O_INPUT_COST_PER_1K: float = 0.0025   # $2.50 per 1M tokens
    OPENAI_GPT4O_OUTPUT_COST_PER_1K: float = 0.010   # $10 per 1M tokens

    # OpenAI GPT-4 Turbo (legacy, for reference)
    OPENAI_GPT4_TURBO_INPUT_COST_PER_1K: float = 0.01   # $10 per 1M
    OPENAI_GPT4_TURBO_OUTPUT_COST_PER_1K: float = 0.03  # $30 per 1M

    # Default to GPT-4o pricing (current model)
    OPENAI_GPT4_INPUT_COST_PER_1K: float = 0.0025   # Uses GPT-4o pricing
    OPENAI_GPT4_OUTPUT_COST_PER_1K: float = 0.010    # Uses GPT-4o pricing

    ANTHROPIC_SONNET_INPUT_COST_PER_1K: float = 0.003
    ANTHROPIC_SONNET_OUTPUT_COST_PER_1K: float = 0.015
    # Gemini 2.0 Flash pricing ($0.075 per 1M input, $0.30 per 1M output)
    GOOGLE_GEMINI_INPUT_COST_PER_1K: float = 0.000075  # $0.075 per 1M tokens
    GOOGLE_GEMINI_OUTPUT_COST_PER_1K: float = 0.0003   # $0.30 per 1M tokens

    # ==================== Server Ports ====================
    API_PORT: int = 8002
    FRONTEND_PORT: int = 3002
    API_URL: str = "http://localhost:8002"
    FRONTEND_URL: str = "http://localhost:3002"

    # ==================== CORS ====================
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:8001",
        "http://localhost:8002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:8001",
        "http://127.0.0.1:8002"
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]

    # ==================== Phase 2: Research Enhancements ====================

    # Parallel Research (Feature 1)
    PARALLEL_RESEARCH_ENABLED: bool = True

    # PubMed Caching (Feature 2)
    PUBMED_CACHE_ENABLED: bool = True
    PUBMED_CACHE_TTL: int = 86400  # 24 hours

    # AI Relevance Filtering (Feature 3 - Week 3-4)
    AI_RELEVANCE_FILTERING_ENABLED: bool = True  # ✓ ENABLED for Phase 2
    AI_RELEVANCE_THRESHOLD: float = 0.75

    # Intelligent Deduplication (Feature 4 - Week 3-4)
    DEDUPLICATION_STRATEGY: str = "exact"  # 'exact', 'fuzzy', 'semantic' (change to 'fuzzy' in Week 3-4)
    SEMANTIC_SIMILARITY_THRESHOLD: float = 0.85

    # Gap Analysis (Feature 5 - Week 5) ✅
    GAP_ANALYSIS_ENABLED: bool = True  # Enable after deployment
    GAP_ANALYSIS_ON_GENERATION: bool = False  # Only on-demand by default (set True to run automatically)
    GAP_ANALYSIS_MIN_COMPLETENESS: float = 0.75  # Minimum completeness score to pass
    GAP_ANALYSIS_CRITICAL_GAP_THRESHOLD: int = 0  # Max critical gaps allowed before requiring revision

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def validate_gemini_config(self) -> bool:
        """
        Validate Gemini configuration at startup

        Returns:
            bool: True if valid, raises ValueError if invalid
        """
        # Check API key format
        if self.GOOGLE_API_KEY:
            if not self.GOOGLE_API_KEY.startswith("AIza"):
                raise ValueError(
                    f"Invalid Google API key format. Expected key to start with 'AIza', "
                    f"got: {self.GOOGLE_API_KEY[:10]}..."
                )

        # Check model name is valid
        valid_models = [
            "gemini-2.0-flash-exp",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-1.0-pro"
        ]
        if self.GOOGLE_MODEL not in valid_models:
            print(
                f"⚠️  WARNING: Gemini model '{self.GOOGLE_MODEL}' may not exist. "
                f"Valid models: {', '.join(valid_models)}"
            )

        # Verify pricing is configured
        if self.GOOGLE_GEMINI_INPUT_COST_PER_1K <= 0:
            raise ValueError("Invalid Gemini input cost (must be > 0)")
        if self.GOOGLE_GEMINI_OUTPUT_COST_PER_1K <= 0:
            raise ValueError("Invalid Gemini output cost (must be > 0)")

        # Check for common configuration mistakes
        if self.GOOGLE_MODEL == "gemini-pro-2.5":
            raise ValueError(
                "Invalid model 'gemini-pro-2.5' does not exist. "
                "Use 'gemini-2.0-flash-exp' or 'gemini-1.5-flash'"
            )

        return True


# Global settings instance
settings = Settings()

# Validate Gemini configuration at import time
if settings.GOOGLE_API_KEY:
    try:
        settings.validate_gemini_config()
        print("✓ Gemini configuration validated successfully")
    except ValueError as e:
        print(f"⚠️  Gemini configuration error: {str(e)}")
        print("   Fix the configuration in .env or settings.py")
