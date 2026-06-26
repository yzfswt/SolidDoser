"""上位机业务动作审计日志：内存累积，退出时写入项目根/日志/ 目录。"""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR_NAME = "日志"


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

    def persist(self) -> Path | None:
        with self._lock:
            if self._persisted:
                return None
            self._persisted = True
            lines_copy = list(self._lines)

        log_dir = PROJECT_ROOT / LOG_DIR_NAME
        log_dir.mkdir(parents=True, exist_ok=True)
        fname = datetime.now().strftime("%Y%m%d_%H%M%S_%f.txt")
        path = log_dir / fname
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
