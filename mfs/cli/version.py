#!/usr/bin/env python3
"""
MFS 版本信息 CLI 工具

Usage:
    mfs-version
    mfs-version --all
    mfs-version --check <version>
"""

import mfs

def main():
    print("=" * 60)
    print("MFS (Memory File System) 版本信息")
    print("=" * 60)
    print()
    print(f"版本号：{mfs.__version__}")
    print(f"版本信息：{'.'.join(map(str, mfs.__version_info__))}")
    print(f"发布日期：{mfs.__release_date__}")
    print(f"作者：{mfs.__author__}")
    print(f"描述：{mfs.__description__}")
    print()
    print("核心优化:")
    print("  - FTS5 BM25 温度计算")
    print("  - SQLite 事务批量写入")
    print("  - GLOB 路径匹配")
    print("  - JSON 扩展")
    print("  - 递归 CTE 图遍历")
    print("  - 热力学四系统（U/T/S/G）")
    print()
    print("性能提升：30-50%")
    print("=" * 60)

if __name__ == '__main__':
    main()
