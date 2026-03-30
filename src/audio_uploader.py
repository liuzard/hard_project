"""
音频上传模块
将检测到的霸凌音频上传到远程服务器
"""

import requests
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class UploadResult:
    """上传结果"""
    success: bool
    audio_id: Optional[str] = None
    audio_url: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class AudioUploader:
    """音频文件上传器"""

    def __init__(self, api_url: str = "http://118.195.132.62:18098/audio/upload/file"):
        """
        初始化上传器

        Args:
            api_url: 上传接口地址
        """
        self.api_url = api_url
        self.timeout = 30  # 上传超时时间（秒）

    def upload(
        self,
        audio_path: Path,
        text_content: str = "疑似发生霸凌",
        audio_type: str = "bully",
        duration: Optional[int] = None
    ) -> UploadResult:
        """
        上传音频文件

        Args:
            audio_path: 音频文件路径
            text_content: 音频文字内容
            audio_type: 音频类型（normal, bully）
            duration: 音频时长（秒）

        Returns:
            UploadResult 上传结果
        """
        if not audio_path.exists():
            return UploadResult(
                success=False,
                error=f"音频文件不存在: {audio_path}"
            )

        try:
            # 准备上传数据
            with open(audio_path, 'rb') as f:
                files = {
                    'file': (audio_path.name, f, 'audio/wav')
                }
                data = {
                    'textContent': text_content,
                    'audioType': audio_type
                }
                if duration is not None:
                    data['duration'] = str(duration)

                # 发送上传请求
                response = requests.post(
                    self.api_url,
                    files=files,
                    data=data,
                    timeout=self.timeout
                )

            # 解析响应
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    upload_data = result.get('data', {})
                    return UploadResult(
                        success=True,
                        audio_id=upload_data.get('audioId'),
                        audio_url=upload_data.get('audioUrl'),
                        message=upload_data.get('message', '上传成功')
                    )
                else:
                    return UploadResult(
                        success=False,
                        error=result.get('message', '上传失败')
                    )
            else:
                return UploadResult(
                    success=False,
                    error=f"HTTP错误: {response.status_code}"
                )

        except requests.exceptions.Timeout:
            return UploadResult(
                success=False,
                error="上传超时"
            )
        except requests.exceptions.ConnectionError:
            return UploadResult(
                success=False,
                error="连接服务器失败"
            )
        except Exception as e:
            return UploadResult(
                success=False,
                error=f"上传异常: {str(e)}"
            )

    def upload_with_retry(
        self,
        audio_path: Path,
        text_content: str = "疑似发生霸凌",
        audio_type: str = "bully",
        duration: Optional[int] = None,
        max_retries: int = 3
    ) -> UploadResult:
        """
        带重试的上传

        Args:
            audio_path: 音频文件路径
            text_content: 音频文字内容
            audio_type: 音频类型
            duration: 音频时长（秒）
            max_retries: 最大重试次数

        Returns:
            UploadResult 上传结果
        """
        last_result = None

        for attempt in range(max_retries):
            result = self.upload(audio_path, text_content, audio_type, duration)
            if result.success:
                return result

            last_result = result
            if attempt < max_retries - 1:
                print(f"[WARN] 上传失败，正在重试 ({attempt + 1}/{max_retries}): {result.error}")

        return last_result
