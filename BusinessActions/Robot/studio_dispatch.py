"""通过 HitbotStudio F99 调度流程执行机器人动作。"""
from __future__ import annotations

from typing import Tuple

from Drivers.Robot import robot_config as cfg
from Drivers.Robot.hitbot_studio_bridge import get_studio_bridge


def dispatch_studio_action(action_key: str, param1: int = 0) -> Tuple[bool, str]:
    """向 Studio 下发 cmd 并等待子流程结束。"""
    if action_key in cfg.STUDIO_SKIP_ACTIONS:
        return False, "该动作不由 Studio 调度。"
    cmd = cfg.ACTION_TO_CMD.get(action_key)
    if cmd is None:
        return False, f"未配置 Studio 命令号: {action_key}"
    return get_studio_bridge().run_command(cmd, param1=param1)


def studio_dispatch_enabled() -> bool:
    return cfg.USE_STUDIO_DISPATCH
