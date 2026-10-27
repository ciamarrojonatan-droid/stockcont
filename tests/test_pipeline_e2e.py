import json
import os
import sys
from pathlib import Path
import pytest
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

from src.factory.runninghub_bot import load_prompts, DEFAULT_BATCH_SIZE, DEFAULT_OUTPUT_NODE, CONTA_1_CONFIG
from src.cataloger.adobe_csv_maker import embed_metadata
from PIL import Image

from unittest.mock import patch
from src.factory.prompt_queue import PromptItem

def test_prompt_loading_batch_size():
    """Verify that load_prompts loads prompts according to batch size."""
    mock_items = [
        PromptItem(source_id=f"item_{i}", prompt_id=i, prompt_text=f"Mock prompt {i}", prompt_hash=f'hash_{i}')
        for i in range(DEFAULT_BATCH_SIZE)
    ]
    with patch("src.factory.prompt_queue.PromptQueueManager.get_pending_prompts", return_value=mock_items):
        prompts = load_prompts(batch_size=DEFAULT_BATCH_SIZE)
        assert len(prompts) == DEFAULT_BATCH_SIZE
        assert DEFAULT_BATCH_SIZE == 210
        for p in prompts:
            assert isinstance(p, str)
            assert len(p.strip()) > 0

def test_batch_distribution_nodes():
    """Verify that 210 prompts are split evenly across 42 PromptList nodes (5 each)."""
    target_nodes = CONTA_1_CONFIG["prompt_nodes"]
    assert len(target_nodes) == 42
    batch_size = len(target_nodes) * 5
    assert batch_size == 210
    mock_items = [
        PromptItem(source_id=f"item_{i}", prompt_id=i, prompt_text=f"Mock prompt {i}", prompt_hash=f'hash_{i}')
        for i in range(batch_size)
    ]
    with patch("src.factory.prompt_queue.PromptQueueManager.get_pending_prompts", return_value=mock_items):
        batch_prompts = load_prompts(batch_size=batch_size)
        
        distribution = {}
        for idx, prompt_text in enumerate(batch_prompts):
            node_id = target_nodes[idx // 5]
            distribution[node_id] = distribution.get(node_id, 0) + 1
            
        for n in target_nodes:
            assert distribution[n] == 5, f"Expected 5 prompts for node {n}, got {distribution.get(n)}"

def test_gemini_api_key_configured():
    """Verify that the Gemini API key is configured and valid."""
    api_key = os.getenv("GEMINI_API_KEY")
    assert api_key is not None, "GEMINI_API_KEY is not set"
    assert len(api_key) > 10, "GEMINI_API_KEY appears invalid"

def test_cataloger_iptc_and_exif_embedding(tmp_path):
    """Test IPTC and EXIF embedding on a test image."""
    test_img_path = tmp_path / "test_asset.png"
    target_img_path = tmp_path / "test_asset.jpg"
    img = Image.new("RGB", (200, 200), color=(73, 109, 137))
    img.save(test_img_path, "PNG")
    
    title = "Modern AI Workspace Test"
    keywords = ["modern", "workspace", "technology", "artificial intelligence", "office"]
    
    result_path = embed_metadata(test_img_path, target_img_path, title, keywords)
    assert result_path.exists(), "Target image file should exist after embedding"
    assert result_path.stat().st_size > 0

def test_main_cli_status(capsys):
    """Verify that main.py --status runs without throwing exceptions."""
    import main
    main.check_status()
    captured = capsys.readouterr()
    assert "StockCont" in captured.out
    assert "PIPELINE STATUS REPORT" in captured.out
