"""测试主系统试剂瓶进/出料 UDP。

运行前请先启动 main.py 或 main_soliddoser.py。

进料（主系统 → 加样 8890）：
  python test_udp_bottle_feed.py request --request-id t1
  python test_udp_bottle_feed.py done --request-id t1

出料完成（主系统 → 加样 8890，需先在自动页点「试剂瓶出料」）：
  python test_udp_bottle_feed.py discharge-done --request-id <出料请求id>

模拟主系统监听出料请求（加样 → 主系统 8891）：
  python test_udp_bottle_feed.py listen-main
"""
from __future__ import annotations

import argparse
import json
import socket
import uuid

from Common.HostBottleFeedConfig import (
    BOTTLE_FEED_UDP_HOST,
    BOTTLE_FEED_UDP_PORT,
    CMD_BOTTLE_DISCHARGE_DONE,
    CMD_BOTTLE_DISCHARGE_REQUEST,
    CMD_BOTTLE_FEED_DONE,
    CMD_BOTTLE_FEED_REQUEST,
    HOST_MAIN_UDP_HOST,
    HOST_MAIN_UDP_PORT,
)


def send_cmd(payload: dict, host: str, port: int, timeout: float) -> dict:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        sock.sendto(json.dumps(payload, ensure_ascii=False).encode("utf-8"), (host, port))
        data, _addr = sock.recvfrom(4096)
        raw = data.decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"status": "error", "message": f"non-json: {raw}"}


def listen_main(host: str, port: int) -> None:
    """模拟主系统：收出料请求后自动回 BOTTLE_DISCHARGE_DONE。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f"模拟主系统监听 {host}:{port} …")
    while True:
        data, addr = sock.recvfrom(4096)
        raw = data.decode("utf-8")
        print(f"← from {addr}: {raw}")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if payload.get("cmd") != CMD_BOTTLE_DISCHARGE_REQUEST:
            continue
        rid = str(payload.get("request_id") or "")
        done = {"cmd": CMD_BOTTLE_DISCHARGE_DONE, "request_id": rid}
        # 出料完成发到加样系统 8890
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as out:
            out.settimeout(5.0)
            out.sendto(
                json.dumps(done, ensure_ascii=False).encode("utf-8"),
                (BOTTLE_FEED_UDP_HOST, BOTTLE_FEED_UDP_PORT),
            )
            try:
                resp, _ = out.recvfrom(4096)
                print(f"→ DONE 回执: {resp.decode('utf-8')}")
            except OSError as exc:
                print(f"→ DONE 无回执: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test bottle feed/discharge UDP.")
    parser.add_argument(
        "action",
        choices=("request", "done", "discharge-done", "listen-main"),
    )
    parser.add_argument("--host", default=BOTTLE_FEED_UDP_HOST)
    parser.add_argument("--port", type=int, default=BOTTLE_FEED_UDP_PORT)
    parser.add_argument("--request-id", default="")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    if args.action == "listen-main":
        listen_main(HOST_MAIN_UDP_HOST, HOST_MAIN_UDP_PORT)
        return

    rid = args.request_id.strip() or str(uuid.uuid4())
    if args.action == "request":
        cmd = CMD_BOTTLE_FEED_REQUEST
    elif args.action == "done":
        cmd = CMD_BOTTLE_FEED_DONE
    else:
        cmd = CMD_BOTTLE_DISCHARGE_DONE
    payload = {"cmd": cmd, "request_id": rid}
    print(f"→ {args.host}:{args.port} {payload}")
    resp = send_cmd(payload, args.host, args.port, args.timeout)
    print(f"← {json.dumps(resp, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
