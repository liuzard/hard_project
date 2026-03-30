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
        config['output']['directory'] = Path(config['output']['directory'])

        # 处理 FSMN-VAD 配置路径
        if 'fsmn_vad' in config['vad'] and 'model_dir' in config['vad']['fsmn_vad']:
            config['vad']['fsmn_vad']['model_dir'] = Path(config['vad']['fsmn_vad']['model_dir'])

        # 处理ASR配置：支持新旧两种格式
        # 新格式：model_dir 在 models 下面
        # 旧格式：model_dir 直接在 asr 下面
        if 'models' in config['asr']:
            # 新格式：转换所有预配置模型的路径
            for model_name, model_config in config['asr']['models'].items():
                if 'model_dir' in model_config:
                    config['asr']['models'][model_name]['model_dir'] = Path(model_config['model_dir'])
        else:
            # 旧格式：直接转换 model_dir（向后兼容）
            if 'model_dir' in config['asr']:
                config['asr']['model_dir'] = Path(config['asr']['model_dir'])

        return config

    def save(self):
        """保存配置到文件"""
        # 将Path对象转换回字符串
        config_copy = self._config.copy()
        config_copy['vad']['model_path'] = str(config_copy['vad']['model_path'])
        config_copy['output']['directory'] = str(config_copy['output']['directory'])

        # 处理 FSMN-VAD 配置路径转换
        if 'fsmn_vad' in config_copy['vad'] and 'model_dir' in config_copy['vad']['fsmn_vad']:
            if isinstance(config_copy['vad']['fsmn_vad']['model_dir'], Path):
                config_copy['vad']['fsmn_vad']['model_dir'] = str(config_copy['vad']['fsmn_vad']['model_dir'])

        # 处理ASR配置路径转换
        if 'models' in config_copy['asr']:
            # 新格式：转换所有预配置模型的路径
            for model_name, model_config in config_copy['asr']['models'].items():
                if 'model_dir' in model_config and isinstance(model_config['model_dir'], Path):
                    config_copy['asr']['models'][model_name]['model_dir'] = str(model_config['model_dir'])
        else:
            # 旧格式：直接转换 model_dir
            if 'model_dir' in config_copy['asr'] and isinstance(config_copy['asr']['model_dir'], Path):
                config_copy['asr']['model_dir'] = str(config_copy['asr']['model_dir'])

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
    def vad_model_type(self) -> str:
        """VAD模型类型（silero_vad, fsmn_vad）"""
        return self._config['vad'].get('model_type', 'silero_vad')

    @property
    def fsmn_vad_model_dir(self) -> Path:
        """FSMN-VAD模型目录"""
        return self._config['vad'].get('fsmn_vad', {}).get('model_dir', Path('./models/01-vad/speech_fsmn_vad_zh-cn-16k-common-onnx'))

    @property
    def fsmn_vad_quantize(self) -> bool:
        """FSMN-VAD是否使用量化模型"""
        return self._config['vad'].get('fsmn_vad', {}).get('quantize', True)

    @property
    def fsmn_vad_max_end_sil(self) -> int:
        """FSMN-VAD最大结尾静音时长（毫秒）"""
        return self._config['vad'].get('fsmn_vad', {}).get('max_end_sil', 800)

    @property
    def fsmn_vad_num_threads(self) -> int:
        """FSMN-VAD线程数"""
        return self._config['vad'].get('fsmn_vad', {}).get('intra_op_num_threads', 4)

    @property
    def asr_model_type(self) -> str:
        """ASR模型类型（paraformer-zh、sense-voice等）"""
        return self._config['asr'].get('model_type', 'paraformer-zh')

    @property
    def _asr_model_config(self) -> Dict[str, Any]:
        """获取当前模型配置"""
        model_type = self.asr_model_type
        models_config = self._config['asr'].get('models', {})

        # 如果有预配置的模型列表，从列表中获取
        if model_type in models_config:
            return models_config[model_type]

        # 兼容旧配置格式（直接在asr下配置）
        return {
            'model_dir': self._config['asr'].get('model_dir', './models/02-asr/sherpa-onnx-paraformer-zh-2023-09-14'),
            'model_file': self._config['asr'].get('model_file', 'model.int8.onnx'),
            'tokens_file': self._config['asr'].get('tokens_file', 'tokens.txt')
        }

    @property
    def asr_model_dir(self) -> Path:
        """ASR模型目录"""
        return Path(self._asr_model_config['model_dir'])

    @property
    def asr_model_file(self) -> str:
        """ASR模型文件名（传统模型使用）"""
        return self._asr_model_config.get('model_file', '')

    @property
    def asr_tokens_file(self) -> str:
        """ASR tokens文件名（传统模型使用）"""
        return self._asr_model_config.get('tokens_file', '')

    @property
    def asr_num_threads(self) -> int:
        """ASR线程数"""
        return self._config['asr']['num_threads']

    @property
    def asr_use_itn(self) -> bool:
        """是否启用ITN（Inverse Text Normalization）"""
        return self._config['asr'].get('use_itn', True)

    @property
    def asr_model_path(self) -> Path:
        """完整的ASR模型路径"""
        return self.asr_model_dir / self.asr_model_file

    @property
    def asr_tokens_path(self) -> Path:
        """完整的ASR tokens路径"""
        return self.asr_model_dir / self.asr_tokens_file

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

        # 根据VAD模型类型检查模型文件
        vad_type = self.vad_model_type.lower()
        if vad_type == "fsmn_vad":
            # FSMN-VAD 检查模型目录
            if not self.fsmn_vad_model_dir.exists():
                errors.append(f"FSMN-VAD模型目录不存在: {self.fsmn_vad_model_dir}")
            else:
                # 检查模型文件
                model_file = self.fsmn_vad_model_dir / "model_quant.onnx" if self.fsmn_vad_quantize else self.fsmn_vad_model_dir / "model.onnx"
                if not model_file.exists():
                    errors.append(f"FSMN-VAD模型文件不存在: {model_file}")
        else:
            # Silero VAD 检查模型文件
            if not self.vad_model_path.exists():
                errors.append(f"VAD模型文件不存在: {self.vad_model_path}")

        # 根据模型类型检查 ASR 模型文件
        model_type = self.asr_model_type.lower()
        if model_type == "funasr-nano":
            # FunASR-nano 使用多文件结构
            model_config = self._asr_model_config
            model_dir = self.asr_model_dir

            encoder_adaptor = model_dir / model_config.get('encoder_adaptor', 'encoder_adaptor.int8.onnx')
            llm = model_dir / model_config.get('llm', 'llm.int8.onnx')
            embedding = model_dir / model_config.get('embedding', 'embedding.int8.onnx')
            tokenizer_dir = model_dir / model_config.get('tokenizer_dir', 'Qwen3-0.6B')

            if not encoder_adaptor.exists():
                errors.append(f"FunASR-nano encoder_adaptor 不存在: {encoder_adaptor}")
            if not llm.exists():
                errors.append(f"FunASR-nano llm 不存在: {llm}")
            if not embedding.exists():
                errors.append(f"FunASR-nano embedding 不存在: {embedding}")
            if not tokenizer_dir.exists():
                errors.append(f"FunASR-nano tokenizer 目录不存在: {tokenizer_dir}")
        else:
            # 传统模型（paraformer, sense-voice 等）
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
