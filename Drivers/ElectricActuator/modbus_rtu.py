"""Modbus-RTU 组帧 / CRC16 / 应答解析。"""
from __future__ import annotations

from typing import Optional, Tuple


def crc16_modbus(data: bytes) -> bytes:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def build_write_register(slave_id: int, address: int, value: int) -> bytes:
    pdu = bytes([
        slave_id & 0xFF,
        0x06,
        (address >> 8) & 0xFF,
        address & 0xFF,
        (value >> 8) & 0xFF,
        value & 0xFF,
    ])
    return pdu + crc16_modbus(pdu)


def build_write_registers(slave_id: int, address: int, values: list[int]) -> bytes:
    count = len(values)
    pdu = bytes([
        slave_id & 0xFF,
        0x10,
        (address >> 8) & 0xFF,
        address & 0xFF,
        (count >> 8) & 0xFF,
        count & 0xFF,
        (count * 2) & 0xFF,
    ])
    for value in values:
        pdu += bytes([(value >> 8) & 0xFF, value & 0xFF])
    return pdu + crc16_modbus(pdu)


def build_read_registers(slave_id: int, address: int, count: int = 1) -> bytes:
    pdu = bytes([
        slave_id & 0xFF,
        0x03,
        (address >> 8) & 0xFF,
        address & 0xFF,
        (count >> 8) & 0xFF,
        count & 0xFF,
    ])
    return pdu + crc16_modbus(pdu)


def _verify_crc(frame: bytes) -> bool:
    if len(frame) < 3:
        return False
    body, crc = frame[:-2], frame[-2:]
    return crc16_modbus(body) == crc


def parse_write_response(frame: bytes, slave_id: int) -> Tuple[bool, str]:
    if len(frame) < 8:
        return False, f"应答过短：{frame.hex()}"
    if not _verify_crc(frame[:8]):
        return False, f"CRC 校验失败：{frame.hex()}"
    if frame[0] != slave_id or frame[1] not in (0x06, 0x10):
        return False, f"Modbus 写入应答异常：{frame.hex()}"
    return True, ""


def parse_read_u16(frame: bytes, slave_id: int) -> Tuple[Optional[int], str]:
    values, err = parse_read_registers(frame, slave_id, 1)
    if err:
        return None, err
    return values[0], ""


def parse_read_registers(
    frame: bytes,
    slave_id: int,
    count: int,
) -> Tuple[Optional[list[int]], str]:
    byte_count = count * 2
    min_len = 5 + byte_count
    if len(frame) < min_len:
        return None, f"应答过短：{frame.hex()}"
    if not _verify_crc(frame[:min_len]):
        return None, f"CRC 校验失败：{frame.hex()}"
    if frame[0] != slave_id or frame[1] != 0x03 or frame[2] != byte_count:
        return None, f"Modbus 读取应答异常：{frame.hex()}"
    values = [
        (frame[3 + i * 2] << 8) | frame[4 + i * 2]
        for i in range(count)
    ]
    return values, ""
