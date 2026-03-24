"""
音频录制模块
使用PyAudio实现持续的USB麦克风录音
支持自动检测USB麦克风设备和优雅退出
"""

import pyaudio
import signal
import sys
from typing import Optional, Callable
from config import get_config


class AudioRecorder:
    """音频录制器"""

    def __init__(self, on_audio_callback: Callable[[bytes], None]):
        """
        初始化音频录制器

        Args:
            on_audio_callback: 音频数据回调函数，接收原始PCM数据
        """
        self.config = get_config()
        self.on_audio_callback = on_audio_callback

        # PyAudio实例
        self.pyaudio = None
        self.stream = None

        # 控制标志
        self.is_running = False

        # 设备索引
        self.device_index = None

        # 设置信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, sig, frame):
        """信号处理器：优雅退出"""
        print(f"\n[INFO] 收到停止信号 (signal {sig})，正在停止录音...")
        self.stop()

    def find_usb_device(self) -> int:
        """
        自动查找USB录音设备

        Returns:
            USB设备索引，如果找不到则返回None
        """
        if self.pyaudio is None:
            self.pyaudio = pyaudio.PyAudio()

        print("[INFO] 正在查找录音设备...")

        for i in range(self.pyaudio.get_device_count()):
            info = self.pyaudio.get_device_info_by_index(i)
            device_name = info.get("name", "")

            # 检查是否是USB设备且有输入通道
            if "USB" in device_name and info["maxInputChannels"] > 0:
                print(f"[INFO] 找到USB录音设备: {device_name} (index={i})")
                print(f"       - 采样率: {info['defaultSampleRate']:.0f} Hz")
                print(f"       - 输入通道: {info['maxInputChannels']}")
                return i

            # 检查是否是 hw:2 设备（树莓派常见情况）
            if info["maxInputChannels"] > 0:
                # 尝试从设备名中识别卡号
                if "hw:2" in device_name.lower() or "card 2" in device_name.lower():
                    print(f"[INFO] 找到 hw:2 设备: {device_name} (index={i})")
                    print(f"       - 采样率: {info['defaultSampleRate']:.0f} Hz")
                    print(f"       - 输入通道: {info['maxInputChannels']}")
                    return i

        print("[WARN] 未自动找到USB或hw:2设备")
        print("[INFO] 运行 'python find_audio_device.py' 查看所有可用设备")
        return None

    def get_device_index(self) -> int:
        """
        获取录音设备索引

        Returns:
            设备索引
        """
        # 优先使用配置文件中的设备索引
        if self.config.audio_device_index is not None:
            return self.config.audio_device_index

        # 尝试自动查找USB设备
        device_idx = self.find_usb_device()

        if device_idx is None:
            # 使用默认设备
            print("[INFO] 使用系统默认录音设备")
            device_idx = None  # None表示使用默认设备

        return device_idx

    def start(self):
        """开始录音"""
        if self.is_running:
            print("[WARN] 录音已在运行中")
            return

        print("[INFO] 正在初始化音频录制...")

        # 初始化PyAudio
        self.pyaudio = pyaudio.PyAudio()

        # 获取设备索引
        self.device_index = self.get_device_index()

        # 打印录音参数
        print(f"[INFO] 录音参数:")
        print(f"       - 设备索引: {self.device_index if self.device_index is not None else '默认'}")
        print(f"       - 采样率: {self.config.sample_rate} Hz")
        print(f"       - 声道数: {self.config.channels}")
        print(f"       - 格式: {self.config.audio_format}")
        print(f"       - 每次读取: {self.config.chunk_size} 帧")

        try:
            # 打开音频流
            self.stream = self.pyaudio.open(
                format=pyaudio.paInt16,  # 16-bit PCM
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.config.chunk_size,
                stream_callback=self._audio_callback
            )

            self.is_running = True
            print("[INFO] 音频录制已启动")
            print("[INFO] 按 Ctrl+C 停止录音\n")

        except Exception as e:
            print(f"[ERROR] 无法打开音频流: {e}")
            self.cleanup()
            raise

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """
        PyAudio流回调函数

        Args:
            in_data: 输入音频数据
            frame_count: 帧数
            time_info: 时间信息
            status: 状态

        Returns:
            (None, pyaudio.paContinue)
        """
        if status:
            print(f"[WARN] 音频流状态: {status}")

        # 调用用户提供的回调函数
        if self.on_audio_callback:
            self.on_audio_callback(in_data)

        return (None, pyaudio.paContinue)

    def read_chunk(self) -> Optional[bytes]:
        """
        阻塞式读取一个音频块

        Returns:
            音频数据（bytes），如果出错则返回None
        """
        if not self.is_running or self.stream is None:
            return None

        try:
            data = self.stream.read(self.config.chunk_size, exception_on_overflow=False)
            return data
        except Exception as e:
            print(f"[ERROR] 读取音频数据异常: {e}")
            return None

    def stop(self):
        """停止录音"""
        if not self.is_running:
            return

        print("[INFO] 正在停止音频录制...")
        self.is_running = False

        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                print(f"[WARN] 关闭音频流时出错: {e}")

        self.cleanup()

    def cleanup(self):
        """清理资源"""
        if self.stream:
            try:
                self.stream.close()
            except:
                pass
            self.stream = None

        if self.pyaudio:
            try:
                self.pyaudio.terminate()
            except Exception as e:
                print(f"[WARN] 终止PyAudio时出错: {e}")
            self.pyaudio = None

        print("[INFO] 音频录制已停止")

    def list_devices(self):
        """列出所有可用的音频设备"""
        if self.pyaudio is None:
            self.pyaudio = pyaudio.PyAudio()

        print("\n=== 可用音频设备 ===")
        for i in range(self.pyaudio.get_device_count()):
            info = self.pyaudio.get_device_info_by_index(i)
            name = info.get("name", "未知设备")
            max_input = info["maxInputChannels"]
            max_output = info["maxOutputChannels"]
            sample_rate = info["defaultSampleRate"]

            input_str = f"输入: {max_input}ch" if max_input > 0 else "无输入"
            output_str = f"输出: {max_output}ch" if max_output > 0 else "无输出"

            print(f"设备 {i}: {name}")
            print(f"       {input_str}, {output_str}, 采样率: {sample_rate:.0f} Hz")

        print("=====================\n")


def pcm_int16_to_float32(data: bytes) -> 'np.ndarray':
    """
    将int16 PCM字节流转换为float32 numpy数组（归一化到[-1, 1]）

    Args:
        data: int16 PCM字节流

    Returns:
        float32 numpy数组，归一化到[-1, 1]
    """
    import numpy as np
    samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
    return samples
