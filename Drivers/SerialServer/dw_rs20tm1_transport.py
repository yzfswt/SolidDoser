"""达而稳 DW-RS20TM1 TCP 透传客户端（串口 ↔ 以太网）。"""
from __future__ import annotations

import logging
import socket
from typing import Optional, Tuple

from Drivers.SerialServer import dw_rs20tm1_config as cfg

logger = logging.getLogger("soliddoser.serial_server")

Result = Tuple[bool, str]


class DwRs20tm1TcpClient:
    """作为 TCP Client 连接串口服务器的 TCP Server，原始字节双向透传。"""

    def __init__(self) -> None:
        self._sock: Optional[socket.socket] = None

    def connect(self) -> Result:
        self.close()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(cfg.CONNECT_TIMEOUT_S)
        try:
            sock.connect((cfg.SERIAL_SERVER_HOST, cfg.SERIAL_SERVER_PORT))
        except OSError as exc:
            sock.close()
            return (
                False,
                f"无法连接串口服务器 {cfg.SERIAL_SERVER_HOST}:{cfg.SERIAL_SERVER_PORT}（{exc}）",
            )
        self._sock = sock
        return True, ""

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
        self._sock = None

    @property
    def connected(self) -> bool:
        return self._sock is not None

    def test_connection(self) -> Result:
        ok, detail = self.connect()
        if not ok:
            return False, detail
        self.close()
        return True, f"已连通 {cfg.SERIAL_SERVER_HOST}:{cfg.SERIAL_SERVER_PORT}"

    def write(self, data: bytes) -> Result:
        if not self.connected or self._sock is None:
            return False, "串口服务器未连接"
        try:
            self._sock.sendall(data)
        except OSError as exc:
            self.close()
            return False, f"发送失败：{exc}"
        return True, ""

    def read_until(
        self, terminator: bytes = b"\r\n", *, max_bytes: int = 256
    ) -> Tuple[Optional[bytes], str]:
        if not self.connected or self._sock is None:
            return None, "串口服务器未连接"
        assert self._sock is not None
        self._sock.settimeout(cfg.IO_TIMEOUT_S)
        buf = bytearray()
        try:
            while len(buf) < max_bytes:
                chunk = self._sock.recv(1)
                if not chunk:
                    break
                buf.extend(chunk)
                if buf.endswith(terminator):
                    return bytes(buf), ""
        except socket.timeout:
            if buf:
                return bytes(buf), ""
            return None, "读取响应超时"
        except OSError as exc:
            self.close()
            return None, f"读取失败：{exc}"
        if not buf:
            return None, "串口返回空响应"
        return bytes(buf), ""

    def transact(
        self, request: bytes, *, terminator: bytes = b"\r\n"
    ) -> Tuple[Optional[bytes], str]:
        ok, detail = self.connect()
        if not ok:
            return None, detail
        ok, detail = self.write(request)
        if not ok:
            return None, detail
        data, err = self.read_until(terminator)
        self.close()
        if data is None:
            return None, err
        return data, ""
