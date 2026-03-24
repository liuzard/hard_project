"""
主程序入口
整合所有模块，实现持续的录音、VAD、ASR和关键词检测
"""

import sys
import time
import signal
from pathlib import Path
from datetime import datetime

import numpy as np

from config import get_config
from audio_recorder import AudioRecorder, pcm_int16_to_float32
from audio_buffer import AudioBuffer
from vad_processor import VADProcessor
from asr_processor import ASRProcessor
from keyword_detector import KeywordDetector


class VoiceKeywordDetector:
    """语音关键词检测系统"""

    def __init__(self):
        """初始化系统"""
        print("=" * 60)
        print("语音关键词检测系统")
        print("=" * 60)

        # 加载配置
        self.config = get_config()

        # 验证配置
        if not self.config.validate():
            print("[ERROR] 配置验证失败，请检查配置文件")
            sys.exit(1)

        # 创建输出目录
        self.config.output_directory.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] 输出目录: {self.config.output_directory.absolute()}")

        # 初始化各个模块
        print("\n[INFO] 正在初始化各个模块...")

        self.audio_buffer = AudioBuffer(
            sample_rate=self.config.sample_rate,
            duration=self.config.get_audio_buffer_duration()
        )

        self.vad_processor = VADProcessor()
        self.asr_processor = ASRProcessor()
        self.keyword_detector = KeywordDetector()

        # 统计信息
        self.stats = {
            "total_keywords_detected": 0,
            "total_clips_saved": 0,
            "start_time": None,
            "last_detection_time": None
        }

        # 控制标志
        self.is_running = False
        self._stop_requested = False
        self._in_signal_handler = False

        # 设置信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, sig, frame):
        """信号��理器"""
        # 防止递归调用
        if self._in_signal_handler:
            return

        self._in_signal_handler = True
        print(f"\n[INFO] 收到停止信号 (signal {sig})")
        self._stop_requested = True
        self.is_running = False

    def process_audio_chunk(self, raw_data: bytes):
        """
        处理音频数据块

        Args:
            raw_data: 原始PCM音频数据（int16）
        """
        # 转换音频格式
        samples = pcm_int16_to_float32(raw_data)
        current_time = time.time()

        # 1. 将音频数据添加到循环缓冲区
        self.audio_buffer.append(samples, current_time)

        # 2. VAD处理
        self.vad_processor.process(samples)

        # 3. 获取检测到的语音段
        while True:
            speech_segment = self.vad_processor.get_latest_speech_segment()
            if speech_segment is None:
                break

            # 4. ASR处理
            text, duration = self.asr_processor.process_with_duration(
                speech_segment.samples
            )

            if text:
                # 打印识别结果
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] 识别: {text} ({duration:.1f}s)")

                # 5. 关键词检测
                matched_keyword = self.keyword_detector.detect(text)

                if matched_keyword:
                    self._handle_keyword_detection(matched_keyword, current_time)

    def _handle_keyword_detection(self, keyword: str, detection_time: float):
        """
        处理关键词检测事件

        Args:
            keyword: 检测到的关键词
            detection_time: 检测时间戳
        """
        self.stats["total_keywords_detected"] += 1
        self.stats["last_detection_time"] = detection_time

        # 打印检测信息
        timestamp = datetime.fromtimestamp(detection_time).strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n*** 检测到关键词: {keyword} ***")
        print(f"    时间: {timestamp}")
        print(f"    总检测次数: {self.stats['total_keywords_detected']}")

        try:
            # 保存音频片段
            wav_path, meta_path = self.audio_buffer.save_detected_clip(
                keyword=keyword,
                detected_at=detection_time,
                output_dir=self.config.output_directory,
                save_metadata=self.config.save_metadata
            )

            self.stats["total_clips_saved"] += 1

            print(f"    音频已保存: {wav_path.name}")
            if meta_path:
                print(f"    元数据已保存: {meta_path.name}")
            print()

        except Exception as e:
            print(f"    [ERROR] 保存音频片段失败: {e}\n")

    def start(self):
        """启动系统"""
        if self.is_running:
            print("[WARN] 系统已在运行中")
            return

        print("\n" + "=" * 60)
        print("系统启动")
        print("=" * 60)

        # 创建音频录制器
        recorder = AudioRecorder()

        try:
            # 启动录音
            recorder.start()

            self.is_running = True
            self.stats["start_time"] = time.time()

            print("\n[INFO] 系统运行中...")
            print("[INFO] 开始监听关键词:", ", ".join(self.keyword_detector.get_keywords()))
            print("[INFO] 按 Ctrl+C 停止\n")

            # 主循环
            while self.is_running and not self._stop_requested:
                # 读取音频块
                raw_data = recorder.read_chunk()

                if raw_data is None:
                    # 录音器已停止
                    break

                # 处理音频
                self.process_audio_chunk(raw_data)

        except KeyboardInterrupt:
            print("\n[INFO] 收到键盘中断信号")
        except Exception as e:
            if not self._in_signal_handler:
                print(f"\n[ERROR] 系统运行异常: {e}")
                import traceback
                traceback.print_exc()
        finally:
            self.stop()
            recorder.stop()

    def stop(self):
        """停止系统"""
        if not self.is_running:
            return

        # 防止在信号处理器中打印
        if not self._in_signal_handler:
            print("\n[INFO] 正在停止系统...")

        self.is_running = False
        self._stop_requested = True

        # 只在非信号处理中打印统计信息
        if not self._in_signal_handler and self.stats["start_time"]:
            runtime = time.time() - self.stats["start_time"]
            print(f"\n" + "=" * 60)
            print("运行统计")
            print("=" * 60)
            print(f"运行时长: {runtime:.1f} 秒 ({runtime/60:.1f} 分钟)")
            print(f"关键词检测次数: {self.stats['total_keywords_detected']}")
            print(f"保存音频片段数: {self.stats['total_clips_saved']}")

            if self.stats["total_keywords_detected"] > 0:
                rate = self.stats["total_keywords_detected"] / (runtime / 60)
                print(f"平均检测率: {rate:.2f} 次/分钟")

        if not self._in_signal_handler:
            print("\n[INFO] 系统已停止")


def main():
    """主函数"""
    try:
        # 创建并启动系统
        system = VoiceKeywordDetector()
        system.start()

    except Exception as e:
        print(f"\n[ERROR] 程序异常退出: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
