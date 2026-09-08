"""工艺文件 SQLite 访问（底层库见 Common.LocalDatabase）。"""
from __future__ import annotations

import datetime
import sys

from Common.LocalDatabase import connect, get_db_path, init_schema

# 兼容旧调用方打印 / 脚本
db_path = str(get_db_path())


def init_database():
    """初始化数据库目录、连接和表结构（可重复执行）。"""
    global db_path
    path = init_schema()
    db_path = str(path)
    return path


def save_process_file(filename, content):
    """保存工艺文件到数据库，返回文件 ID；失败返回 None。"""
    conn = connect()
    try:
        conn.execute("BEGIN")
        conn.execute("UPDATE process_files SET is_active = 0")
        import_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.execute(
            """
            INSERT INTO process_files (filename, content, import_time, is_active)
            VALUES (?, ?, ?, 1)
            """,
            (filename, content, import_time),
        )
        file_id = cur.lastrowid
        conn.commit()
        return file_id
    except Exception as e:
        conn.rollback()
        print(f"❌ 保存工艺文件失败：{e}")
        return None
    finally:
        conn.close()


def get_active_process_file():
    """获取当前活跃工艺文件 → (filename, content)；无则 (None, None)。"""
    conn = connect()
    try:
        cur = conn.execute(
            "SELECT filename, content FROM process_files WHERE is_active = 1"
        )
        result = cur.fetchone()
        if result:
            return result["filename"], result["content"]
        print("⚠️  没有找到活跃的工艺文件")
        return (None, None)
    except Exception as e:
        print(f"❌ 获取活跃工艺文件失败：{e}")
        return (None, None)
    finally:
        conn.close()


def get_process_file_by_id(file_id):
    """根据 ID 获取工艺文件 → (filename, content)。"""
    conn = connect()
    try:
        cur = conn.execute(
            "SELECT filename, content FROM process_files WHERE id = ?",
            (file_id,),
        )
        result = cur.fetchone()
        if result:
            return result["filename"], result["content"]
        print(f"⚠️  没有找到ID为{file_id}的工艺文件")
        return (None, None)
    except Exception as e:
        print(f"❌ 获取工艺文件失败：{e}")
        return (None, None)
    finally:
        conn.close()


def set_active_file(file_id):
    """设置指定文件为活跃状态。"""
    conn = connect()
    try:
        conn.execute("BEGIN")
        conn.execute("UPDATE process_files SET is_active = 0")
        cur = conn.execute(
            "UPDATE process_files SET is_active = 1 WHERE id = ?",
            (file_id,),
        )
        if cur.rowcount == 0:
            conn.rollback()
            print(f"⚠️  没有找到ID为{file_id}的工艺文件")
            return False
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"❌ 设置活跃文件失败：{e}")
        return False
    finally:
        conn.close()


def _configure_stdio_utf8_windows():
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def main():
    """作为独立脚本运行：先初始化数据库再退出。"""
    _configure_stdio_utf8_windows()
    try:
        path = init_database()
        print(f"数据库初始化完成: {path.resolve()}")
        return 0
    except Exception as e:
        print(f"数据库初始化失败: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
