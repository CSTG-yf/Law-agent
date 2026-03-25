import os
from pathlib import Path


def clear_logs():
    logs_dir = Path(__file__).parent / "backend" / "logs"
    
    if not logs_dir.exists():
        print(f"日志目录不存在: {logs_dir}")
        return
    
    log_files = list(logs_dir.glob("*.log"))
    
    if not log_files:
        print("没有找到日志文件")
        return
    
    for log_file in log_files:
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write('')
            print(f"已清空: {log_file.name}")
        except Exception as e:
            print(f"清空失败 {log_filse.name}: {e}")
    
    print(f"\n共清空 {len(log_files)} 个日志文件")


if __name__ == "__main__":
    clear_logs()
