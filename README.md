# 树莓派语音关键词检测系统

基于树莓派5的持续语音录音、VAD（语音活动检测）、ASR（语音识别）和关键词检测系统，支持霸凌音频自动上传。

## 功能特性

- **持续录音**：使用USB麦克风进行持续录音
- **VAD检测**：支持 FSMN-VAD（默认）和 Silero VAD v6 两种模型
- **ASR识别**：支持多种模型（Paraformer-zh、SenseVoice、FunASR-nano）
- **关键词检测**：可配置的关键词列表，实时检测语音中的关键词
- **自动保存**：检测到关键词时自动保存前后30秒（各15秒）的音频片段
- **自动上传**：检测到霸凌关键词时自动上传音频到服务器
- **元数据记录**：保存详细的检测元数据（时间、关键词、时长等）
- **多线程架构**：录音与ASR处理分离，避免阻塞
- **文件模拟模式**：支持从WAV文件模拟录音，便于测试

## 硬件要求

- **开发环境**：macOS M1 Max（或其他开发机器）
- **目标环境**：树莓派5 2GB版本
- **音频设备**：USB麦克风
- **存储**：至少4GB可用空间（用于模型和录音文件）

## 软件依赖

### Python 3.8+

```bash
pip install -r requirements.txt
```

### 系统依赖

**macOS开发环境**：
```bash
brew install portaudio
```

**树莓派环境**：
```bash
sudo apt update
sudo apt install -y python3-pip portaudio19-dev
```

## 项目结构

```
hard_project/
├── run.py                     # 程序入口
├── config.json                # 配置文件
├── requirements.txt           # Python依赖
├── README.md                  # 本文档
├── src/                       # 源代码目录
│   ├── __init__.py
│   ├── main.py               # 主程序逻辑
│   ├── config.py             # 配置管理
│   ├── audio_recorder.py     # 音频录制模块
│   ├── audio_buffer.py       # 音频循环缓冲区
│   ├── vad_processor.py      # VAD处理模块
│   ├── fsmn_vad_processor.py # FSMN-VAD处理器
│   ├── asr_processor.py      # ASR处理模块
│   ├── keyword_detector.py   # 关键词检测模块
│   └── audio_uploader.py     # 音频上传模块
├── models/                    # 模型文件目录
│   ├── 01-vad/
│   │   └── speech_fsmn_vad_zh-cn-16k-common-onnx/
│   │       └── model_quant.onnx      # FSMN-VAD模型
│   └── 02-asr/
│       ├── sherpa-onnx-paraformer-zh-2023-09-14/
│       ├── sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/
│       └── sherpa-onnx-funasr-nano-int8-2025-12-30/
├── tests/                     # 测试脚本
└── detected_clips/            # 检测到的音频片段输出目录
```

## 快速开始

### 1. 配置关键词

编辑 `config.json` 文件，修改 `keywords` 字段：

```json
{
  "keywords": [
    "你好",
    "帮助",
    "紧急",
    "救命",
    "保护费",
    "欺负"
  ]
}
```

### 2. 运行程序

**实时录音模式**：
```bash
python run.py
```

**文件模拟模式**（用于测试）：
```bash
# 实时速度播放
python run.py --file test.wav

# 快速模式（不等待实时播放）
python run.py --file test.wav --fast
```

### 3. 输出示例

```
============================================================
语音关键词检测系统
============================================================
[INFO] 正在初始化各个模块...
[INFO] 正在加载 FSMN-VAD 模型...
[INFO] FSMN-VAD 模型加载完成
       - 模型目录: ./models/01-vad/speech_fsmn_vad_zh-cn-16k-common-onnx
       - 量化: True
       - 最大结尾静音: 800ms
[INFO] ASR模型加载完成 (Paraformer-zh)
[INFO] 关键词检测器初始化完成
       - 关键词列表: ['你好', '帮助', '紧急', '救命', '保护费', '欺负']
[INFO] 音频上传已启用: http://118.195.132.62:18098/audio/upload/file

============================================================
系统启动
============================================================
[INFO] 音频录制已启动
[INFO] 系统运行中...
[INFO] 监听关键词: 你好, 帮助, 紧急, 救命, 保护费, 欺负
[INFO] 按 Ctrl+C 停止

------------------------------------------------------------
[14:23:45] [10s] ● 录音正常 | 音频时间: 10s | 语音段: 2 | 识别: 1 | 关键词: 0 | ASR队列: 0
[14:23:47] 🎤 识别: 请帮帮我 (0.8s)

*** 检测到关键词: 帮助 ***
    时间: 2024-03-24 14:23:47
    音频位置: 12.5秒
    总检测次数: 1
    音频已保存: 帮助_20240324_142347.wav
    元数据已保存: 帮助_20240324_142347.json
    正在上传音频...
    上传成功: audioId=audio_a1b2c3d4e5f6g7h8
    音频URL: http://localhost:8080/files/audio/20240328/a1b2c3d4e5f6g7h8.wav

^C[INFO] 收到停止信号 (signal 2)

============================================================
运行统计
============================================================
运行时长: 30.5 秒 (0.5 分钟)
语音段检测: 5 次
ASR识别成功: 4 次
关键词检测: 1 次
保存音频片段: 1 个
识别成功率: 80.0%

[INFO] 系统已停止
```

## 配置说明

### 音频配置

```json
"audio": {
  "device_index": null,        // 音频设备索引（null=自动检测USB设备）
  "sample_rate": 16000,        // 采样率（Hz）
  "channels": 1,               // 声道数（1=单声道）
  "chunk_size": 1600           // 每次读取帧数（100ms@16kHz）
}
```

### VAD配置

```json
"vad": {
  "model_type": "fsmn_vad",            // VAD模型类型：fsmn_vad 或 silero_vad
  "threshold": 0.3,                    // 语音检测阈值（Silero VAD）
  "min_silence_duration": 0.6,         // 最小静音时长（秒）
  "min_speech_duration": 0.25,         // 最小语音时长（秒）
  "buffer_size_seconds": 60,           // VAD缓冲区大小（秒）
  "num_threads": 2,                    // 线程数
  "fsmn_vad": {
    "model_dir": "./models/01-vad/speech_fsmn_vad_zh-cn-16k-common-onnx",
    "quantize": true,                  // 使用量化模型
    "max_end_sil": 800,                // 最大结尾静音时长（毫秒）
    "intra_op_num_threads": 2          // 推理线程数
  }
}
```

**VAD模型选择**：
- **FSMN-VAD**（推荐）：FunASR 的流式 VAD 模型，针对中文优化，延迟低
- **Silero VAD v6**：通用 VAD 模型，支持多语言

### ASR配置

```json
"asr": {
  "model_type": "paraformer-zh",       // 模型类型：paraformer-zh, sense-voice, funasr-nano
  "num_threads": 4,                    // 线程数
  "use_itn": true,                     // 是否使用逆文本标准化
  "models": {
    "paraformer-zh": {
      "model_dir": "./models/02-asr/sherpa-onnx-paraformer-zh-2023-09-14",
      "model_file": "model.int8.onnx",
      "tokens_file": "tokens.txt"
    },
    "sense-voice": {
      "model_dir": "./models/02-asr/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17",
      "model_file": "model.int8.onnx",
      "tokens_file": "tokens.txt"
    }
  }
}
```

**ASR模型选择**：
- **Paraformer-zh**（推荐）：中文语音识别，速度快，准确率高
- **SenseVoice**：多语言识别（中/英/日/韩/粤语），支持情感识别
- **FunASR-nano**：最新模型，支持更多功能

### 上传配置

```json
"upload": {
  "enabled": true,                     // 是否启用上传功能
  "api_url": "http://118.195.132.62:18098/audio/upload/file",
  "text_content": "疑似发生霸凌",       // 上传时的文字内容
  "audio_type": "bully",               // 音频类型
  "max_retries": 3,                    // 最大重试次数
  "timeout": 30                        // 超时时间（秒）
}
```

### 输出配置

```json
"output": {
  "directory": "./detected_clips",     // 输出目录
  "buffer_seconds": 15,                // 前后各缓冲多少秒
  "save_metadata": true                // 是否保存元数据
}
```

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        主程序 (main.py)                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ AudioRecorder│───►│ AudioBuffer  │    │              │  │
│  │  (录音线程)   │    │  (30秒循环)   │    │              │  │
│  └──────────────┘    └──────────────┘    │              │  │
│         │                    │           │              │  │
│         ▼                    │           │              │  │
│  ┌──────────────┐            │           │              │  │
│  │ VADProcessor │            │           │              │  │
│  │  (FSMN-VAD)  │            │           │              │  │
│  └──────────────┘            │           │              │  │
│         │                    │           │              │  │
│         ▼                    ▼           │              │  │
│  ┌──────────────────────────────┐        │              │  │
│  │      ASR Queue (max=100)     │        │              │  │
│  └──────────────────────────────┘        │              │  │
│         │                                │              │  │
│         ▼                                │              │  │
│  ┌──────────────┐    ┌──────────────┐    │              │  │
│  │ ASRProcessor │───►│KeywordDetect │────┘              │  │
│  │  (ASR线程)    │    │   (关键词)    │                   │  │
│  └──────────────┘    └──────────────┘                   │  │
│                              │                           │  │
│                              ▼                           │  │
│                    ┌──────────────┐                      │  │
│                    │AudioUploader │                      │  │
│                    │  (上传服务器) │                      │  │
│                    └──────────────┘                      │  │
│                                                          │  │
└─────────────────────────────────────────────────────────────┘
```

**关键设计**：
- 录音线程只负责采集音频，不做耗时处理
- VAD 在录音线程中轻量级处理
- ASR 在独立线程中处理，避免阻塞录音
- 队列限制 100 个语音段，满时丢弃最旧的
- 统一的时间戳系统确保音频片段提取准确

## 树莓派部署指南

### 1. 系统准备

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv portaudio19-dev
```

### 2. 创建Python虚拟环境

```bash
python3 -m venv voice_detector_env
source voice_detector_env/bin/activate
```

### 3. 安装Python依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. 传输项目文件

```bash
# 在开发机器上
rsync -av --progress hard_project/ pi@raspberrypi5:/home/pi/hard_project/
```

### 5. 运行程序

```bash
cd /home/pi/hard_project
python run.py
```

### 6. 设置开机自启动

创建 systemd 服务文件：
```bash
sudo nano /etc/systemd/system/voice-detector.service
```

内容：
```ini
[Unit]
Description=Voice Keyword Detector
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/hard_project
Environment="PATH=/home/pi/voice_detector_env/bin"
ExecStart=/home/pi/voice_detector_env/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable voice-detector.service
sudo systemctl start voice-detector.service
```

## 性能优化

### 内存优化

树莓派5 2GB版本建议：
- 使用量化模型（`model.int8.onnx`）
- 减少线程数：`num_threads: 2`
- 监控内存：`htop` 或 `free -h`

### CPU优化

```json
"vad": { "num_threads": 2 },
"asr": { "num_threads": 4 }
```

## 故障排查

### 找不到USB麦克风

```bash
# 列出录音设备
arecord -l

# 测试麦克风
arecord -D plughw:2,0 -f S16_LE -r 16000 -c 1 -d 3 test.wav
```

### 模型加载失败

确保模型文件完整：
```bash
ls -lh models/01-vad/speech_fsmn_vad_zh-cn-16k-common-onnx/model_quant.onnx
ls -lh models/02-asr/sherpa-onnx-paraformer-zh-2023-09-14/model.int8.onnx
```

### 内存不足

- 减少缓冲区大小
- 减少线程数
- 增加 swap 空间

## 元数据格式

```json
{
  "keyword": "帮助",
  "buffer_time_seconds": 12.5,
  "actual_center_time": 12.48,
  "time_offset": -0.02,
  "duration": 30.0,
  "sample_rate": 16000,
  "channels": 1,
  "saved_at": "2024-03-24T14:23:47.123456"
}
```

## 更新日志

### v2.0.0 (2024-03-30)
- 重构为多线程架构，避免 ASR 阻塞录音
- 新增 FSMN-VAD 支持（默认）
- 新增多种 ASR 模型支持
- 新增音频自动上传功能
- 修复时间戳同步问题
- 新增 ASR 队列限制，防止内存溢出
- 新增文件模拟模式，便于测试
- 优化线程安全

### v1.0.0 (2024-03-24)
- 初始版本发布
- 支持 VAD、ASR、关键词检测
- 支持树莓派5 2GB版本
- 自动保存检测到的音频片段

## 许可证

本项目使用的模型：
- **FSMN-VAD**：FunASR 项目，遵循其原始许可证
- **Paraformer/SenseVoice**：遵循其原始许可证

## 联系方式

如有问题，请提交 Issue。
