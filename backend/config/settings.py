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

    # Connection pool settings
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

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
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-ada-002"
    OPENAI_EMBEDDING_DIMENSIONS: int = 1536
    OPENAI_CHAT_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_MAX_TOKENS: int = 4096
    OPENAI_TEMPERATURE: float = 0.7

    # Anthropic Claude
    ANTHROPIC_API_KEY: str
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5-20250929"
    ANTHROPIC_MAX_TOKENS: int = 8192
    ANTHROPIC_TEMPERATURE: float = 0.7

    # Google Gemini
    GOOGLE_API_KEY: str
    GOOGLE_MODEL: str = "gemini-pro-2.5"
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
    PUBMED_EMAIL: Optional[str] = None
    PUBMED_API_KEY: Optional[str] = None
    PUBMED_MAX_RESULTS: int = 100

    # Google Scholar (via SerpAPI or similar)
    SCHOLAR_API_KEY: Optional[str] = None
    SCHOLAR_MAX_RESULTS: int = 50

    # arXiv
    ARXIV_API_URL: str = "http://export.arxiv.org/api/query"
    ARXIV_MAX_RESULTS: int = 50

    # ==================== Monitoring & Observability ====================
    ENABLE_METRICS: bool = True
    ENABLE_CACHE_ANALYTICS: bool = True
    METRICS_EXPORT_INTERVAL: int = 60  # seconds

    # Cost tracking
    OPENAI_EMBEDDING_COST_PER_1K: float = 0.0001
    OPENAI_GPT4_INPUT_COST_PER_1K: float = 0.01
    OPENAI_GPT4_OUTPUT_COST_PER_1K: float = 0.03
    ANTHROPIC_SONNET_INPUT_COST_PER_1K: float = 0.003
    ANTHROPIC_SONNET_OUTPUT_COST_PER_1K: float = 0.015
    GOOGLE_GEMINI_INPUT_COST_PER_1K: float = 0.00025
    GOOGLE_GEMINI_OUTPUT_COST_PER_1K: float = 0.0005

    # ==================== CORS ====================
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
