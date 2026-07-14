"""基恩士扫码枪调试动作。"""
from __future__ import annotations

from typing import Tuple

from BusinessActions.KeyenceScanner.scanner_context import ScannerContext
from Drivers.KeyenceScanner.scanner_driver import get_scanner_driver

ActionResult = Tuple[bool, str]


def _ok(ctx: ScannerContext, action: str, msg: str) -> ActionResult:
    ctx.scanner.last_action = action
    ctx.scanner.last_message = msg
    ctx.scanner.last_success = True
    return True, msg


def _fail(ctx: ScannerContext, action: str, msg: str) -> ActionResult:
    ctx.scanner.last_action = action
    ctx.scanner.last_message = msg
    ctx.scanner.last_success = False
    return False, msg


def scanner_test_connection(ctx: ScannerContext) -> ActionResult:
    action = "扫码枪连接测试"
    driver = get_scanner_driver()
    ctx.scanner.simulation_mode = driver.simulation
    ok, detail = driver.test_connection()
    ctx.scanner.connected = ok
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def scanner_trigger_read(ctx: ScannerContext) -> ActionResult:
    action = "触发扫码"
    driver = get_scanner_driver()
    ctx.scanner.simulation_mode = driver.simulation
    barcode, err = driver.trigger_read()
    if barcode is None:
        ctx.scanner.connected = False
        return _fail(ctx, action, err or "读码失败")
    ctx.scanner.connected = True
    ctx.scanner.last_barcode = barcode
    ctx.scanner.append_history(barcode)
    return _ok(ctx, action, f"读码成功：{barcode}")


def scanner_clear_result(ctx: ScannerContext) -> ActionResult:
    action = "清空读码结果"
    ctx.scanner.last_barcode = ""
    return _ok(ctx, action, "已清空")
