"""
FSMN-VAD（语音活动检测）处理模块
使用 FunASR FSMN-VAD 模型进行流式语音活动检测
"""

import numpy as np
import threading
from pathlib import Path
from typing import Optional, List, Tuple
from .config import get_config

try:
    from funasr_onnx import Fsmn_vad_online
except ImportError:
    Fsmn_vad_online = None


class FSMNSpeechSegment:
    """FSMN-VAD 语音段封装类"""

    def __init__(self, samples: np.ndarray, start: float, end: float, sample_rate: int = 16000):
        """
        初始化语音段

        Args:
            samples: 音频样本数据
            start: 开始时间（秒）
            end: 结束时间（秒）
            sample_rate: 采样率
        """
        self._samples = samples
        self._start = start
        self._end = end
        self._sample_rate = sample_rate

    @property
    def samples(self) -> np.ndarray:
        """获取音频样本数据"""
        return self._samples

    @property
    def start(self) -> float:
        """获取语音段开始时间（秒）"""
        return self._start

    @property
    def end(self) -> float:
        """获取语音段结束时间（秒）"""
        return self._end

    @property
    def duration(self) -> float:
        """获取语音段时长（秒）"""
        return self._end - self._start


class FSMNVADProcessor:
    """FSMN-VAD 处理器（流式处理）"""

    def __init__(self):
        """初始化 FSMN-VAD 处理器"""
        self.config = get_config()
        self.model = None
        self.param_dict = None
        self._sample_rate = self.config.sample_rate

        # 缓存音频数据用于提取语音段
        self._audio_buffer: List[Tuple[np.ndarray, float]] = []
        self._buffer_duration: float = 30.0  # 缓存最近30秒的音频

        # 当前正在进行的语音段
        self._current_segment_start: Optional[float] = None
        self._current_segment_samples: List[np.ndarray] = []

        # 已完成的语音段队列
        self._completed_segments: List[FSMNSpeechSegment] = []

        # 线程锁保护
        self._lock = threading.Lock()

        self._init_vad()

    def _init_vad(self):
        """初始化 FSMN-VAD 模型"""
        if Fsmn_vad_online is None:
            raise ImportError("funasr_onnx 未安装，请运行: pip install funasr_onnx")

        print("[INFO] 正在加载 FSMN-VAD 模型...")

        model_dir = self.config.fsmn_vad_model_dir
        if not model_dir.exists():
            raise FileNotFoundError(f"FSMN-VAD 模型目录不存在: {model_dir}")

        # 创建模型实例
        self.model = Fsmn_vad_online(
            model_dir=str(model_dir),
            quantize=self.config.fsmn_vad_quantize
        )

        # 初始化缓存参数
        self.param_dict = {
            "in_cache": [],
            "is_final": False
        }

        print("[INFO] FSMN-VAD 模型加载完成")
        print(f"       - 模型目录: {model_dir}")
        print(f"       - 量化: {self.config.fsmn_vad_quantize}")
        print(f"       - 最大结尾静音: {self.config.fsmn_vad_max_end_sil}ms")
        print(f"       - 线程数: {self.config.fsmn_vad_num_threads}")

    def process(self, samples: np.ndarray, timestamp: float = None):
        """
        处理音频数据，检测语音活动

        Args:
            samples: 音频数据（float32 numpy数组，归一化到[-1, 1]）
            timestamp: 当前音频块的开始时间戳（秒），从程序启动后计算的音频时间
        """
        if self.model is None:
            return

        with self._lock:
            # 计算当前块的时长
            chunk_duration = len(samples) / self._sample_rate

            # timestamp 是当前块的开始时间
            buffer_timestamp = timestamp if timestamp is not None else 0.0

            # 缓存音频数据
            self._audio_buffer.append((samples.copy(), buffer_timestamp))
            self._prune_buffer()

            # 调用 FSMN-VAD 进行检测
            segments = self.model(samples, param_dict=self.param_dict)

            # 处理返回的语音段事件
            if segments and len(segments) > 0:
                for batch_segs in segments:
                    for seg in batch_segs:
                        start_ms, end_ms = seg

                        # 处理语音段开始事件
                        if start_ms != -1:
                            self._current_segment_start = start_ms / 1000.0  # 转换为秒
                            self._current_segment_samples = []
                            print(f"[VAD] 语音段开始: {start_ms}ms")

                        # 处理语音段结束事件
                        if end_ms != -1 and self._current_segment_start is not None:
                            end_sec = end_ms / 1000.0
                            duration = end_sec - self._current_segment_start
                            print(f"[VAD] 语音段结束: {self._current_segment_start:.2f}s ~ {end_sec:.2f}s (时长 {duration:.2f}s)")

                            # 提取语音段音频
                            segment_samples = self._extract_segment_samples(
                                self._current_segment_start,
                                end_sec
                            )

                            if segment_samples is not None and len(segment_samples) > 0:
                                # 验证提取的音频长度是否合理
                                expected_duration = duration
                                actual_duration = len(segment_samples) / self._sample_rate
                                if abs(actual_duration - expected_duration) > 0.5:
                                    print(f"[WARN] 语音段长度不匹配: 预期 {expected_duration:.2f}s, 实际 {actual_duration:.2f}s")

                                # 创建语音段对象
                                speech_segment = FSMNSpeechSegment(
                                    samples=segment_samples,
                                    start=self._current_segment_start,
                                    end=end_sec,
                                    sample_rate=self._sample_rate
                                )
                                self._completed_segments.append(speech_segment)

                            self._current_segment_start = None
                            self._current_segment_samples = []

    def _prune_buffer(self):
        """修剪音频缓冲区，只保留最近的数据（调用前需持有锁）"""
        if len(self._audio_buffer) == 0:
            return

        # 计算缓冲区总时长
        total_samples = sum(len(s) for s, _ in self._audio_buffer)
        total_duration = total_samples / self._sample_rate

        # 如果超过最大时长，删除旧数据
        while total_duration > self._buffer_duration and len(self._audio_buffer) > 1:
            old_samples, _ = self._audio_buffer.pop(0)
            total_duration -= len(old_samples) / self._sample_rate

    def _extract_segment_samples(self, start_sec: float, end_sec: float) -> Optional[np.ndarray]:
        """
        从缓冲区提取指定时间段的音频样本（调用前需持有锁）

        Args:
            start_sec: 开始时间（秒）
            end_sec: 结束时间（秒）

        Returns:
            音频样本数组，如果没有数据则返回 None
        """
        samples_list = []

        for samples, timestamp in self._audio_buffer:
            chunk_duration = len(samples) / self._sample_rate
            chunk_start = timestamp
            chunk_end = timestamp + chunk_duration

            # 检查是否有重叠
            if chunk_end < start_sec or chunk_start > end_sec:
                continue

            # 计算重叠部分
            overlap_start = max(0, start_sec - chunk_start)
            overlap_end = min(chunk_duration, end_sec - chunk_start)

            start_sample = int(overlap_start * self._sample_rate)
            end_sample = int(overlap_end * self._sample_rate)

            if start_sample < end_sample:
                samples_list.append(samples[start_sample:end_sample])

        if samples_list:
            return np.concatenate(samples_list)
        return None

    def has_speech_segment(self) -> bool:
        """检查是否有完成的语音段"""
        with self._lock:
            return len(self._completed_segments) > 0

    def get_latest_speech_segment(self) -> Optional[FSMNSpeechSegment]:
        """
        获取最新的语音段

        Returns:
            语音段对象，如果没有则返回 None
        """
        with self._lock:
            if not self._completed_segments:
                return None
            return self._completed_segments.pop(0)

    def flush(self):
        """刷新 VAD 缓冲区，强制输出剩余的语音段"""
        with self._lock:
            if self.model is not None and self.param_dict is not None:
                # 标记为最后一帧
                self.param_dict["is_final"] = True

                # 处理剩余数据
                # 使用空数组触发最终处理
                try:
                    segments = self.model(np.array([], dtype=np.float32), param_dict=self.param_dict)
                    if segments and len(segments) > 0:
                        for batch_segs in segments:
                            for seg in batch_segs:
                                start_ms, end_ms = seg
                                if end_ms != -1 and self._current_segment_start is not None:
                                    end_sec = end_ms / 1000.0
                                    segment_samples = self._extract_segment_samples(
                                        self._current_segment_start,
                                        end_sec
                                    )
                                    if segment_samples is not None and len(segment_samples) > 0:
                                        speech_segment = FSMNSpeechSegment(
                                            samples=segment_samples,
                                            start=self._current_segment_start,
                                            end=end_sec,
                                            sample_rate=self._sample_rate
                                        )
                                        self._completed_segments.append(speech_segment)
                                    self._current_segment_start = None
                except Exception as e:
                    print(f"[WARN] FSMN-VAD flush 异常: {e}")

                # 重置 is_final 标志
                self.param_dict["is_final"] = False

    def reset(self):
        """重置 VAD 状态"""
        with self._lock:
            if self.model is not None:
                # 重新初始化缓存
                self.param_dict = {
                    "in_cache": [],
                    "is_final": False
                }

            # 清空缓冲区和状态
            self._audio_buffer = []
            self._current_segment_start = None
            self._current_segment_samples = []
            self._completed_segments = []

    def get_stats(self) -> dict:
        """获取 VAD 统计信息"""
        with self._lock:
            return {
                "status": "initialized" if self.model is not None else "not_initialized",
                "buffer_size": len(self._audio_buffer),
                "pending_segments": len(self._completed_segments),
                "current_segment_active": self._current_segment_start is not None
            }
