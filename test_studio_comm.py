"""模拟 HitbotStudio 客户端「手动请求」，测试与 SolidDoser 的 TCP 通讯。

用法（先另开终端运行 main_soliddoser.py）：
    python test_studio_comm.py
    python test_studio_comm.py --cmd 1
"""
from __future__ import annotations

import argparse
import socket
import sys

HOST = "127.0.0.1"
PORT = 6000
ROBOT_ID = 77
HEADER = "LabClient01"  # 与 Studio 手动请求里第一个字段一致即可；SolidDoser 会原样回显


def build_request(header: str, cmd: int, status: int, param1: int, err: int) -> str:
    return (
        f"{header},{ROBOT_ID},globalvars,"
        f"int-cmd#{cmd},int-status#{status},int-param1#{param1},int-err_code#{err};"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="测试 SolidDoser Studio TCP 通讯")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--header", default=HEADER, help="客户端 ID，与 Studio 手动请求一致")
    parser.add_argument("--cmd", type=int, default=0)
    parser.add_argument("--status", type=int, default=0)
    parser.add_argument("--param1", type=int, default=0)
    parser.add_argument("--err", type=int, default=0)
    args = parser.parse_args()

    req = build_request(args.header, args.cmd, args.status, args.param1, args.err)
    print("发送:", req)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((args.host, args.port))
        sock.sendall(req.encode("utf-8"))
        resp = sock.recv(4096).decode("utf-8", errors="replace")
        sock.close()
    except OSError as exc:
        print(f"连接失败: {exc}")
        print("请先运行: python main_soliddoser.py")
        return 1

    print("接收:", repr(resp))
    if not (resp.endswith(";") or resp.endswith(";\r\n") or resp.endswith("\r\n")):
        print("警告: 响应结尾非常规")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
