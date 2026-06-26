"""经 ZLAN5212DI 串口服务器 TCP 透传 RS485（移液枪、电爪、电缸等共用）。"""
from __future__ import annotations

import logging
import socket
import threading
import time

from Drivers.SerialServer import zlan5212di_config as cfg

logger = logging.getLogger("soliddoser.serial_server.rs485")

_lock = threading.Lock()
_sock: socket.socket | None = None
_last_error = "串口服务器未连接"


def sdk_available() -> bool:
    """兼容旧接口：串口服务器方案不依赖 Hitbot SDK。"""
    return True


def _close_socket() -> None:
    global _sock
    if _sock is not None:
        try:
            _sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            _sock.close()
        except OSError:
            pass
    _sock = None


def _ensure_connected(*, allow_retry: bool = True) -> bool:
    global _sock, _last_error
    if _sock is not None:
        return True
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(cfg.CONNECT_TIMEOUT_S)
        sock.connect((cfg.SERIAL_SERVER_HOST, cfg.SERIAL_SERVER_PORT))
        sock.settimeout(cfg.SOCKET_RECV_TIMEOUT_S)
        _sock = sock
        logger.info(
            "已连接 ZLAN5212DI %s:%s（PORT1 RS485 透传）",
            cfg.SERIAL_SERVER_HOST,
            cfg.SERIAL_SERVER_PORT,
        )
        return True
    except OSError as exc:
        _close_socket()
        _last_error = (
            f"无法连接 ZLAN5212DI {cfg.SERIAL_SERVER_HOST}:{cfg.SERIAL_SERVER_PORT}：{exc}。"
            "请确认设备 IP/端口、工作模式为 TCP 服务器、网线与本机同网段。"
        )
        logger.error(_last_error)
        if allow_retry:
            time.sleep(0.2)
            return _ensure_connected(allow_retry=False)
        return False


def _drain_recv_buffer(*, max_rounds: int = 8) -> None:
    if _sock is None:
        return
    old_timeout = _sock.gettimeout()
    _sock.settimeout(0.01)
    try:
        for _ in range(max_rounds):
            try:
                chunk = _sock.recv(4096)
            except socket.timeout:
                return
            except OSError:
                _close_socket()
                return
            if not chunk:
                _close_socket()
                return
    finally:
        if _sock is not None:
            _sock.settimeout(old_timeout)


def _recv_raw() -> bytes:
    if _sock is None:
        return b""
    try:
        return _sock.recv(4096)
    except socket.timeout:
        return b""
    except OSError as exc:
        _last_error = f"串口服务器接收失败：{exc}"
        _close_socket()
        return b""


def _send_with_retry(frame: bytes) -> None:
    global _last_error
    _drain_recv_buffer()
    last_exc: OSError | None = None
    for attempt in range(cfg.SEND_RETRY_COUNT):
        if attempt > 0:
            _drain_recv_buffer()
            time.sleep(cfg.SEND_RETRY_DELAY_S)
            _close_socket()
        if not _ensure_connected():
            continue
        assert _sock is not None
        try:
            _sock.sendall(frame)
            return
        except OSError as exc:
            last_exc = exc
            _last_error = f"串口服务器发送失败：{exc}"
            _close_socket()
    if last_exc is not None:
        raise RuntimeError(_last_error)
    raise RuntimeError(_last_error)


def send_frame(frame: bytes) -> None:
    with _lock:
        _send_with_retry(frame)


def recv_frame() -> bytes:
    with _lock:
        if not _ensure_connected():
            return b""
        return _recv_raw()


def transact(
    frame: bytes,
    *,
    min_response_len: int = 8,
    timeout_s: float | None = None,
) -> bytes:
    """发送帧并等待应答（Modbus 等请求-应答协议）。"""
    with _lock:
        _send_with_retry(frame)

        rx = bytearray()
        deadline = time.monotonic() + (
            timeout_s if timeout_s is not None else cfg.RS485_TRANSACT_TIMEOUT_S
        )
        while time.monotonic() < deadline:
            chunk = _recv_raw()
            if chunk:
                rx.extend(chunk)
                if len(rx) >= min_response_len:
                    return bytes(rx)
            time.sleep(cfg.RS485_RECV_POLL_S)
        return bytes(rx)


def reset_connection() -> None:
    with _lock:
        _close_socket()


def warmup_async() -> None:
    """启动后在后台预连接串口服务器，减少首次工具操作等待。"""

    def _run() -> None:
        if _ensure_connected():
            logger.info(
                "ZLAN5212DI RS485 预连接成功（%s:%s）",
                cfg.SERIAL_SERVER_HOST,
                cfg.SERIAL_SERVER_PORT,
            )
        else:
            logger.warning("ZLAN5212DI RS485 预连接未完成：%s", _last_error)

    threading.Thread(
        target=_run,
        name="zlan5212di-rs485-warmup",
        daemon=True,
    ).start()
