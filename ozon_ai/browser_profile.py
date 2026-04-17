from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class BrowserProfileConfig:
    user_agent: str = USER_AGENT
    locale: str = "ru-RU"
    timezone_id: str = "Europe/Moscow"
    color_scheme: str = "light"
    viewport_width: int = 1440
    viewport_height: int = 900
    hardware_concurrency: int = 8
    device_memory: int = 8
    platform: str = "Win32"
    webgl_vendor: str = "Google Inc. (NVIDIA)"
    webgl_renderer: str = (
        "ANGLE (NVIDIA, NVIDIA GeForce GTX 750 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)"
    )

    @property
    def viewport(self) -> Dict[str, int]:
        return {"width": self.viewport_width, "height": self.viewport_height}

    @property
    def screen(self) -> Dict[str, int]:
        return {"width": self.viewport_width, "height": self.viewport_height}

    @property
    def launch_args(self) -> list[str]:
        return [
            "--start-maximized",
            "--disable-blink-features=AutomationControlled",
        ]


DEFAULT_BROWSER_PROFILE = BrowserProfileConfig()


def build_persistent_context_kwargs(
    proxy: Optional[Dict[str, str]] = None,
    config: BrowserProfileConfig = DEFAULT_BROWSER_PROFILE,
) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
        "headless": False,
        "args": config.launch_args,
        "user_agent": config.user_agent,
        "locale": config.locale,
        "timezone_id": config.timezone_id,
        "color_scheme": config.color_scheme,
        "viewport": config.viewport,
        "screen": config.screen,
    }
    if proxy:
        kwargs["proxy"] = proxy
    return kwargs


def build_init_script(config: BrowserProfileConfig = DEFAULT_BROWSER_PROFILE) -> str:
    payload = {
        "languages": ["ru-RU", "ru", "en-US", "en"],
        "platform": config.platform,
        "hardwareConcurrency": config.hardware_concurrency,
        "deviceMemory": config.device_memory,
        "vendor": config.webgl_vendor,
        "renderer": config.webgl_renderer,
    }
    data = json.dumps(payload, ensure_ascii=False)
    return f"""
(() => {{
  const cfg = {data};
  window.__ozonFingerprintPatchApplied = true;

  const patchProperty = (obj, key, value) => {{
    try {{
      Object.defineProperty(obj, key, {{
        configurable: true,
        enumerable: true,
        get: () => value,
      }});
    }} catch (error) {{
      console.debug("patchProperty failed", key, error);
    }}
  }};

  const navigatorProto = Object.getPrototypeOf(window.navigator);
  patchProperty(window.navigator, "webdriver", undefined);
  patchProperty(navigatorProto, "webdriver", undefined);
  patchProperty(window.navigator, "languages", cfg.languages);
  patchProperty(navigatorProto, "languages", cfg.languages);
  patchProperty(window.navigator, "platform", cfg.platform);
  patchProperty(navigatorProto, "platform", cfg.platform);
  patchProperty(window.navigator, "hardwareConcurrency", cfg.hardwareConcurrency);
  patchProperty(navigatorProto, "hardwareConcurrency", cfg.hardwareConcurrency);
  patchProperty(window.navigator, "deviceMemory", cfg.deviceMemory);
  patchProperty(navigatorProto, "deviceMemory", cfg.deviceMemory);

  const fakePluginArray = [
    {{ name: "Chrome PDF Plugin", filename: "internal-pdf-viewer" }},
    {{ name: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai" }},
    {{ name: "Native Client", filename: "internal-nacl-plugin" }},
  ];
  patchProperty(window.navigator, "plugins", fakePluginArray);
  patchProperty(navigatorProto, "plugins", fakePluginArray);
  patchProperty(window.navigator, "mimeTypes", [
    {{ type: "application/pdf", suffixes: "pdf", description: "Portable Document Format" }},
  ]);
  patchProperty(navigatorProto, "mimeTypes", [
    {{ type: "application/pdf", suffixes: "pdf", description: "Portable Document Format" }},
  ]);

  const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
  if (originalQuery) {{
    window.navigator.permissions.query = (parameters) => {{
      if (parameters && parameters.name === "notifications") {{
        return Promise.resolve({{ state: Notification.permission }});
      }}
      return originalQuery.call(window.navigator.permissions, parameters);
    }};
  }}

  if (!window.chrome) {{
    Object.defineProperty(window, "chrome", {{
      configurable: true,
      enumerable: true,
      writable: false,
      value: {{}},
    }});
  }}
  if (!window.chrome.runtime) {{
    window.chrome.runtime = {{}};
  }}
  if (!window.chrome.app) {{
    window.chrome.app = {{
      isInstalled: false,
      InstallState: {{ DISABLED: "disabled", INSTALLED: "installed", NOT_INSTALLED: "not_installed" }},
      RunningState: {{ CANNOT_RUN: "cannot_run", READY_TO_RUN: "ready_to_run", RUNNING: "running" }},
    }};
  }}

  const patchWebGl = (proto) => {{
    if (!proto || !proto.getParameter) {{
      return;
    }}
    const originalGetParameter = proto.getParameter;
    proto.getParameter = function(parameter) {{
      if (parameter === 37445) {{
        return cfg.vendor;
      }}
      if (parameter === 37446) {{
        return cfg.renderer;
      }}
      return originalGetParameter.call(this, parameter);
    }};
  }};
  patchWebGl(window.WebGLRenderingContext && window.WebGLRenderingContext.prototype);
  patchWebGl(window.WebGL2RenderingContext && window.WebGL2RenderingContext.prototype);

  const originalGetContext = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function(type, ...args) {{
    const context = originalGetContext.call(this, type, ...args);
    if (!context || typeof context.getParameter !== "function") {{
      return context;
    }}
    const original = context.getParameter.bind(context);
    context.getParameter = (parameter) => {{
      if (parameter === 37445) {{
        return cfg.vendor;
      }}
      if (parameter === 37446) {{
        return cfg.renderer;
      }}
      return original(parameter);
    }};
    return context;
  }};

  const originalOffsetHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetHeight");
  if (originalOffsetHeight && originalOffsetHeight.get) {{
    Object.defineProperty(HTMLDivElement.prototype, "offsetHeight", {{
      configurable: true,
      get() {{
        if (this.id === "modernizr") {{
          return 1;
        }}
        return originalOffsetHeight.get.call(this);
      }},
    }});
  }}
}})();
"""


def apply_browser_profile(context: Any, logger: Optional[logging.Logger] = None) -> None:
    from playwright_stealth import Stealth

    stealth = Stealth()
    init_script = build_init_script()
    context.add_init_script(script=init_script)

    def _configure_page(page: Any) -> None:
        try:
            page.add_init_script(script=init_script)
            stealth.apply_stealth_sync(page)
            if logger:
                logger.info("Applied stealth to page: %s", page.url)
        except Exception:
            if logger:
                logger.exception("Failed to apply stealth to page")

    for page in list(context.pages):
        _configure_page(page)
    context.on("page", _configure_page)
