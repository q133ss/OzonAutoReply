from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional
from urllib.parse import quote


SUPPORTED_PROXY_TYPES = ("http", "https", "socks5")


def _is_truthy(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ProxyConfig:
    enabled: bool = False
    proxy_type: str = "http"
    host: str = ""
    port: str = ""
    username: str = ""
    password: str = ""

    @classmethod
    def from_db(cls, db: Any) -> "ProxyConfig":
        return cls(
            enabled=_is_truthy(db.get_setting("proxy_enabled")),
            proxy_type=(db.get_setting("proxy_type") or "http").strip().lower(),
            host=(db.get_setting("proxy_host") or "").strip(),
            port=(db.get_setting("proxy_port") or "").strip(),
            username=(db.get_setting("proxy_username") or "").strip(),
            password=db.get_setting("proxy_password") or "",
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProxyConfig":
        return cls(
            enabled=bool(data.get("enabled")),
            proxy_type=str(data.get("proxy_type") or "http").strip().lower(),
            host=str(data.get("host") or "").strip(),
            port=str(data.get("port") or "").strip(),
            username=str(data.get("username") or "").strip(),
            password=str(data.get("password") or ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "proxy_type": self.proxy_type,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
        }

    def validate(self) -> None:
        if not self.enabled:
            return
        if self.proxy_type not in SUPPORTED_PROXY_TYPES:
            raise ValueError("Unsupported proxy type.")
        if not self.host:
            raise ValueError("Proxy host is required.")
        try:
            port = int(self.port)
        except (TypeError, ValueError) as exc:
            raise ValueError("Proxy port must be a number.") from exc
        if port < 1 or port > 65535:
            raise ValueError("Proxy port must be between 1 and 65535.")

    def server_url(self, *, include_credentials: bool = False) -> Optional[str]:
        if not self.enabled:
            return None
        self.validate()
        credentials = ""
        if include_credentials and self.username:
            credentials = quote(self.username, safe="")
            if self.password:
                credentials += f":{quote(self.password, safe='')}"
            credentials += "@"
        return f"{self.proxy_type}://{credentials}{self.host}:{int(self.port)}"

    def to_playwright_proxy(self) -> Optional[Dict[str, str]]:
        server = self.server_url()
        if not server:
            return None
        proxy: Dict[str, str] = {"server": server}
        if self.username:
            proxy["username"] = self.username
            proxy["password"] = self.password
        return proxy

    def to_requests_proxies(self) -> Optional[Dict[str, str]]:
        server = self.server_url(include_credentials=True)
        if not server:
            return None
        return {"http": server, "https": server}
