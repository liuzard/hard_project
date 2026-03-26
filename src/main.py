"""
主程序入口
整合所有模块，实现持续的录音、VAD、ASR和关键词检测
支持实时录音或使用录音文件模拟
使用多线程架构避免 ASR 处理阻塞录音
"""

import sys
import time
import signal
import wave
import threading
import queue
from pathlib import Path
from datetime import datetime

import numpy as np

from .config import get_config
from .audio_buffer import AudioBuffer
from .vad_processor import VADProcessor
from .asr_processor import ASRProcessor
from .keyword_detector import KeywordDetector


def pcm_int16_to_float32(data: bytes) -> 'np.ndarray':
    """
    将int16 PCM字节流转换为float32 numpy数组（归一化到[-1, 1]）

    Args:
        data: int16 PCM字节流

    Returns:
        float32 numpy数组，归一化到[-1, 1]
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

    def read_chunk(self) -> bytes:
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


class VoiceKeywordDetector:
    """语音关键词检测系统（多线程架构）"""

    def __init__(self, audio_file: str = None, fast_mode: bool = False):
        """
        初始化系统

        Args:
            audio_file: 录音文件路径，如果指定则使用文件模拟，否则使用实时录音
            fast_mode: 快速模式，不等待实时播放速度（仅在使用文件模拟时有效）
        """
        print("=" * 60)
        if audio_file:
            print("语音关键词检测系统 (文件模拟模式)")
        else:
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

        # 音频源配置
        self.audio_file = audio_file
        self.fast_mode = fast_mode
        self.audio_recorder = None
        self.file_simulator = None

        # ASR 处理队列和线程（避免阻塞录音）
        self._asr_queue = queue.Queue()
        self._asr_thread = None
        self._asr_thread_running = False

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
        self._stats_lock = threading.Lock()

        # 控制标志
        self.is_running = False
        self._stop_requested = False
        self._in_signal_handler = False

        # 上一个音频块的时间戳（用于检测录音流中断）
        self._last_chunk_time: float = None

        # 状态心跳相关
        self._last_activity_time: float = None
        self._heartbeat_interval: float = 10.0

        # 模拟时间偏移（用于文件模拟模式）
        self._simulated_time_offset: float = 0

        # 设置信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, sig, frame):
        """信号处理器"""
        if self._in_signal_handler:
            return

        self._in_signal_handler = True
        print(f"\n[INFO] 收到停止信号 (signal {sig})")
        self._stop_requested = True
        self.is_running = False

    def _asr_worker(self):
        """ASR 处理线程工作函数"""
        while self._asr_thread_running or not self._asr_queue.empty():
            try:
                # 从队列获取语音段，超时 0.1 秒
                item = self._asr_queue.get(timeout=0.1)
                if item is None:
                    break

                samples, buffer_timestamp, real_time = item

                # ASR 处理
                duration = len(samples) / self.config.sample_rate
                text = self.asr_processor.process(samples)

                # 打印识别结果
                timestamp = datetime.now().strftime("%H:%M:%S")

                with self._stats_lock:
                    self.stats["last_asr_time"] = buffer_timestamp

                if text:
                    with self._stats_lock:
                        self.stats["total_asr_results"] += 1
                    print(f"[{timestamp}] 🎤 识别: {text} ({duration:.1f}s)")

                    # 关键词检测
                    matched_keyword = self.keyword_detector.detect(text)
                    if matched_keyword:
                        # 使用 buffer_timestamp 作为检测时间（用于从缓冲区提取音频）
                        self._handle_keyword_detection(matched_keyword, buffer_timestamp)
                else:
                    print(f"[{timestamp}] 🔊 检测到语音 ({duration:.1f}s) - 无法识别文字")

                self._asr_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"[ERROR] ASR 线程异常: {e}")

    def _start_asr_thread(self):
        """启动 ASR 处理线程"""
        self._asr_thread_running = True
        self._asr_thread = threading.Thread(target=self._asr_worker, daemon=True)
        self._asr_thread.start()
        print("[INFO] ASR 处理线程已启动")

    def _stop_asr_thread(self):
        """停止 ASR 处理线程"""
        self._asr_thread_running = False
        # 放入 None 作为结束信号
        self._asr_queue.put(None)
        if self._asr_thread:
            self._asr_thread.join(timeout=3.0)
            self._asr_thread = None
        print("[INFO] ASR 处理线程已停止")

    def process_audio_chunk(self, raw_data: bytes, use_simulated_time: bool = False):
        """
        处理音频数据块（轻量级，不阻塞）

        Args:
            raw_data: 原始PCM音频数据（int16）
            use_simulated_time: 是否使用模拟时间（文件模式）
        """
        # 转换音频格式
        samples = pcm_int16_to_float32(raw_data)
        current_real_time = time.time()

        # 计算时间戳：统一使用相对时间（从程序开始计算的秒数）
        # 文件模式和实时模式都使用相同的时间系统
        chunk_duration = len(raw_data) / 2 / self.config.sample_rate  # 字节数/2 = 样本数

        if self._simulated_time_offset == 0:
            # 第一次调用，初始化时间偏移
            self._simulated_time_offset = current_real_time

        # 计算当前块的结束时间戳（相对时间，从0开始）
        timestamp_for_buffer = current_real_time - self._simulated_time_offset

        # 1. 将音频数据添加到循环缓冲区
        self.audio_buffer.append(samples, timestamp_for_buffer)

        # 2. VAD处理
        self.vad_processor.process(samples)

        # 3. 获取检测到的语音段，放入 ASR 队列
        while True:
            speech_segment = self.vad_processor.get_latest_speech_segment()
            if speech_segment is None:
                break

            with self._stats_lock:
                self.stats["total_speech_segments"] += 1

            self._last_activity_time = current_real_time

            # 将语音段放入 ASR 队列（异步处理，不阻塞）
            # 传递：samples, buffer时间戳, 当前实际时间
            self._asr_queue.put((
                speech_segment.samples,
                speech_segment.start,  # buffer中的相对时间
                current_real_time      # 实际时间（用于保存文件名）
            ))

        # 4. 更新最后活动时间（用于心跳检测）
        self._last_chunk_time = current_real_time

        # 5. 状态心跳
        if self._last_activity_time is None:
            self._last_activity_time = current_real_time

        idle = current_real_time - self._last_activity_time
        if idle >= self._heartbeat_interval:
            # 读取 start_time 需要加锁保护
            with self._stats_lock:
                elapsed = current_real_time - self.stats["start_time"]
                seg_count = self.stats["total_speech_segments"]
                asr_count = self.stats["total_asr_results"]
                kw_count = self.stats["total_keywords_detected"]

            buf_stats = self.audio_buffer.get_stats()
            status = "● 录音正常" if buf_stats["is_filled"] else "○ 等待缓冲区填满"
            queue_size = self._asr_queue.qsize()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                  f"[{elapsed:.0f}s] {status} | "
                  f"语音段: {seg_count} | 识别: {asr_count} | "
                  f"关键词: {kw_count} | ASR队列: {queue_size}")
            self._last_activity_time = current_real_time

    def _handle_keyword_detection(self, keyword: str, buffer_time: float):
        """
        处理关键词检测事件

        Args:
            keyword: 检测到的关键词
            buffer_time: 缓冲区中的相对时间（秒），用于提取音频
        """
        with self._stats_lock:
            self.stats["total_keywords_detected"] += 1
            self.stats["last_detection_time"] = buffer_time

        # 使用当前时间作为显示时间
        current_time = time.time()
        timestamp_str = datetime.fromtimestamp(current_time).strftime("%Y-%m-%d %H:%M:%S")

        print(f"\n*** 检测到关键词: {keyword} ***")
        print(f"    时间: {timestamp_str}")
        print(f"    音频位置: {buffer_time:.1f}秒")
        with self._stats_lock:
            print(f"    总检测次数: {self.stats['total_keywords_detected']}")

        try:
            wav_path, meta_path = self.audio_buffer.save_detected_clip(
                keyword=keyword,
                detected_at=buffer_time,  # 使用 buffer 时间提取音频
                output_dir=self.config.output_directory,
                save_metadata=self.config.save_metadata
            )

            with self._stats_lock:
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
        if self.audio_file:
            print("系统启动 (文件模拟模式)")
        else:
            print("系统启动")
        print("=" * 60)

        try:
            # 根据模式选择音频源
            if self.audio_file:
                self.file_simulator = FileAudioSimulator(
                    self.audio_file,
                    realtime=not self.fast_mode
                )
                self.file_simulator.start()
                audio_source = self.file_simulator
                use_simulated_time = True
            else:
                from .audio_recorder import AudioRecorder
                self.audio_recorder = AudioRecorder()
                self.audio_recorder.start()
                audio_source = self.audio_recorder
                use_simulated_time = False

            # 启动 ASR 处理线程
            self._start_asr_thread()

            self.is_running = True
            self.stats["start_time"] = time.time()

            print("\n[INFO] 系统运行中...")
            print("[INFO] 监听关键词:", ", ".join(self.keyword_detector.get_keywords()))
            print("[INFO] 实时显示ASR识别结果...")
            print("[INFO] 按 Ctrl+C 停止\n")
            print("-" * 60)

            # 主循环（只负责读取音频，不阻塞）
            while self.is_running and not self._stop_requested:
                raw_data = audio_source.read_chunk()

                if raw_data is None:
                    if self.audio_file:
                        print("\n[INFO] 录音文件播放完毕")
                    break

                # 处理音频（轻量级，不阻塞）
                self.process_audio_chunk(raw_data, use_simulated_time=use_simulated_time)

        except KeyboardInterrupt:
            print("\n[INFO] 收到键盘中断信号")
        except Exception as e:
            if not self._in_signal_handler:
                print(f"\n[ERROR] 系统运行异常: {e}")
                import traceback
                traceback.print_exc()
        finally:
            self.stop()
            if self.audio_recorder:
                self.audio_recorder.stop()
            if self.file_simulator:
                self.file_simulator.stop()

    def stop(self):
        """停止系统"""
        if not self.is_running:
            return

        if not self._in_signal_handler:
            print("\n[INFO] 正在停止系统...")

        self.is_running = False
        self._stop_requested = True

        # 停止 ASR 线程
        self._stop_asr_thread()

        # 刷新 VAD 并处理剩余语音段
        print("[INFO] 处理剩余语音段...")
        self.vad_processor.flush()
        while True:
            speech_segment = self.vad_processor.get_latest_speech_segment()
            if speech_segment is None:
                break

            with self._stats_lock:
                self.stats["total_speech_segments"] += 1

            duration = len(speech_segment.samples) / self.config.sample_rate
            text = self.asr_processor.process(speech_segment.samples)

            if text:
                with self._stats_lock:
                    self.stats["total_asr_results"] += 1
                print(f"[最终] 🎤 识别: {text} ({duration:.1f}s)")

                matched_keyword = self.keyword_detector.detect(text)
                if matched_keyword:
                    # 使用语音段自己的时间戳（相对于缓冲区开始时间）
                    self._handle_keyword_detection(matched_keyword, speech_segment.start)

        # 打印统计信息
        if not self._in_signal_handler and self.stats["start_time"]:
            runtime = time.time() - self.stats["start_time"]
            print(f"\n" + "=" * 60)
            print("运行统计")
            print("=" * 60)
            print(f"运行时长: {runtime:.1f} 秒 ({runtime/60:.1f} 分钟)")
            with self._stats_lock:
                print(f"语音段检测: {self.stats['total_speech_segments']} 次")
                print(f"ASR识别成功: {self.stats['total_asr_results']} 次")
                print(f"关键词检测: {self.stats['total_keywords_detected']} 次")
                print(f"保存音频片段: {self.stats['total_clips_saved']} 个")

                if self.stats["total_speech_segments"] > 0:
                    asr_rate = (self.stats['total_asr_results'] / self.stats['total_speech_segments']) * 100
                    print(f"识别成功率: {asr_rate:.1f}%")

        if not self._in_signal_handler:
            print("\n[INFO] 系统已停止")


def main(audio_file: str = None, fast_mode: bool = False):
    """
    主函数

    Args:
        audio_file: 录音文件路径，如果指定则使用文件模拟，否则使用实时录音
        fast_mode: 快速模式，不等待实时播放速度（仅在使用文件模拟时有效）
    """
    try:
        system = VoiceKeywordDetector(audio_file=audio_file, fast_mode=fast_mode)
        system.start()

    except Exception as e:
        print(f"\n[ERROR] 程序异常退出: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
