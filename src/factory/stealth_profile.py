"""Stealth Browser Profile & Fingerprint Randomizer.

Provides distinct, realistic, high-entropy browser fingerprints for multi-account
autonomous operation on RunningHub, preventing account correlation, bot detection,
and canvas/WebGL/hardware fingerprint tracking.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class StealthFingerprint:
    account: int
    user_agent: str
    sec_ch_ua: str
    sec_ch_ua_platform: str
    platform: str
    hardware_concurrency: int
    device_memory: int
    screen_width: int
    screen_height: int
    device_pixel_ratio: float
    webgl_vendor: str
    webgl_renderer: str
    languages: List[str]
    timezone: str
    canvas_noise_offset: float
    session_dir: str


# Profile 1: Windows 11 Enterprise | Desktop RTX 3080 | 16 Cores | 1080p
CONTA_1_FINGERPRINT = StealthFingerprint(
    account=1,
    user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.6613.138 Safari/537.36"
    ),
    sec_ch_ua='"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
    sec_ch_ua_platform='"Windows"',
    platform="Win32",
    hardware_concurrency=16,
    device_memory=16,
    screen_width=1920,
    screen_height=1080,
    device_pixel_ratio=1.0,
    webgl_vendor="Google Inc. (NVIDIA)",
    webgl_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    languages=["pt-BR", "pt", "en-US", "en"],
    timezone="America/Sao_Paulo",
    canvas_noise_offset=0.00013,
    session_dir="playwright_session_raw",
)

# Profile 2: Windows 11 Pro | Desktop RTX 4070 | 12 Cores | 1440p
CONTA_2_FINGERPRINT = StealthFingerprint(
    account=2,
    user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/129.0.6668.71 Safari/537.36"
    ),
    sec_ch_ua='"Chromium";v="129", "Not;A=Brand";v="8", "Google Chrome";v="129"',
    sec_ch_ua_platform='"Windows"',
    platform="Win32",
    hardware_concurrency=12,
    device_memory=32,
    screen_width=2560,
    screen_height=1440,
    device_pixel_ratio=1.25,
    webgl_vendor="Google Inc. (NVIDIA)",
    webgl_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    languages=["pt-BR", "en-US", "pt", "es"],
    timezone="America/Sao_Paulo",
    canvas_noise_offset=0.00027,
    session_dir="playwright_session_upscale",
)


def get_stealth_fingerprint(account: int = 1) -> StealthFingerprint:
    """Return the designated stealth profile for the account."""
    if account == 2:
        return CONTA_2_FINGERPRINT
    return CONTA_1_FINGERPRINT


def build_stealth_init_script(fp: StealthFingerprint) -> str:
    """
    Build client-side JavaScript injected before page scripts load to spoof
    WebGL, Canvas, Hardware, Webdriver, Plugins and Permissions.
    """
    return f"""
(() => {{
    'use strict';

    // 1. Remove webdriver flag
    try {{
        delete Object.getPrototypeOf(navigator).webdriver;
    }} catch (e) {{}}
    Object.defineProperty(navigator, 'webdriver', {{
        get: () => undefined,
        configurable: true
    }});

    // 2. Hardware and Device Memory spoofing
    Object.defineProperty(navigator, 'hardwareConcurrency', {{
        get: () => {fp.hardware_concurrency},
        configurable: true
    }});
    Object.defineProperty(navigator, 'deviceMemory', {{
        get: () => {fp.device_memory},
        configurable: true
    }});
    Object.defineProperty(navigator, 'platform', {{
        get: () => '{fp.platform}',
        configurable: true
    }});

    // 3. Languages spoofing
    Object.defineProperty(navigator, 'languages', {{
        get: () => {fp.languages},
        configurable: true
    }});

    // 4. Screen resolution spoofing
    const screenProps = {{
        width: {fp.screen_width},
        height: {fp.screen_height},
        availWidth: {fp.screen_width},
        availHeight: {fp.screen_height - 40},
        colorDepth: 24,
        pixelDepth: 24
    }};
    for (const [prop, val] of Object.entries(screenProps)) {{
        try {{
            Object.defineProperty(screen, prop, {{ get: () => val, configurable: true }});
        }} catch(e) {{}}
    }}
    try {{
        Object.defineProperty(window, 'devicePixelRatio', {{
            get: () => {fp.device_pixel_ratio},
            configurable: true
        }});
    }} catch(e) {{}}

    // 5. WebGL Vendor & Renderer Spoofing
    const fakeVendor = '{fp.webgl_vendor}';
    const fakeRenderer = '{fp.webgl_renderer}';

    const patchWebGL = (proto) => {{
        if (!proto) return;
        const origGetParameter = proto.getParameter;
        proto.getParameter = function(param) {{
            // UNMASKED_VENDOR_WEBGL
            if (param === 0x9245) return fakeVendor;
            // UNMASKED_RENDERER_WEBGL
            if (param === 0x9246) return fakeRenderer;
            return origGetParameter.apply(this, arguments);
        }};
    }};

    try {{
        if (typeof WebGLRenderingContext !== 'undefined') {{
            patchWebGL(WebGLRenderingContext.prototype);
        }}
        if (typeof WebGL2RenderingContext !== 'undefined') {{
            patchWebGL(WebGL2RenderingContext.prototype);
        }}
    }} catch (e) {{}}

    // 6. Canvas Fingerprint Noise (Subtle deterministic shift per account)
    const noise = {fp.canvas_noise_offset};
    const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {{
        try {{
            const ctx = this.getContext('2d');
            if (ctx && this.width > 16 && this.height > 16) {{
                const imgData = ctx.getImageData(0, 0, Math.min(10, this.width), Math.min(10, this.height));
                for (let i = 0; i < imgData.data.length; i += 4) {{
                    imgData.data[i] = Math.min(255, Math.max(0, imgData.data[i] + Math.round((i % 3 === 0 ? 1 : -1) * noise * 255)));
                }}
                ctx.putImageData(imgData, 0, 0);
            }}
        }} catch (e) {{}}
        return origToDataURL.apply(this, arguments);
    }};

    // 7. Mock realistic window.chrome
    if (!window.chrome) {{
        window.chrome = {{}};
    }}
    if (!window.chrome.app) {{
        window.chrome.app = {{
            isInstalled: false,
            InstallState: {{ DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' }},
            RunningState: {{ CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' }}
        }};
    }}
    if (!window.chrome.runtime) {{
        window.chrome.runtime = {{
            OnInstalledReason: {{ CHROME_UPDATE: 'chrome_update', INSTALL: 'install', SHARED_MODULE_UPDATE: 'shared_module_update', UPDATE: 'update' }},
            PlatformArch: {{ ARM: 'arm', ARM64: 'arm64', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' }},
            PlatformNaclArch: {{ ARM: 'arm', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' }},
            PlatformOs: {{ ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', OPENBSD: 'openbsd', WIN: 'win' }}
        }};
    }}

    // 8. Fake Chrome Plugins list (avoid empty plugin array detection)
    try {{
        const fakePlugins = [
            {{ name: 'PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' }},
            {{ name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' }},
            {{ name: 'Chromium PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' }}
        ];
        Object.defineProperty(navigator, 'plugins', {{
            get: () => fakePlugins,
            configurable: true
        }});
    }} catch (e) {{}}

    // 9. Permissions Query (Notification permission prompt)
    if (navigator.permissions && navigator.permissions.query) {{
        const origQuery = navigator.permissions.query;
        navigator.permissions.query = (params) => {{
            if (params && params.name === 'notifications') {{
                return Promise.resolve({{ state: Notification.permission }});
            }}
            return origQuery(params);
        }};
    }}
}})();
"""


def get_playwright_launch_options(account: int, base_dir: Path) -> Dict[str, Any]:
    """
    Returns Playwright context configuration dictionary tailored for the account,
    with distinct viewport, user agent, locale, timezone, and isolated session directory.
    """
    fp = get_stealth_fingerprint(account)

    session_dir = base_dir / fp.session_dir
    # Fallback to legacy playwright_session if account 1 and raw dir doesn't exist yet
    if account == 1 and not session_dir.exists() and (base_dir / "playwright_session").exists():
        session_dir = base_dir / "playwright_session"

    chrome_installed = (
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe").exists()
        or Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe").exists()
    )

    opts: Dict[str, Any] = {
        "user_data_dir": session_dir,
        "headless": False,
        "viewport": {"width": fp.screen_width, "height": fp.screen_height},
        "user_agent": fp.user_agent,
        "locale": fp.languages[0],
        "timezone_id": fp.timezone,
        "device_scale_factor": fp.device_pixel_ratio,
        "accept_downloads": True,
        "extra_http_headers": {
            "Sec-Ch-Ua": fp.sec_ch_ua,
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": fp.sec_ch_ua_platform,
            "Accept-Language": f"{fp.languages[0]},{fp.languages[1]};q=0.9,en-US;q=0.8,en;q=0.7",
        },
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--new-window",
            f"--window-size={fp.screen_width},{fp.screen_height}",
            "--start-maximized",
        ],
    }
    if chrome_installed:
        opts["channel"] = "chrome"
    return opts
