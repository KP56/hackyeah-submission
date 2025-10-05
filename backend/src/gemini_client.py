from __future__ import annotations
from typing import Optional, Callable
import google.generativeai as genai


class Gemini:
    def __init__(self, api_key: Optional[str], model: str = "gemini-2.5-flash-lite", verbose: bool = False, on_interaction: Optional[Callable[[str, str], None]] = None):
        self._configured = False
        self._verbose = verbose
        self._on_interaction = on_interaction
        self._model_name = model
        if api_key:
            genai.configure(api_key=api_key)
            self._configured = True
        self._model = None

    @property
    def is_configured(self) -> bool:
        """Check if Gemini is properly configured with an API key"""
        return self._configured

    def _get_model(self):
        if self._model is None and self._configured:
            self._model = genai.GenerativeModel(self._model_name)
        return self._model

    def prompt(self, text: str) -> str:
        if self._verbose:
            print("[gemini] prompt invoked")
        model = self._get_model()
        if not model:
            response = "Gemini is not configured."
        else:
            resp = model.generate_content(text)
            response = getattr(resp, "text", "") or ""
        
        # Log interaction to AI panel
        if self._on_interaction:
            self._on_interaction(text, response)
            
        return response
