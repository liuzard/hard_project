#!/usr/bin/env python3
"""
音频录制测试脚本
测试 PyAudio 录音功能是否正常
"""

import time
import sys
from audio_recorder import AudioRecorder, pcm_int16_to_float32

print("=" * 60)
print("音频录制测试")
print("=" * 60)

print("\n[测试] 开始5秒录音测试...")
print("请对着麦克风说话...\n")

recorder = AudioRecorder()

try:
    # 启动录音
    recorder.start()

    # 录制5秒
    chunks = []
    start_time = time.time()
    chunk_count = 0

    while time.time() - start_time < 5:
        data = recorder.read_chunk()
        if data:
            chunks.append(data)
            chunk_count += 1
            # 每0.5秒打印一次进度
            if chunk_count % 5 == 0:
                elapsed = time.time() - start_time
                print(f"  已录制: {elapsed:.1f}秒")
        else:
            break

    # 停止录音
    recorder.stop()

    print(f"\n[结果] 录音完成")
    print(f"  - 录制时长: {time.time() - start_time:.1f} 秒")
    print(f"  - 音频块数: {chunk_count}")
    print(f"  - 数据大小: {sum(len(d) for d in chunks)} bytes")

    if chunk_count > 0:
        print("\n✓ 录音测试成功！音频设备工作正常。")
        print("\n现在可以运行主程序:")
        print("  python3 main.py")
    else:
        print("\n✗ 录音测试失败！未接收到音频数据。")
        print("\n故障排查:")
        print("1. 检查麦克风是否正确连接")
        print("2. 运行 'python3 find_audio_device.py' 查找正确的设备索引")
        print("3. 运行 'arecord -D plughw:2,0 -f S16_LE -r 16000 -c 1 -d 3 test.wav' 测试 ALSA")

except Exception as e:
    print(f"\n[ERROR] 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    recorder.cleanup()

print("\n" + "=" * 60)
