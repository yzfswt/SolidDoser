import os
import socket
import datetime
import sqlite3

from config import create_llm_client, DB_PATH


LLM_CLIENT = create_llm_client()


def read_txt_file(file_path):
    """读取文本文件内容

    Args:
        file_path: 文件路径

    Returns:
        str: 文件内容
    """
    if not os.path.exists(file_path):
        return f"错误：文本文件 {file_path} 不存在"
    try:
        # 读取文本文件，限制大小以防过长
        max_chars = 5000  # 根据需要调整
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read(max_chars)
            # 检查文件是否超过限制
            if len(content) == max_chars:
                content += "\n...\n（文件内容过长，已截断）"
        return f"文本文件内容：\n{content}"
    except UnicodeDecodeError:
        # 如果UTF-8解码失败，尝试其他编码
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read(max_chars)
                if len(content) == max_chars:
                    content += "\n...\n（文件内容过长，已截断）"
            return f"文本文件内容：\n{content}"
        except Exception as e:
            return f"读取文本文件时出错：{str(e)}"
    except Exception as e:
        return f"读取文本文件时出错：{str(e)}"


def save_process_file(filename, content):
    """保存工艺文件到数据库

    Args:
        filename: 文件名
        content: 文件内容

    Returns:
        int: 保存的文件ID
    """
    conn = sqlite3.connect(DB_PATH)
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


def UDP_sendcmd():
    # 创建UDP套接字
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # 目标地址（本地回环+程序B监听端口）
    target_addr = ("127.0.0.1", 8888)

    send_data = "OK"
    # 发送数据
    udp_socket.sendto(send_data.encode("utf-8"), target_addr)
    print("已发送数据")


def generate_equipment_instructions(experiment_workflow):
    """生成设备控制指令（流式返回）

    Args:
        llm_client: 大模型客户端实例
        experiment_workflow: 实验工作流参数

    Yields:
        str: 生成的设备控制指令的一部分
    """
    # 文件路径

    # 获取当前脚本文件的绝对路径目录
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 拼接文件名
    standard_flow_path = os.path.join(current_dir, "标准控制指令流程_new.txt")
    optimization_params_path = os.path.join(current_dir, "优化参数输入.txt")

    # 读取文件内容
    standard_flow_content = read_txt_file(standard_flow_path)
    optimization_params_content = read_txt_file(optimization_params_path)

    # 构建messages列表
    messages = [
        ("system", "你是一个了解化学流程和编程语言的助手，需要你根据给定的优化参数，生成符合指令集定义的设备控制指令。"),
        ("user", f'''请参考以下文件内容回答问题：\n\n{standard_flow_content}\n\n{optimization_params_content}\n\n
            请你先学习优化参数输入文档和这份标准控制指令流程之间的对应关系，标准控制流程是依照优化参数输入而生成的。
            然后根据你学习到的对应关系，给出以下优化参数输入的标准控制流程指令：
            优化参数如下：{experiment_workflow}''')
    ]

    # 调用大模型生成指令（流式）
    content = ""
    for chunk in LLM_CLIENT.stream(messages):
        content += chunk.content
        print(chunk.content, end="")

    # 返回完整内容（如果需要）
    return content.strip()


def handle_generate_instructions(experiment_plan):
    """处理实验参数，激活实验指令到数据库，给实验UDP发送数据指令"""
    result_content = generate_equipment_instructions(experiment_plan)
    save_process_file("control_instructions", result_content)
    UDP_sendcmd()