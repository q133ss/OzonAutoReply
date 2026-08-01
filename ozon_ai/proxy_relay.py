"""Локальный прокси-релей для обычного браузера.

Chrome не принимает логин и пароль в --proxy-server: вместо этого он показал бы
диалог авторизации, который в автоматическом сценарии некому заполнить. Поэтому
поднимаем на 127.0.0.1 локальный HTTP-прокси без пароля, а он уже пересылает
трафик на upstream, подставляя заголовок Proxy-Authorization.
"""

from __future__ import annotations

import base64
import logging
import socket
import threading
from typing import Any, Optional

logger = logging.getLogger(__name__)

_CHUNK = 65536
_MAX_HEADER = 65536
_CONNECT_TIMEOUT = 30


class ProxyRelay:
    def __init__(
        self,
        host: str,
        port: Any,
        username: str = "",
        password: str = "",
        listen_host: str = "127.0.0.1",
    ) -> None:
        self.upstream_host = host
        self.upstream_port = int(port)
        self.listen_host = listen_host
        self.port = 0
        self._auth: Optional[bytes] = None
        if username:
            token = base64.b64encode(f"{username}:{password}".encode("utf-8"))
            self._auth = b"Proxy-Authorization: Basic " + token
        self._server: Optional[socket.socket] = None
        self._stopping = threading.Event()

    @classmethod
    def from_config(cls, config: Any) -> Optional["ProxyRelay"]:
        """Релей нужен только для http(s)-прокси с логином и паролем."""
        if config is None or not getattr(config, "enabled", False):
            return None
        if getattr(config, "proxy_type", "http") not in ("http", "https"):
            return None
        if not getattr(config, "username", ""):
            return None
        return cls(config.host, config.port, config.username, config.password)

    @property
    def server_url(self) -> str:
        return f"http://{self.listen_host}:{self.port}"

    def start(self) -> int:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.listen_host, 0))
        server.listen(64)
        self.port = server.getsockname()[1]
        self._server = server
        threading.Thread(target=self._serve, daemon=True, name="proxy-relay").start()
        logger.info(
            "Proxy relay: %s -> %s:%s", self.server_url, self.upstream_host, self.upstream_port
        )
        return self.port

    def stop(self) -> None:
        self._stopping.set()
        server, self._server = self._server, None
        if server is not None:
            try:
                server.close()
            except OSError:
                pass

    def _serve(self) -> None:
        server = self._server
        while not self._stopping.is_set() and server is not None:
            try:
                client, _ = server.accept()
            except OSError:
                break
            threading.Thread(target=self._handle, args=(client,), daemon=True).start()

    def _handle(self, client: socket.socket) -> None:
        upstream = None
        try:
            client.settimeout(_CONNECT_TIMEOUT)
            head = b""
            while b"\r\n\r\n" not in head:
                chunk = client.recv(_CHUNK)
                if not chunk:
                    return
                head += chunk
                if len(head) > _MAX_HEADER:
                    return
            header_blob, _, body = head.partition(b"\r\n\r\n")
            upstream = socket.create_connection(
                (self.upstream_host, self.upstream_port), timeout=_CONNECT_TIMEOUT
            )
            upstream.sendall(self._with_auth(header_blob) + body)
            client.settimeout(None)
            upstream.settimeout(None)
            self._pump(client, upstream)
        except Exception:
            logger.debug("Proxy relay: соединение оборвалось", exc_info=True)
        finally:
            for sock in (client, upstream):
                if sock is not None:
                    try:
                        sock.close()
                    except OSError:
                        pass

    def _with_auth(self, header_blob: bytes) -> bytes:
        if self._auth is None:
            return header_blob + b"\r\n\r\n"
        lines = header_blob.split(b"\r\n")
        kept = [line for line in lines[1:] if not line.lower().startswith(b"proxy-authorization:")]
        return b"\r\n".join([lines[0], self._auth] + kept) + b"\r\n\r\n"

    def _pump(self, client: socket.socket, upstream: socket.socket) -> None:
        finished = threading.Event()
        back = threading.Thread(
            target=self._copy, args=(upstream, client, finished), daemon=True
        )
        back.start()
        self._copy(client, upstream, finished)
        finished.wait(timeout=5)

    @staticmethod
    def _copy(src: socket.socket, dst: socket.socket, finished: threading.Event) -> None:
        try:
            while True:
                data = src.recv(_CHUNK)
                if not data:
                    break
                dst.sendall(data)
        except OSError:
            pass
        finally:
            try:
                dst.shutdown(socket.SHUT_WR)
            except OSError:
                pass
            finished.set()
