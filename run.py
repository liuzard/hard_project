
#!/usr/bin/env python3
"""
主程序入口
支持实时录音或使用录音文件模拟
"""

import sys
import argparse
from pathlib import Path

# 确保能找到 src 模块
sys.path.insert(0, str(Path(__file__).parent))

from src.main import main


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='语音关键词检测系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 实时录音模式（默认）
  python run.py

  # 使用录音文件模拟（实时播放速度）
  python run.py -f resources/recording.wav

  # 使用录音文件模拟（快速模式，不等待）
  python run.py -f resources/recording.wav --fast
        '''
    )

    parser.add_argument(
        '-f', '--file',
        type=str,
        default=None,
        help='录音文件路径，用于模拟实时录音流（不指定则使用实时录音）'
    )

    parser.add_argument(
        '--fast',
        action='store_true',
        help='快速模式，不等待实时播放速度（仅在使用 -f 时有效）'
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # 传递参数给 main 函数
    sys.exit(main(
        audio_file=args.file,
        fast_mode=args.fast
    ))
