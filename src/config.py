import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

PROVIDER = os.getenv("AGENT_LOOP_PROVIDER", "").strip().lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or None

if not PROVIDER:
    PROVIDER = "anthropic" if ANTHROPIC_API_KEY and not OPENAI_API_KEY else "openai"

if PROVIDER == "anthropic":
    DEFAULT_MODEL = os.getenv("AGENT_LOOP_MODEL", "claude-sonnet-4-5")
else:
    DEFAULT_MODEL = os.getenv("AGENT_LOOP_MODEL", "gpt-4o-mini")
