"""
独立测试：UDP 指令 GET_PROCESS_EXECUTION_STATE（工艺流程执行状态查询）

运行前请先启动主程序（main.py），确保监听 UDP 8889。

默认：发送一次查询，校验 JSON 结构与 status/command；executing 可为 True 或 False。

若需在「正在执行工艺」时强制断言，可先启动工艺执行，再使用：
  python test_udp_get_process_execution_state.py --expect-executing
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


def assert_response_shape(resp: dict):
    cmd = "GET_PROCESS_EXECUTION_STATE"
    if resp.get("status") != "success":
        raise AssertionError(f"{cmd} failed: {resp}")
    if resp.get("command") != cmd:
        raise AssertionError(
            f"{cmd} unexpected command field: {resp.get('command')}, full={resp}"
        )
    if "executing" not in resp or not isinstance(resp["executing"], bool):
        raise AssertionError(f"missing or invalid 'executing' (bool): {resp}")
    for key in ("process_name", "current_step", "total_steps"):
        if key not in resp:
            raise AssertionError(f"missing key '{key}': {resp}")
    if not isinstance(resp["process_name"], str):
        raise AssertionError(f"'process_name' must be str: {resp}")
    if not isinstance(resp["current_step"], int):
        raise AssertionError(f"'current_step' must be int: {resp}")
    if not isinstance(resp["total_steps"], int):
        raise AssertionError(f"'total_steps' must be int: {resp}")


def assert_idle_consistency(resp: dict):
    """executing 为 False 时，服务端约定 name 与步数为 0。"""
    if resp["executing"]:
        return
    if resp["process_name"] != "" or resp["current_step"] != 0 or resp["total_steps"] != 0:
        raise AssertionError(
            "when executing=False, expect process_name='', current_step=0, total_steps=0; "
            f"got {resp}"
        )


def assert_executing_consistency(resp: dict):
    """executing 为 True 时，校验步数合理（启动瞬间可能出现 total_steps=0）。"""
    if not resp["executing"]:
        return
    total = resp["total_steps"]
    current = resp["current_step"]
    if total < 0 or current < 0:
        raise AssertionError(f"negative step counts: {resp}")
    if total > 0 and current > total:
        raise AssertionError(f"current_step out of range [0,{total}]: {resp}")


def main():
    parser = argparse.ArgumentParser(
        description="Test UDP GET_PROCESS_EXECUTION_STATE command."
    )
    parser.add_argument("--host", default="127.0.0.1", help="UDP server host")
    parser.add_argument("--port", type=int, default=8889, help="UDP server port")
    parser.add_argument("--timeout", type=float, default=6.0, help="UDP recv timeout in seconds")
    parser.add_argument(
        "--expect-executing",
        action="store_true",
        help="要求本次查询 executing 必须为 True（需工艺正在跑）",
    )
    args = parser.parse_args()

    query = "GET_PROCESS_EXECUTION_STATE"
    print(f"send: {query}")
    resp, addr, _ = send_udp_command(query, args.host, args.port, args.timeout)
    print(f"recv from {addr}: {resp}")

    assert_response_shape(resp)

    if args.expect_executing and not resp["executing"]:
        raise AssertionError(
            "expected executing=True (--expect-executing). "
            "请先触发 EXECUTE_PROCESS_FILE 或界面执行，并在运行中重试。"
        )

    if resp["executing"]:
        assert_executing_consistency(resp)
    else:
        assert_idle_consistency(resp)

    print("PASS: GET_PROCESS_EXECUTION_STATE 响应格式与约定一致。")


if __name__ == "__main__":
    main()
