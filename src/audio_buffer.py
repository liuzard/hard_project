"""
音频循环缓冲区模块
实现固定大小的循环缓冲区，用于存储最近的音频数据
支持按时间戳提取音频片段
"""

import numpy as np
import wave
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
import json


class AudioBuffer:
    """音频循环缓冲区"""

    def __init__(self, sample_rate: int = 16000, duration: int = 30):
        """
        初始化音频缓冲区

        Args:
            sample_rate: 采样率（Hz）
            duration: 缓冲区时长（秒）
        """
        self.sample_rate = sample_rate
        self.duration = duration
        self.buffer_size = sample_rate * duration

        # 音频数据缓冲区（float32，归一化到[-1, 1]）
        self.buffer = np.zeros(self.buffer_size, dtype=np.float32)

        # 时间戳缓冲区（记录每个采样点的时间戳）
        self.timestamps = np.zeros(self.buffer_size, dtype=np.float64)

        # 写入索引
        self.write_index = 0

        # 线程锁
        self.lock = threading.Lock()

        # 统计信息
        self.total_samples = 0
        self.is_filled = False

    def append(self, samples: np.ndarray, timestamp: float, timestamp_is_end: bool = True) -> int:
        """
        向缓冲区追加音频数据

        Args:
            samples: 音频数据（float32 numpy数组）
            timestamp: 时间戳。默认为这批音频最后一个样本对应的时间戳。
                       如果 timestamp_is_end=False，则表示第一个样本的时间戳。
            timestamp_is_end: True 表示 timestamp 是最后一个样本的时间戳，
                             False 表示 timestamp 是第一个样本的时间戳。

        Returns:
            实际写入的样本数
        """
        with self.lock:
            num_samples = len(samples)

            # 如果样本数超过缓冲区大小，只保留最后部分
            if num_samples > self.buffer_size:
                samples = samples[-self.buffer_size:]
                num_samples = self.buffer_size

            # 为每个样本计算时间戳
            # 根据 timestamp_is_end 参数决定如何计算
            offsets = np.arange(num_samples, dtype=np.float64)
            if timestamp_is_end:
                # timestamp 是最后一个样本的时间戳，向前推算
                # t[i] = timestamp - (num_samples - 1 - i) / sample_rate
                sample_timestamps = timestamp - (num_samples - 1 - offsets) / self.sample_rate
            else:
                # timestamp 是第一个样本的时间戳，向后推算
                # t[i] = timestamp + i / sample_rate
                sample_timestamps = timestamp + offsets / self.sample_rate

            # 计算写入位置
            end_index = self.write_index + num_samples

            if end_index <= self.buffer_size:
                # 不需要回绕
                self.buffer[self.write_index:end_index] = samples
                self.timestamps[self.write_index:end_index] = sample_timestamps
            else:
                # 需要回绕
                first_part = self.buffer_size - self.write_index
                second_part = num_samples - first_part

                self.buffer[self.write_index:] = samples[:first_part]
                self.buffer[:second_part] = samples[first_part:]
                self.timestamps[self.write_index:] = sample_timestamps[:first_part]
                self.timestamps[:second_part] = sample_timestamps[first_part:]

            # 更新写入索引
            self.write_index = (self.write_index + num_samples) % self.buffer_size
            self.total_samples += num_samples

            # 标记缓冲区已填满
            if self.total_samples >= self.buffer_size:
                self.is_filled = True

            return num_samples

    def get_window(self, center_timestamp: float, window_seconds: int = 30) -> Optional[Tuple[np.ndarray, float]]:
        """
        获取指定时间戳周围的音频窗口

        Args:
            center_timestamp: 中心时间戳
            window_seconds: 窗口时长（秒），默认30秒

        Returns:
            (音频数据, 实际中心时间戳) 的元组，如果无法获取则返回 None
            返回实际中心时间戳用于验证提取的音频位置是否正确
        """
        with self.lock:
            window_samples = window_seconds * self.sample_rate
            half_window = window_samples // 2

            # 查找最接近中心时间戳的索引
            # 注意： timestamps 数组中未填满的部分值为0
            # 所以需要找到有效的非零时间戳范围
            valid_indices = np.where(self.timestamps > 0)[0]

            if len(valid_indices) == 0:
                # 缓冲区完全为空
                return None

            # 检查请求的时间戳是否在有效范围内
            min_valid_time = np.min(self.timestamps[valid_indices])
            max_valid_time = np.max(self.timestamps[valid_indices])

            # 如果请求的时间戳超出范围，尝试调整到最近的有效时间
            adjusted_timestamp = center_timestamp
            if center_timestamp < min_valid_time:
                adjusted_timestamp = min_valid_time
            elif center_timestamp > max_valid_time:
                adjusted_timestamp = max_valid_time

            # 如果调整幅度过大（超过1秒），返回 None
            if abs(adjusted_timestamp - center_timestamp) > 1.0:
                return None

            # 查找最接近中心时间戳的索引
            time_diffs = np.abs(self.timestamps - adjusted_timestamp)
            # 只考虑有效时间戳（时间戳>0的位置）
            valid_mask = self.timestamps > 0
            time_diffs[~valid_mask] = np.inf
            center_idx = np.argmin(time_diffs)

            # 获取实际找到的时间戳
            actual_center_timestamp = self.timestamps[center_idx]

            # 计算窗口的起始和结束索引
            start_idx = center_idx - half_window
            end_idx = center_idx + half_window

            # 处理循环缓冲区的索引
            if start_idx < 0:
                start_idx += self.buffer_size

            if end_idx >= self.buffer_size:
                end_idx -= self.buffer_size

            # 提取音频数据
            if start_idx < end_idx:
                # 不需要回绕
                result = self.buffer[start_idx:end_idx].copy()
            else:
                # 需要回绕
                first_part = self.buffer[start_idx:].copy()
                second_part = self.buffer[:end_idx].copy()
                result = np.concatenate([first_part, second_part])

            # 检查提取的数据是否有效（非静音数据比例）
            # 如果大部分是静音（接近0），可能表示数据不完整
            non_silent_ratio = np.sum(np.abs(result) > 0.01) / len(result)
            if non_silent_ratio < 0.1 and not self.is_filled:
                # 缓冲区未满且大部分是静音，返回 None
                return None

            return result, actual_center_timestamp

    def get_recent(self, seconds: int = 30) -> Optional[np.ndarray]:
        """
        获取最近N秒的音频数据

        Args:
            seconds: 秒数

        Returns:
            音频数据（float32 numpy数组），如果数据不足则返回None
        """
        with self.lock:
            if not self.is_filled:
                # 缓冲区未填满
                return None

            num_samples = seconds * self.sample_rate
            start_idx = (self.write_index - num_samples) % self.buffer_size

            if start_idx < self.write_index:
                return self.buffer[start_idx:self.write_index].copy()
            else:
                first_part = self.buffer[start_idx:].copy()
                second_part = self.buffer[:self.write_index].copy()
                return np.concatenate([first_part, second_part])

    def save_to_wav(self, audio_data: np.ndarray, output_path: Path,
                    metadata: Optional[dict] = None) -> None:
        """
        将音频数据保存为WAV文件

        Args:
            audio_data: 音频数据（float32 numpy数组，归一化到[-1, 1]）
            output_path: 输出文件路径
            metadata: 可选的元数据字典
        """
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 转换为int16 PCM格式
        int16_data = (audio_data * 32767).astype(np.int16)

        # 写入WAV文件
        with wave.open(str(output_path), 'wb') as wf:
            wf.setnchannels(1)  # 单声道
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(int16_data.tobytes())

        # 如果提供了元数据，保存为JSON文件
        if metadata:
            metadata_path = output_path.with_suffix('.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

    def save_detected_clip(self, keyword: str, detected_at: float,
                          output_dir: Path, save_metadata: bool = True) -> Tuple[Path, Optional[Path]]:
        """
        保存检测到的关键词音频片段

        Args:
            keyword: 检测到的关键词
            detected_at: 检测到关键词的缓冲区相对时间（秒）
            output_dir: 输出目录
            save_metadata: 是否保存元数据

        Returns:
            (wav文件路径, 元数据文件路径)
        """
        # 生成文件名（使用当前时间）
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        wav_filename = f"{keyword}_{timestamp_str}.wav"
        wav_path = output_dir / wav_filename

        # 获取30秒音频窗口
        result = self.get_window(detected_at, window_seconds=30)

        if result is None:
            raise RuntimeError("无法从缓冲区获取音频数据")

        audio_data, actual_center_time = result

        # 准备元数据
        metadata = None
        if save_metadata:
            metadata = {
                "keyword": keyword,
                "buffer_time_seconds": detected_at,  # 缓冲区中的相对时间
                "actual_center_time": actual_center_time,  # 实际提取的中心时间
                "time_offset": actual_center_time - detected_at,  # 时间偏移量
                "duration": len(audio_data) / self.sample_rate,
                "sample_rate": self.sample_rate,
                "channels": 1,
                "saved_at": datetime.now().isoformat()
            }

        # 保存音频文件
        self.save_to_wav(audio_data, wav_path, metadata)

        metadata_path = None
        if save_metadata:
            metadata_path = wav_path.with_suffix('.json')

        return wav_path, metadata_path

    def clear(self) -> None:
        """清空缓冲区"""
        with self.lock:
            self.buffer.fill(0)
            self.timestamps.fill(0)
            self.write_index = 0
            self.total_samples = 0
            self.is_filled = False

    def get_stats(self) -> dict:
        """获取缓冲区统计信息"""
        with self.lock:
            return {
                "buffer_size": self.buffer_size,
                "write_index": self.write_index,
                "total_samples": self.total_samples,
                "is_filled": self.is_filled,
                "fill_percentage": min(100, (self.total_samples / self.buffer_size) * 100)
            }
