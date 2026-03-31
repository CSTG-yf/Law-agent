import subprocess
import sys
import argparse


def kill_port(port: int):
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True
        )
    except Exception as e:
        print(f"执行 netstat 失败: {e}")
        sys.exit(1)

    pids = set()
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 5 and f":{port}" in parts[1] and "LISTENING" in line:
            pid = int(parts[-1])
            pids.add(pid)

    if not pids:
        print(f"端口 {port} 上没有运行的进程")
        return

    print(f"端口 {port} 上发现 {len(pids)} 个进程: {pids}")

    for pid in pids:
        try:
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True, text=True
            )
            print(f"已终止 PID {pid}")
        except Exception as e:
            print(f"终止 PID {pid} 失败: {e}")

    print("完成")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="杀掉占用指定端口的所有进程")
    parser.add_argument("port", type=int, help="端口号")
    args = parser.parse_args()
    kill_port(args.port)
