import time


def Wait(time_sec: int):
    for elapsed_time in range(1, time_sec + 1):
        time.sleep(1)
        print(f"当前步骤需等待反应处理，已等待 {elapsed_time} /{time_sec}秒")
