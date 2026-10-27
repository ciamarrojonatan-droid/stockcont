"""Tests for the Stealth Browser Fingerprinting system."""

from pathlib import Path
from src.factory.stealth_profile import (
    get_stealth_fingerprint,
    build_stealth_init_script,
    get_playwright_launch_options,
)


def test_dual_account_fingerprints_are_distinct():
    fp1 = get_stealth_fingerprint(1)
    fp2 = get_stealth_fingerprint(2)

    assert fp1.account == 1
    assert fp2.account == 2

    # User-Agent must be different
    assert fp1.user_agent != fp2.user_agent
    assert "Chrome/128" in fp1.user_agent
    assert "Chrome/129" in fp2.user_agent

    # Hardware specs must be different
    assert fp1.hardware_concurrency != fp2.hardware_concurrency
    assert fp1.device_memory != fp2.device_memory

    # WebGL Renderers must be different
    assert fp1.webgl_renderer != fp2.webgl_renderer
    assert "RTX 3080" in fp1.webgl_renderer
    assert "RTX 4070" in fp2.webgl_renderer

    # Screen metrics must be different
    assert fp1.screen_width != fp2.screen_width
    assert fp1.screen_height != fp2.screen_height

    # Session directories must be completely isolated
    assert fp1.session_dir != fp2.session_dir
    assert fp1.session_dir == "playwright_session_raw"
    assert fp2.session_dir == "playwright_session_upscale"


def test_stealth_init_script_contains_spoofing():
    fp1 = get_stealth_fingerprint(1)
    script1 = build_stealth_init_script(fp1)

    assert "webdriver" in script1
    assert "hardwareConcurrency" in script1
    assert "RTX 3080" in script1
    assert "deviceMemory" in script1
    assert "HTMLCanvasElement.prototype.toDataURL" in script1

    fp2 = get_stealth_fingerprint(2)
    script2 = build_stealth_init_script(fp2)

    assert "RTX 4070" in script2
    assert str(fp2.screen_width) in script2


def test_playwright_launch_options(tmp_path):
    opt1 = get_playwright_launch_options(1, tmp_path)
    opt2 = get_playwright_launch_options(2, tmp_path)

    # Verify session paths are isolated
    assert opt1["user_data_dir"] != opt2["user_data_dir"]
    assert Path(opt1["user_data_dir"]).name in ("playwright_session_raw", "playwright_session")
    assert Path(opt2["user_data_dir"]).name == "playwright_session_upscale"

    # Verify headers and user agents differ
    assert opt1["user_agent"] != opt2["user_agent"]
    assert opt1["viewport"] != opt2["viewport"]


def test_account_config_dual_mode():
    from src.factory.runninghub_bot import get_account_config

    cfg1 = get_account_config(1)
    cfg2 = get_account_config(2)

    # Conta 1: Raw producer
    assert cfg1["account"] == 1
    assert cfg1["role"] == "raw_producer"
    assert cfg1["output_node"] == 121
    assert cfg1["save_mode"] == "batch_all"
    assert len(cfg1["prompt_nodes"]) == 42
    assert cfg1["default_batch_size"] == 210
    assert cfg1["session_dir_name"] == "playwright_session_raw"

    # Conta 2: SeedVR 8K Upscaler
    assert cfg2["account"] == 2
    assert cfg2["role"] == "seedvr_8k_upscaler"
    assert cfg2["input_node"] == 5
    assert cfg2["output_node"] == 55
    assert cfg2["save_mode"] == "realtime_single"
    assert cfg2["session_dir_name"] == "playwright_session_upscale"

