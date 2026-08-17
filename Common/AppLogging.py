"""应用日志：按日轮转、按月归档压缩、超过 6 个月自动删除。

目录结构：
  日志/
    soliddoser.log          # 当天活动日志
    soliddoser.log.YYYY-MM-DD  # TimedRotating 切出的历史日文件
    归档/
      YYYY-MM.zip           # 按月归档（内含若干 .log / .txt）
"""
from __future__ import annotations

import logging
import re
import threading
import zipfile
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR_NAME = "日志"
ARCHIVE_DIR_NAME = "归档"
ACTIVE_LOG_NAME = "soliddoser.log"

# 保留时长：超过即删除（活动文件、切分文件、归档 zip）
RETENTION_DAYS = 180  # 约 6 个月
# 日切分文件超过该天数后打入月归档 zip，并删除原文件
ARCHIVE_AFTER_DAYS = 7

_DATE_SUFFIX_RE = re.compile(r"\.(\d{4}-\d{2}-\d{2})$")
_ZIP_MONTH_RE = re.compile(r"^(\d{4}-\d{2})\.zip$", re.IGNORECASE)
_ACTION_TXT_RE = re.compile(r"^(\d{8})_\d{6}_\d+\.txt$")

_setup_done = False
_setup_lock = threading.Lock()
_maint_timer: threading.Timer | None = None
_maint_interval_s = 24 * 3600


def log_dir() -> Path:
    return PROJECT_ROOT / LOG_DIR_NAME


def archive_dir() -> Path:
    return log_dir() / ARCHIVE_DIR_NAME


def setup_app_logging(*, level: int = logging.INFO) -> Path:
    """配置控制台 + 按日滚动文件日志，并启动维护任务。可重复调用（仅首次生效）。"""
    global _setup_done
    with _setup_lock:
        if _setup_done:
            return log_dir()
        _setup_done = True

        out = log_dir()
        out.mkdir(parents=True, exist_ok=True)
        archive_dir().mkdir(parents=True, exist_ok=True)

        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        root = logging.getLogger()
        root.setLevel(level)

        # 避免重复 basicConfig / 多次 handler
        for h in list(root.handlers):
            root.removeHandler(h)

        console = logging.StreamHandler()
        console.setLevel(level)
        console.setFormatter(fmt)
        root.addHandler(console)

        file_handler = TimedRotatingFileHandler(
            filename=str(out / ACTIVE_LOG_NAME),
            when="midnight",
            interval=1,
            backupCount=0,  # 保留策略由本模块维护
            encoding="utf-8",
            utc=False,
        )
        file_handler.suffix = "%Y-%m-%d"
        file_handler.setLevel(level)
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)

        logging.getLogger("soliddoser").setLevel(level)
        run_log_maintenance()
        _schedule_maintenance()
        logging.getLogger("soliddoser.logging").info(
            "日志已启用：目录=%s，归档=%s，保留=%s 天，归档阈值=%s 天",
            out,
            archive_dir(),
            RETENTION_DAYS,
            ARCHIVE_AFTER_DAYS,
        )
        return out


def run_log_maintenance() -> None:
    """归档过期日日志，并删除超过保留期的文件/归档。"""
    try:
        base = log_dir()
        base.mkdir(parents=True, exist_ok=True)
        arch = archive_dir()
        arch.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        _archive_old_daily_files(base, arch, now)
        _archive_old_action_txt(base, arch, now)
        _purge_expired(base, arch, now)
    except Exception:  # noqa: BLE001
        logging.getLogger("soliddoser.logging").exception("日志维护失败")


def _schedule_maintenance() -> None:
    global _maint_timer

    def _tick() -> None:
        run_log_maintenance()
        _schedule_maintenance()

    _maint_timer = threading.Timer(_maint_interval_s, _tick)
    _maint_timer.daemon = True
    _maint_timer.start()


def stop_log_maintenance() -> None:
    global _maint_timer
    if _maint_timer is not None:
        _maint_timer.cancel()
        _maint_timer = None


def _file_date_from_name(path: Path) -> datetime | None:
    m = _DATE_SUFFIX_RE.search(path.name)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d")
        except ValueError:
            return None
    m2 = _ACTION_TXT_RE.match(path.name)
    if m2:
        try:
            return datetime.strptime(m2.group(1), "%Y%m%d")
        except ValueError:
            return None
    return None


def _archive_old_daily_files(base: Path, arch: Path, now: datetime) -> None:
    cutoff = now - timedelta(days=ARCHIVE_AFTER_DAYS)
    for path in base.iterdir():
        if not path.is_file():
            continue
        if path.name == ACTIVE_LOG_NAME:
            continue
        if not path.name.startswith(ACTIVE_LOG_NAME + "."):
            continue
        file_day = _file_date_from_name(path)
        if file_day is None or file_day.date() >= cutoff.date():
            continue
        _add_to_month_zip(arch, file_day, path)
        try:
            path.unlink()
        except OSError:
            logging.getLogger("soliddoser.logging").warning("无法删除已归档日日志: %s", path)


def _archive_old_action_txt(base: Path, arch: Path, now: datetime) -> None:
    """兼容旧 ActionLogger 退出时写出的 txt，超过 ARCHIVE_AFTER_DAYS 打入月归档。"""
    cutoff = now - timedelta(days=ARCHIVE_AFTER_DAYS)
    for path in base.iterdir():
        if not path.is_file() or path.suffix.lower() != ".txt":
            continue
        file_day = _file_date_from_name(path)
        if file_day is None or file_day.date() >= cutoff.date():
            continue
        _add_to_month_zip(arch, file_day, path)
        try:
            path.unlink()
        except OSError:
            logging.getLogger("soliddoser.logging").warning("无法删除已归档审计日志: %s", path)


def _add_to_month_zip(arch: Path, file_day: datetime, path: Path) -> None:
    zip_path = arch / f"{file_day.strftime('%Y-%m')}.zip"
    arcname = path.name
    with zipfile.ZipFile(zip_path, mode="a", compression=zipfile.ZIP_DEFLATED) as zf:
        # 同名跳过，避免重复追加
        if arcname in zf.namelist():
            arcname = f"{file_day.strftime('%Y%m%d')}_{path.name}"
        zf.write(path, arcname=arcname)


def _purge_expired(base: Path, arch: Path, now: datetime) -> None:
    expire_before = now - timedelta(days=RETENTION_DAYS)

    for path in base.iterdir():
        if not path.is_file():
            continue
        if path.name == ACTIVE_LOG_NAME:
            continue
        file_day = _file_date_from_name(path)
        if file_day is not None and file_day < expire_before:
            try:
                path.unlink()
            except OSError:
                pass
            continue
        # 无日期后缀：按 mtime
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            continue
        if mtime < expire_before:
            try:
                path.unlink()
            except OSError:
                pass

    for path in arch.iterdir():
        if not path.is_file():
            continue
        m = _ZIP_MONTH_RE.match(path.name)
        if m:
            try:
                month_start = datetime.strptime(m.group(1) + "-01", "%Y-%m-%d")
            except ValueError:
                month_start = None
            if month_start is not None and month_start < expire_before:
                try:
                    path.unlink()
                except OSError:
                    pass
                continue
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            continue
        if mtime < expire_before:
            try:
                path.unlink()
            except OSError:
                pass
