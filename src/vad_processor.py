"""
VAD（语音活动检测）处理模块
支持多种 VAD 模型：Silero VAD v6 和 FSMN-VAD
"""

import sherpa_onnx
import numpy as np
import threading
from pathlib import Path
from typing import Optional, Union
from .config import get_config


class SpeechSegmentWrapper:
    """语音段包装器，用于在 pop 后保留 samples 数据"""

    def __init__(self, original_segment, sample_rate: int = 16000):
        """
        初始化包装器

        Args:
            original_segment: 原始的 SpeechSegment 对象
            sample_rate: 采样率，用于将采样点数转换为秒
        """
        # 在 pop 之前复制 samples 数据
        self._samples = np.array(original_segment.samples, copy=True)
        # start 是采样点数，转换为秒
        self._start = original_segment.start / sample_rate
        self._sample_rate = sample_rate

    @property
    def samples(self) -> np.ndarray:
        """获取音频样本数据"""
        return self._samples

    @property
    def start(self) -> float:
        """获取语音段开始时间（秒）"""
        return self._start


class VADProcessor:
    """VAD处理器，支持多种模型"""

    def __init__(self):
        """初始化VAD处理器"""
        self.config = get_config()
        self.vad = None
        self._fsmn_vad = None
        self._model_type = self.config.vad_model_type.lower()
        self._lock = threading.Lock()  # 线程锁保护
        self._init_vad()

    def _init_vad(self):
        """初始化VAD模型"""
        if self._model_type == "fsmn_vad":
            self._init_fsmn_vad()
        else:
            self._init_silero_vad()

    def _init_silero_vad(self):
        """初始化 Silero VAD 模型"""
        print("[INFO] 正在加载 VAD 模型 (Silero VAD)...")

        # 验证模型文件存在
        if not self.config.vad_model_path.exists():
            raise FileNotFoundError(f"VAD模型文件不存在: {self.config.vad_model_path}")

        # 创建 Silero VAD v6 配置
        silero_vad_config = sherpa_onnx.SileroVadModelConfig(
            model=str(self.config.vad_model_path),
            threshold=self.config.vad_threshold,
            min_silence_duration=self.config.vad_min_silence_duration,
            min_speech_duration=self.config.vad_min_speech_duration,
            window_size=self.config.vad_window_size
        )

        # 创建VAD配置
        vad_config = sherpa_onnx.VadModelConfig(
            silero_vad=silero_vad_config,
            sample_rate=self.config.sample_rate,
            num_threads=self.config.vad_num_threads
        )

        # 创建VAD实例
        self.vad = sherpa_onnx.VoiceActivityDetector(
            vad_config,
            buffer_size_in_seconds=self.config.vad_buffer_size_seconds
        )

        print("[INFO] VAD模型加载完成 (Silero VAD v6)")
        print(f"       - 阈值: {self.config.vad_threshold}")
        print(f"       - 最小静音时长: {self.config.vad_min_silence_duration}s")
        print(f"       - 最小语音时长: {self.config.vad_min_speech_duration}s")
        print(f"       - 缓冲区大小: {self.config.vad_buffer_size_seconds}s")

    def _init_fsmn_vad(self):
        """初始化 FSMN-VAD 模型"""
        from .fsmn_vad_processor import FSMNVADProcessor
        self._fsmn_vad = FSMNVADProcessor()

    def process(self, samples: np.ndarray, timestamp: float = None) -> bool:
        """
        处理音频数据，检测是否有语音活动

        Args:
            samples: 音频数据（float32 numpy数组，归一化到[-1, 1]）
            timestamp: 当前音频块的开始时间戳（秒），仅 FSMN-VAD 使用

        Returns:
            True表示检测到语音，False表示没有语音
        """
        with self._lock:
            if self._model_type == "fsmn_vad":
                return self._process_fsmn(samples, timestamp)
            else:
                return self._process_silero(samples)

    def _process_silero(self, samples: np.ndarray) -> bool:
        """使用 Silero VAD 处理音频（调用前需持有锁）"""
        if self.vad is None:
            return False

        # 将音频数据送入VAD
        self.vad.accept_waveform(samples)

        # 检查是否有语音段
        return not self.vad.empty()

    def _process_fsmn(self, samples: np.ndarray, timestamp: float = None) -> bool:
        """使用 FSMN-VAD 处理音频（调用前需持有锁）"""
        if self._fsmn_vad is None:
            return False

        self._fsmn_vad.process(samples, timestamp)
        return self._fsmn_vad.has_speech_segment()

    def get_speech_segments(self) -> list:
        """
        获取所有检测到的语音段

        Returns:
            语音段列表
        """
        with self._lock:
            if self._model_type == "fsmn_vad":
                segments = []
                while self._fsmn_vad.has_speech_segment():
                    seg = self._fsmn_vad.get_latest_speech_segment()
                    if seg:
                        segments.append(seg)
                return segments
            else:
                if self.vad is None:
                    return []

                segments = []
                while not self.vad.empty():
                    speech_segment = self.vad.front
                    segments.append(speech_segment)
                    self.vad.pop()

                return segments

    def get_latest_speech_segment(self) -> Optional[Union['SpeechSegmentWrapper', 'FSMNSpeechSegment']]:
        """
        获取最新的语音段

        Returns:
            语音段对象，如果没有则返回None
        """
        with self._lock:
            if self._model_type == "fsmn_vad":
                return self._fsmn_vad.get_latest_speech_segment()
            else:
                if self.vad is None or self.vad.empty():
                    return None

                speech_segment = self.vad.front
                # 在 pop 之前创建包装器，复制 samples 数据
                wrapper = SpeechSegmentWrapper(speech_segment, sample_rate=self.config.sample_rate)
                self.vad.pop()
                return wrapper

    def flush(self):
        """刷新VAD缓冲区，强制输出剩余的语音段"""
        with self._lock:
            if self._model_type == "fsmn_vad":
                if self._fsmn_vad is not None:
                    self._fsmn_vad.flush()
            else:
                if self.vad is not None:
                    self.vad.flush()

    def reset(self):
        """重置VAD状态"""
        with self._lock:
            if self._model_type == "fsmn_vad":
                if self._fsmn_vad is not None:
                    self._fsmn_vad.reset()
            else:
                if self.vad is not None:
                    self.vad.reset()

    def get_stats(self) -> dict:
        """获取VAD统计信息"""
        with self._lock:
            if self._model_type == "fsmn_vad":
                if self._fsmn_vad is None:
                    return {"status": "not_initialized", "model_type": "fsmn_vad"}
                stats = self._fsmn_vad.get_stats()
                stats["model_type"] = "fsmn_vad"
                return stats
            else:
                if self.vad is None:
                    return {"status": "not_initialized", "model_type": "silero_vad"}

                return {
                    "status": "initialized",
                    "model_type": "silero_vad",
                    "is_empty": self.vad.empty(),
                    "buffer_size_seconds": self.config.vad_buffer_size_seconds
                }
