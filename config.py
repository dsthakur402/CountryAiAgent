import logging
import os

from dotenv import load_dotenv

load_dotenv()


def _get_api_key() -> str:
    key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not key:
        # streamlit cloud puts secrets into env too, but only after app start,
        # so we also try reading from st.secrets lazily from the UI layer.
        return ""
    return key


GOOGLE_API_KEY = _get_api_key()
MODEL_NAME = os.environ.get("MODEL_NAME", "gemini-1.5-flash")
HTTP_TIMEOUT_S = float(os.environ.get("HTTP_TIMEOUT_S", "5"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

REST_COUNTRIES_BASE = "https://restcountries.com/v3.1"


def setup_logging() -> None:
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
