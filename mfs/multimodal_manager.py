"""
MFS 多模态记忆管理器

支持图片和语音的存储、AI 概括生成、可搜索
"""

import os
import json
import uuid
import hashlib
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path


class MultimodalMemoryManager:
    """多模态记忆管理器"""
    
    def __init__(self, db_path: str, storage_dir: str, config: Dict = None):
        """
        初始化多模态管理器
        
        Args:
            db_path: SQLite 数据库路径
            storage_dir: 文件存储目录
            config: 配置字典
        """
        self.db_path = db_path
        self.storage_dir = Path(storage_dir)
        self.config = config or {}
        
        # 配置选项
        self.enable_ai_summary = self.config.get('ENABLE_AI_SUMMARY', True)
        self.enable_smart_trigger = self.config.get('ENABLE_SMART_TRIGGER', True)
        self.enable_temperature = self.config.get('ENABLE_TEMPERATURE', True)
        self.enable_entropy = self.config.get('ENABLE_ENTROPY', False)
        
        # 智能触发阈值
        self.ai_trigger_filesize = self.config.get('AI_TRIGGER_FILESIZE', 1024 * 1024)  # 1MB
        self.ai_trigger_max_monthly = self.config.get('AI_TRIGGER_MAX_MONTHLY', 100)
        
        # 初始化
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self._init_schema()
        self._ensure_storage_dirs()
    
    def _init_schema(self):
        """初始化数据库表"""
        schema_file = os.path.join(os.path.dirname(__file__), 'multimodal_schema.sql')
        if os.path.exists(schema_file):
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            self.db.executescript(schema_sql)
            self.db.commit()
    
    def _ensure_storage_dirs(self):
        """确保存储目录存在"""
        # 按日期组织目录结构
        base_dirs = [
            self.storage_dir / 'images' / datetime.now().strftime('%Y') / datetime.now().strftime('%m'),
            self.storage_dir / 'audio' / datetime.now().strftime('%Y') / datetime.now().strftime('%m'),
            self.storage_dir / 'thumbnails',
        ]
        for dir_path in base_dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def store_image(self, image_data: bytes, memory_path: str,
                    original_filename: str = None,
                    generate_ai_summary: bool = None) -> Dict:
        """
        存储图片
        
        Args:
            image_data: 图片二进制
            memory_path: 关联的记忆路径
            original_filename: 原始文件名
            generate_ai_summary: 是否生成 AI 概括（None=智能触发）
        
        Returns:
            切片信息
        """
        import hashlib
        
        # 1. 计算哈希（去重）
        file_hash = hashlib.sha256(image_data).hexdigest()
        
        # 2. 检查是否已存在
        existing = self._find_by_hash(file_hash)
        if existing:
            self._add_reference(existing['slice_id'], memory_path)
            return {
                'slice_id': existing['slice_id'],
                'file_hash': file_hash,
                'is_duplicate': True,
                'message': '文件已存在，已添加引用'
            }
        
        # 3. 存储文件
        storage_path = self._save_file(image_data, 'image', original_filename)
        
        # 4. 决定是否调用 AI
        should_call_ai = self._should_call_ai(
            file_type='image',
            file_data=image_data,
            force_flag=generate_ai_summary
        )
        
        # 5. AI 生成概括（如果触发）
        ai_summary = None
        ai_keywords = []
        ai_entities = []
        ai_confidence = 0.0
        
        if should_call_ai and self.enable_ai_summary:
            ai_result = self._analyze_image(image_data)
            ai_summary = ai_result.get('summary')
            ai_keywords = ai_result.get('keywords', [])
            ai_entities = ai_result.get('entities', [])
            ai_confidence = ai_result.get('confidence', 0.0)
        
        # 6. 创建切片记录
        slice_id = str(uuid.uuid4())
        self.db.execute("""
            INSERT INTO multimodal_slices (
                slice_id, memory_path, file_hash, file_type, file_size,
                file_extension, storage_path, original_filename,
                ai_summary, ai_keywords, ai_entities, ai_confidence,
                temperature, temperature_score,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            slice_id, memory_path, file_hash, 'image/jpeg', len(image_data),
            original_filename.split('.')[-1] if original_filename else 'jpg',
            storage_path, original_filename,
            ai_summary, json.dumps(ai_keywords), json.dumps(ai_entities), ai_confidence,
            'warm', 50,
            datetime.now(), datetime.now()
        ))
        
        self.db.commit()
        
        # 7. 构建搜索向量
        search_vector = self._build_search_vector(ai_summary, ai_keywords, ai_entities)
        self.db.execute("""
            UPDATE multimodal_slices 
            SET search_vector = ?
            WHERE slice_id = ?
        """, (search_vector, slice_id))
        self.db.commit()
        
        # 8. 记录 AI 调用（如果调用了）
        if should_call_ai:
            self._log_ai_call(slice_id, 'image_summary')
        
        return {
            'slice_id': slice_id,
            'file_hash': file_hash,
            'storage_path': str(storage_path),
            'ai_summary': ai_summary,
            'is_duplicate': False,
            'ai_called': should_call_ai
        }
    
    def store_audio(self, audio_data: bytes, memory_path: str,
                    original_filename: str = None,
                    generate_ai_summary: bool = None) -> Dict:
        """
        存储语音
        
        Args:
            audio_data: 语音二进制
            memory_path: 关联的记忆路径
            original_filename: 原始文件名
            generate_ai_summary: 是否生成 AI 概括（None=智能触发）
        
        Returns:
            切片信息
        """
        import hashlib
        
        # 1. 计算哈希
        file_hash = hashlib.sha256(audio_data).hexdigest()
        
        # 2. 检查去重
        existing = self._find_by_hash(file_hash)
        if existing:
            self._add_reference(existing['slice_id'], memory_path)
            return {
                'slice_id': existing['slice_id'],
                'file_hash': file_hash,
                'is_duplicate': True,
                'message': '文件已存在，已添加引用'
            }
        
        # 3. 存储文件
        storage_path = self._save_file(audio_data, 'audio', original_filename)
        
        # 4. 决定是否调用 AI（语音默认调用，因为转文字价值高）
        should_call_ai = self._should_call_ai(
            file_type='audio',
            file_data=audio_data,
            force_flag=generate_ai_summary,
            default_for_audio=True  # 语音默认调用
        )
        
        # 5. AI 处理
        ai_summary = None
        ai_keywords = []
        raw_transcript = None
        duration_seconds = None
        
        if should_call_ai and self.enable_ai_summary:
            ai_result = self._analyze_audio(audio_data)
            ai_summary = ai_result.get('summary')
            ai_keywords = ai_result.get('keywords', [])
            raw_transcript = ai_result.get('transcript')
            duration_seconds = ai_result.get('duration')
        
        # 6. 创建切片记录
        slice_id = str(uuid.uuid4())
        self.db.execute("""
            INSERT INTO multimodal_slices (
                slice_id, memory_path, file_hash, file_type, file_size,
                file_extension, storage_path, original_filename,
                ai_summary, ai_keywords, raw_transcript, duration_seconds,
                temperature, temperature_score,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            slice_id, memory_path, file_hash, 'audio/ogg', len(audio_data),
            original_filename.split('.')[-1] if original_filename else 'ogg',
            storage_path, original_filename,
            ai_summary, json.dumps(ai_keywords), raw_transcript, duration_seconds,
            'warm', 50,
            datetime.now(), datetime.now()
        ))
        
        self.db.commit()
        
        # 7. 构建搜索向量
        search_vector = self._build_search_vector(ai_summary, ai_keywords, transcript=raw_transcript)
        self.db.execute("""
            UPDATE multimodal_slices 
            SET search_vector = ?
            WHERE slice_id = ?
        """, (search_vector, slice_id))
        self.db.commit()
        
        # 8. 记录 AI 调用
        if should_call_ai:
            self._log_ai_call(slice_id, 'audio_transcribe')
        
        return {
            'slice_id': slice_id,
            'file_hash': file_hash,
            'storage_path': str(storage_path),
            'ai_summary': ai_summary,
            'raw_transcript': raw_transcript,
            'is_duplicate': False,
            'ai_called': should_call_ai
        }
    
    def _should_call_ai(self, file_type: str, file_data: bytes,
                       force_flag: bool = None,
                       default_for_audio: bool = False) -> bool:
        """
        智能触发 AI 调用
        
        Args:
            file_type: image 或 audio
            file_data: 文件二进制
            force_flag: 用户强制指定（True/False/None）
            default_for_audio: 语音默认调用
        
        Returns:
            是否调用 AI
        """
        # 用户强制指定优先
        if force_flag is not None:
            return force_flag
        
        # 智能触发未启用时，默认不调用
        if not self.enable_smart_trigger:
            return False
        
        # 语音默认调用（转文字价值高）
        if file_type == 'audio' and default_for_audio:
            return True
        
        # 图片：检查文件大小
        if file_type == 'image':
            if len(file_data) > self.ai_trigger_filesize:
                return True  # 大图片，可能是重要照片
        
        # 默认不调用（节省成本）
        return False
    
    def _save_file(self, file_data: bytes, file_type: str,
                   original_filename: str = None) -> str:
        """保存文件到存储目录"""
        # 按日期组织目录
        date_dir = datetime.now().strftime('%Y/%m')
        
        if file_type == 'image':
            base_dir = self.storage_dir / 'images' / date_dir
        else:
            base_dir = self.storage_dir / 'audio' / date_dir
        
        # 使用 hash 作为文件名（去重）
        file_hash = hashlib.sha256(file_data).hexdigest()
        extension = original_filename.split('.')[-1] if original_filename else ('jpg' if file_type == 'image' else 'ogg')
        
        file_path = base_dir / f"{file_hash}.{extension}"
        
        # 如果文件已存在（重复上传），直接返回
        if file_path.exists():
            return str(file_path)
        
        # 保存文件
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        return str(file_path)
    
    def _find_by_hash(self, file_hash: str) -> Optional[Dict]:
        """根据哈希查找已存在的文件"""
        cursor = self.db.execute("""
            SELECT slice_id, memory_path, reference_count
            FROM multimodal_slices
            WHERE file_hash = ?
        """, (file_hash,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def _add_reference(self, slice_id: str, memory_path: str):
        """添加引用（同一文件被多个记忆引用）"""
        self.db.execute("""
            UPDATE multimodal_slices 
            SET reference_count = reference_count + 1,
                updated_at = ?
            WHERE slice_id = ?
        """, (datetime.now(), slice_id))
        self.db.commit()
    
    def _build_search_vector(self, ai_summary: str = None,
                            ai_keywords: list = None,
                            ai_entities: list = None,
                            transcript: str = None) -> str:
        """构建 FTS5 搜索向量"""
        parts = [
            ai_summary or '',
            ' '.join(ai_keywords or []),
            ' '.join(ai_entities or []),
            transcript or ''
        ]
        return ' '.join(filter(None, parts))
    
    def _analyze_image(self, image_data: bytes) -> Dict:
        """
        AI 分析图片
        
        TODO: 集成 MCP 多模态工具
        目前返回模拟数据
        """
        # 模拟 AI 分析结果
        return {
            'summary': '图片内容分析',
            'keywords': ['图片', '记忆'],
            'entities': [],
            'confidence': 0.8
        }
    
    def _analyze_audio(self, audio_data: bytes) -> Dict:
        """
        AI 分析语音
        
        TODO: 集成 MCP 多模态工具
        目前返回模拟数据
        """
        # 模拟 AI 分析结果
        return {
            'summary': '语音内容概括',
            'keywords': ['语音', '备忘'],
            'transcript': '语音转文字结果',
            'duration': 30.0
        }
    
    def _log_ai_call(self, slice_id: str, call_type: str):
        """记录 AI 调用日志"""
        self.db.execute("""
            INSERT INTO ai_call_log (slice_id, call_type, model_name, called_at)
            VALUES (?, ?, 'qwen-vl-max', ?)
        """, (slice_id, call_type, datetime.now()))
        self.db.commit()
    
    def search(self, query: str, include_multimodal: bool = True) -> List[Dict]:
        """搜索记忆（包含多模态）"""
        results = []
        
        if include_multimodal:
            cursor = self.db.execute("""
                SELECT m.slice_id, m.memory_path, m.file_type, m.ai_summary,
                       m.raw_transcript, m.storage_path, m.temperature
                FROM multimodal_search s
                JOIN multimodal_slices m ON s.rowid = m.rowid
                WHERE multimodal_search MATCH ?
                LIMIT 20
            """, (query,))
            
            for row in cursor.fetchall():
                results.append({
                    'type': 'multimodal_slice',
                    'slice_id': row['slice_id'],
                    'memory_path': row['memory_path'],
                    'file_type': row['file_type'],
                    'ai_summary': row['ai_summary'],
                    'raw_transcript': row['raw_transcript'],
                    'storage_path': row['storage_path'],
                    'temperature': row['temperature']
                })
        
        return results
    
    def close(self):
        """关闭数据库连接"""
        self.db.close()
