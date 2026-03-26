"""
语音关键词检测系统
"""

from .config import Config, get_config
from .audio_buffer import AudioBuffer
from .vad_processor import VADProcessor
from .asr_processor import ASRProcessor
from .keyword_detector import KeywordDetector

# AudioRecorder 依赖 pyaudio，可选导入
try:
    from .audio_recorder import AudioRecorder, pcm_int16_to_float32
except ImportError:
    AudioRecorder = None
    pcm_int16_to_float32 = None

__all__ = [
    'Config',
    'get_config',
    'AudioBuffer',
    'AudioRecorder',
    'pcm_int16_to_float32',
    'VADProcessor',
    'ASRProcessor',
    'KeywordDetector',
]
