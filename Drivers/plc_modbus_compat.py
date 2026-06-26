"""pymodbus 2.x(slave) / 3.x(device_id) 兼容封装（Easy521 Modbus TCP）。"""
from __future__ import annotations

from typing import Any


def _device_kw(device_id: int) -> dict[str, int]:
    return {"device_id": device_id}


def write_coil(client: Any, address: int, value: bool, *, device_id: int = 1) -> Any:
    kw = _device_kw(device_id)
    try:
        return client.write_coil(address, value, **kw)
    except TypeError:
        return client.write_coil(address, value, slave=device_id)


def read_coils(client: Any, address: int, *, count: int = 1, device_id: int = 1) -> Any:
    kw = _device_kw(device_id)
    try:
        return client.read_coils(address, count=count, **kw)
    except TypeError:
        return client.read_coils(address, count, slave=device_id)


def write_registers(
    client: Any, address: int, values: list[int], *, device_id: int = 1
) -> Any:
    kw = _device_kw(device_id)
    try:
        return client.write_registers(address, values, **kw)
    except TypeError:
        return client.write_registers(address, values, slave=device_id)


def read_holding_registers(
    client: Any, address: int, *, count: int = 1, device_id: int = 1
) -> Any:
    kw = _device_kw(device_id)
    try:
        return client.read_holding_registers(address, count=count, **kw)
    except TypeError:
        return client.read_holding_registers(address, count, slave=device_id)
