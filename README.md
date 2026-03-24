# 树莓派语音关键词检测系统

基于树莓派5的持续语音录音、VAD（语音活动检测）、ASR（语音识别）和关键词检测系统。

## 功能特性

- **持续录音**：使用USB麦克风进行持续录音
- **VAD检测**：使用tenVAD模型进行语音活动检测，准确识别人声
- **ASR识别**：使用SenseVoice-Small模型进行多语言语音识别（中文/英文/日文/韩文/粤语）
- **关键词检测**：可配置的关键词列表，实时检测语音中的关键词
- **自动保存**：检测到关键词时自动保存前后30秒（各15秒）的音频片段
- **元数据记录**：保存详细的检测元数据（时间、关键词、时长等）

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
├── main.py                    # 主程序入口
├── config.py                  # 配置管理
├── config.json                # 配置文件
├── audio_recorder.py          # 音频录制模块
├── audio_buffer.py            # 音频循环缓冲区
├── vad_processor.py           # VAD处理模块
├── asr_processor.py           # ASR处理模块
├── keyword_detector.py        # 关键词检测模块
├── requirements.txt           # Python依赖
├── README.md                  # 本文档
├── models/                    # 模型文件目录
│   ├── 01-vad/
│   │   └── ten-vad.onnx      # VAD模型 (332KB)
│   └── 02-asr/
│       └── sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/
│           ├── model.int8.onnx      # ASR量化模型 (239MB)
│           └── tokens.txt           # Token词汇表
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
    "救命"
  ]
}
```

### 2. 运行程序

```bash
python main.py
```

### 3. 输出示例

```
==============================================================
语音关键词检测系统
==============================================================
[INFO] 正在加载VAD模型...
[INFO] VAD模型加载完成
[INFO] 正在加载ASR模型...
[INFO] ASR模型加载完成
[INFO] 关键词检测器初始化完成
       - 关键词列表: ['你好', '帮助', '紧急', '救命']

==============================================================
系统启动
==============================================================
[INFO] 音频录制已启动
[INFO] 按 Ctrl+C 停止录音

[14:23:45] 识别: 你好你好 (1.2s)

*** 检测到关键词: 你好 ***
    时间: 2024-03-24 14:23:45
    总检测次数: 1
    音频已保存: 你好_20240324_142345.wav
    元数据已保存: 你好_20240324_142345.json
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
  "threshold": 0.5,                    // 语音检测阈值（0-1）
  "min_silence_duration": 0.5,         // 最小静音时长（秒）
  "min_speech_duration": 0.25,         // 最小语音时长（秒）
  "max_speech_duration": 30.0,         // 最大语音时长（秒）
  "buffer_size_seconds": 60,           // VAD缓冲区大小（秒）
  "num_threads": 2                     // 线程数
}
```

### ASR配置

```json
"asr": {
  "model_file": "model.int8.onnx",     // 模型文件（使用int8量化版本）
  "language": "zh",                    // 语言设置（zh/en/ja/ko/yue）
  "use_itn": true,                     // 是否使用逆文本标准化
  "num_threads": 4                     // 线程数
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

## 树莓派部署指南

### 1. 系统准备

#### 更新系统
```bash
sudo apt update
sudo apt upgrade -y
```

#### 安装系统依赖
```bash
sudo apt install -y python3-pip python3-venv portaudio19-dev
```

### 2. 创建Python虚拟环境（推荐）

```bash
# 创建虚拟环境
python3 -m venv voice_detector_env

# 激活虚拟环境
source voice_detector_env/bin/activate
```

### 3. 安装Python依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**注意**：如果sherpa-onnx安装失败，可能需要先安装系统依赖：
```bash
sudo apt install -y cmake build-essential
```

### 4. 传输项目文件

将整个项目目录传输到树莓派：

```bash
# 在开发机器上
scp -r hard_project/ pi@raspberrypi5:/home/pi/

# 或使用rsync
rsync -av --progress hard_project/ pi@raspberrypi5:/home/pi/hard_project/
```

### 5. 配置USB麦克风

#### 检查音频设备
```bash
# 列出所有录音设备
arecord -l

# 测试麦克风
arecord -f cd -D hw:1,0 | aplay -f cd
```

#### 配置音频设备（可选）
如果需要指定特定设备，修改 `config.json`：
```json
"audio": {
  "device_index": 1  // 改为你的设备索引
}
```

### 6. 运行程序

```bash
cd /home/pi/hard_project
python main.py
```

### 7. 设置开机自启动（可选）

#### 创建systemd服务文件
```bash
sudo nano /etc/systemd/system/voice-detector.service
```

#### 服务文件内容
```ini
[Unit]
Description=Voice Keyword Detector
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/hard_project
Environment="PATH=/home/pi/voice_detector_env/bin"
ExecStart=/home/pi/voice_detector_env/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 启用并启动服务
```bash
sudo systemctl daemon-reload
sudo systemctl enable voice-detector.service
sudo systemctl start voice-detector.service

# 查看服务状态
sudo systemctl status voice-detector.service

# 查看日志
sudo journalctl -u voice-detector.service -f
```

## 性能优化

### 内存优化

树莓派5 2GB版本内存有限，建议：

1. **使用量化模型**：已默认使用 `model.int8.onnx`（239MB）而非完整模型（937MB）
2. **减少线程数**：在 `config.json` 中调整 `num_threads`
3. **监控内存使用**：
   ```bash
   htop
   # 或
   free -h
   ```

### CPU优化

1. **调整线程数**：根据CPU核心数调整
   ```json
   "vad": { "num_threads": 2 },
   "asr": { "num_threads": 4 }
   ```

2. **降低采样率**：如果不需要高质量，可降低采样率到8000Hz

3. **禁用不必要的系统服务**：
   ```bash
   sudo systemctl disable bluetooth
   sudo systemctl stop bluetooth
   ```

### 存储优化

1. **定期清理旧录音**：
   ```bash
   # 删除7天前的录音
   find ./detected_clips -name "*.wav" -mtime +7 -delete
   find ./detected_clips -name "*.json" -mtime +7 -delete
   ```

2. **使用外部存储**：将输出目录挂载到外接硬盘

## 故障排查

### 问题1：找不到USB麦克风

**解决方案**：
```bash
# 列出所有音频设备
python -c "import pyaudio; p = pyaudio.PyAudio(); [print(f'{i}: {p.get_device_info_by_index(i)[\"name\"]}') for i in range(p.get_device_count())]"

# 在config.json中设置正确的device_index
```

### 问题2：sherpa-onnx安装失败

**解决方案**：
```bash
# 尝试使用预编译的wheel包
pip install sherpa-onnx --extra-index-url https://k2-fsa.github.io/k2/cpu.html

# 或从源码编译
git clone https://github.com/k2-fsa/sherpa-onnx
cd sherpa-onnx
mkdir build && cd build
cmake .. -DSHERPA_ONNX_ENABLE_PYTHON=ON
make
pip install install/lib/python3*/site-packages/*.whl
```

### 问题3：内存不足

**解决方案**：
- 减少VAD缓冲区大小：`buffer_size_seconds: 30`
- 减少线程数：`num_threads: 1`
- 使用swap：
  ```bash
  sudo dphys-swapfile swapoff
  sudo nano /etc/dphys-swapfile
  # 修改 CONF_SWAPSIZE=1024
  sudo dphys-swapfile setup
  sudo dphys-swapfile swapon
  ```

### 问题4：识别准确率低

**解决方案**：
- 调整VAD阈值：`threshold: 0.6`
- 确保麦克风距离适当（1-3米）
- 减少环境噪音
- 调整采样率和音频格式

### 问题5：程序崩溃或重启

**解决方案**：
- 检查日志：`sudo journalctl -u voice-detector.service -n 50`
- 增加swap空间
- 使用systemd自动重启（已在服务文件中配置）
- 监控温度：`vcgencmd measure_temp`

## 元数据格式

检测到的音频片段会生成对应的JSON元数据文件：

```json
{
  "keyword": "你好",
  "detected_at": "2024-03-24T14:23:45.123456",
  "detected_timestamp": 1711289025.123456,
  "duration": 30.0,
  "sample_rate": 16000,
  "channels": 1,
  "saved_at": "2024-03-24T14:23:46.789012"
}
```

## 开发和测试

### macOS开发环境测试

1. **安装依赖**：
   ```bash
   brew install portaudio
   pip install -r requirements.txt
   ```

2. **使用内置麦克风测试**：
   - 修改 `config.json`：`"device_index": null`
   - 运行：`python main.py`

3. **使用测试音频文件**：
   - 可以修改代码从WAV文件读取而非实时录音
   - 用于调试VAD和ASR参数

### 日志级别

在 `config.json` 中调整日志级别：
```json
"logging": {
  "level": "DEBUG",   // DEBUG, INFO, WARNING, ERROR
  "console": true
}
```

## 贡献

欢迎提交问题和改进建议！

## 许可证

本项目使用的模型：

- **tenVAD**：遵循其原始许可证
- **SenseVoice**：遵循其原始许可证（见模型目录中的LICENSE文件）

## 联系方式

如有问题，请提交Issue或联系开发者。

## 更新日志

### v1.0.0 (2024-03-24)
- 初始版本发布
- 支持VAD、ASR、关键词检测
- 支持树莓派5 2GB版本
- 自动保存检测到的音频片段
