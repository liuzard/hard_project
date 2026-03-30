阅读项目中所有的文档和代码。

当前项目采用vad+asr两阶段语音识别，其中vad包含silero_vad和ten-vad，现在需要在项目中新增fsmn_vad。
fsmn_vad对应的模型文件：/Users/liuzard/Documents/claude_code/hard_project/models/01-vad/speech_fsmn_vad_zh-cn-16k-common-onnx

fsmn_vad不支持sherpa-onnx生态，需要采用funasr_onnx，参考代码如下：

```python
from funasr_onnx import Fsmn_vad_online
import numpy as np
import librosa

# model_dir 可以是本地路径或 ModelScope 模型 ID
model_dir = "models/speech_fsmn_vad_zh-cn-16k-common-onnx"  # 本地路径

model = Fsmn_vad_online(model_dir, quantize=True)

# 加载音频文件
wav_path = "../../resources/recording_120s_20260328_220927.wav"
waveform, sr = librosa.load(wav_path, sr=16000)

# 模拟在线流式处理：分块处理音频
chunk_size = 16000 * 5  # 每次处理 5 秒的音频 (16kHz * 5s)
total_samples = len(waveform)

# 初始化缓存
param_dict = {
    "in_cache": [],
    "is_final": False
}

all_segments = []
current_start = None  # 当前正在进行的语音段起始时间

print(f"音频总时长: {total_samples / sr:.2f}s")
print(f"分块大小: {chunk_size / sr:.2f}s")
print("-" * 50)

# 分块处理
for start in range(0, total_samples, chunk_size):
    end = min(start + chunk_size, total_samples)
    chunk = waveform[start:end]

    # 判断是否为最后一块
    param_dict["is_final"] = (end >= total_samples)

    # 在线 VAD 处理
    segments = model(chunk, param_dict=param_dict)

    # 缓存已自动更新在 param_dict["in_cache"] 中
    # 在线模式返回格式说明:
    # - 当检测到语音段开始时: [start_ms, -1]
    # - 当检测到语音段结束时: [-1, end_ms]
    # - 完整语音段: [start_ms, end_ms]
    if segments and len(segments) > 0:
        for batch_segs in segments:
            for seg in batch_segs:
                start_ms, end_ms = seg

                # 处理开始事件
                if start_ms != -1:
                    current_start = start_ms
                    print(f"[开始] 语音段起始: {start_ms}ms")

                # 处理结束事件
                if end_ms != -1 and current_start is not None:
                    print(f"[结束] 语音段: {current_start}ms ~ {end_ms}ms "
                          f"(时长 {(end_ms - current_start) / 1000:.2f}s)")
                    all_segments.append([current_start, end_ms])
                    current_start = None

print("-" * 50)
print(f"\n共检测到 {len(all_segments)} 个完整语音段:")
for i, seg in enumerate(all_segments):
    start_ms, end_ms = seg
    print(f"  语音段 {i + 1}: {start_ms}ms ~ {end_ms}ms "
          f"(时长 {(end_ms - start_ms) / 1000:.2f}s)")

```

参考上面的代码，将fsmn_vad集成到项目中，作为一个新的配置项。