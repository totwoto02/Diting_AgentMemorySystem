"""
数据库迁移脚本：001_add_lcn_pointers.py

添加 lcn_pointers 字段到 MFT 表，支持切片指针存储
"""

import sqlite3



def migrate_add_lcn_pointers(db_path: str) -> bool:
    """
    添加 lcn_pointers 字段到 MFT 表

    Args:
        db_path: SQLite 数据库路径

    Returns:
        True 如果迁移成功
    """
    conn = sqlite3.connect(db_path)
    try:
        # 检查字段是否已存在
        cursor = conn.execute("PRAGMA table_info(mft)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'lcn_pointers' in columns:
            print("✓ lcn_pointers 字段已存在，跳过迁移")
            return True
        
        # 添加 lcn_pointers 字段 (JSON 格式存储)
        conn.execute("""
            ALTER TABLE mft ADD COLUMN lcn_pointers TEXT DEFAULT NULL
        """)
        
        # 创建索引优化查询
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_lcn_pointers ON mft(lcn_pointers) 
            WHERE lcn_pointers IS NOT NULL
        """)
        
        conn.commit()
        print("✓ 成功添加 lcn_pointers 字段到 MFT 表")
        return True
        
    except sqlite3.Error as e:
        print(f"✗ 迁移失败：{e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def verify_migration(db_path: str) -> bool:
    """
    验证迁移是否成功

    Args:
        db_path: SQLite 数据库路径

    Returns:
        True 如果验证通过
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("PRAGMA table_info(mft)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'lcn_pointers' not in columns:
            print("✗ 验证失败：lcn_pointers 字段不存在")
            return False
        
        print("✓ 验证通过：lcn_pointers 字段存在")
        return True
        
    except sqlite3.Error as e:
        print(f"✗ 验证失败：{e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    
    db_path = sys.argv[1] if len(sys.argv) > 1 else ":memory:"
    
    print(f"开始数据库迁移：{db_path}")
    print("-" * 50)
    
    success = migrate_add_lcn_pointers(db_path)
    if success:
        verify_migration(db_path)
        print("-" * 50)
        print("迁移完成！")
    else:
        print("-" * 50)
        print("迁移失败！")
        sys.exit(1)
