"""
ASR（自动语音识别）处理模块
支持 Paraformer 和 SenseVoice 模型进行语音转文字

设计说明
--------
当前使用 sherpa_onnx.OfflineRecognizer，属于离线（batch）识别模式：
- 每个语音段（VAD 切分的结果）独立创建 stream、decode、读取结果。
- 这种方式实现简单，VAD 和 ASR 完全解耦，适合关键词检测这类"听一段识别一段"的场景。

支持的模型：
- Paraformer-zh: 中文语音识别，使用 from_paraformer()
- SenseVoice: 多语言识别，使用 from_sense_voice()

未来若需低延迟实时流式识别（边听边识别），需要切换到 OnlineRecognizer：
1. 创建单个持久化 OnlineStream，在主循环中持续 feed() 音频块。
2. 用 decode_stream() 逐步获取已解码的部分结果。
3. 关键词检测改为在增量文本上执行（而非等待整段结束）。
4. AudioBuffer 的时间戳逻辑不需要改变。
如无此类需求，当前设计已足够。
"""

import sherpa_onnx
import numpy as np
from pathlib import Path
from typing import Optional
from .config import get_config


class ASRProcessor:
    """ASR处理器（离线模式）"""

    def __init__(self):
        """初始化ASR处理器"""
        self.config = get_config()
        self.recognizer = None
        self.model_type = None
        self._init_asr()

    def _init_asr(self):
        """初始化ASR模型"""
        print("[INFO] 正在加载ASR模型...")

        # 验证模型文件存在
        if not self.config.asr_model_path.exists():
            raise FileNotFoundError(f"ASR模型文件不存在: {self.config.asr_model_path}")

        if not self.config.asr_tokens_path.exists():
            raise FileNotFoundError(f"ASR tokens文件不存在: {self.config.asr_tokens_path}")

        # 根据配置文件中的模型类型选择模型
        model_type = self.config.asr_model_type.lower()

        if model_type == "paraformer-zh" or model_type == "paraformer":
            # 使用 Paraformer 模型
            self._init_paraformer()
        elif model_type == "sense-voice" or model_type == "sensevoice":
            # 使用 SenseVoice 模型
            self._init_sense_voice()
        else:
            # 未知模型类型，尝试 Paraformer 作为默认
            print(f"[WARN] 未知的ASR模型类型: {model_type}，使用默认的 Paraformer 模型")
            self._init_paraformer()

    def _init_paraformer(self):
        """初始化 Paraformer 模型"""
        self.model_type = "paraformer"

        # 创建离线识别器（使用 Paraformer）
        self.recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
            paraformer=str(self.config.asr_model_path),
            tokens=str(self.config.asr_tokens_path),
            num_threads=self.config.asr_num_threads,
            sample_rate=16000,
            feature_dim=80,
            decoding_method="greedy_search",
            debug=False,
        )

        print("[INFO] ASR模型加载完成 (Paraformer-zh)")
        print(f"       - 模型类型: {self.config.asr_model_type}")
        print(f"       - 模型文件: {self.config.asr_model_file}")
        print(f"       - 线程数: {self.config.asr_num_threads}")

    def _init_sense_voice(self):
        """初始化 SenseVoice 模型"""
        self.model_type = "sense_voice"

        # 创建离线识别器（使用 SenseVoice）
        self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=str(self.config.asr_model_path),
            tokens=str(self.config.asr_tokens_path),
            num_threads=self.config.asr_num_threads,
            sample_rate=16000,
            feature_dim=80,
            decoding_method="greedy_search",
            debug=False,
            use_itn=self.config.asr_use_itn,  # 根据配置决定是否启用 ITN
        )

        print("[INFO] ASR模型加载完成 (SenseVoice)")
        print(f"       - 模型类型: {self.config.asr_model_type}")
        print(f"       - 模型文件: {self.config.asr_model_file}")
        print(f"       - 线程数: {self.config.asr_num_threads}")
        print(f"       - ITN启用: {self.config.asr_use_itn}")

    def process(self, samples: np.ndarray) -> str:
        """
        处理音频数据，进行语音识别

        Args:
            samples: 音频数据（float32 numpy数组，归一化到[-1, 1]）

        Returns:
            识别的文本，如果识别失败则返回空字符串
        """
        if self.recognizer is None:
            return ""

        try:
            # 创建识别流
            stream = self.recognizer.create_stream()

            # 送入音频数据
            stream.accept_waveform(self.config.sample_rate, samples)

            # 执行识别
            self.recognizer.decode_stream(stream)

            # 获取识别结果
            text = stream.result.text.strip()

            return text

        except Exception as e:
            print(f"[ERROR] ASR处理异常: {e}")
            return ""

    def process_with_duration(self, samples: np.ndarray) -> tuple:
        """
        处理音频数据，返回识别文本和时长

        Args:
            samples: 音频数据（float32 numpy数组，归一化到[-1, 1]）

        Returns:
            (识别文本, 音频时长秒数)
        """
        duration = len(samples) / self.config.sample_rate
        text = self.process(samples)
        return text, duration

    def is_ready(self) -> bool:
        """
        检查ASR是否已准备就绪

        Returns:
            True表示已就绪，False表示未就绪
        """
        return self.recognizer is not None
