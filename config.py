"""
Configuration Module for Incident Response Agent.

Loads environment variables, manages API credentials, and intelligently
detects whether to run against live Hindsight Cloud / Groq APIs or
in self-contained offline Fallback/Mock mode.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import certifi

# Ensure SSL certificates are properly loaded on macOS
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())


# Find and load the .env file in the project root
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Check Streamlit secrets if running in Streamlit Cloud
try:
    import streamlit as st
    if hasattr(st, "secrets"):
        for key in ["HINDSIGHT_API_KEY", "HINDSIGHT_BASE_URL", "HINDSIGHT_BANK_ID", "GROQ_API_KEY", "GROQ_MODEL", "FORCE_MOCK_MODE"]:
            if key in st.secrets and not os.getenv(key):
                os.environ[key] = str(st.secrets[key])
except Exception:
    pass

# ==============================================================================
# Hindsight Memory Configuration
# ==============================================================================
HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY", "").strip()
HINDSIGHT_BASE_URL = os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io").rstrip("/")
HINDSIGHT_BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "incident-response-bank").strip()

# ==============================================================================
# Groq LLM Configuration
# ==============================================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()

# ==============================================================================
# Fallback / Mock Mode Handling
# ==============================================================================
# If FORCE_MOCK_MODE is enabled OR if the respective API key is missing,
# we gracefully switch to offline Mock mode. This prevents crashes during live demos.
FORCE_MOCK = os.getenv("FORCE_MOCK_MODE", "false").lower() in ("true", "1", "yes")

IS_MOCK_HINDSIGHT = FORCE_MOCK or not bool(HINDSIGHT_API_KEY)
IS_MOCK_GROQ = FORCE_MOCK or not bool(GROQ_API_KEY)


def get_status() -> dict:
    """Returns a summary of the current operational configuration."""
    return {
        "hindsight_mode": "Mock/Simulated" if IS_MOCK_HINDSIGHT else "Live Hindsight Cloud",
        "hindsight_bank": HINDSIGHT_BANK_ID,
        "hindsight_base_url": HINDSIGHT_BASE_URL,
        "groq_mode": "Mock/Simulated" if IS_MOCK_GROQ else f"Live Groq ({GROQ_MODEL})",
    }


if __name__ == "__main__":
    status = get_status()
    print("========================================")
    print(" Incident Response Agent Configuration  ")
    print("========================================")
    for k, v in status.items():
        print(f" • {k}: {v}")
    print("========================================")
