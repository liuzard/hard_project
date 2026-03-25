
#!/usr/bin/env python3
"""
主程序入口
"""

import sys
from pathlib import Path

# 确保能找到 src 模块
sys.path.insert(0, str(Path(__file__).parent))

from src.main import main

if __name__ == "__main__":
    sys.exit(main())
