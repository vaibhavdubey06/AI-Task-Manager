"""Application configuration and environment management."""
import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file with override=True
load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent

@dataclass
class Settings:
    # OpenAI-compatible LLM configuration (works with OpenAI, Groq, Ollama, etc.)
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_api_key: str = os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY") or ""
    openai_model: str = os.getenv("OPENAI_MODEL", "llama-3.3-70b-versatile")

    # Data paths
    database_path: Path = BASE_DIR / os.getenv("DATABASE_PATH", "data/company.db")
    invoices_dir: Path = BASE_DIR / os.getenv("INVOICES_DIR", "data/invoices")

    # Autonomous execution parameters
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    auto_approve: bool = os.getenv("AUTO_APPROVE", "false").lower() in ("true", "1", "yes")

    def is_llm_configured(self) -> bool:
        """Check if an actual OpenAI/compatible API key is configured."""
        return bool(self.openai_api_key and self.openai_api_key.strip() != "your-api-key-here")

# Global singleton settings
settings = Settings()
