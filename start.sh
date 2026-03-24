#!/bin/bash
# 快速启动脚本

echo "=================================================="
echo "语音关键词检测系统 - 快速启动"
echo "=================================================="

# 检查Python版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python版本: $python_version"

# 检查依赖
echo ""
echo "检查依赖..."
python3 -c "import sherpa_onnx" 2>/dev/null && echo "✓ sherpa-onnx" || echo "✗ sherpa-onnx 未安装"
python3 -c "import pyaudio" 2>/dev/null && echo "✓ pyaudio" || echo "✗ pyaudio 未安装"
python3 -c "import numpy" 2>/dev/null && echo "✓ numpy" || echo "✗ numpy 未安装"

# 检查模型文件
echo ""
echo "检查模型文件..."
if [ -f "./models/01-vad/ten-vad.onnx" ]; then
    echo "✓ VAD模型存在"
else
    echo "✗ VAD模型不存在: ./models/01-vad/ten-vad.onnx"
fi

if [ -f "./models/02-asr/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/model.int8.onnx" ]; then
    echo "✓ ASR模型存在"
else
    echo "✗ ASR模型不存在: ./models/02-asr/.../model.int8.onnx"
fi

if [ -f "./models/02-asr/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/tokens.txt" ]; then
    echo "✓ ASR tokens存在"
else
    echo "✗ ASR tokens不存在: ./models/02-asr/.../tokens.txt"
fi

# 创建输出目录
echo ""
echo "创建输出目录..."
mkdir -p detected_clips
echo "✓ 输出目录已创建: ./detected_clips"

# 启动程序
echo ""
echo "=================================================="
echo "启动程序..."
echo "=================================================="
echo ""

python3 main.py
