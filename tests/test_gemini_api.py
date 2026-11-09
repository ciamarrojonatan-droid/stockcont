"""Test suite for Gemini API capability suite and key detection."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from scripts.test_gemini_suite import get_api_key, run_suite


def test_get_api_key_empty_or_placeholder():
    """Verify placeholder or empty keys return None."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "sua_chave_gemini_aqui"}, clear=True):
        assert get_api_key() is None


def test_get_api_key_valid_env():
    """Verify valid environment key is detected."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSyFakeValidKey12345678901234567"}, clear=True):
        assert get_api_key() == "AIzaSyFakeValidKey12345678901234567"


def test_run_suite_handles_missing_key(capsys):
    """Verify run_suite displays helpful diagnostic when key is missing."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=True):
        result = run_suite()
        assert result is False
        captured = capsys.readouterr()
        assert "ERRO CRÍTICO" in captured.out
        assert "https://aistudio.google.com/app/apikey" in captured.out
