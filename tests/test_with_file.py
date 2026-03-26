"""
使用录音文件模拟录音流测试主流程
模拟 AudioRecorder 的行为，从 WAV 文件读取数据
"""

import sys
import wave
import time
import numpy as np
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config
from src.audio_buffer import AudioBuffer
from src.vad_processor import VADProcessor
from src.asr_processor import ASRProcessor
from src.keyword_detector import KeywordDetector


def pcm_int16_to_float32(data: bytes) -> 'np.ndarray':
    """
    将 int16 PCM 字节流转换为 float32 numpy 数组（归一化到 [-1, 1]）

    Args:
        data: int16 PCM 字节流

    Returns:
        float32 numpy 数组，归一化到 [-1, 1]
    """
    samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
    return samples


class FileAudioSimulator:
    """模拟录音流，从 WAV 文件读取音频数据"""

    def __init__(self, wav_path: str, realtime: bool = True):
        """
        初始化文件音频模拟器

        Args:
            wav_path: WAV 文件路径
            realtime: 是否实时模拟（按实际音频速度播放）
        """
        self.config = get_config()
        self.wav_path = Path(wav_path)
        self.realtime = realtime

        self.wf = None
        self.is_running = False
        self._stop_requested = False

        # 音频信息
        self.sample_rate = None
        self.channels = None
        self.total_frames = 0
        self.frames_read = 0

    def start(self):
        """开始读取音频文件"""
        if self.is_running:
            print("[WARN] 模拟器已在运行中")
            return

        print(f"[INFO] 正在加载录音文件: {self.wav_path}")

        if not self.wav_path.exists():
            raise FileNotFoundError(f"录音文件不存在: {self.wav_path}")

        # 打开 WAV 文件
        self.wf = wave.open(str(self.wav_path), 'rb')

        # 获取音频信息
        self.sample_rate = self.wf.getframerate()
        self.channels = self.wf.getnchannels()
        self.total_frames = self.wf.getnframes()
        sample_width = self.wf.getsampwidth()

        print(f"[INFO] 录音文件信息:")
        print(f"       - 采样率: {self.sample_rate} Hz")
        print(f"       - 声道数: {self.channels}")
        print(f"       - 采样宽度: {sample_width * 8} bit")
        print(f"       - 总帧数: {self.total_frames}")
        print(f"       - 时长: {self.total_frames / self.sample_rate:.1f} 秒")

        # 检查格式
        if self.sample_rate != self.config.sample_rate:
            print(f"[WARN] 文件采样率 ({self.sample_rate}) 与配置 ({self.config.sample_rate}) 不一致")

        if self.channels != 1:
            print(f"[WARN] 文件声道数 ({self.channels}) 不是单声道，将只使用第一个声道")

        self.is_running = True
        self._stop_requested = False
        self.frames_read = 0

        print("[INFO] 音频模拟器已启动")
        print(f"[INFO] 实时模式: {'开启' if self.realtime else '关闭'}\n")

    def read_chunk(self) -> Optional[bytes]:
        """
        读取一个音频块

        Returns:
            音频数据（bytes），如果文件结束或停止则返回 None
        """
        if not self.is_running or self._stop_requested:
            return None

        if self.wf is None:
            return None

        # 计算每个 chunk 的帧数
        chunk_frames = self.config.chunk_size

        # 读取音频数据
        raw_data = self.wf.readframes(chunk_frames)
        self.frames_read += len(raw_data) // (self.wf.getsampwidth() * self.channels)

        if len(raw_data) == 0:
            # 文件结束
            return None

        # 如果是多声道，只取第一个声道
        if self.channels > 1:
            # 假设是 16-bit PCM
            samples = np.frombuffer(raw_data, dtype=np.int16)
            # 重塑为 (frames, channels)
            samples = samples.reshape(-1, self.channels)
            # 只取第一个声道
            samples = samples[:, 0]
            raw_data = samples.tobytes()

        # 实时模式：按实际音频速度播放
        if self.realtime:
            chunk_duration = chunk_frames / self.sample_rate
            time.sleep(chunk_duration)

        return raw_data

    def stop(self):
        """停止模拟器"""
        if not self.is_running:
            return

        print("\n[INFO] 正在停止音频模拟器...")
        self._stop_requested = True
        self.is_running = False

        if self.wf:
            self.wf.close()
            self.wf = None

        print(f"[INFO] 已读取 {self.frames_read} 帧 ({self.frames_read / self.sample_rate:.1f} 秒)")

    def get_progress(self) -> float:
        """获取播放进度（0.0 - 1.0）"""
        if self.total_frames == 0:
            return 0.0
        return self.frames_read / self.total_frames


class FileBasedVoiceKeywordDetector:
    """基于文件的语音关键词检测系统"""

    def __init__(self, wav_path: str, realtime: bool = True):
        """
        初始化系统

        Args:
            wav_path: WAV 文件路径
            realtime: 是否实时模拟
        """
        print("=" * 60)
        print("语音关键词检测系统 (文件模拟模式)")
        print("=" * 60)

        # 加载配置
        self.config = get_config()

        # 验证配置
        if not self.config.validate():
            print("[ERROR] 配置验证失败，请检查配置文件")
            raise RuntimeError("配置验证失败")

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

        # 创建文件音频模拟器
        self.simulator = FileAudioSimulator(wav_path, realtime=realtime)

        # 统计信息
        self.stats = {
            "total_keywords_detected": 0,
            "total_clips_saved": 0,
            "total_speech_segments": 0,
            "total_asr_results": 0,
            "start_time": None,
            "last_detection_time": None,
            "last_asr_time": None
        }

        # 控制标志
        self.is_running = False
        self._stop_requested = False

        # 上一个音频块的时间戳
        self._last_chunk_time: float = None

        # 模拟时间（从文件开始播放时计算）
        self._simulated_time_offset: float = 0

    def process_audio_chunk(self, raw_data: bytes):
        """
        处理音频数据块

        Args:
            raw_data: 原始 PCM 音频数据（int16）
        """
        # 转换音频格式
        samples = pcm_int16_to_float32(raw_data)

        # 计算模拟时间戳
        current_time = time.time()
        if self._simulated_time_offset == 0:
            self._simulated_time_offset = current_time

        # 使用模拟时间（基于音频播放进度）
        simulated_time = current_time - self._simulated_time_offset

        # 1. 将音频数据添加到循环缓冲区
        self.audio_buffer.append(samples, simulated_time)

        # 2. VAD 处理
        self.vad_processor.process(samples)

        # 3. 获取检测到的语音段
        while True:
            speech_segment = self.vad_processor.get_latest_speech_segment()
            if speech_segment is None:
                break

            # 更新语音段统计
            self.stats["total_speech_segments"] += 1

            # 4. ASR 处理
            samples = speech_segment.samples
            duration = len(samples) / self.config.sample_rate

            # 跳过极短的片段
            if duration < 0.2:
                continue

            text, _ = self.asr_processor.process_with_duration(samples)

            # 打印 ASR 识别结果
            timestamp = time.strftime("%H:%M:%S", time.localtime(simulated_time))
            self.stats["last_asr_time"] = simulated_time

            if text:
                self.stats["total_asr_results"] += 1
                print(f"[{timestamp}] 🎤 识别: {text} ({duration:.1f}s)")
            else:
                print(f"[{timestamp}] 🔊 检测到语音 ({duration:.1f}s) - 无法识别文字")

            # 5. 关键词检测
            if text:
                matched_keyword = self.keyword_detector.detect(text)
                if matched_keyword:
                    self._handle_keyword_detection(matched_keyword, simulated_time)

        # 6. 更新时间戳
        self._last_chunk_time = current_time

        # 7. 显示进度
        progress = self.simulator.get_progress()
        elapsed = time.time() - self.stats["start_time"]
        if int(elapsed) % 10 == 0 and int(elapsed) > 0:
            buf_stats = self.audio_buffer.get_stats()
            status = "● 缓冲正常" if buf_stats["is_filled"] else "○ 等待缓冲"
            print(f"[进度] {progress*100:.1f}% | {status} | "
                  f"语音段: {self.stats['total_speech_segments']} | "
                  f"识别: {self.stats['total_asr_results']} | "
                  f"关键词: {self.stats['total_keywords_detected']}")

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
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(detection_time))
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
        print("系统启动 (文件模拟模式)")
        print("=" * 60)

        try:
            # 启动模拟器
            self.simulator.start()

            self.is_running = True
            self.stats["start_time"] = time.time()

            print("\n[INFO] 系统运行中...")
            print("[INFO] 监听关键词:", ", ".join(self.keyword_detector.get_keywords()))
            print("[INFO] 实时显示 ASR 识别结果...")
            print("[INFO] 按 Ctrl+C 停止\n")
            print("-" * 60)

            # 主循环
            while self.is_running and not self._stop_requested:
                # 读取音频块
                raw_data = self.simulator.read_chunk()

                if raw_data is None:
                    # 文件结束
                    print("\n[INFO] 录音文件播放完毕")
                    break

                # 处理音频
                self.process_audio_chunk(raw_data)

        except KeyboardInterrupt:
            print("\n[INFO] 收到键盘中断信号")
        except Exception as e:
            print(f"\n[ERROR] 系统运行异常: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()

    def stop(self):
        """停止系统"""
        if not self.is_running:
            return

        print("\n[INFO] 正在停止系统...")

        self.is_running = False
        self._stop_requested = True

        # 停止模拟器
        self.simulator.stop()

        # 刷新 VAD 缓冲区
        self.vad_processor.flush()

        # 处理剩余的语音段
        print("[INFO] 处理剩余语音段...")
        while True:
            speech_segment = self.vad_processor.get_latest_speech_segment()
            if speech_segment is None:
                break

            self.stats["total_speech_segments"] += 1
            text, duration = self.asr_processor.process_with_duration(
                speech_segment.samples
            )

            if text:
                self.stats["total_asr_results"] += 1
                print(f"[最终] 🎤 识别: {text} ({duration:.1f}s)")

                # 关键词检测
                matched_keyword = self.keyword_detector.detect(text)
                if matched_keyword:
                    self._handle_keyword_detection(matched_keyword, time.time())

        # 打印统计信息
        if self.stats["start_time"]:
            runtime = time.time() - self.stats["start_time"]
            print(f"\n" + "=" * 60)
            print("运行统计")
            print("=" * 60)
            print(f"运行时长: {runtime:.1f} 秒 ({runtime/60:.1f} 分钟)")
            print(f"语音段检测: {self.stats['total_speech_segments']} 次")
            print(f"ASR 识别成功: {self.stats['total_asr_results']} 次")
            print(f"关键词检测: {self.stats['total_keywords_detected']} 次")
            print(f"保存音频片段: {self.stats['total_clips_saved']} 个")

            if self.stats["total_speech_segments"] > 0:
                asr_rate = (self.stats['total_asr_results'] / self.stats['total_speech_segments']) * 100
                print(f"识别成功率: {asr_rate:.1f}%")

        print("\n[INFO] 系统已停止")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="使用录音文件测试主流程")
    parser.add_argument(
        "wav_file",
        nargs="?",
        default="resources/recording_600s_20260326_075538.wav",
        help="WAV 录音文件路径 (默认: resources/recording_600s_20260326_075538.wav)"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="快速模式（不等待实时播放，尽快处理）"
    )

    args = parser.parse_args()

    try:
        # 创建并启动系统
        system = FileBasedVoiceKeywordDetector(
            wav_path=args.wav_file,
            realtime=not args.fast
        )
        system.start()

    except Exception as e:
        print(f"\n[ERROR] 程序异常退出: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
