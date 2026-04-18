"""
统一数据库测试辅助模块

提供统一数据库初始化和清理功能
"""

import sqlite3
import random
import time


def create_unified_db(db_id: str) -> str:
    """
    创建统一数据库（包含所有 DITING_ 表）
    
    Args:
        db_id: 数据库 ID
        
    Returns:
        数据库路径
    """
    db_path = f"file:{db_id}?mode=memory&cache=private"
    
    # 创建 MFT 表（FTS5 依赖）
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    
    # MFT 表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mft (
            inode INTEGER PRIMARY KEY AUTOINCREMENT,
            v_path TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            content TEXT,
            deleted INTEGER DEFAULT 0,
            create_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            update_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            parent_inode INTEGER,
            lcn_pointers TEXT DEFAULT NULL,
            CHECK(type IN ('NOTE', 'RULE', 'CODE', 'TASK', 'CONTACT', 'EVENT')),
            CHECK(status IN ('active', 'archived', 'deleted'))
        )
    """)
    
    # FTS5 虚拟表
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS mft_fts5 USING fts5(
            content,
            v_path,
            type,
            content='mft',
            content_rowid='inode'
        )
    """)
    
    # FTS5 触发器
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS mft_ai AFTER INSERT ON mft BEGIN
            INSERT INTO mft_fts5(rowid, content, v_path, type)
            VALUES (new.inode, new.content, new.v_path, new.type);
        END
    """)
    
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS mft_ad AFTER DELETE ON mft BEGIN
            INSERT INTO mft_fts5(mft_fts5, rowid, content, v_path, type)
            VALUES ('delete', old.inode, old.content, old.v_path, old.type);
        END
    """)
    
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS mft_au AFTER UPDATE ON mft BEGIN
            INSERT INTO mft_fts5(mft_fts5, rowid, content, v_path, type)
            VALUES ('delete', old.inode, old.content, old.v_path, old.type);
            INSERT INTO mft_fts5(rowid, content, v_path, type)
            VALUES (new.inode, new.content, new.v_path, new.type);
        END
    """)
    
    # 知识图谱表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kg_concepts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            aliases TEXT DEFAULT '[]',
            created_at REAL DEFAULT (strftime('%s', 'now'))
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kg_aliases (
            alias TEXT PRIMARY KEY,
            concept_id INTEGER NOT NULL,
            FOREIGN KEY (concept_id) REFERENCES kg_concepts(id)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kg_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_concept TEXT NOT NULL,
            to_concept TEXT NOT NULL,
            relation TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            timestamp REAL DEFAULT (strftime('%s', 'now')),
            UNIQUE(from_concept, to_concept)
        )
    """)
    
    # 四系统架构预留字段说明（已添加到 multimodal_slices）：
    # 内能（U）：heat_score - 记忆被访问总次数的标准化 (0-100)
    # 温度（T）：temp_score - 与当前上下文的关联度 (0-1)，待实现
    # 熵（S）：entropy_score - 记忆争议性/混乱度 (0-1)，待实现
    # 自由能（G）：free_energy_score - G = U - TS，记忆有效性，待实现
    
    # WAL 日志表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wal_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation TEXT NOT NULL,
            v_path TEXT NOT NULL,
            old_content TEXT,
            new_content TEXT,
            agent TEXT,
            conversation_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            trust_score REAL DEFAULT 1.0
        )
    """)
    
    conn.commit()
    conn.close()
    
    return db_path


def cleanup_db(db_path: str):
    """
    清理数据库（关闭连接）
    
    Args:
        db_path: 数据库路径
    """
    # SQLite 内存数据库会自动清理
    pass
