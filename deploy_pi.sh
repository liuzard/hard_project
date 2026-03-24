#!/bin/bash
# 树莓派部署脚本
# 在树莓派5上运行此脚本进行自动部署

set -e  # 遇到错误立即退出

echo "=================================================="
echo "树莓派5 语音关键词检测系统 - 自动部署"
echo "=================================================="

# 检测是否为root用户
if [ "$EUID" -eq 0 ]; then
    echo "[提示] 以root权限运行"
    SUDO=""
else
    echo "[提示] 将使用sudo安装系统包"
    SUDO="sudo"
fi

# 更新系统
echo ""
echo "[1/7] 更新系统包..."
$SUDO apt update
$SUDO apt upgrade -y

# 安装系统依赖
echo ""
echo "[2/7] 安装系统依赖..."
$SUDO apt install -y python3-pip python3-venv portaudio19-dev build-essential cmake

# 创建虚拟环境
echo ""
echo "[3/7] 创建Python虚拟环境..."
if [ -d "voice_detector_env" ]; then
    echo "虚拟环境已存在，跳过创建"
else
    python3 -m venv voice_detector_env
fi

# 激活虚拟环境并安装Python包
echo ""
echo "[4/7] 安装Python依赖..."
source voice_detector_env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 创建输出目录
echo ""
echo "[5/7] 创建输出目录..."
mkdir -p detected_clips

# 检查模型文件
echo ""
echo "[6/7] 检查模型文件..."
if [ -f "./models/01-vad/ten-vad.onnx" ]; then
    echo "✓ VAD模型存在"
else
    echo "✗ 警告: VAD模型不存在"
fi

if [ -f "./models/02-asr/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/model.int8.onnx" ]; then
    echo "✓ ASR模型存在"
else
    echo "✗ 警告: ASR模型不存在"
fi

# 启动服务（可选）
echo ""
echo "[7/7] 部署完成！"
echo ""
echo "=================================================="
echo "下一步操作："
echo "=================================================="
echo ""
echo "1. 激活虚拟环境："
echo "   source voice_detector_env/bin/activate"
echo ""
echo "2. 运行程序："
echo "   python main.py"
echo ""
echo "3. 设置开机自启动（可选）："
echo "   sudo cp voice-detector.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable voice-detector.service"
echo "   sudo systemctl start voice-detector.service"
echo ""
echo "=================================================="

# 询问是否启动程序
read -p "是否现在启动程序？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "启动程序..."
    python main.py
fi
