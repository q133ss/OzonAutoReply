from __future__ import annotations

import ctypes
import logging
import os
import threading
from contextlib import contextmanager
from typing import Iterator

LOGGER = logging.getLogger(__name__)

COINIT_MULTITHREADED = 0x0
COINIT_APARTMENTTHREADED = 0x2

_S_OK = 0x00000000
_S_FALSE = 0x00000001
_RPC_E_CHANGED_MODE = 0x80010106
_IS_WINDOWS = os.name == "nt"
_THREADING_HOOK_INSTALLED = False
_QTHREAD_HOOK_INSTALLED = False
_MAIN_THREAD_INITIALIZED = False

if _IS_WINDOWS:
    _ole32 = ctypes.WinDLL("ole32")
    _co_initialize_ex = _ole32.CoInitializeEx
    _co_initialize_ex.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    _co_initialize_ex.restype = ctypes.c_long
    _co_uninitialize = _ole32.CoUninitialize
    _co_uninitialize.argtypes = []
    _co_uninitialize.restype = None


def _normalize_hresult(value: int) -> int:
    return int(value) & 0xFFFFFFFF


def _co_initialize(apartment: int) -> tuple[int, bool]:
    if not _IS_WINDOWS:
        return _S_OK, False

    result = _normalize_hresult(_co_initialize_ex(None, apartment))
    if result in {_S_OK, _S_FALSE}:
        return result, True
    if result == _RPC_E_CHANGED_MODE:
        LOGGER.debug("COM already initialized with another apartment model on this thread.")
        return result, False
    raise OSError(f"CoInitializeEx failed with HRESULT 0x{result:08X}")


def initialize_main_thread(apartment: int = COINIT_APARTMENTTHREADED) -> None:
    global _MAIN_THREAD_INITIALIZED

    if _MAIN_THREAD_INITIALIZED or not _IS_WINDOWS:
        return

    result, _ = _co_initialize(apartment)
    _MAIN_THREAD_INITIALIZED = True
    LOGGER.info("COM initialized for main thread. apartment=%s hresult=0x%08X", apartment, result)


@contextmanager
def com_initialized(apartment: int = COINIT_MULTITHREADED) -> Iterator[None]:
    result, should_uninitialize = _co_initialize(apartment)
    try:
        yield
    finally:
        if should_uninitialize and _IS_WINDOWS:
            _co_uninitialize()
            LOGGER.debug("COM uninitialized for thread. apartment=%s hresult=0x%08X", apartment, result)


def install_threading_com_hook(apartment: int = COINIT_MULTITHREADED) -> None:
    global _THREADING_HOOK_INSTALLED

    if _THREADING_HOOK_INSTALLED or not _IS_WINDOWS:
        return

    original_run = threading.Thread.run

    def run_with_com(self: threading.Thread) -> None:
        with com_initialized(apartment):
            original_run(self)

    threading.Thread.run = run_with_com  # type: ignore[assignment]
    _THREADING_HOOK_INSTALLED = True
    LOGGER.info("Installed COM bootstrap for threading.Thread. apartment=%s", apartment)


def install_qthread_com_hook(apartment: int = COINIT_MULTITHREADED) -> None:
    global _QTHREAD_HOOK_INSTALLED

    if _QTHREAD_HOOK_INSTALLED or not _IS_WINDOWS:
        return

    try:
        from PyQt6.QtCore import QThread
    except Exception:
        return

    original_run = QThread.run

    def run_with_com(self: object) -> None:
        with com_initialized(apartment):
            original_run(self)

    QThread.run = run_with_com  # type: ignore[assignment]
    _QTHREAD_HOOK_INSTALLED = True
    LOGGER.info("Installed COM bootstrap for PyQt QThread. apartment=%s", apartment)


def bootstrap_windows_com() -> None:
    install_threading_com_hook()
    install_qthread_com_hook()
    initialize_main_thread()
