"""经 Hitbot Z-Arm com485_send/recv 透传 RS485（移液枪、电缸等共用）。"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from ctypes import c_int, c_ubyte
from pathlib import Path

from Drivers.Robot import robot_com485_config as cfg

logger = logging.getLogger("soliddoser.robot.rs485")

_lock = threading.Lock()
_robot = None
_sdk_loaded = False
_com485_ready = False
_net_port_initialized = False
_robot_initialized = False
_recv_buf = None
_last_error = "机器人 RS485 未就绪"
_last_connect_value: int | None = None


def _ensure_sdk_log_dir() -> None:
    log_dir = Path(cfg.HITBOT_SDK_DIR) / "SDK_LOG"
    log_dir.mkdir(parents=True, exist_ok=True)


def _port_40000_owner() -> tuple[bool, str]:
    """检查 40000 端口是否被占用，返回 (是否占用, PID)。"""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            encoding="gbk",
            errors="replace",
            timeout=5,
            check=False,
        )
    except Exception:
        return False, ""
    for line in result.stdout.splitlines():
        if ":40000" not in line.upper() or "LISTENING" not in line.upper():
            continue
        parts = line.split()
        if parts:
            return True, parts[-1]
    return False, ""


def _net_port_failure_message(ret: int) -> str:
    in_use, pid = _port_40000_owner()
    if ret == -1 and in_use:
        return (
            f"net_port_initial 失败（返回 {ret}）：端口 40000 已被 server.exe 占用"
            f"（PID {pid}，多为 HitbotStudio）。请完全退出 HitbotStudio，"
            "在任务管理器中结束所有 server.exe 后，仅通过 SolidDoser 重试。"
            "不要同时运行 Studio 与 SolidDoser。"
        )
    if ret == 0 and in_use:
        return (
            "net_port_initial 返回 0：端口 40000 已被占用。"
            "请关闭 HitbotStudio 并结束 server.exe 后重试。"
        )
    return (
        f"net_port_initial 失败（返回 {ret}）。请确认 "
        f"{cfg.HITBOT_SDK_DIR} 下 server.exe、share.dll、"
        "small_scara_interface.dll 完整，并以管理员结束残留的 server.exe 后重试。"
    )


@contextmanager
def _sdk_working_directory():
    """server.exe / share.dll 与 SDK 同目录，须在 SDK 目录下加载 DLL 并初始化。"""
    sdk_dir = Path(cfg.HITBOT_SDK_DIR)
    prev = os.getcwd()
    try:
        os.chdir(sdk_dir)
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(sdk_dir))
        yield
    finally:
        os.chdir(prev)


def sdk_available() -> bool:
    return _ensure_sdk()


def _ensure_sdk() -> bool:
    global _sdk_loaded, _robot, _recv_buf
    if _sdk_loaded:
        return _robot is not None
    sdk_dir = Path(cfg.HITBOT_SDK_DIR)
    hitbot_py = sdk_dir / "HitbotInterface.py"
    if not hitbot_py.is_file():
        logger.warning("未找到 HitbotInterface.py: %s", hitbot_py)
        return False
    _ensure_sdk_log_dir()
    if str(sdk_dir) not in sys.path:
        sys.path.insert(0, str(sdk_dir))
    try:
        from HitbotInterface import HitbotInterface  # type: ignore

        _robot = HitbotInterface(cfg.ROBOT_ID)
        _recv_buf = (c_ubyte * 256)()
        _sdk_loaded = True
        return True
    except Exception as exc:
        logger.warning("加载 Hitbot SDK 失败: %s", exc)
        return False


def _com485_send_raw(frame: bytes) -> int:
    if _robot is None or not hasattr(_robot, "dll"):
        raise RuntimeError("Hitbot DLL 未加载")
    payload = (c_ubyte * len(frame)).from_buffer_copy(frame)
    return int(
        _robot.dll.robot_com485_send(
            c_int(_robot.card_number),
            payload,
            c_ubyte(len(frame)),
        )
    )


def _drain_recv_buffer(*, max_rounds: int = 8) -> None:
    """清掉残留应答，避免总线堆积导致后续 send 返回 -2。"""
    for _ in range(max_rounds):
        if not _com485_recv_raw():
            return


def _com485_send_hint(ret: int) -> str:
    if ret in (-2, -3):
        return (
            "（-2=485 发送超时/下位机未进入收发状态；常见原因："
            "HitbotStudio 未对 485 扩展模块初始化并保存、末端 485 模块未接好、"
            "与 HitbotStudio 同时占用 server.exe；设备运动中可稍后重试）"
        )
    return ""


def _wait_robot_stopped(*, timeout_s: float = 15.0) -> None:
    """robot.initial 后会触发短距离运动，须等停稳再开 485。"""
    if _robot is None or not hasattr(_robot, "is_stop"):
        time.sleep(1.0)
        return
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            if int(_robot.is_stop()) == 1:
                return
        except Exception:
            return
        time.sleep(0.1)


def _setup_com485() -> bool:
    global _com485_ready, _last_error
    if _robot is None:
        return False
    ret = int(_robot.com485_initial(cfg.RS485_BAUD))
    if ret == 2 and hasattr(_robot, "com485_init"):
        init_ret = int(_robot.com485_init())
        logger.info("com485_initial 返回 2，已尝试 com485_init，结果 %s", init_ret)
        ret = int(_robot.com485_initial(cfg.RS485_BAUD))
    if ret != 1:
        hints = {
            2: "485 扩展模块未初始化（请在 HitbotStudio 中完成「485夹爪」初始化并保存到控制器）",
            3: "机械臂未连接",
            4: "波特率过小",
            5: "波特率过大",
            6: "接收超时",
            7: "设定反馈超时",
            8: "非 485 扩展模块（末端未装或未识别 485 模块）",
        }
        hint = hints.get(ret, "见 Hitbot API com485_initial 返回值说明")
        _last_error = f"com485_initial 失败，返回码 {ret}：{hint}"
        logger.error(_last_error)
        return False
    _com485_ready = True
    return True


def _reinit_com485() -> bool:
    """发送失败时尝试重新进入 485 透传模式。"""
    global _com485_ready
    if _robot is None:
        return False
    _com485_ready = False
    _wait_robot_stopped(timeout_s=5.0)
    if hasattr(_robot, "com485_init"):
        init_ret = int(_robot.com485_init())
        logger.info("com485 重连：com485_init 结果 %s", init_ret)
    return _setup_com485()


def _com485_send_with_retry(frame: bytes) -> int:
    """发送 Modbus 帧；-2 时延时重试（电缸行程初始化/回零运动中常见）。"""
    _drain_recv_buffer()
    last_ret = -999
    for attempt in range(cfg.RS485_SEND_RETRY_COUNT):
        if attempt > 0:
            _drain_recv_buffer()
            time.sleep(cfg.RS485_SEND_RETRY_DELAY_S)
        last_ret = _com485_send_raw(frame)
        if last_ret == 1:
            return 1
        if last_ret not in (-2, -3):
            break
    return last_ret


def _com485_send_with_recovery(frame: bytes) -> int:
    ret = _com485_send_with_retry(frame)
    if ret == 1:
        return 1
    if ret in (-2, -3) and _reinit_com485():
        time.sleep(0.2)
        return _com485_send_with_retry(frame)
    return ret


def _com485_recv_raw() -> bytes:
    if _robot is None or not hasattr(_robot, "dll") or _recv_buf is None:
        return b""
    length = int(
        _robot.dll.robot_com485_recv(
            c_int(_robot.card_number),
            _recv_buf,
        )
    )
    if length <= 0:
        return b""
    return bytes(_recv_buf[:length])


def _bind_dll_signatures() -> None:
    if _robot is None or not hasattr(_robot, "dll"):
        return
    dll = _robot.dll
    dll.robot_is_connect.argtypes = [c_int]
    dll.robot_is_connect.restype = c_int


def _close_server_if_possible() -> None:
    if _robot is None or not hasattr(_robot, "close_server"):
        return
    try:
        with _sdk_working_directory():
            _robot.close_server()
    except Exception:
        pass


def _wait_robot_connect() -> bool:
    global _last_error, _last_connect_value
    if _robot is None:
        return False

    deadline = time.monotonic() + cfg.ROBOT_CONNECT_TIMEOUT_S
    last_value = -1
    while time.monotonic() < deadline:
        try:
            last_value = int(_robot.is_connect())
            _last_connect_value = last_value
            if last_value == 1:
                return True
        except OSError as exc:
            _last_error = f"机器人 SDK 未正确初始化：{exc}"
            logger.error(_last_error)
            return False
        except Exception as exc:
            _last_error = f"is_connect 异常：{exc}"
            logger.error(_last_error)
            return False
        time.sleep(0.1)

    _last_error = (
        f"机器人未连接（ROBOT_ID={cfg.ROBOT_ID}，IP={cfg.ROBOT_CONTROLLER_IP}，"
        f"is_connect={last_value}）。"
        "Ping 通后请等待机械臂控制器就绪（约 10–30 秒）再试；"
        "或完全退出 HitbotStudio 后重启 SolidDoser。"
    )
    logger.error(_last_error)
    return False


def _ensure_robot_connected(*, allow_retry: bool = True) -> bool:
    global _com485_ready, _net_port_initialized, _robot_initialized, _last_error
    if _robot is None:
        return False
    if not hasattr(_robot, "net_port_initial"):
        return False

    net_port_ret: int | None = None
    if not _net_port_initialized:
        with _sdk_working_directory():
            net_port_ret = int(_robot.net_port_initial())
        _bind_dll_signatures()
        # 1=成功；0=40000 端口已被占用（可能已有 server 在跑）
        if net_port_ret not in (0, 1):
            _last_error = _net_port_failure_message(net_port_ret)
            logger.error(_last_error)
            return False
        if net_port_ret == 0:
            logger.info("net_port_initial：端口 40000 已占用，尝试连接已有 server")
        else:
            logger.info("net_port_initial 成功，等待机器人上线…")
        _net_port_initialized = True
        time.sleep(0.5)

    if not hasattr(_robot, "dll"):
        _last_error = "Hitbot DLL 未加载，无法连接机器人"
        logger.error(_last_error)
        return False

    if not _wait_robot_connect():
        if allow_retry:
            logger.warning("机器人连接超时，尝试重启 server.exe 后重试")
            _com485_ready = False
            _robot_initialized = False
            _net_port_initialized = False
            _close_server_if_possible()
            time.sleep(1.0)
            return _ensure_robot_connected(allow_retry=False)
        return False

    if not _robot_initialized:
        ret = int(_robot.initial(cfg.ROBOT_GENERATION, cfg.ROBOT_Z_TRAIL_MM))
        if ret != 1:
            logger.warning(
                "robot.initial(%s, %s) 返回 %s",
                cfg.ROBOT_GENERATION,
                cfg.ROBOT_Z_TRAIL_MM,
                ret,
            )
        _robot_initialized = True
        _wait_robot_stopped()

    if not _com485_ready and not _setup_com485():
        return False
    return True


def send_frame(frame: bytes) -> None:
    with _lock:
        if not _ensure_robot_connected():
            raise RuntimeError(_last_error)
        ret = _com485_send_with_recovery(frame)
        if ret != 1:
            raise RuntimeError(f"com485_send 失败，返回码 {ret}{_com485_send_hint(ret)}")


def recv_frame() -> bytes:
    with _lock:
        if _robot is None:
            return b""
        return _com485_recv_raw()


def transact(
    frame: bytes,
    *,
    min_response_len: int = 8,
    timeout_s: float | None = None,
) -> bytes:
    """发送帧并等待应答（Modbus 等请求-应答协议）。"""
    with _lock:
        if not _ensure_robot_connected():
            raise RuntimeError(_last_error)
        ret = _com485_send_with_recovery(frame)
        if ret != 1:
            raise RuntimeError(f"com485_send 失败，返回码 {ret}{_com485_send_hint(ret)}")

        rx = bytearray()
        deadline = time.monotonic() + (
            timeout_s if timeout_s is not None else cfg.RS485_TRANSACT_TIMEOUT_S
        )
        while time.monotonic() < deadline:
            chunk = _com485_recv_raw()
            if chunk:
                rx.extend(chunk)
                if len(rx) >= min_response_len:
                    return bytes(rx)
            time.sleep(cfg.RS485_RECV_POLL_S)
        return bytes(rx)


def stop_robot_move() -> tuple[bool, str]:
    """经 Hitbot SDK 停止机械臂运动（Studio 模式下 SDK 可能未连接）。"""
    with _lock:
        if not _ensure_sdk() or _robot is None:
            return False, "Hitbot SDK 未加载"
        try:
            with _sdk_working_directory():
                ret = int(_robot.stop_move())
            if ret == 1:
                return True, "机械臂运动已停止"
            return False, f"robot_stop_move 返回 {ret}"
        except Exception as exc:
            return False, str(exc)


def reset_connection() -> None:
    global _com485_ready, _net_port_initialized, _robot_initialized, _robot, _sdk_loaded, _recv_buf
    with _lock:
        _com485_ready = False
        _net_port_initialized = False
        _robot_initialized = False
        _recv_buf = None
        if _robot is not None and hasattr(_robot, "close_server"):
            try:
                with _sdk_working_directory():
                    _robot.close_server()
            except Exception:
                pass
        _robot = None
        _sdk_loaded = False


def warmup_async() -> None:
    """启动后在后台预连接机器人，减少首次电爪/移液枪操作等待。"""

    def _run() -> None:
        if not _ensure_sdk():
            return
        if _ensure_robot_connected():
            logger.info(
                "机器人 RS485 预连接成功（ROBOT_ID=%s）",
                cfg.ROBOT_ID,
            )
        else:
            logger.warning("机器人 RS485 预连接未完成：%s", _last_error)

    threading.Thread(
        target=_run,
        name="robot-rs485-warmup",
        daemon=True,
    ).start()
