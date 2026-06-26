import sqlite3
import datetime
import os
import sys


def _default_db_path():
    """开发环境沿用 E 盘路径；PyInstaller 打包后使用本机可写目录，避免目标机无 E 盘失败。"""
    override = os.environ.get("RESIN_PROCESS_DB")
    if override:
        return os.path.normpath(override)
    if getattr(sys, "frozen", False):
        base = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "ResinWorkstation",
        )
        return os.path.join(base, "process_db.db")
    return os.path.join("E:\\AI_PJDataBase", "process_db.db")


# 数据库文件路径（与主程序、InitDatabase.exe 共用同一逻辑）
db_path = _default_db_path()


def init_database():
    """初始化数据库目录、连接和表结构（可重复执行，表已存在则跳过创建）"""
    db_dir = os.path.dirname(os.path.abspath(db_path))
    os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建工艺文件表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS process_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        content TEXT NOT NULL,
        import_time TIMESTAMP NOT NULL,
        is_active INTEGER DEFAULT 0
    )
    ''')
    
    conn.commit()
    conn.close()

def save_process_file(filename, content):
    """保存工艺文件到数据库
    
    Args:
        filename: 文件名
        content: 文件内容
    
    Returns:
        int: 保存的文件ID
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 开始事务
        conn.execute('BEGIN TRANSACTION')
        
        # 将所有文件设为非活跃
        cursor.execute('UPDATE process_files SET is_active = 0')
        
        # 插入新文件，设置为活跃状态
        import_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
        INSERT INTO process_files (filename, content, import_time, is_active)
        VALUES (?, ?, ?, 1)
        ''', (filename, content, import_time))
        
        file_id = cursor.lastrowid
        
        # 提交事务
        conn.commit()
        return file_id
    except Exception as e:
        # 回滚事务
        conn.rollback()
        print(f"❌ 保存工艺文件失败：{e}")
        return None
    finally:
        conn.close()

def get_active_process_file():
    """获取当前活跃的工艺文件
    
    Returns:
        tuple: (filename, content)，如果没有活跃文件返回(None, None)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT filename, content FROM process_files WHERE is_active = 1
        ''')
        result = cursor.fetchone()
        
        if result:
            return result
        else:
            print("⚠️  没有找到活跃的工艺文件")
            return (None, None)
    except Exception as e:
        print(f"❌ 获取活跃工艺文件失败：{e}")
        return (None, None)
    finally:
        conn.close()

def get_process_file_by_id(file_id):
    """根据ID获取工艺文件
    
    Args:
        file_id: 文件ID
    
    Returns:
        tuple: (filename, content)，如果没有找到返回(None, None)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT filename, content FROM process_files WHERE id = ?
        ''', (file_id,))
        result = cursor.fetchone()
        
        if result:
            return result
        else:
            print(f"⚠️  没有找到ID为{file_id}的工艺文件")
            return (None, None)
    except Exception as e:
        print(f"❌ 获取工艺文件失败：{e}")
        return (None, None)
    finally:
        conn.close()

def set_active_file(file_id):
    """设置指定文件为活跃状态
    
    Args:
        file_id: 文件ID
    
    Returns:
        bool: 是否设置成功
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 开始事务
        conn.execute('BEGIN TRANSACTION')
        
        # 将所有文件设为非活跃
        cursor.execute('UPDATE process_files SET is_active = 0')
        
        # 设置指定文件为活跃
        cursor.execute('UPDATE process_files SET is_active = 1 WHERE id = ?', (file_id,))
        
        # 检查是否有行被更新
        if cursor.rowcount == 0:
            conn.rollback()
            print(f"⚠️  没有找到ID为{file_id}的工艺文件")
            return False
        
        # 提交事务
        conn.commit()
        return True
    except Exception as e:
        # 回滚事务
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
        init_database()
        print(f"数据库初始化完成: {os.path.abspath(db_path)}")
        return 0
    except Exception as e:
        print(f"数据库初始化失败: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
