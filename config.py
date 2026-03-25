"""
配置管理模块
加载和管理项目配置参数
"""

import json
from pathlib import Path
from typing import Dict, Any, List


class Config:
    """配置管理类"""

    def __init__(self, config_path: str = "config.json"):
        """
        初始化配置

        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # 转换路径为Path对象
        config['vad']['model_path'] = Path(config['vad']['model_path'])
        config['asr']['model_dir'] = Path(config['asr']['model_dir'])
        config['output']['directory'] = Path(config['output']['directory'])

        return config

    def save(self):
        """保存配置到文件"""
        # 将Path对象转换回字符串
        config_copy = self._config.copy()
        config_copy['vad']['model_path'] = str(config_copy['vad']['model_path'])
        config_copy['asr']['model_dir'] = str(config_copy['asr']['model_dir'])
        config_copy['output']['directory'] = str(config_copy['output']['directory'])

        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config_copy, f, indent=2, ensure_ascii=False)

    @property
    def audio_device_index(self) -> int:
        """音频设备索引"""
        return self._config['audio']['device_index']

    @audio_device_index.setter
    def audio_device_index(self, value: int):
        self._config['audio']['device_index'] = value

    @property
    def sample_rate(self) -> int:
        """采样率"""
        return self._config['audio']['sample_rate']

    @property
    def channels(self) -> int:
        """声道数"""
        return self._config['audio']['channels']

    @property
    def chunk_size(self) -> int:
        """每次读取的帧数"""
        return self._config['audio']['chunk_size']

    @property
    def audio_format(self) -> str:
        """音频格式"""
        return self._config['audio']['format']

    @property
    def vad_model_path(self) -> Path:
        """VAD模型路径"""
        return self._config['vad']['model_path']

    @property
    def vad_threshold(self) -> float:
        """VAD阈值"""
        return self._config['vad']['threshold']

    @property
    def vad_min_silence_duration(self) -> float:
        """VAD最小静音时长"""
        return self._config['vad']['min_silence_duration']

    @property
    def vad_min_speech_duration(self) -> float:
        """VAD最小语音时长"""
        return self._config['vad']['min_speech_duration']

    @property
    def vad_buffer_size_seconds(self) -> float:
        """VAD缓冲区大小（秒）"""
        return self._config['vad']['buffer_size_seconds']

    @property
    def vad_num_threads(self) -> int:
        """VAD线程数"""
        return self._config['vad']['num_threads']

    @property
    def vad_window_size(self) -> int:
        """VAD窗口大小"""
        return self._config['vad'].get('window_size', 512)

    @property
    def asr_model_dir(self) -> Path:
        """ASR模型目录"""
        return self._config['asr']['model_dir']

    @property
    def asr_model_file(self) -> str:
        """ASR模型文件名"""
        return self._config['asr']['model_file']

    @property
    def asr_tokens_file(self) -> str:
        """ASR tokens文件名"""
        return self._config['asr']['tokens_file']

    @property
    def asr_language(self) -> str:
        """ASR语言设置"""
        return self._config['asr']['language']

    @property
    def asr_use_itn(self) -> bool:
        """是否使用ITN（逆文本标准化）"""
        return self._config['asr']['use_itn']

    @property
    def asr_num_threads(self) -> int:
        """ASR线程数"""
        return self._config['asr']['num_threads']

    @property
    def asr_model_path(self) -> Path:
        """完整的ASR模型路径"""
        return self._config['asr']['model_dir'] / self._config['asr']['model_file']

    @property
    def asr_tokens_path(self) -> Path:
        """完整的ASR tokens路径"""
        return self._config['asr']['model_dir'] / self._config['asr']['tokens_file']

    @property
    def keywords(self) -> List[str]:
        """关键词列表"""
        return self._config['keywords']

    @keywords.setter
    def keywords(self, value: List[str]):
        self._config['keywords'] = value

    @property
    def output_directory(self) -> Path:
        """输出目录"""
        return self._config['output']['directory']

    @property
    def buffer_seconds(self) -> int:
        """缓冲区秒数（前后各多少秒）"""
        return self._config['output']['buffer_seconds']

    @property
    def save_metadata(self) -> bool:
        """是否保存元数据"""
        return self._config['output']['save_metadata']

    @property
    def logging_level(self) -> str:
        """日志级别"""
        return self._config['logging']['level']

    @property
    def console_logging(self) -> bool:
        """是否启用控制台日志"""
        return self._config['logging']['console']

    def get_audio_buffer_duration(self) -> int:
        """获取音频缓冲区总时长（秒）"""
        return self.buffer_seconds * 2

    def validate(self) -> bool:
        """验证配置是否有效"""
        errors = []

        # 检查模型文件是否存在
        if not self.vad_model_path.exists():
            errors.append(f"VAD模型文件不存在: {self.vad_model_path}")

        if not self.asr_model_path.exists():
            errors.append(f"ASR模型文件不存在: {self.asr_model_path}")

        if not self.asr_tokens_path.exists():
            errors.append(f"ASR tokens文件不存在: {self.asr_tokens_path}")

        # 检查关键词列表
        if not self.keywords:
            errors.append("关键词列表为空")

        # 检查音频参数
        if self.sample_rate <= 0:
            errors.append(f"无效的采样率: {self.sample_rate}")

        if self.channels <= 0:
            errors.append(f"无效的声道数: {self.channels}")

        if self.chunk_size <= 0:
            errors.append(f"无效的chunk大小: {self.chunk_size}")

        if errors:
            print("配置验证失败:")
            for error in errors:
                print(f"  - {error}")
            return False

        return True


# 全局配置实例
_config_instance = None


def get_config(config_path: str = "config.json") -> Config:
    """获取配置实例（单例模式）"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance
