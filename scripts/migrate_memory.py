#!/usr/bin/env python3
"""
记忆迁移脚本：将 Main Agent 的 MEMORY.md 和 memory/ 目录导入 MFS
"""

import os
import sys
from datetime import datetime

# 添加 MFS 到路径
sys.path.insert(0, '/root/.openclaw/workspace/projects/mfs-memory')

from diting.mft import MFT
from diting.dialog_manager import DialogManager


def migrate_memory_file(mft: MFT, file_path: str, category: str = "memory"):
    """迁移单个记忆文件到 MFS"""
    if not os.path.exists(file_path):
        print(f"  ⚠️  文件不存在：{file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 生成 MFS 路径
    file_name = os.path.basename(file_path)
    mfs_path = f"/{category}/{file_name}"
    
    # 写入 MFS
    try:
        mft.create(mfs_path, "NOTE", content)
        print(f"  ✅ {mfs_path} ({len(content)} 字)")
        return True
    except Exception as e:
        print(f"  ❌ 失败：{e}")
        return False


def migrate_memory_directory(mft: MFT, dir_path: str, category: str = "memory"):
    """迁移整个目录到 MFS"""
    if not os.path.exists(dir_path):
        print(f"  ⚠️  目录不存在：{dir_path}")
        return 0
    
    count = 0
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            file_path = os.path.join(root, file)
            # 生成相对路径
            rel_path = os.path.relpath(file_path, dir_path)
            mfs_path = f"/{category}/{rel_path}"
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                mft.create(mfs_path, "NOTE", content)
                print(f"  ✅ {mfs_path} ({len(content)} 字)")
                count += 1
            except Exception as e:
                print(f"  ❌ {mfs_path}: {e}")
    
    return count


def main():
    """主函数"""
    print("=" * 70)
    print("Main Agent 记忆迁移到 MFS")
    print("=" * 70)
    
    # 备份目录（从参数或默认）
    backup_dir = "/root/.openclaw/backups/main_agent_memory_20260415_135758"
    
    # MFS 数据库路径
    mfs_db = "/root/.openclaw/workspace/projects/mfs-memory/mfs.db"
    kg_db = "/root/.openclaw/workspace/projects/mfs-memory/mfs_kg.db"
    
    print(f"\n备份目录：{backup_dir}")
    print(f"MFS 数据库：{mfs_db}")
    print(f"KG 数据库：{kg_db}")
    
    # 创建 MFT（带 KG）
    print("\n[1/4] 初始化 MFT...")
    mft = MFT(db_path=mfs_db, kg_db_path=kg_db)
    print(f"   ✅ MFT 已初始化 (KG: {mft.kg is not None})")
    
    # 迁移 MEMORY.md
    print("\n[2/4] 迁移 MEMORY.md...")
    memory_md_path = os.path.join(backup_dir, "MEMORY.md")
    migrate_memory_file(mft, memory_md_path, "agent/main")
    
    # 迁移 memory/ 目录
    print("\n[3/4] 迁移 memory/ 目录...")
    memory_dir = os.path.join(backup_dir, "memory/")
    count = migrate_memory_directory(mft, memory_dir, "agent/main/memory")
    print(f"   迁移了 {count} 个文件")
    
    # 迁移配置文件
    print("\n[4/4] 迁移配置文件...")
    for config_file in ["SOUL.md", "USER.md", "TOOLS.md"]:
        config_path = os.path.join(backup_dir, config_file)
        migrate_memory_file(mft, config_path, "agent/main/config")
    
    # 查看 KG 统计
    print("\n📊 知识图谱统计:")
    if mft.kg:
        stats = mft.kg.get_stats()
        print(f"   概念数：{stats['concept_count']}")
        print(f"   边数：{stats['edge_count']}")
        print(f"   平均每概念边数：{stats['avg_edges_per_concept']:.2f}")
    
    # MFS 统计
    print("\n📊 MFS 统计:")
    mft_stats = mft.get_stats()
    print(f"   总记录数：{mft_stats['total']}")
    print(f"   按类型：{mft_stats['by_type']}")
    
    print("\n" + "=" * 70)
    print("🎉 记忆迁移完成！")
    print("=" * 70)
    
    print("\n✅ 验证方法:")
    print("   # 使用 MCP 工具搜索记忆")
    print("   mcporter call mfs-memory.mfs_search query=\"朋友\"")
    print("   mcporter call mfs-memory.kg_stats")
    print("   mcporter call mfs-memory.kg_search query=\"拍照\"")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 迁移失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
