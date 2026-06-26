"""
独立测试：UDP 指令 IMPORT_PROCESS_FILE(path)
运行前请先启动主程序（main.py），确保监听 UDP 8889。
"""
import argparse
import json
import socket
import tempfile
from pathlib import Path


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
    parser = argparse.ArgumentParser(description="Test UDP IMPORT_PROCESS_FILE command.")
    parser.add_argument("--host", default="127.0.0.1", help="UDP server host")
    parser.add_argument("--port", type=int, default=8889, help="UDP server port")
    parser.add_argument(
        "--process-file",
        default="",
        help="Existing process file path. If omitted, a temp file is created.",
    )
    parser.add_argument("--timeout", type=float, default=6.0, help="UDP recv timeout in seconds")
    args = parser.parse_args()

    temp_file = None
    if args.process_file:
        process_path = Path(args.process_file)
    else:
        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        )
        temp_file.write("# auto generated test process\nS WAIT(1)\n")
        temp_file.flush()
        process_path = Path(temp_file.name)

    try:
        import_cmd = f"IMPORT_PROCESS_FILE({process_path.as_posix()})"
        print(f"send: {import_cmd}")
        import_resp, import_from, _ = send_udp_command(
            import_cmd, args.host, args.port, args.timeout
        )
        print(f"recv from {import_from}: {import_resp}")
        assert_success(import_resp, "IMPORT_PROCESS_FILE")
        print("PASS: IMPORT_PROCESS_FILE 返回成功。")
    finally:
        if temp_file is not None:
            try:
                Path(temp_file.name).unlink(missing_ok=True)
            except Exception:
                pass


if __name__ == "__main__":
    main()
