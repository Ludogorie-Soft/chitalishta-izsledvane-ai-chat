from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str

    # Chroma vector store
    chroma_persist_directory: str = "chroma_db"
    chroma_collection_name: str = "chitalishta_documents"

    # Embedding configuration
    embedding_provider: str = "openai"  # Options: "openai" or "huggingface"
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    huggingface_model_name: str = "intfloat/multilingual-e5-base"  # Good for Bulgarian

    # LLM configuration (for LangChain-based components)
    llm_provider: str = "openai"  # Options: "openai", "huggingface", or "tgi"
    # Task-specific providers (optional, defaults to llm_provider)
    llm_provider_classification: str = ""  # Provider for classification tasks (empty = use llm_provider)
    llm_provider_generation: str = ""  # Provider for generation tasks (empty = use llm_provider)
    llm_provider_synthesis: str = ""  # Provider for synthesis tasks (empty = use llm_provider)
    openai_chat_model: str = "gpt-4o-mini"
    huggingface_llm_model: str = "HuggingFaceH4/zephyr-7b-beta"  # Good multilingual support, no authentication required

    # Fallback LLM configuration (for retry with more powerful model when initial answer is "no information")
    llm_provider_fallback: str = ""  # Provider for fallback/retry (empty = use llm_provider)
    openai_chat_model_fallback: str = "gpt-4o"  # More powerful model for fallback (e.g., gpt-4o, gpt-4-turbo)
    huggingface_llm_model_fallback: str = ""  # Fallback Hugging Face model (empty = use huggingface_llm_model)
    rag_enable_fallback: bool = True  # Enable fallback retry for RAG queries when answer is "no information"
    # Alternative Hugging Face models:
    # - "mistralai/Mistral-7B-Instruct-v0.2" (larger, better quality, may require auth)
    # - "meta-llama/Llama-3.2-3B-Instruct" (good for Bulgarian, requires Hugging Face auth)
    # - "google/gemma-2b-it" (smaller, faster, requires Hugging Face auth - gated model)
    # - "microsoft/Phi-3-mini-4k-instruct" (small, fast, no auth required)

    # TGI (Text Generation Inference) configuration (for local Docker-based LLM)
    tgi_base_url: str = "http://localhost:8080/v1"  # OpenAI-compatible API endpoint
    tgi_model_name: str = "google/gemma-2b-it"  # Model name (must match docker-compose.yml)
    tgi_timeout: int = 30  # Request timeout in seconds
    tgi_enabled: bool = True  # Whether to use TGI when llm_provider="tgi"

    # Logging configuration
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_format: str = "json"  # "json" or "console" (human-readable)
    log_file: str = ""  # Optional: path to log file (empty = stdout only)
    log_file_max_bytes: int = 10485760  # 10MB per log file
    log_file_backup_count: int = 5  # Number of backup log files to keep

    # Rate limiting configuration
    rate_limit_enabled: bool = True  # Enable/disable rate limiting
    rate_limit_per_minute: int = 5  # Requests per minute for chat endpoints
    rate_limit_per_hour: int = 40  # Requests per hour for chat endpoints
    rate_limit_per_day: int = 200  # Requests per day for chat endpoints
    rate_limit_cleanup_interval_hours: int = 24  # Cleanup old rate limit records every N hours
    rate_limit_violation_retention_days: int = 30  # Keep violation logs for N days

    # Abuse protection configuration
    abuse_protection_enabled: bool = True  # Enable/disable abuse protection
    # Note: SQL injection detection is NOT implemented in rate limiter because:
    # - User queries are natural language (Bulgarian), not SQL
    # - The SQL agent (sql_agent.py) provides comprehensive SQL security validation
    # - Pattern matching on natural language causes false positives
    abuse_max_query_length: int = 10000  # Maximum query length in characters
    abuse_min_request_interval_seconds: float = 0.5  # Minimum time between requests (DoS protection)
    abuse_ip_block_duration_hours: int = 1  # Duration of IP block in hours
    abuse_max_rapid_requests: int = 10  # Max requests in short time window for DoS detection
    abuse_rapid_requests_window_seconds: int = 5  # Time window for rapid request detection

    # Swagger UI authentication configuration
    swagger_ui_username: str = ""  # Username for Swagger UI Basic Auth (empty = disabled)
    swagger_ui_password: str = ""  # Password for Swagger UI Basic Auth (empty = disabled)

    # JWT authentication configuration
    jwt_secret_key: str = ""  # JWT secret key (for HS256) - not used with RS256
    jwt_algorithm: str = "RS256"  # JWT algorithm (RS256 for asymmetric)
    jwt_access_token_expire_minutes: int = 30  # Access token expiration in minutes
    jwt_refresh_token_expire_days: int = 7  # Refresh token expiration in days
    # RSA key pair for RS256 (PEM format)
    # If not provided, keys will be auto-generated (not recommended for production)
    jwt_rsa_private_key: str = ""  # RSA private key in PEM format
    jwt_rsa_public_key: str = ""  # RSA public key in PEM format

    # API key authentication configuration
    api_key: str = ""  # API key for Public API and System API endpoints (empty = disabled)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
