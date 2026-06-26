"""SOPA ST5000P RS485 OEM 帧协议（说明书附录 D）。"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, List, Optional

OEM_HEADER = 0x5B  # '['
RESP_HEADER = 0x2F  # '/'
FRAME_TAIL = 0x45  # 'E'
RESP_DATA_LEN = 9

# 说明书 5.10.2 错误码（第二状态字节）
ERR_NAMES: dict[int, str] = {
    0x00: "无错误",
    0x01: "上次动作未完成",
    0x02: "设备未初始化",
    0x03: "设备过载",
    0x04: "无效指令",
    0x05: "液位探测故障",
    0x07: "超时",
    0x08: "执行指令失败",
    0x09: "指令缓冲溢出",
    0x0A: "开始执行命令",
    0x0B: "枪头丢失",
    0x0D: "空吸",
    0x0E: "堵针",
    0x10: "泡沫",
    0x11: "吸液超过枪头容量",
    0x14: "空排",
    0x15: "排堵",
}


@dataclass(frozen=True)
class St5000pResponse:
    raw: bytes
    address: int
    status_byte: int
    error_code: int

    @property
    def started(self) -> bool:
        return self.error_code == 0x0A

    @property
    def ok(self) -> bool:
        return self.error_code == 0x00

    @property
    def error_name(self) -> str:
        return ERR_NAMES.get(self.error_code, f"未知错误 0x{self.error_code:02X}")


def format_volume_ul(volume_ul: int | float) -> str:
    if isinstance(volume_ul, int):
        return str(volume_ul)
    text = f"{volume_ul:.3f}".rstrip("0").rstrip(".")
    return text or "0"


def _append_checksum_16le_le(body: bytes) -> bytes:
    """对帧头+负载求和，取低 16 位，低字节在前、高字节在后追加。"""
    total = sum(body) & 0xFFFF
    return body + bytes([total & 0xFF, (total >> 8) & 0xFF])


def build_oem_frame(address: int, command: str) -> bytes:
    """组装 OEM 发送帧：[地址] + ASCII 命令 + 2 字节校验（AddChecksum）。"""
    if not 1 <= address <= 254:
        raise ValueError(f"移液枪地址须在 1–254，当前为 {address}")
    body = f"[{address}{command}".encode("ascii")
    return _append_checksum_16le_le(body)


def parse_response(data: bytes) -> Optional[St5000pResponse]:
    if len(data) < 1 + 1 + RESP_DATA_LEN + 1 + 1:
        return None
    if data[0] != RESP_HEADER:
        return None
    if data[-2] != FRAME_TAIL:
        return None
    expected = sum(data[:-1]) & 0xFF
    if data[-1] != expected:
        return None
    addr = data[1]
    payload = data[2 : 2 + RESP_DATA_LEN]
    return St5000pResponse(
        raw=data,
        address=addr,
        status_byte=payload[0],
        error_code=payload[1],
    )


def build_init_command() -> str:
    return "HE"


def build_aspirate_command(volume_ul: int | float, profile: str) -> str:
    vol = format_volume_ul(volume_ul)
    return f"{profile}P{vol}E"


def build_dispense_command(volume_ul: int | float, profile: str) -> str:
    vol = format_volume_ul(volume_ul)
    return f"{profile}D{vol}E"


def build_eject_tip_command() -> str:
    return "RE"


def build_version_query_command() -> str:
    return "V"


def probe_device(
    send_frame: Callable[[bytes], None],
    recv_frame: Callable[[], bytes],
    address: int,
    *,
    timeout_s: float = 0.35,
    poll_interval_s: float = 0.02,
) -> bool:
    """发送版本查询，收到合法应答帧则视为设备在线。"""
    frame = build_oem_frame(address, build_version_query_command())
    send_frame(frame)
    rx_buffer = bytearray()
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        chunk = recv_frame()
        if chunk:
            rx_buffer.extend(chunk)
        parsed = _take_frame_from_buffer(rx_buffer)
        if parsed is not None and parsed.address == address:
            return True
        if not chunk:
            time.sleep(poll_interval_s)
    return False


def _take_frame_from_buffer(buffer: bytearray) -> Optional[St5000pResponse]:
    min_len = 1 + 1 + RESP_DATA_LEN + 1 + 1
    start = 0
    while start <= len(buffer) - min_len:
        if buffer[start] != RESP_HEADER:
            start += 1
            continue
        for tail in range(start + min_len - 2, len(buffer)):
            if buffer[tail] != FRAME_TAIL or tail + 1 >= len(buffer):
                continue
            frame = bytes(buffer[start : tail + 2])
            parsed = parse_response(frame)
            if parsed is not None:
                del buffer[: tail + 2]
                return parsed
        break
    return None


def execute_command(
    send_frame: Callable[[bytes], None],
    recv_frame: Callable[[], bytes],
    address: int,
    command: str,
    *,
    timeout_s: float,
    poll_interval_s: float,
) -> tuple[bool, str, List[St5000pResponse]]:
    """发送命令并等待执行完成（0x0A 开始 → 0x00 完成）。"""
    frame = build_oem_frame(address, command)
    send_frame(frame)

    responses: List[St5000pResponse] = []
    rx_buffer = bytearray()
    deadline = time.monotonic() + timeout_s
    saw_start = False

    while time.monotonic() < deadline:
        chunk = recv_frame()
        if chunk:
            rx_buffer.extend(chunk)
        parsed = _take_frame_from_buffer(rx_buffer)
        if parsed is not None:
            responses.append(parsed)
            if parsed.ok:
                return True, "完成", responses
            if parsed.started:
                saw_start = True
            elif parsed.error_code == 0x01 and saw_start:
                pass
            else:
                return False, parsed.error_name, responses
        if not chunk and not parsed:
            time.sleep(poll_interval_s)

    return False, "移液枪应答超时", responses
