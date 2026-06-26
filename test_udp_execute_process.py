"""
独立测试：UDP 指令 EXECUTE_PROCESS_FILE
运行前请先启动主程序（main.py），确保监听 UDP 8889。
建议先通过导入或界面加载工艺文件，再运行本脚本。
"""
import argparse
import json
import socket


def send_udp_command(command: str, host: str, port: int, timeout: float = 5.0):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        sock.sendto(command.encode("utf-8"), (host, port))
        data, addr = sock.recvfrom(4096)
        raw = data.decode("utf-8")
        try:
            return json.loads(raw), addr, raw
        except json.JSONDecodeError:
            return {"status": "error", "message": f"non-json response: {raw}"}, addr, raw


def assert_success(resp: dict, expected_cmd: str):
    if resp.get("status") != "success":
        raise AssertionError(f"{expected_cmd} failed: {resp}")
    if resp.get("command") != expected_cmd:
        raise AssertionError(
            f"{expected_cmd} unexpected command field: {resp.get('command')}, full={resp}"
        )


def main():
    parser = argparse.ArgumentParser(description="Test UDP EXECUTE_PROCESS_FILE command.")
    parser.add_argument("--host", default="127.0.0.1", help="UDP server host")
    parser.add_argument("--port", type=int, default=8889, help="UDP server port")
    parser.add_argument("--timeout", type=float, default=6.0, help="UDP recv timeout in seconds")
    args = parser.parse_args()

    execute_cmd = "EXECUTE_PROCESS_FILE"
    print(f"send: {execute_cmd}")
    exec_resp, exec_from, _ = send_udp_command(
        execute_cmd, args.host, args.port, args.timeout
    )
    print(f"recv from {exec_from}: {exec_resp}")
    assert_success(exec_resp, "EXECUTE_PROCESS_FILE")
    print("PASS: EXECUTE_PROCESS_FILE 返回成功。")


if __name__ == "__main__":
    main()
