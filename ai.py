import time
import streamlit as st
from google import genai
from google.genai import types

API_KEY = st.secrets.get("GOOGLE_API_KEY", "")
MODEL_NAME = st.secrets.get("GEMINI_MODEL", "gemini-3-flash-preview")

ai_client = genai.Client(api_key=API_KEY)


def ai_generate(contents, config=None, retries=2, delay=3):
    """呼叫 Gemini API，遇到 503 自動重試"""
    for attempt in range(retries + 1):
        try:
            resp = ai_client.models.generate_content(
                model=MODEL_NAME,
                contents=contents,
                config=config,
            )
            return resp
        except Exception as e:
            if "503" in str(e) and attempt < retries:
                time.sleep(delay)
                continue
            raise
