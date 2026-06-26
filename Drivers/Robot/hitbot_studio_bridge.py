"""SolidDoser 侧 TCP 服务：响应 HitbotStudio 客户端模块的 globalvars 轮询并下发 cmd。"""
from __future__ import annotations

import logging
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from Drivers.Robot import robot_config as cfg
from Drivers.Robot.hitbot_studio_protocol import (
    build_globalvars_response,
    build_set_var_response,
    parse_int_var,
    parse_message,
)

logger = logging.getLogger("soliddoser.hitbot_studio")

_bridge: Optional["HitbotStudioBridge"] = None


@dataclass
class _PendingCommand:
    cmd: int
    param1: int
    phase: str = "dispatch"
    done: threading.Event = field(default_factory=threading.Event)
    result_ok: bool = False
    result_message: str = ""


class HitbotStudioBridge:
    """单例：后台 TCP 服务 + 阻塞式 run_command。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._server_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._running = False
        self._pending: Optional[_PendingCommand] = None
        self._last_studio_vars: Dict[str, int] = {
            cfg.VAR_CMD: 0,
            cfg.VAR_STATUS: cfg.STATUS_IDLE,
            cfg.VAR_PARAM1: 0,
            cfg.VAR_ERR_CODE: 0,
        }

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        self._stop.clear()
        self._server_thread = threading.Thread(
            target=self._serve_forever,
            name="HitbotStudioBridge",
            daemon=True,
        )
        self._server_thread.start()
        self._running = True
        logger.info(
            "HitbotStudio bridge listening on %s:%s (header=%s)",
            cfg.STUDIO_TCP_HOST,
            cfg.STUDIO_TCP_PORT,
            cfg.STUDIO_CLIENT_HEADER,
        )

    def stop(self) -> None:
        self._stop.set()
        self._running = False

    def run_command(
        self,
        cmd: int,
        param1: int = 0,
        timeout_s: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """下发 cmd，阻塞至 Studio 回报 status=2/3。"""
        if cmd == cfg.RobotCmd.NONE:
            return False, "无效命令号 0"

        timeout = timeout_s if timeout_s is not None else cfg.STUDIO_COMMAND_TIMEOUT_S
        pending = _PendingCommand(cmd=cmd, param1=param1)

        with self._lock:
            if self._pending is not None:
                return False, "上一条机器人指令尚未结束，请稍后再试。"
            self._pending = pending

        if not self._running:
            self.start()
            time.sleep(0.2)

        if not pending.done.wait(timeout=timeout):
            with self._lock:
                if self._pending is pending:
                    self._pending = None
            return (
                False,
                f"等待 Studio 超时（{timeout:g}s）。请确认 Server.exe、Studio 已连接机械臂，"
                f"且 F99 调度流程在运行，客户端指向 127.0.0.1:{cfg.STUDIO_TCP_PORT}。",
            )

        with self._lock:
            if self._pending is pending:
                self._pending = None

        if pending.result_ok:
            return True, pending.result_message or "Studio 子流程执行完成。"
        return False, pending.result_message or "Studio 子流程执行失败。"

    def cancel_pending(self, reason: str = "已停止") -> bool:
        """中止当前 run_command 等待（不保证 Studio 侧运动已停）。"""
        with self._lock:
            pending = self._pending
            if pending is None:
                return False
            pending.result_ok = False
            pending.result_message = reason
            pending.done.set()
            self._pending = None
            return True

    def _serve_forever(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((cfg.STUDIO_TCP_HOST, cfg.STUDIO_TCP_PORT))
            sock.listen(2)
            sock.settimeout(1.0)
            while not self._stop.is_set():
                try:
                    conn, addr = sock.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                logger.debug("Studio client connected from %s", addr)
                threading.Thread(
                    target=self._handle_client,
                    args=(conn,),
                    daemon=True,
                ).start()
        except OSError as exc:
            logger.error(
                "无法启动 Studio TCP 服务 %s:%s — %s",
                cfg.STUDIO_TCP_HOST,
                cfg.STUDIO_TCP_PORT,
                exc,
            )
        finally:
            sock.close()
            self._running = False

    def _handle_client(self, conn: socket.socket) -> None:
        with conn:
            conn.settimeout(30.0)
            buffer = ""
            try:
                while not self._stop.is_set():
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    buffer += chunk.decode("utf-8", errors="replace")
                    while ";" in buffer:
                        msg_text, buffer = buffer.split(";", 1)
                        msg_text = msg_text.strip()
                        if not msg_text:
                            continue
                        response = self._on_message(msg_text + ";")
                        if response:
                            conn.sendall(response.encode("utf-8"))
            except (ConnectionResetError, socket.timeout, OSError):
                pass

    def _parse_studio_vars(self, msg) -> tuple[int, int, int, int]:
        return (
            parse_int_var(msg, cfg.WIRE_VAR_CMD, aliases=(cfg.VAR_CMD,)),
            parse_int_var(msg, cfg.WIRE_VAR_STATUS, aliases=(cfg.VAR_STATUS,)),
            parse_int_var(msg, cfg.WIRE_VAR_PARAM1, aliases=(cfg.VAR_PARAM1,)),
            parse_int_var(msg, cfg.WIRE_VAR_ERR_CODE, aliases=(cfg.VAR_ERR_CODE,)),
        )

    def _wire_vars(
        self,
        cmd: int,
        status: int,
        param1: int,
        err_code: int,
    ) -> Dict[str, int | str]:
        return {
            cfg.WIRE_VAR_CMD: cmd,
            cfg.WIRE_VAR_STATUS: status,
            cfg.WIRE_VAR_PARAM1: param1,
            cfg.WIRE_VAR_ERR_CODE: err_code,
        }

    def _response_header(self, msg) -> str:
        if cfg.STUDIO_CLIENT_HEADER:
            return cfg.STUDIO_CLIENT_HEADER
        return msg.header or "SolidDoser0"

    def _on_message(self, raw: str) -> str:
        msg = parse_message(raw)
        if msg is None:
            return ""
        if msg.kind != "globalvars":
            return ""

        studio_cmd, studio_status, studio_param1, studio_err = self._parse_studio_vars(msg)

        with self._lock:
            self._last_studio_vars = {
                cfg.VAR_CMD: studio_cmd,
                cfg.VAR_STATUS: studio_status,
                cfg.VAR_PARAM1: studio_param1,
                cfg.VAR_ERR_CODE: studio_err,
            }
            pending = self._pending
            response_vars = self._build_response_vars(
                pending, studio_cmd, studio_status, studio_param1, studio_err
            )
            self._check_pending_done(pending, studio_cmd, studio_status, studio_err)

        return self._format_response(msg, response_vars)

    def _format_response(self, msg, response_vars: Dict[str, int | str]) -> str:
        mode = getattr(cfg, "STUDIO_RESPONSE_MODE", "globalvars_no_semi")
        if mode == "set_var_server":
            return build_set_var_response(response_vars)
        terminator_map = {
            "globalvars_no_semi": "",
            "globalvars_semi": ";",
            "globalvars_semi_crlf": ";\r\n",
        }
        terminator = terminator_map.get(mode, "")
        return build_globalvars_response(
            self._response_header(msg),
            cfg.ROBOT_ID,
            response_vars,
            variable_order=msg.variable_order,
            terminator=terminator,
        )

    def _build_response_vars(
        self,
        pending: Optional[_PendingCommand],
        studio_cmd: int,
        studio_status: int,
        studio_param1: int,
        studio_err: int,
    ) -> Dict[str, int | str]:
        if pending is None:
            return self._wire_vars(0, studio_status, studio_param1, studio_err)

        if pending.phase == "dispatch":
            pending.phase = "wait_done"
            return self._wire_vars(
                pending.cmd, cfg.STATUS_RUNNING, pending.param1, 0
            )

        return self._wire_vars(studio_cmd, studio_status, studio_param1, studio_err)

    def _check_pending_done(
        self,
        pending: Optional[_PendingCommand],
        studio_cmd: int,
        studio_status: int,
        studio_err: int,
    ) -> None:
        if pending is None or pending.phase != "wait_done":
            return
        if studio_status == cfg.STATUS_OK and studio_cmd == cfg.RobotCmd.NONE:
            pending.result_ok = True
            pending.result_message = "执行成功"
            pending.done.set()
        elif studio_status == cfg.STATUS_FAIL:
            pending.result_ok = False
            pending.result_message = f"Studio 报错 err_code={studio_err}"
            pending.done.set()


def get_studio_bridge() -> HitbotStudioBridge:
    global _bridge
    if _bridge is None:
        _bridge = HitbotStudioBridge()
    return _bridge
