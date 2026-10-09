"""Environment configuration; credentials are never written to reports."""
from pathlib import Path
import os
ROOT = Path(__file__).resolve().parents[1]
def load_environment():
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT / '.env', override=False)
def configuration_status():
    load_environment()
    missing = [key for key in ('LLM_BASE_URL', 'LLM_API_KEY', 'LLM_MODEL') if not os.getenv(key)]
    return {'configured': not missing, 'missing': missing, 'model': os.getenv('LLM_MODEL', 'Unconfigured')}
