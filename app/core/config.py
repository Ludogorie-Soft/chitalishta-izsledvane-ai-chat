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
    openai_chat_model: str = "gpt-4o-mini"
    huggingface_llm_model: str = "HuggingFaceH4/zephyr-7b-beta"  # Good multilingual support, no authentication required
    # Alternative Hugging Face models:
    # - "mistralai/Mistral-7B-Instruct-v0.2" (larger, better quality, may require auth)
    # - "meta-llama/Llama-3.2-3B-Instruct" (good for Bulgarian, requires Hugging Face auth)
    # - "google/gemma-2b-it" (smaller, faster, no auth required)
    # - "microsoft/Phi-3-mini-4k-instruct" (small, fast, no auth required)

    # TGI (Text Generation Inference) configuration (for local Docker-based LLM)
    tgi_base_url: str = "http://localhost:8080/v1"  # OpenAI-compatible API endpoint
    tgi_model_name: str = "google/gemma-2b-it"  # Model name (must match docker-compose.yml)
    tgi_timeout: int = 30  # Request timeout in seconds
    tgi_enabled: bool = True  # Whether to use TGI when llm_provider="tgi"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
