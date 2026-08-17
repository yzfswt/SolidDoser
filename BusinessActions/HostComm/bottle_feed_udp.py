"""试剂瓶进/出料 UDP：本机监听 + 向主系统发请求。"""
from __future__ import annotations

import json
import logging
import socket
import threading
from typing import Optional

from PySide6.QtCore import QObject, Signal

from BusinessActions.SolidDoserSystem.system_actions import (
    system_bottle_discharge_done,
    system_bottle_feed_done,
    system_bottle_feed_request,
)
from BusinessActions.SolidDoserSystem.system_context import SolidDoserSystemContext
from Common.HostBottleFeedConfig import (
    BOTTLE_FEED_UDP_HOST,
    BOTTLE_FEED_UDP_PORT,
    CMD_BOTTLE_DISCHARGE_DONE,
    CMD_BOTTLE_FEED_DONE,
    CMD_BOTTLE_FEED_REQUEST,
    HOST_MAIN_UDP_HOST,
    HOST_MAIN_UDP_PORT,
)

logger = logging.getLogger("soliddoser.bottle_feed_udp")

_bridge: Optional["BottleFeedUdpBridge"] = None


def get_bottle_comm() -> "BottleFeedUdpBridge":
    if _bridge is None:
        raise RuntimeError("试剂瓶进/出料 UDP 未启动，请用 main.py / main_soliddoser.py 启动。")
    return _bridge


class BottleFeedUdpBridge(QObject):
    """UDP 线程 → Qt 主线程；处理进料/出料完成并回包。"""

    command_received = Signal(dict, str, int)  # payload, reply_host, reply_port

    def __init__(self, ctx: SolidDoserSystemContext, parent=None):
        super().__init__(parent)
        self._ctx = ctx
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self.command_received.connect(self._on_command)

    def start(self, host: str = BOTTLE_FEED_UDP_HOST, port: int = BOTTLE_FEED_UDP_PORT) -> None:
        if self._running:
            return
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((host, port))
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("试剂瓶进/出料 UDP 已监听 %s:%s", host, port)

    def stop(self) -> None:
        self._running = False
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        logger.info("试剂瓶进/出料 UDP 已停止")

    def send_to_host(self, message: dict) -> bool:
        """向主系统监听端口发送 JSON（出料请求等）。"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                raw = json.dumps(message, ensure_ascii=False).encode("utf-8")
                sock.sendto(raw, (HOST_MAIN_UDP_HOST, HOST_MAIN_UDP_PORT))
            logger.info(
                "已发往主系统 %s:%s %s",
                HOST_MAIN_UDP_HOST,
                HOST_MAIN_UDP_PORT,
                message,
            )
            return True
        except OSError:
            logger.exception(
                "发往主系统失败 → %s:%s", HOST_MAIN_UDP_HOST, HOST_MAIN_UDP_PORT
            )
            return False

    def _listen_loop(self) -> None:
        assert self._sock is not None
        while self._running:
            try:
                data, addr = self._sock.recvfrom(4096)
            except OSError:
                if self._running:
                    logger.exception("试剂瓶 UDP 接收失败")
                break
            try:
                raw = data.decode("utf-8").strip()
                payload = json.loads(raw)
                if not isinstance(payload, dict):
                    raise ValueError("payload 不是 JSON 对象")
            except Exception as exc:  # noqa: BLE001
                logger.warning("无效试剂瓶 UDP 报文 from %s: %s", addr, exc)
                self._send_reply(
                    addr[0],
                    addr[1],
                    {
                        "cmd": "UNKNOWN",
                        "status": "error",
                        "reason": "bad_request",
                        "message": f"无效 JSON：{exc}",
                    },
                )
                continue
            self.command_received.emit(payload, addr[0], int(addr[1]))

    def _send_reply(self, host: str, port: int, message: dict) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(
                    json.dumps(message, ensure_ascii=False).encode("utf-8"),
                    (host, port),
                )
        except OSError:
            logger.exception("试剂瓶 UDP 回包失败 → %s:%s", host, port)

    def _on_command(self, payload: dict, host: str, port: int) -> None:
        cmd = str(payload.get("cmd") or payload.get("command") or "").strip()
        request_id = str(payload.get("request_id") or "")
        if cmd == CMD_BOTTLE_FEED_REQUEST:
            _, _, resp = system_bottle_feed_request(self._ctx, request_id)
            self._send_reply(host, port, resp)
            return
        if cmd == CMD_BOTTLE_FEED_DONE:
            _, _, resp = system_bottle_feed_done(self._ctx, request_id)
            self._send_reply(host, port, resp)
            return
        if cmd == CMD_BOTTLE_DISCHARGE_DONE:
            _, _, resp = system_bottle_discharge_done(self._ctx, request_id)
            self._send_reply(host, port, resp)
            return
        self._send_reply(
            host,
            port,
            {
                "cmd": cmd or "UNKNOWN",
                "status": "error",
                "reason": "unknown_cmd",
                "message": f"未知命令：{cmd}",
                "request_id": request_id,
            },
        )


def start_bottle_feed_udp(ctx: SolidDoserSystemContext) -> BottleFeedUdpBridge:
    global _bridge
    bridge = BottleFeedUdpBridge(ctx)
    bridge.start()
    _bridge = bridge
    return bridge
