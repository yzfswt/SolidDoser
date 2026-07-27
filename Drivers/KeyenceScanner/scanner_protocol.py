"""基恩士 SR-X 系列 TCP ASCII 协议客户端。"""
from __future__ import annotations

import logging
import socket
import time
from typing import List, Optional, Tuple

from Drivers.KeyenceScanner import scanner_config as cfg

logger = logging.getLogger("soliddoser.scanner")

Result = Tuple[bool, str]


class KeyenceScannerTcpClient:
    """经 TCP 9004 端口发送 LON 等 ASCII 命令。"""

    def __init__(self) -> None:
        self._sock: Optional[socket.socket] = None
        self._rx_buf = bytearray()

    def connect(self) -> Result:
        if self.connected:
            return True, ""
        self.close()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(cfg.CONNECT_TIMEOUT_S)
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            # 某些平台/环境不支持该选项，忽略即可
            pass
        try:
            sock.connect((cfg.SCANNER_HOST, cfg.SCANNER_PORT))
        except OSError as exc:
            sock.close()
            return False, f"无法连接扫码枪 {cfg.SCANNER_HOST}:{cfg.SCANNER_PORT}（{exc}）"
        self._sock = sock
        self._rx_buf.clear()
        return True, ""

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
        self._sock = None
        self._rx_buf.clear()

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
        # 扫码枪以 CR(0x0D) 作为行终止。这里用内部 buffer 做分隔，
        # 避免逐字节 recv(1) 导致的高开销与额外延迟。
        try:
            while True:
                idx = self._rx_buf.find(b"\r")
                if idx >= 0:
                    line_bytes = bytes(self._rx_buf[:idx])
                    del self._rx_buf[: idx + 1]
                    if not line_bytes:
                        return None, "扫码枪返回空响应"
                    return line_bytes.decode("ascii", errors="replace"), ""

                chunk = self._sock.recv(1024)
                if not chunk:
                    self.close()
                    return None, "扫码枪连接已断开"
                self._rx_buf.extend(chunk)
        except socket.timeout:
            if self._rx_buf:
                # 超时但已有部分数据，尽量返回给上层解析（不清空 buffer）
                return self._rx_buf.decode("ascii", errors="replace"), ""
            return None, "读取响应超时"
        except OSError as exc:
            self.close()
            return None, f"读取响应失败：{exc}"

    def test_connection(self) -> Result:
        ok, detail = self.connect()
        if not ok:
            return False, detail
        # 测试后释放连接，避免长期占用
        self.close()
        return True, f"已连通 {cfg.SCANNER_HOST}:{cfg.SCANNER_PORT}"

    def trigger_read(self) -> Tuple[Optional[str], str]:
        t0 = time.perf_counter()
        ok, detail = self.connect()
        if not ok:
            return None, detail
        assert self._sock is not None
        self._sock.settimeout(cfg.READ_TIMEOUT_S)

        t1 = time.perf_counter()
        ok, detail = self._send_command(cfg.CMD_TRIGGER_ONCE)
        if not ok:
            return None, detail

        lines: List[str] = []
        barcode: Optional[str] = None
        err = ""
        for _ in range(8):
            line, read_err = self._read_line()
            if line is None:
                if lines:
                    break
                return None, read_err or "未收到扫码结果"
            line = line.strip()
            if line:
                lines.append(line)
            barcode, err = _extract_barcode(lines)
            if barcode is not None or err:
                # LON/LOFF 默认无命令响应，只回一行读码结果；收到后立即返回，
                # 避免再次 read_line() 空等 READ_TIMEOUT_S（约 5s）。
                break

        self._finish_level_trigger()

        t2 = time.perf_counter()
        if barcode is None:
            return None, err or "；".join(lines) or "未识别到条码"
        barcode = normalize_barcode(barcode)
        logger.info(
            "扫码耗时：connect=%.0fms, read=%.0fms, total=%.0fms, lines=%s",
            (t1 - t0) * 1000.0,
            (t2 - t1) * 1000.0,
            (t2 - t0) * 1000.0,
            lines,
        )
        return barcode, ""

    def _finish_level_trigger(self) -> None:
        """电平同步触发下发送 LOFF，结束本次读取并复位触发状态。"""
        if not self.connected or self._sock is None:
            return
        prev_timeout = self._sock.gettimeout()
        try:
            self._sock.settimeout(cfg.FOLLOWUP_TIMEOUT_S)
            self._send_command(cfg.CMD_STOP_CONTINUOUS)
            self._read_line()
        finally:
            self._sock.settimeout(prev_timeout)


def normalize_barcode(raw: str) -> str:
    """去掉 SR-X 附加数据，仅保留条码本体（第一段，分隔符为 ':'）。"""
    if not cfg.STRIP_ADDITIONAL_DATA:
        return raw
    if ":" not in raw:
        return raw
    return raw.split(":", 1)[0]


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
