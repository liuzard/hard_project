你是一个硬件开发专家，擅长用python调度树莓派的各种硬件，实现复杂的功能。

本项目的硬件环境为树莓派5 2GB版本。请实现如下功能：

（1）利用树莓派中的usb麦克风，实现持续的录音。

（2）利用VAD模型，判定是否需要ASR介入，实现人声的识别

（3）识别出人声之后，判定是否命中关键词，关键词可以人为配置，如果命中关键词，则把命中的关键词，以及命中关键词的时刻，前后15s的录音文件，保存到项目的指定文件夹中。



VAD采用tenVAD，相关的模型文件已经在项目中。ASR采用SenseVoice-Small，相关的模型文件也项目中。

请进行完整的项目实现，并给出Readme文档，注意，当前的开发环境为mac os，M1max，开发以树莓派的环境为准。
下面的代码仅供参考，硬件的信息是准确的，软件需要根据具体的需求优化：

```python
import sherpa_onnx
import pyaudio
import wave
import numpy as np
import os
import sys
import time
import signal
import struct
from pathlib import Path
from datetime import datetime

# ============ 配置参数 ============
# ASR 模型路径
MODEL_DIR = Path.home() / "asr-models" / "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"
VAD_MODEL = Path.home() / "asr-models" / "silero_vad.onnx"

# 录音参数
DEVICE_INDEX = 2          # 默认录音设备索引（USB PnP Audio Device）
SAMPLE_RATE = 16000       # 采样率 16kHz
CHANNELS = 1              # 单声道
FORMAT = pyaudio.paInt16  # 16-bit PCM
CHUNK = 1600              # 每次读取帧数（100ms @16kHz，与 VAD 窗口对齐）
SEGMENT_DURATION = 300    # 每段录音保存时长（秒），默认5分钟
OUTPUT_DIR = "./recordings"  # 录音文件保存目录
ENABLE_SAVE_WAV = True    # 是否同时保存 WAV 文件
# ==================================

is_running = True


def signal_handler(sig, frame):
    """优雅退出：捕获 Ctrl+C 信号"""
    global is_running
    print("\n[INFO] 收到停止信号，正在保存当前录音并退出...")
    is_running = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def get_device_index(p):
    """自动查找 USB 录音设备，若找不到则使用配置的 DEVICE_INDEX"""
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if "USB" in info.get("name", "") and info["maxInputChannels"] > 0:
            print(f"[INFO] 找到 USB 录音设备: {info['name']} (index={i})")
            return i
    print(f"[WARN] 未自动找到 USB 设备，使用默认 DEVICE_INDEX={DEVICE_INDEX}")
    return DEVICE_INDEX


def save_wav(filename, frames, p):
    """将录音帧保存为 WAV 文件"""
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    size_mb = os.path.getsize(filename) / (1024 * 1024)
    print(f"[INFO] 已保存: {filename} ({size_mb:.2f} MB)")


def pcm_int16_to_float32(data):
    """将 PyAudio 的 int16 PCM bytes 转换为 float32 numpy 数组（归一化到 [-1, 1]）"""
    samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
    return samples


def create_recognizer():
    """创建离线(非流式)识别器 - SenseVoice"""
    recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=str(MODEL_DIR / "model.int8.onnx"),
        tokens=str(MODEL_DIR / "tokens.txt"),
        num_threads=4,
        use_itn=True,
        language="zh",
        debug=False,
    )
    return recognizer


def create_vad():
    """创建 VAD 语音活动检测器"""
    config = sherpa_onnx.VadModelConfig()
    config.silero_vad.model = str(VAD_MODEL)
    config.silero_vad.threshold = 0.5
    config.silero_vad.min_silence_duration = 0.5
    config.silero_vad.min_speech_duration = 0.25
    config.silero_vad.max_speech_duration = 30.0
    config.sample_rate = SAMPLE_RATE
    config.num_threads = 2

    vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=60)
    return vad


def main():
    global is_running

    # ---- 初始化录音保存目录 ----
    if ENABLE_SAVE_WAV:
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ---- 加载 ASR 模型 ----
    print("[INFO] 正在加载 ASR 模型...")
    t0 = time.time()
    recognizer = create_recognizer()
    vad = create_vad()
    print(f"[INFO] 模型加载完成，耗时 {time.time() - t0:.1f}s")

    # ---- 初始化 PyAudio ----
    p = pyaudio.PyAudio()
    device_idx = get_device_index(p)

    print(f"[INFO] 录音参数: 设备={device_idx}, 采样率={SAMPLE_RATE}, "
          f"声道={CHANNELS}, 每段={SEGMENT_DURATION}秒")
    if ENABLE_SAVE_WAV:
        print(f"[INFO] 录音文件保存至: {os.path.abspath(OUTPUT_DIR)}")
    print("[INFO] 开始实时录音 + ASR 识别，按 Ctrl+C 退出\n")
    print("=" * 60)

    try:
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            input_device_index=device_idx,
            frames_per_buffer=CHUNK
        )
    except Exception as e:
        print(f"[ERROR] 无法打开录音流: {e}")
        p.terminate()
        sys.exit(1)

    segment_count = 0      # WAV 文件分段计数
    asr_segment_idx = 0    # ASR 识别段计数
    wav_frames = []        # 当前分段的 WAV 帧缓存
    chunk_in_segment = 0   # 当前分段已录制的 chunk 数
    num_chunks_per_segment = int(SAMPLE_RATE / CHUNK * SEGMENT_DURATION)

    # 开始新的录音分段
    segment_count += 1
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    wav_filename = os.path.join(OUTPUT_DIR, f"rec_{timestamp}.wav")
    if ENABLE_SAVE_WAV:
        print(f"[REC] 第 {segment_count} 段录音开始: {wav_filename}")

    try:
        while is_running:
            # ---- 读取一帧音频 ----
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
            except Exception as e:
                print(f"[WARN] 读取音频数据异常: {e}")
                continue

            # ---- 同步保存 WAV ----
            if ENABLE_SAVE_WAV:
                wav_frames.append(data)
                chunk_in_segment += 1

                # 达到分段时长，保存文件并开启新段
                if chunk_in_segment >= num_chunks_per_segment:
                    save_wav(wav_filename, wav_frames, p)
                    wav_frames = []
                    chunk_in_segment = 0
                    segment_count += 1
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    wav_filename = os.path.join(OUTPUT_DIR, f"rec_{timestamp}.wav")
                    print(f"[REC] 第 {segment_count} 段录音开始: {wav_filename}")

            # ---- 实时 ASR：PCM int16 → float32 → VAD → 识别 ----
            samples = pcm_int16_to_float32(data)
            vad.accept_waveform(samples)

            while not vad.empty():
                asr_segment_idx += 1
                speech = vad.front
                vad.pop()

                # 将语音段送入识别器
                asr_stream = recognizer.create_stream()
                asr_stream.accept_waveform(SAMPLE_RATE, speech.samples)
                recognizer.decode_stream(asr_stream)
                text = asr_stream.result.text.strip()

                if text:
                    duration = len(speech.samples) / SAMPLE_RATE
                    print(f"[ASR {asr_segment_idx:03d}] ({duration:.1f}s) {text}")

    except Exception as e:
        print(f"[ERROR] 运行异常: {e}")
    finally:
        # ---- 保存最后一段录音 ----
        if ENABLE_SAVE_WAV and wav_frames:
            save_wav(wav_filename, wav_frames, p)

        # ---- 清理资源 ----
        print("\n" + "=" * 60)
        print("[INFO] 正在释放资源...")
        stream.stop_stream()
        stream.close()
        p.terminate()
        print(f"[INFO] 录音结束，共录制 {segment_count} 段，ASR 识别 {asr_segment_idx} 段语音")


if __name__ == "__main__":
    main()
```









