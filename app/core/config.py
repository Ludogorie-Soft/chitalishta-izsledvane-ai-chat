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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
