import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

class Settings:
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    
    # Models config (defaulting to llama3.2:3b)
    ROUTER_MODEL: str = os.getenv("ROUTER_MODEL", "llama3.2:3b")
    INTAKE_MODEL: str = os.getenv("INTAKE_MODEL", "llama3.2:3b")
    GP_MODEL: str = os.getenv("GP_MODEL", "llama3.2:3b")
    RESPIRATORY_MODEL: str = os.getenv("RESPIRATORY_MODEL", "llama3.2:3b")
    VALIDATOR_MODEL: str = os.getenv("VALIDATOR_MODEL", "llama3.2:3b")
    COMPILER_MODEL: str = os.getenv("COMPILER_MODEL", "llama3.2:3b")
    
    # SQLite DB config
    APP_DATA_DIR: str = os.path.expanduser("~/.gemini/antigravity")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", os.path.join(APP_DATA_DIR, "symptom_triage.db"))
    CHECKPOINTS_PATH: str = os.getenv("CHECKPOINTS_PATH", os.path.join(APP_DATA_DIR, "symptom_triage_checkpoints.db"))

# Ensure directory exists
os.makedirs(Settings.APP_DATA_DIR, exist_ok=True)

settings = Settings()
