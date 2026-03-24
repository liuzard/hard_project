"""
关键词检测模块
在ASR识别的文本中检测关键词
支持配置多个关键词，不区分大小写
"""

from typing import List, Optional, Tuple
from config import get_config


class KeywordDetector:
    """关键词检测器"""

    def __init__(self, keywords: Optional[List[str]] = None):
        """
        初始化关键词检测器

        Args:
            keywords: 关键词列表，如果为None则从配置文件加载
        """
        self.config = get_config()

        if keywords is not None:
            self.keywords = keywords
        else:
            self.keywords = self.config.keywords

        # 预处理关键词（转为小写）
        self.keywords_lower = [kw.lower() for kw in self.keywords]

        print(f"[INFO] 关键词检测器初始化完成")
        print(f"       - 关键词列表: {self.keywords}")

    def detect(self, text: str) -> Optional[str]:
        """
        检测文本中是否包含关键词

        Args:
            text: 待检测的文本

        Returns:
            匹配到的关键词（原始大小写），如果没有匹配则返回None
        """
        if not text:
            return None

        text_lower = text.lower()

        # 遍历所有关键词
        for keyword, keyword_lower in zip(self.keywords, self.keywords_lower):
            if keyword_lower in text_lower:
                return keyword

        return None

    def detect_all(self, text: str) -> List[str]:
        """
        检测文本中包含的所有关键词

        Args:
            text: 待检测的文本

        Returns:
            匹配到的关键词列表
        """
        if not text:
            return []

        text_lower = text.lower()
        matched = []

        # 遍历所有关键词
        for keyword, keyword_lower in zip(self.keywords, self.keywords_lower):
            if keyword_lower in text_lower:
                matched.append(keyword)

        return matched

    def detect_with_position(self, text: str) -> Optional[Tuple[str, int, int]]:
        """
        检测文本中是否包含关键词，并返回位置信息

        Args:
            text: 待检测的文本

        Returns:
            (关键词, 起始位置, 结束位置)，如果没有匹配则返回None
        """
        if not text:
            return None

        text_lower = text.lower()

        # 遍历所有关键词
        for keyword, keyword_lower in zip(self.keywords, self.keywords_lower):
            pos = text_lower.find(keyword_lower)
            if pos != -1:
                return (keyword, pos, pos + len(keyword))

        return None

    def update_keywords(self, new_keywords: List[str]):
        """
        更新关键词列表

        Args:
            new_keywords: 新的关键词列表
        """
        self.keywords = new_keywords
        self.keywords_lower = [kw.lower() for kw in new_keywords]
        print(f"[INFO] 关键词列表已更新: {self.keywords}")

    def add_keyword(self, keyword: str):
        """
        添加单个关键词

        Args:
            keyword: 要添加的关键词
        """
        if keyword not in self.keywords:
            self.keywords.append(keyword)
            self.keywords_lower.append(keyword.lower())
            print(f"[INFO] 已添加关键词: {keyword}")

    def remove_keyword(self, keyword: str):
        """
        移除关键词

        Args:
            keyword: 要移除的关键词
        """
        if keyword in self.keywords:
            idx = self.keywords.index(keyword)
            self.keywords.pop(idx)
            self.keywords_lower.pop(idx)
            print(f"[INFO] 已移除关键词: {keyword}")

    def get_keywords(self) -> List[str]:
        """
        获取当前的关键词列表

        Returns:
            关键词列表
        """
        return self.keywords.copy()

    def is_empty(self) -> bool:
        """
        检查关键词列表是否为空

        Returns:
            True表示为空，False表示不为空
        """
        return len(self.keywords) == 0
