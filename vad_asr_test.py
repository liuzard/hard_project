#!/usr/bin/env python3
"""
ASR测试脚本 (VAD 增强版)
读取WAV文件 -> VAD自动切音断句 -> SenseVoice-Small逐句识别 -> 拼接结果
"""

import sys
import argparse
from pathlib import Path
import wave
import numpy as np

try:
    import sherpa_onnx
except ImportError:
    print("[ERROR] 需要安装 sherpa-onnx")
    print("请运行: pip install sherpa-onnx")
    sys.exit(1)


def load_wav_file(wav_path):
    """加载WAV文件，并强制转换为单声道 float32 格式"""
    wav_path = Path(wav_path)
    if not wav_path.exists():
        raise FileNotFoundError(f"文件不存在: {wav_path}")

    print(f"\n[1/3] 正在加载音频: {wav_path.name}")
    try:
        wf = wave.open(str(wav_path), 'rb')
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()

        frames = wf.readframes(n_frames)
        wf.close()

        if sample_width == 2:
            dtype = np.int16
        elif sample_width == 4:
            dtype = np.int32
        else:
            raise ValueError(f"不支持的位深: {sample_width}")

        audio_data = np.frombuffer(frames, dtype=dtype)

        # 转换为单声道
        if n_channels > 1:
            audio_data = audio_data.reshape(-1, n_channels)[:, 0]

        # 归一化为 float32 (sherpa-onnx 要求)
        audio_data = audio_data.astype(np.float32) / np.iinfo(dtype).max

        print(f"  - 采样率: {sample_rate} Hz | 时长: {n_frames / sample_rate:.2f} 秒")
        return audio_data, sample_rate

    except Exception as e:
        raise Exception(f"加载WAV文件失败: {e}")


def create_vad_detector(config):
    """创建 VAD 语音端点检测器"""
    print("\n[2/3] 正在加载 VAD 模型...")
    if not config.vad_model_path.exists():
        raise FileNotFoundError(f"VAD模型文件不存在: {config.vad_model_path}")

    # Silero VAD v6 使用 SileroVadModelConfig
    silero_vad_config = sherpa_onnx.SileroVadModelConfig(
        model=str(config.vad_model_path),
        threshold=config.vad_threshold,
        min_silence_duration=config.vad_min_silence_duration,
        min_speech_duration=config.vad_min_speech_duration,
        window_size=config.vad_window_size
    )

    vad_config = sherpa_onnx.VadModelConfig(
        silero_vad=silero_vad_config,
        sample_rate=config.sample_rate,
        num_threads=config.vad_num_threads
    )

    vad = sherpa_onnx.VoiceActivityDetector(
        vad_config,
        buffer_size_in_seconds=config.vad_buffer_size_seconds
    )

    print("  ✓ VAD 模型加载完成 (Silero VAD v6)")
    return vad


def create_asr_recognizer(config):
    """创建 ASR 识别器"""
    print("\n[3/3] 正在加载 ASR 模型...")
    if not config.asr_model_path.exists():
        raise FileNotFoundError(f"ASR模型文件不存在: {config.asr_model_path}")

    recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=str(config.asr_model_path),
        tokens=str(config.asr_tokens_path),
        num_threads=config.asr_num_threads,
        use_itn=config.asr_use_itn,
        language=config.asr_language,
        debug=False,
    )
    print("  ✓ ASR 模型加载完成")
    return recognizer


def recognize_audio_with_vad(vad, recognizer, audio_data, sample_rate, window_size):
    """使用 VAD 切片并进行分段识别"""
    print(f"\n开始流水线识别 (VAD切片 -> ASR识别)...")

    # 优化喂数据逻辑：每次送入 0.1秒 (1600个采样点) 的数据，减少 Python 循环开销
    chunk_size = int(sample_rate * 0.1)
    segments = []

    for i in range(0, len(audio_data), chunk_size):
        chunk = audio_data[i: i + chunk_size]
        vad.accept_waveform(chunk)

        while not vad.empty():
            segments.append(vad.front.samples)
            vad.pop()

    # 冲刷 VAD 缓存
    vad.flush()
    while not vad.empty():
        segments.append(vad.front.samples)
        vad.pop()

    total_segments = len(segments)
    if total_segments == 0:
        print("  ⚠️ VAD 未检测到任何有效语音！请检查音频音量或调低 VAD threshold。")
        return ""

    print(f"  - VAD 成功将音频切割为 {total_segments} 个有效片段。")

    # 2. 逐个片段送入 SenseVoice 识别
    full_text = []
    for i, segment_samples in enumerate(segments):
        duration = len(segment_samples) / sample_rate

        # 跳过极短的无效噪音片段
        if duration < 0.2:
            continue

        stream = recognizer.create_stream()
        stream.accept_waveform(sample_rate, segment_samples)
        recognizer.decode_stream(stream)

        text = stream.result.text.strip()
        if text:
            # 打印片段的准确时长，方便排查截断问题
            print(f"    ▶ 片段 {i + 1}/{total_segments} ({duration:.2f}s): {text}")
            full_text.append(text)

    # SenseVoice 已自带标点，直接拼接即可（为防粘连可加个空格）
    final_result = " ".join(full_text) if full_text else ""
    return final_result


def print_result(text, audio_data, sample_rate):
    """打印最终结果"""
    duration = len(audio_data) / sample_rate
    print("\n" + "=" * 60)
    print("最终识别结果")
    print("=" * 60)

    if text:
        print(f"\n「{text}」\n")
        print(f"统计:")
        print(f"  - 文字长度: {len(text)} 字符")
        print(f"  - 音频时长: {duration:.2f} 秒")
    else:
        print("\n✗ 无有效识别结果\n")
    print("=" * 60)


class Config:
    """配置类：支持解析 VAD 节点"""

    def __init__(self, config_path):
        import json
        with open(config_path, 'r') as f:
            self._config = json.load(f)
        self._config['asr']['model_dir'] = Path(self._config['asr']['model_dir'])

        # 兼容相对路径的 VAD
        if 'vad' in self._config:
            self._config['vad']['model_path'] = Path(self._config['vad']['model_path'])

    def validate(self):
        return Path(self._config['asr']['model_dir'] / self._config['asr']['model_file']).exists()

    @property
    def sample_rate(self): return self._config['audio']['sample_rate']

    # --- VAD 配置 ---
    @property
    def vad_model_path(self): return self._config['vad']['model_path']

    @property
    def vad_threshold(self): return self._config['vad']['threshold']

    @property
    def vad_min_silence_duration(self): return self._config['vad']['min_silence_duration']

    @property
    def vad_min_speech_duration(self): return self._config['vad']['min_speech_duration']

    @property
    def vad_buffer_size_seconds(self): return self._config['vad']['buffer_size_seconds']

    @property
    def vad_num_threads(self): return self._config['vad']['num_threads']

    @property
    def vad_window_size(self): return self._config['vad']['window_size']

    # --- ASR 配置 ---
    @property
    def asr_model_path(self): return self._config['asr']['model_dir'] / self._config['asr']['model_file']

    @property
    def asr_tokens_path(self): return self._config['asr']['model_dir'] / self._config['asr']['tokens_file']

    @property
    def asr_num_threads(self): return self._config['asr']['num_threads']

    @property
    def asr_language(self): return self._config['asr']['language']

    @property
    def asr_use_itn(self): return self._config['asr']['use_itn']


def main():
    parser = argparse.ArgumentParser(description='ASR测试脚本 (含 VAD 自动断句)')
    parser.add_argument('files', nargs='+', help='WAV文件路径')
    parser.add_argument('-c', '--config', type=str, default='config.json', help='配置文件路径')
    args = parser.parse_args()

    try:
        config = Config(args.config)
        if not config.validate():
            print("[ERROR] ASR 模型文件验证失败，请检查 config.json 路径")
            return 1

        vad = create_vad_detector(config)
        recognizer = create_asr_recognizer(config)

    except Exception as e:
        print(f"[初始化失败] {e}")
        return 1

    for wav_file in args.files:
        try:
            audio_data, sample_rate = load_wav_file(wav_file)

            # 核心执行：将 VAD 实例、ASR 实例和音频数据串联
            text = recognize_audio_with_vad(
                vad=vad,
                recognizer=recognizer,
                audio_data=audio_data,
                sample_rate=sample_rate,
                window_size=config.vad_window_size
            )

            print_result(text, audio_data, sample_rate)

        except Exception as e:
            print(f"\n[处理文件失败] {wav_file}: {e}")
            continue

    return 0


if __name__ == "__main__":
    sys.exit(main())