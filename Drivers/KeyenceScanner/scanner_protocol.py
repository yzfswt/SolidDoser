"""基恩士 SR-X 系列 TCP ASCII 协议客户端。"""
from __future__ import annotations

import logging
import socket
from typing import List, Optional, Tuple

from Drivers.KeyenceScanner import scanner_config as cfg

logger = logging.getLogger("soliddoser.scanner")

Result = Tuple[bool, str]


class KeyenceScannerTcpClient:
    """经 TCP 9004 端口发送 LON 等 ASCII 命令。"""

    def __init__(self) -> None:
        self._sock: Optional[socket.socket] = None

    def connect(self) -> Result:
        self.close()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(cfg.CONNECT_TIMEOUT_S)
        try:
            sock.connect((cfg.SCANNER_HOST, cfg.SCANNER_PORT))
        except OSError as exc:
            sock.close()
            return False, f"无法连接扫码枪 {cfg.SCANNER_HOST}:{cfg.SCANNER_PORT}（{exc}）"
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

    def _send_command(self, command: str) -> Result:
        if not self.connected or self._sock is None:
            return False, "扫码枪未连接"
        payload = f"{command}\r".encode("ascii")
        try:
            self._sock.sendall(payload)
        except OSError as exc:
            self.close()
            return False, f"发送命令失败：{exc}"
        return True, ""

    def _read_line(self) -> Tuple[Optional[str], str]:
        if not self.connected or self._sock is None:
            return None, "扫码枪未连接"
        chunks: List[bytes] = []
        try:
            while True:
                data = self._sock.recv(1)
                if not data:
                    break
                if data == b"\r":
                    break
                chunks.append(data)
        except socket.timeout:
            if chunks:
                return b"".join(chunks).decode("ascii", errors="replace"), ""
            return None, "读取响应超时"
        except OSError as exc:
            self.close()
            return None, f"读取响应失败：{exc}"
        if not chunks:
            return None, "扫码枪返回空响应"
        return b"".join(chunks).decode("ascii", errors="replace"), ""

    def test_connection(self) -> Result:
        ok, detail = self.connect()
        if not ok:
            return False, detail
        self.close()
        return True, f"已连通 {cfg.SCANNER_HOST}:{cfg.SCANNER_PORT}"

    def trigger_read(self) -> Tuple[Optional[str], str]:
        ok, detail = self.connect()
        if not ok:
            return None, detail
        assert self._sock is not None
        self._sock.settimeout(cfg.READ_TIMEOUT_S)

        ok, detail = self._send_command(cfg.CMD_TRIGGER_ONCE)
        if not ok:
            return None, detail

        lines: List[str] = []
        for _ in range(8):
            line, err = self._read_line()
            if line is None:
                if lines:
                    break
                self.close()
                return None, err or "未收到扫码结果"
            line = line.strip()
            if line:
                lines.append(line)

        self.close()
        barcode, err = _extract_barcode(lines)
        if barcode is None:
            return None, err or "；".join(lines) or "未识别到条码"
        return barcode, ""


def _extract_barcode(lines: List[str]) -> Tuple[Optional[str], str]:
    for line in lines:
        upper = line.upper()
        if upper.startswith("ER") or upper.startswith("ERROR"):
            return None, line
        if upper.startswith("OK"):
            continue
        if upper in {"LON", "LOFF"}:
            continue
        return line, ""
    return None, "；".join(lines) if lines else "无有效读码数据"
