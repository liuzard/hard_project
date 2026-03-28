#!/usr/bin/env python3
"""
简单的录音测试脚本
直接录制指定时长音频并保存为WAV文件
"""

import sys
import time
import wave
from datetime import datetime
from pathlib import Path

try:
    import pyaudio
except ImportError:
    print("[ERROR] 需要安装 pyaudio")
    print("请运行: pip install pyaudio")
    sys.exit(1)

# 固定参数
DURATION = 120  # 录音时长（秒）
SAMPLE_RATE = 16000  # 采样率 16kHz
CHANNELS = 1  # 单声道
FORMAT = pyaudio.paInt16  # 16-bit PCM
CHUNK = 1600  # 每次读取帧数

# 输出目录
OUTPUT_DIR = Path(__file__).parent.parent / "resources"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 生成文件名
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = OUTPUT_DIR / f"recording_{DURATION}s_{timestamp}.wav"

print("=" * 60)
print(f"{DURATION}秒录音测试")
print("=" * 60)
print(f"\n录音参数:")
print(f"  - 时长: {DURATION} 秒")
print(f"  - 采样率: {SAMPLE_RATE} Hz")
print(f"  - 声道: {CHANNELS}")
print(f"  - 格式: 16-bit PCM")
print(f"  - 输出文件: {OUTPUT_FILE}")

# 初始化 PyAudio
print("\n正在初始化音频设备...")
p = pyaudio.PyAudio()

# 查找可用的输入设备
device_index = None
print("\n可用的录音设备:")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info['maxInputChannels'] > 0:
        print(f"  设备 {i}: {info['name']}")
        # 自动选择USB设备或hw:2设备
        if device_index is None:
            if "USB" in info['name'] or "hw:2" in str(info['name']).lower():
                device_index = i
                print(f"       → 自动选择此设备")

# 如果没找到USB设备，使用第一个可用设备
if device_index is None:
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            device_index = i
            print(f"\n使用第一个可用设备: {info['name']} (index={i})")
            break

if device_index is None:
    print("\n[ERROR] 未找到可用的录音设备")
    p.terminate()
    sys.exit(1)

print(f"\n使用设备索引: {device_index}")
print("\n准备开始录音...")
print("提示：请对着麦克风说话")
print("\n按 Enter 键开始录音...")

input()

print(f"\n🎤 开始录音 {DURATION} 秒...")
print("请现在开始说话\n")

try:
    # 打开音频流
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=CHUNK
    )

    # 录制音频
    frames = []
    start_time = time.time()

    while time.time() - start_time < DURATION:
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)

        # 显示进度（每秒更新一次）
        elapsed = int(time.time() - start_time)
        remaining = DURATION - elapsed
        progress = (elapsed / DURATION) * 100

        # 进度条
        bar_length = 40
        filled = int(bar_length * elapsed / DURATION)
        bar = '█' * filled + '░' * (bar_length - filled)

        print(f"\r[{bar}] {progress:.0f}% ({elapsed}s/{DURATION}s, 剩余{remaining}s)", end='', flush=True)

    # 录音完成
    print("\n\n✓ 录音完成")

    # 停止流
    stream.stop_stream()
    stream.close()

except Exception as e:
    print(f"\n[ERROR] 录音失败: {e}")
    import traceback
    traceback.print_exc()
    p.terminate()
    sys.exit(1)

# 获取采样宽度（在 terminate 之前）
sample_width = p.get_sample_size(FORMAT)
p.terminate()

# 保存为WAV文件
print(f"\n正在保存到: {OUTPUT_FILE}")

try:
    wf = wave.open(str(OUTPUT_FILE), 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(sample_width)
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    # 显示文件信息
    file_size = Path(OUTPUT_FILE).stat().st_size
    file_size_mb = file_size / (1024 * 1024)

    print(f"✓ 文件已保存")
    print(f"\n文件信息:")
    print(f"  - 文件名: {OUTPUT_FILE}")
    print(f"  - 大小: {file_size_mb:.2f} MB ({file_size:,} bytes)")
    print(f"  - 时长: {DURATION} 秒")
    print(f"  - 采样率: {SAMPLE_RATE} Hz")
    print(f"  - 声道: {CHANNELS}")
    print(f"  - 位深: 16-bit")

    # 检查音频数据
    import numpy as np
    audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
    print(f"\n音频检查:")
    print(f"  - 样本数: {len(audio_data):,}")
    print(f"  - 最大值: {audio_data.max()}")
    print(f"  - 最小值: {audio_data.min()}")
    print(f"  - 标准差: {audio_data.std():.2f}")

    if audio_data.std() < 100:
        print(f"\n⚠️  警告: 音频信号很弱！")
        print("   请检查:")
        print("   1. 麦克风是否正确连接")
        print("   2. 麦克风音量是否太低")
        print("   3. 录音时是否真的在说话")
    else:
        print(f"\n✓ 音频信号正常")

except Exception as e:
    print(f"\n[ERROR] 保存文件失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print(f"\n✓ 录音成功完成！")
print(f"\n播放录音:")
print(f"  aplay {OUTPUT_FILE}")
print("\n或使用主程序进行语音识别:")
print(f"  python run.py -f {OUTPUT_FILE}")
print("\n" + "=" * 60)
