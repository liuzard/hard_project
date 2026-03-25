#!/usr/bin/env python3
"""
模块测试脚本
测试各个模块是否正常工作
"""

import sys
import time
import numpy as np
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("模块测试脚本")
print("=" * 60)

# 测试1: 配置模块
print("\n[测试 1/6] 测试配置模块...")
try:
    from src.config import get_config, Config
    config = Config(str(Path(__file__).parent.parent / "config.json"))
    print("✓ 配置模块正常")
    print(f"  - 采样率: {config.sample_rate}")
    print(f"  - 关键词: {config.keywords}")
except Exception as e:
    print(f"✗ 配置模块失败: {e}")
    sys.exit(1)

# 测试2: 音频缓冲区
print("\n[测试 2/6] 测试音频缓冲区...")
try:
    from src.audio_buffer import AudioBuffer

    # 创建缓冲区
    buffer = AudioBuffer(sample_rate=16000, duration=10)

    # 添加测试数据
    test_samples = np.random.randn(16000).astype(np.float32) * 0.1  # 1秒白噪声
    buffer.append(test_samples, time.time())

    # 检查是否填满
    stats = buffer.get_stats()
    print("✓ 音频缓冲区正常")
    print(f"  - 缓冲区大小: {stats['buffer_size']}")
    print(f"  - 填充状态: {stats['fill_percentage']:.1f}%")
except Exception as e:
    print(f"✗ 音频缓冲区失败: {e}")
    import traceback
    traceback.print_exc()

# 测试3: VAD模块
print("\n[测试 3/6] 测试VAD模块...")
try:
    from src.vad_processor import VADProcessor

    # 跳过VAD测试如果模型文件不存在（开发环境）
    if not config.vad_model_path.exists():
        print("⊘ 跳过VAD测试（模型文件不存在）")
    else:
        vad = VADProcessor()
        print("✓ VAD模块正常")
        print(f"  - 状态: {vad.get_stats()}")
except Exception as e:
    print(f"✗ VAD模块失败: {e}")
    import traceback
    traceback.print_exc()

# 测试4: ASR模块
print("\n[测试 4/6] 测试ASR模块...")
try:
    from src.asr_processor import ASRProcessor

    # 跳过ASR测试如果模型文件不存在（开发环境）
    if not config.asr_model_path.exists():
        print("⊘ 跳过ASR测试（模型文件不存在）")
    else:
        asr = ASRProcessor()
        print("✓ ASR模块正常")
        print(f"  - 就绪状态: {asr.is_ready()}")
except Exception as e:
    print(f"✗ ASR模块失败: {e}")
    import traceback
    traceback.print_exc()

# 测试5: 关键词检测模块
print("\n[测试 5/6] 测试关键词检测模块...")
try:
    from src.keyword_detector import KeywordDetector

    detector = KeywordDetector()
    print("✓ 关键词检测模块正常")
    print(f"  - 关键词列表: {detector.get_keywords()}")

    # 测试检测功能
    test_cases = [
        ("你好世界", "你好"),
        ("紧急情况", "紧急"),
        ("帮我一个忙", "帮助"),
        ("今天天气不错", None)
    ]

    for text, expected in test_cases:
        result = detector.detect(text)
        if expected is None:
            assert result is None, f"期望{text}不检测到关键词，但检测到了{result}"
            print(f"  ✓ '{text}' → 无关键词（正确）")
        else:
            assert result == expected, f"期望{text}检测到'{expected}'，但检测到了'{result}'"
            print(f"  ✓ '{text}' → '{result}'（正确）")
except Exception as e:
    print(f"✗ 关键词检测模块失败: {e}")
    import traceback
    traceback.print_exc()

# 测试6: 音频录制模块
print("\n[测试 6/6] 测试音频录制模块...")
try:
    from src.audio_recorder import AudioRecorder, pcm_int16_to_float32

    # 测试PCM转换
    import struct
    pcm_data = struct.pack('<' + 'h' * 1600, *np.random.randint(-32768, 32767, 1600))
    float_data = pcm_int16_to_float32(pcm_data)
    assert len(float_data) == 1600, "PCM转换后长度不匹配"
    assert -1.0 <= float_data.min() <= 1.0, "PCM转换后数值范围错误"
    print("✓ 音频录制模块正常（PCM转换测试通过）")

    # 列出设备
    print("\n  可用音频设备:")
    recorder = AudioRecorder()
    recorder.list_devices()
except Exception as e:
    print(f"✗ 音频录制模块失败: {e}")
    import traceback
    traceback.print_exc()

# 总结
print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)

print("\n如需运行完整系统，请执行:")
print("  python -m src.main")
