"""
MFT (Master File Table) 管理器

MFS 的核心数据结构，类似 NTFS 的 MFT，记录所有记忆的元数据
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from collections import OrderedDict
import threading
import re

from .database import Database
from .config import Config
from .errors import MFTInvalidPathError

# 延迟导入知识图谱（避免循环依赖）
def _get_kg_class():
    from .knowledge_graph_v2 import KnowledgeGraphV2
    return KnowledgeGraphV2


class LRUCache:
    """
    LRU 缓存实现

    用于缓存频繁访问的记忆数据，减少数据库查询
    """

    def __init__(self, capacity: int = 100):
        """
        初始化 LRU 缓存

        Args:
            capacity: 缓存容量，默认 100 条记录
        """
        self.capacity = capacity
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        从缓存获取数据

        Args:
            key: 缓存键

        Returns:
            缓存的值，不存在返回 None
        """
        with self.lock:
            if key in self.cache:
                # 移动到末尾（最近使用）
                self.cache.move_to_end(key)
                self.hits += 1
                return self.cache[key]
            self.misses += 1
            return None

    def put(self, key: str, value: Any) -> None:
        """
        向缓存添加数据

        Args:
            key: 缓存键
            value: 缓存值
        """
        with self.lock:
            if key in self.cache:
                # 更新并移动到末尾
                self.cache.move_to_end(key)
                self.cache[key] = value
            else:
                # 添加新条目
                if len(self.cache) >= self.capacity:
                    # 删除最旧的条目
                    self.cache.popitem(last=False)
                self.cache[key] = value

    def delete(self, key: str) -> None:
        """
        从缓存删除数据

        Args:
            key: 缓存键
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]

    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            return {
                "capacity": self.capacity,
                "size": len(self.cache),
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": f"{hit_rate:.2f}%"
            }


class MFT:
    """
    MFT 管理器

    提供记忆文件的 CRUD 操作，类似文件系统的 inode 管理
    """

    def __init__(self, db_path: Optional[str] = None, cache_capacity: int = 100, 
                 kg_db_path: Optional[str] = None):
        """
        初始化 MFT 管理器

        Args:
            db_path: SQLite 数据库路径，默认为内存数据库 (用于测试)
            cache_capacity: LRU 缓存容量，默认 100 条记录
            kg_db_path: 知识图谱数据库路径，None 则不启用 KG
        """
        if db_path is None:
            db_path = ":memory:"

        self.config = Config(db_path=db_path) if db_path != ":memory:" else None
        self.db = Database(self.config) if self.config else Database()
        self._init_schema()

        # 初始化 LRU 缓存
        self.cache = LRUCache(capacity=cache_capacity)
        
        # 初始化知识图谱（Phase 2 集成）
        self.kg = None
        if kg_db_path:
            KnowledgeGraphV2 = _get_kg_class()
            self.kg = KnowledgeGraphV2(kg_db_path)

    def _init_schema(self):
        """初始化 MFT 表结构（Phase 2 扩展 lcn_pointers 字段）"""
        schema = """
        CREATE TABLE IF NOT EXISTS mft (
            inode INTEGER PRIMARY KEY AUTOINCREMENT,
            v_path TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            content TEXT NOT NULL,
            create_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            update_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted INTEGER DEFAULT 0,
            parent_inode INTEGER,
            lcn_pointers TEXT DEFAULT NULL,
            CHECK(type IN ('NOTE', 'RULE', 'CODE', 'TASK', 'CONTACT', 'EVENT')),
            CHECK(status IN ('active', 'archived', 'deleted')),
            FOREIGN KEY (parent_inode) REFERENCES mft(inode)
        );

        -- 核心索引：优化路径查询
        CREATE INDEX IF NOT EXISTS idx_v_path ON mft(v_path);

        -- 类型索引：优化 list_by_type 查询
        CREATE INDEX IF NOT EXISTS idx_type ON mft(type);

        -- 状态索引：优化状态过滤查询
        CREATE INDEX IF NOT EXISTS idx_status ON mft(status);

        -- 时间戳索引：优化时间排序和范围查询
        CREATE INDEX IF NOT EXISTS idx_create_ts ON mft(create_ts);
        CREATE INDEX IF NOT EXISTS idx_update_ts ON mft(update_ts);

        -- 父节点索引：优化层级查询
        CREATE INDEX IF NOT EXISTS idx_parent ON mft(parent_inode);

        -- 删除标记索引：优化软删除过滤
        CREATE INDEX IF NOT EXISTS idx_deleted ON mft(deleted);

        -- 复合索引：优化常见查询模式
        CREATE INDEX IF NOT EXISTS idx_type_status ON mft(type, status);
        CREATE INDEX IF NOT EXISTS idx_path_type ON mft(v_path, type);
        """
        self.db.init_schema(schema)

    def create(self, v_path: str, type: str, content: str, status: str = 'active') -> int:
        """
        创建记忆文件

        Args:
            v_path: 虚拟路径 (如：/test/rules)
            type: 类型 (如：RULE, NOTE, CODE)
            content: 内容
            status: 状态 (active/archived/deleted)，默认 'active'

        Returns:
            inode: 新创建的 inode 编号

        Raises:
            MFTInvalidPathError: 路径无效
        """
        if not v_path.startswith("/"):
            raise MFTInvalidPathError(f"路径必须以 / 开头：{v_path}")

        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO mft (v_path, type, status, content, create_ts, update_ts)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (v_path, type, status, content, datetime.now().isoformat(), datetime.now().isoformat())
            )
            conn.commit()
            inode = cursor.lastrowid

            # 预填充缓存
            result = {
                'inode': inode,
                'v_path': v_path,
                'type': type,
                'status': status,
                'content': content,
                'create_ts': datetime.now(),
                'update_ts': datetime.now()
            }
            self.cache.put(v_path, result)
            
            # Phase 2: 知识图谱自动建图
            if self.kg:
                self._auto_build_kg(v_path, content)

            return inode

    def read(self, v_path: str) -> Optional[Dict[str, Any]]:
        """
        读取记忆文件

        Args:
            v_path: 虚拟路径

        Returns:
            包含 inode, v_path, type, content 等的字典，未找到返回 None
        """
        # 先尝试从缓存读取
        cached = self.cache.get(v_path)
        if cached is not None:
            return cached

        # 缓存未命中，从数据库读取
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT inode, v_path, type, status, content, create_ts, update_ts
                FROM mft
                WHERE v_path = ? AND deleted = 0
                """,
                (v_path,)
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                # 写入缓存
                self.cache.put(v_path, result)
                return result
            return None

    def update(self, v_path: str,
               content: Optional[str] = None,
               status: Optional[str] = None) -> bool:
        """
        更新记忆文件内容或状态

        Args:
            v_path: 虚拟路径
            content: 新内容 (可选)
            status: 新状态 (可选)

        Returns:
            True 如果更新成功，False 如果未找到
        """
        if content is None and status is None:
            return False

        with self.db.get_connection() as conn:
            if content is not None and status is not None:
                cursor = conn.execute(
                    """
                    UPDATE mft
                    SET content = ?, status = ?, update_ts = ?
                    WHERE v_path = ? AND deleted = 0
                    """,
                    (content, status, datetime.now().isoformat(), v_path)
                )
            elif content is not None:
                cursor = conn.execute(
                    """
                    UPDATE mft
                    SET content = ?, update_ts = ?
                    WHERE v_path = ? AND deleted = 0
                    """,
                    (content, datetime.now().isoformat(), v_path)
                )
            else:  # status is not None
                cursor = conn.execute(
                    """
                    UPDATE mft
                    SET status = ?, update_ts = ?
                    WHERE v_path = ? AND deleted = 0
                    """,
                    (status, datetime.now().isoformat(), v_path)
                )
            conn.commit()
            success = cursor.rowcount > 0

            # 更新缓存
            if success:
                cached = self.cache.get(v_path)
                if cached:
                    if content is not None:
                        cached['content'] = content
                    if status is not None:
                        cached['status'] = status
                    cached['update_ts'] = datetime.now()
                    self.cache.put(v_path, cached)

            return success

    def delete(self, v_path: str) -> bool:
        """
        软删除记忆文件

        Args:
            v_path: 虚拟路径

        Returns:
            True 如果删除成功，False 如果未找到
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE mft
                SET deleted = 1, status = 'deleted', update_ts = ?
                WHERE v_path = ? AND deleted = 0
                """,
                (datetime.now().isoformat(), v_path)
            )
            conn.commit()
            success = cursor.rowcount > 0

            # 从缓存删除
            if success:
                self.cache.delete(v_path)

            return success

    def search(self, query: str, scope: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        搜索记忆文件 (使用 LIKE 模糊匹配)

        Args:
            query: 搜索关键词
            scope: 搜索范围 (路径前缀)，默认为 None (全局搜索)

        Returns:
            匹配的记忆文件列表
        """
        with self.db.get_connection() as conn:
            if scope:
                cursor = conn.execute(
                    """
                    SELECT inode, v_path, type, status, content, create_ts, update_ts
                    FROM mft
                    WHERE v_path LIKE ? AND content LIKE ? AND deleted = 0
                    ORDER BY update_ts DESC
                    """,
                    (scope + "%", f"%{query}%")
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT inode, v_path, type, status, content, create_ts, update_ts
                    FROM mft
                    WHERE content LIKE ? AND deleted = 0
                    ORDER BY update_ts DESC
                    """,
                    (f"%{query}%",)
                )

            return [dict(row) for row in cursor.fetchall()]

    def list_by_type(self, type: str) -> List[Dict[str, Any]]:
        """
        按类型列出记忆文件

        Args:
            type: 文件类型

        Returns:
            该类型的所有记忆文件列表
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT inode, v_path, type, status, content, create_ts, update_ts
                FROM mft
                WHERE type = ? AND deleted = 0
                ORDER BY create_ts DESC
                """,
                (type,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def list_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        按状态列出记忆文件

        Args:
            status: 文件状态 (active/archived/deleted)

        Returns:
            该状态的所有记忆文件列表
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT inode, v_path, type, status, content, create_ts, update_ts
                FROM mft
                WHERE status = ? AND deleted = 0
                ORDER BY update_ts DESC
                """,
                (status,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def search_by_type(self, type: str, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        按类型搜索记忆文件

        Args:
            type: 文件类型
            query: 搜索关键词 (可选)

        Returns:
            匹配的记忆文件列表
        """
        with self.db.get_connection() as conn:
            if query:
                cursor = conn.execute(
                    """
                    SELECT inode, v_path, type, status, content, create_ts, update_ts
                    FROM mft
                    WHERE type = ? AND content LIKE ? AND deleted = 0
                    ORDER BY update_ts DESC
                    """,
                    (type, f"%{query}%")
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT inode, v_path, type, status, content, create_ts, update_ts
                    FROM mft
                    WHERE type = ? AND deleted = 0
                    ORDER BY update_ts DESC
                    """,
                    (type,)
                )
            return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict[str, Any]:
        """
        获取 MFT 统计信息

        Returns:
            包含总数、类型分布、状态分布的字典
        """
        with self.db.get_connection() as conn:
            # 总数统计
            total = conn.execute(
                "SELECT COUNT(*) as count FROM mft WHERE deleted = 0"
            ).fetchone()["count"]

            # 按类型统计
            type_stats = conn.execute(
                "SELECT type, COUNT(*) as count FROM mft WHERE deleted = 0 GROUP BY type"
            ).fetchall()

            # 按状态统计
            status_stats = conn.execute(
                "SELECT status, COUNT(*) as count FROM mft WHERE deleted = 0 GROUP BY status"
            ).fetchall()

            return {
                "total": total,
                "by_type": {row["type"]: row["count"] for row in type_stats},
                "by_status": {row["status"]: row["count"] for row in status_stats}
            }
    
    def search_by_path_glob(self, path_pattern: str, type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        使用 GLOB 模式搜索路径（替代正则，性能提升 3-5 倍）
        
        GLOB 模式说明:
        - * 匹配任意数量字符
        - ? 匹配单个字符
        - [] 匹配字符集
        
        Args:
            path_pattern: GLOB 路径模式，例如：
                - "/person/*" 匹配所有/person/下的路径
                - "*/朋友/*" 匹配包含/朋友/的路径
                - "/location/[A-M]*" 匹配 A-M 开头的 location
            type: 类型过滤（可选）
        
        Returns:
            匹配的记忆文件列表
        """
        with self.db.get_connection() as conn:
            if type:
                cursor = conn.execute("""
                    SELECT inode, v_path, type, status, content, create_ts, update_ts
                    FROM mft
                    WHERE v_path GLOB ? AND type = ? AND deleted = 0
                    ORDER BY update_ts DESC
                """, (path_pattern, type))
            else:
                cursor = conn.execute("""
                    SELECT inode, v_path, type, status, content, create_ts, update_ts
                    FROM mft
                    WHERE v_path GLOB ? AND deleted = 0
                    ORDER BY update_ts DESC
                """, (path_pattern,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_json_field(self, v_path: str, json_path: str) -> Optional[Any]:
        """
        使用 SQLite JSON 扩展提取 JSON 字段（替代 Python json.loads，性能提升 3-5 倍）
        
        Args:
            v_path: 虚拟路径
            json_path: JSON 路径，例如：
                - '$.key' 提取顶层 key
                - '$.person.name' 提取嵌套字段
                - '$.tags[0]' 提取数组元素
        
        Returns:
            JSON 字段值，未找到返回 None
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT json_extract(content, ?) AS value
                FROM mft
                WHERE v_path = ? AND deleted = 0
            """, (json_path, v_path))
            
            row = cursor.fetchone()
            return row['value'] if row else None
    
    def search_by_json(self, json_path: str, value: Any) -> List[Dict[str, Any]]:
        """
        使用 SQLite JSON 扩展搜索包含特定 JSON 值的记录
        
        Args:
            json_path: JSON 路径
            value: 要搜索的值
        
        Returns:
            匹配的记忆文件列表
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT inode, v_path, type, status, content, create_ts, update_ts
                FROM mft
                WHERE json_extract(content, ?) = ? AND deleted = 0
                ORDER BY update_ts DESC
            """, (json_path, value))
            
            return [dict(row) for row in cursor.fetchall()]

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            缓存容量、大小、命中率等信息
        """
        return self.cache.get_stats()

    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache.clear()

    # ========== Phase 2: lcn_pointers 支持 ==========

    def get_lcn_pointers(self, v_path: str) -> Optional[list]:
        """
        获取切片指针列表

        Args:
            v_path: 虚拟路径

        Returns:
            切片指针列表，每个指针包含 {chunk_id, offset, length}
            未找到返回 None
        """
        import json

        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT lcn_pointers FROM mft
                WHERE v_path = ? AND deleted = 0
                """,
                (v_path,)
            )
            row = cursor.fetchone()
            if row and row[0]:
                return json.loads(row[0])
            return None

    def set_lcn_pointers(self, v_path: str, pointers: list) -> bool:
        """
        设置切片指针列表

        Args:
            v_path: 虚拟路径
            pointers: 指针列表，每个指针包含 {chunk_id, offset, length}

        Returns:
            True 如果设置成功
        """
        import json

        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE mft
                SET lcn_pointers = ?, update_ts = ?
                WHERE v_path = ? AND deleted = 0
                """,
                (json.dumps(pointers), datetime.now().isoformat(), v_path)
            )
            conn.commit()
            return cursor.rowcount > 0

    def has_slices(self, v_path: str) -> bool:
        """
        检查是否有切片

        Args:
            v_path: 虚拟路径

        Returns:
            True 如果有切片
        """
        pointers = self.get_lcn_pointers(v_path)
        return pointers is not None and len(pointers) > 0

    # ========== Phase 2: 知识图谱集成 ==========
    
    def _extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """
        从文本提取关键词（简化版：按 2-4 字连续词提取）
        
        Args:
            text: 输入文本
            top_k: 返回前 K 个关键词
            
        Returns:
            关键词列表
        """
        # 移除标点和停用词
        text_clean = re.sub(r'[,.!?;:,\s]+', ' ', text)
        words = text_clean.split()
        
        # 过滤停用词
        stopwords = {'的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', 
                     '一个', '特别', '这个', '角色', '类型', 'to', 'the', 'a', 'an', 'is', 'are'}
        filtered_words = [
            w for w in words 
            if len(w) >= 2 and len(w) <= 4 and w not in stopwords
        ]
        
        # 统计词频
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 按频率排序
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        return [word for word, freq in sorted_words[:top_k]]
    
    def _auto_build_kg(self, v_path: str, content: str):
        """
        自动构建知识图谱
        
        Args:
            v_path: 虚拟路径
            content: 内容
        """
        if not self.kg:
            return
        
        try:
            # 提取关键词
            keywords = self._extract_keywords(content, top_k=10)
            
            # 添加概念
            for kw in keywords:
                self.kg.add_concept(kw, "keyword")
            
            # 建立共现关系
            for i, kw1 in enumerate(keywords):
                for kw2 in keywords[i+1:]:
                    self.kg.add_edge(kw1, kw2, "co_occurrence", 1.0)
        except Exception as e:
            # KG 构建失败不影响主流程
            print(f"[KG Build Warning] {e}")
    
    def search_with_kg(self, query: str) -> Dict[str, Any]:
        """
        搜索并获取知识图谱扩展
        
        Args:
            query: 搜索词
            
        Returns:
            搜索结果和 KG 扩展
        """
        # 普通搜索
        results = self.search(query)
        
        # KG 扩展
        kg_expansion = None
        if self.kg:
            kg_result = self.kg.search_with_expansion(query, max_depth=2)
            if kg_result["found"]:
                kg_expansion = {
                    "concept": kg_result.get("concept"),
                    "expanded_concepts": kg_result.get("expanded_concepts", []),
                    "suggestion": kg_result.get("suggestion")
                }
        
        return {
            "search_results": results,
            "kg_expansion": kg_expansion
        }

    def close(self):
        """关闭数据库连接"""
        self.db.close()
        if self.kg:
            # KG 使用 SQLite 连接，不需要额外关闭
            pass

    def __repr__(self) -> str:
        kg_status = "with KG" if self.kg else "no KG"
        return f"MFT(db_path='{self.db.db_path}', {kg_status})"
