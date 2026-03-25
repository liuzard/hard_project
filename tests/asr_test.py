#!/usr/bin/env python3
"""
ASR测试脚本
读取WAV文件并进行语音识别，打印识别结果
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

from config import get_config


def load_wav_file(wav_path):
    """
    加载WAV文件

    Args:
        wav_path: WAV文件路径

    Returns:
        (音频数据numpy数组, 采样率)
    """
    wav_path = Path(wav_path)

    if not wav_path.exists():
        raise FileNotFoundError(f"文件不存在: {wav_path}")

    print(f"\n正在加载: {wav_path.name}")

    try:
        wf = wave.open(str(wav_path), 'rb')

        # 获取音频参数
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()

        print(f"  - 声道数: {n_channels}")
        print(f"  - 采样率: {sample_rate} Hz")
        print(f"  - 位深: {sample_width * 8} bit")
        print(f"  - 总帧数: {n_frames}")
        print(f"  - 时长: {n_frames / sample_rate:.2f} 秒")

        # 读取音频数据
        frames = wf.readframes(n_frames)
        wf.close()

        # 转换为numpy数组
        if sample_width == 2:  # 16-bit
            dtype = np.int16
        elif sample_width == 4:  # 32-bit
            dtype = np.int32
        else:
            raise ValueError(f"不支持的位深: {sample_width}")

        audio_data = np.frombuffer(frames, dtype=dtype)

        # 如果是立体声，转换为单声道（取左声道）
        if n_channels > 1:
            print(f"  - 转换为单声道")
            audio_data = audio_data.reshape(-1, n_channels)
            audio_data = audio_data[:, 0]

        # 转换为float32并归一化
        audio_data = audio_data.astype(np.float32) / np.iinfo(dtype).max

        # 音频统计
        print(f"\n音频数据统计:")
        print(f"  - 样本数: {len(audio_data):,}")
        print(f"  - 最大值: {audio_data.max():.4f}")
        print(f"  - 最小值: {audio_data.min():.4f}")
        print(f"  - 平均值: {audio_data.mean():.6f}")
        print(f"  - 标准差: {audio_data.std():.6f}")

        return audio_data, sample_rate

    except Exception as e:
        raise Exception(f"加载WAV文件失败: {e}")


def create_asr_recognizer(config):
    """
    创建ASR识别器

    Args:
        config: 配置对象

    Returns:
        ASR识别器
    """
    print("\n正在加载ASR模型...")

    # 验证模型文件
    if not config.asr_model_path.exists():
        raise FileNotFoundError(f"ASR模型文件不存在: {config.asr_model_path}")

    if not config.asr_tokens_path.exists():
        raise FileNotFoundError(f"ASR tokens文件不存在: {config.asr_tokens_path}")

    # 创建识别器
    recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=str(config.asr_model_path),
        tokens=str(config.asr_tokens_path),
        num_threads=config.asr_num_threads,
        use_itn=config.asr_use_itn,
        language=config.asr_language,
        debug=False,
    )

    print("✓ ASR模型加载完成")
    print(f"  - 模型: {config.asr_model_file}")
    print(f"  - 语言: {config.asr_language}")
    print(f"  - ITN: {config.asr_use_itn}")

    return recognizer


def recognize_audio(recognizer, audio_data, sample_rate):
    """
    识别音频

    Args:
        recognizer: ASR识别器
        audio_data: 音频数据（float32 numpy数组）
        sample_rate: 采样率

    Returns:
        识别文本
    """
    print(f"\n正在识别...")

    # 创建识别流
    stream = recognizer.create_stream()

    # 送入音频数据
    stream.accept_waveform(sample_rate, audio_data)

    # 执行识别
    recognizer.decode_stream(stream)

    # 获取结果
    text = stream.result.text.strip()

    return text


def print_result(text, audio_data, sample_rate):
    """
    打印识别结果

    Args:
        text: 识别文本
        audio_data: 音频数据
        sample_rate: 采样率
    """
    duration = len(audio_data) / sample_rate
    std_dev = audio_data.std()

    print("\n" + "=" * 60)
    print("识别结果")
    print("=" * 60)

    if text:
        print(f"\n✓ 识别成功")
        print(f"\n识别文本:")
        print(f"  「{text}」")
        print(f"\n详细信息:")
        print(f"  - 文字长度: {len(text)} 字符")
        print(f"  - 音频时长: {duration:.2f} 秒")
        print(f"  - 识别速度: {len(text) / duration:.2f} 字/秒")
    else:
        print(f"\n✗ 识别失败")
        print(f"\n可能原因:")

        # 检查音频信号强度
        if std_dev < 0.01:
            print(f"  ⚠️ 音频信号太弱（标准差: {std_dev:.6f}）")
            print(f"     正常范围应 > 0.01")
            print(f"     录音脚本应该已警告")
        else:
            print(f"  - 音频信号正常（标准差: {std_dev:.6f}）")
            print(f"  - 音频中没有清晰的语音")
            print(f"  - 音频质量太差（噪声太大）")
            print(f"  - 语言不匹配（当前: {get_config().asr_language}）")

    print("\n" + "=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='ASR测试脚本 - 识别WAV文件中的语音',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 识别单个文件
  python3 asr_test.py recording.wav

  # 识别多个文件
  python3 asr_test.py file1.wav file2.wav file3.wav

  # 显示详细信息
  python3 asr_test.py recording.wav -v

  # 指定配置文件
  python3 asr_test.py recording.wav -c custom_config.json
        """
    )

    parser.add_argument(
        'files',
        nargs='+',
        help='WAV文件路径（可以指定多个）'
    )

    parser.add_argument(
        '-c', '--config',
        type=str,
        default='config.json',
        help='配置文件路径（默认: config.json）'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细信息'
    )

    args = parser.parse_args()

    # 加载配置
    try:
        config = Config(args.config)
    except Exception as e:
        print(f"[ERROR] 加载配置失败: {e}")
        return 1

    # 验证模型
    if not config.validate():
        print("[ERROR] 配置验证失败")
        return 1

    # 创建ASR识别器
    try:
        recognizer = create_asr_recognizer(config)
    except Exception as e:
        print(f"[ERROR] 创建ASR识别器失败: {e}")
        return 1

    # 处理每个文件
    files = args.files
    total_files = len(files)

    for idx, wav_file in enumerate(files, 1):
        print("\n" + "=" * 60)
        print(f"处理文件 [{idx}/{total_files}]: {wav_file}")
        print("=" * 60)

        try:
            # 加载音频文件
            audio_data, sample_rate = load_wav_file(wav_file)

            # 检查采样率
            if sample_rate != config.sample_rate:
                print(f"\n⚠️  警告: 采样率不匹配")
                print(f"   文件采样率: {sample_rate} Hz")
                print(f"   配置采样率: {config.sample_rate} Hz")
                print(f"   可能影响识别准确率")

            # 识别音频
            text = recognize_audio(recognizer, audio_data, sample_rate)

            # 打印结果
            print_result(text, audio_data, sample_rate)

            # 如果有多个文件，保存结果到文本文件
            if total_files > 1:
                result_file = Path(wav_file).stem + "_result.txt"
                with open(result_file, 'w', encoding='utf-8') as f:
                    if text:
                        f.write(text)
                    else:
                        f.write("(无识别结果)")
                print(f"\n结果已保存到: {result_file}")

        except Exception as e:
            print(f"\n[ERROR] 处理文件失败: {e}")
            import traceback
            traceback.print_exc()
            continue

    print("\n" + "=" * 60)
    print(f"✓ 处理完成: {total_files} 个文件")
    print("=" * 60)

    return 0


class Config:
    """简化的配置类"""
    def __init__(self, config_path):
        import json
        with open(config_path, 'r') as f:
            self._config = json.load(f)

        from pathlib import Path
        self._config['asr']['model_dir'] = Path(self._config['asr']['model_dir'])
        self._config['output']['directory'] = Path(self._config['output']['directory'])

    def validate(self):
        """验证配置"""
        return Path(self._config['asr']['model_dir'] / self._config['asr']['model_file']).exists()

    @property
    def sample_rate(self):
        return self._config['audio']['sample_rate']

    @property
    def asr_model_dir(self):
        return self._config['asr']['model_dir']

    @property
    def asr_model_file(self):
        return self._config['asr']['model_file']

    @property
    def asr_tokens_path(self):
        return self._config['asr']['model_dir'] / self._config['asr']['tokens_file']

    @property
    def asr_model_path(self):
        return self._config['asr']['model_dir'] / self._config['asr']['model_file']

    @property
    def asr_num_threads(self):
        return self._config['asr']['num_threads']

    @property
    def asr_language(self):
        return self._config['asr']['language']

    @property
    def asr_use_itn(self):
        return self._config['asr']['use_itn']


if __name__ == "__main__":
    sys.exit(main())
