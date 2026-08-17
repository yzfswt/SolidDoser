"""上位机业务动作审计日志：即时写入应用日志，并可选在退出时落一份会话摘要。"""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from pathlib import Path

from Common.AppLogging import log_dir

_action_log = logging.getLogger("soliddoser.action")


class ActionLogger:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._lines: list[str] = []
        self._persisted = False

    def record(self, message: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} | {message}"
        with self._lock:
            self._lines.append(line)
        _action_log.info("%s", message)

    def persist(self) -> Path | None:
        """退出时再写一份会话摘要到 日志/（便于人工翻看本次运行）。"""
        with self._lock:
            if self._persisted:
                return None
            self._persisted = True
            lines_copy = list(self._lines)

        out = log_dir()
        out.mkdir(parents=True, exist_ok=True)
        fname = datetime.now().strftime("%Y%m%d_%H%M%S_%f.txt")
        path = out / fname
        text = "\n".join(lines_copy) + ("\n" if lines_copy else "")
        path.write_text(text, encoding="utf-8")
        return path


_logger: ActionLogger | None = None
_logger_lock = threading.Lock()


def get_action_logger() -> ActionLogger:
    global _logger
    with _logger_lock:
        if _logger is None:
            _logger = ActionLogger()
        return _logger
