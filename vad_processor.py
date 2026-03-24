"""
VAD（语音活动检测）处理模块
使用tenVAD模型进行语音活动检测
"""

import sherpa_onnx
import numpy as np
from pathlib import Path
from typing import Optional
from config import get_config


class VADProcessor:
    """VAD处理器"""

    def __init__(self):
        """初始化VAD处理器"""
        self.config = get_config()
        self.vad = None
        self._init_vad()

    def _init_vad(self):
        """初始化VAD模型"""
        print("[INFO] 正在加载VAD模型...")

        # 验证模型文件存在
        if not self.config.vad_model_path.exists():
            raise FileNotFoundError(f"VAD模型文件不存在: {self.config.vad_model_path}")

        # 创建VAD配置
        vad_config = sherpa_onnx.VadModelConfig()
        vad_config.silero_vad.model = str(self.config.vad_model_path)
        vad_config.silero_vad.threshold = self.config.vad_threshold
        vad_config.silero_vad.min_silence_duration = self.config.vad_min_silence_duration
        vad_config.silero_vad.min_speech_duration = self.config.vad_min_speech_duration
        vad_config.silero_vad.max_speech_duration = self.config.vad_max_speech_duration
        vad_config.sample_rate = self.config.sample_rate
        vad_config.num_threads = self.config.vad_num_threads

        # 创建VAD实例
        self.vad = sherpa_onnx.VoiceActivityDetector(
            vad_config,
            buffer_size_in_seconds=self.config.vad_buffer_size_seconds
        )

        print("[INFO] VAD模型加载完成")
        print(f"       - 阈值: {self.config.vad_threshold}")
        print(f"       - 最小静音时长: {self.config.vad_min_silence_duration}s")
        print(f"       - 最小语音时长: {self.config.vad_min_speech_duration}s")
        print(f"       - 最大语音时长: {self.config.vad_max_speech_duration}s")
        print(f"       - 缓冲区大小: {self.config.vad_buffer_size_seconds}s")

    def process(self, samples: np.ndarray) -> bool:
        """
        处理音频数据，检测是否有语音活动

        Args:
            samples: 音频数据（float32 numpy数组，归一化到[-1, 1]）

        Returns:
            True表示检测到语音，False表示没有语音
        """
        if self.vad is None:
            return False

        # 将音频数据送入VAD
        self.vad.accept_waveform(samples)

        # 检查是否有语音段
        return not self.vad.empty()

    def get_speech_segments(self) -> list:
        """
        获取所有检测到的语音段

        Returns:
            语音段列表
        """
        if self.vad is None:
            return []

        segments = []
        while not self.vad.empty():
            speech_segment = self.vad.front
            segments.append(speech_segment)
            self.vad.pop()

        return segments

    def get_latest_speech_segment(self) -> Optional['sherpa_onnx.SpeechSegment']:
        """
        获取最新的语音段

        Returns:
            语音段对象，如果没有则返回None
        """
        if self.vad is None or self.vad.empty():
            return None

        speech_segment = self.vad.front
        self.vad.pop()
        return speech_segment

    def flush(self):
        """刷新VAD缓冲区，强制输出剩余的语音段"""
        if self.vad is not None:
            self.vad.flush()

    def reset(self):
        """重置VAD状态"""
        if self.vad is not None:
            self.vad.reset()

    def get_stats(self) -> dict:
        """获取VAD统计信息"""
        if self.vad is None:
            return {"status": "not_initialized"}

        return {
            "status": "initialized",
            "is_empty": self.vad.empty(),
            "buffer_size_seconds": self.config.vad_buffer_size_seconds
        }
