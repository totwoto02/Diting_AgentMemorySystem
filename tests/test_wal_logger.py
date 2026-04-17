"""
测试防幻觉盾牌模块（Phase 2）

TDD 第一步：先写测试
"""

import pytest
from diting.wal_logger import WALLogger, WALRecord


class TestWALLogger:
    """测试 WALLogger"""

    def create_fresh_wal(self):
        """创建新的 WALLogger 实例"""
        import random
        import time
        db_id = f"memdb_wal_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        return WALLogger(db_path=f"file:{db_id}?mode=memory&cache=private")

    def test_log_operation(self):
        """测试记录操作"""
        wal = self.create_fresh_wal()
        try:
            # 记录写入操作
            record_id = wal.log_operation(
                operation="CREATE",
                v_path="/test/doc1",
                content="测试内容",
                source_agent="main",
                evidence="conversation_123"
            )
            
            assert record_id > 0
            
            # 验证记录存在
            records = wal.get_history("/test/doc1")
            assert len(records) > 0
            assert records[0]["operation"] == "CREATE"
        finally:
            wal.close()

    def test_log_with_evidence(self):
        """测试记录证据链"""
        wal = self.create_fresh_wal()
        try:
            # 记录带证据的操作
            wal.log_operation(
                operation="UPDATE",
                v_path="/test/doc1",
                content="更新内容",
                source_agent="assistant",
                evidence="conversation_456"
            )
            
            # 获取证据
            records = wal.get_history("/test/doc1")
            assert len(records) > 0
            assert records[0]["evidence"] == "conversation_456"
            assert records[0]["source_agent"] == "assistant"
        finally:
            wal.close()

    def test_get_history(self):
        """测试获取历史记录"""
        wal = self.create_fresh_wal()
        try:
            # 多次操作
            wal.log_operation("CREATE", "/test/doc1", "初始内容", "main", "conv_1")
            wal.log_operation("UPDATE", "/test/doc1", "第一次更新", "main", "conv_2")
            wal.log_operation("UPDATE", "/test/doc1", "第二次更新", "main", "conv_3")
            
            # 获取历史
            history = wal.get_history("/test/doc1")
            
            assert len(history) == 3
            assert history[0]["operation"] == "CREATE"
            assert history[1]["operation"] == "UPDATE"
            assert history[2]["operation"] == "UPDATE"
        finally:
            wal.close()

    def test_rollback(self):
        """测试回滚操作"""
        wal = self.create_fresh_wal()
        try:
            # 创建记录
            wal.log_operation("CREATE", "/test/doc1", "初始内容", "main", "conv_1")
            record_id = wal.log_operation("UPDATE", "/test/doc1", "更新内容", "main", "conv_2")
            
            # 回滚
            success = wal.rollback(record_id)
            
            assert success is True
            
            # 验证回滚后状态
            records = wal.get_history("/test/doc1")
            assert records[-1]["status"] == "ROLLED_BACK"
        finally:
            wal.close()

    def test_get_version(self):
        """测试获取特定版本"""
        wal = self.create_fresh_wal()
        try:
            wal.log_operation("CREATE", "/test/doc1", "V1 内容", "main", "conv_1")
            wal.log_operation("UPDATE", "/test/doc1", "V2 内容", "main", "conv_2")
            wal.log_operation("UPDATE", "/test/doc1", "V3 内容", "main", "conv_3")
            
            # 获取 V2 版本
            v2 = wal.get_version("/test/doc1", version=2)
            
            assert v2 is not None
            assert v2["content"] == "V2 内容"
        finally:
            wal.close()

    def test_get_latest_version(self):
        """测试获取最新版本"""
        wal = self.create_fresh_wal()
        try:
            wal.log_operation("CREATE", "/test/doc1", "V1", "main", "conv_1")
            wal.log_operation("UPDATE", "/test/doc1", "V2", "main", "conv_2")
            
            latest = wal.get_latest_version("/test/doc1")
            
            assert latest is not None
            assert latest["version"] == 2
            assert latest["content"] == "V2"
        finally:
            wal.close()

    def test_trust_score(self):
        """测试置信度评分"""
        wal = self.create_fresh_wal()
        try:
            # 人工录入（高置信度）
            wal.log_operation(
                "CREATE", "/test/doc1", "人工录入",
                source_agent="human",
                evidence="manual_entry",
                confidence=1.0
            )
            
            # AI 推断（低置信度）
            wal.log_operation(
                "CREATE", "/test/doc2", "AI 推断",
                source_agent="assistant",
                evidence="inferred",
                confidence=0.5
            )
            
            # 验证置信度
            doc1 = wal.get_latest_version("/test/doc1")
            doc2 = wal.get_latest_version("/test/doc2")
            
            assert doc1["confidence"] == 1.0
            assert doc2["confidence"] == 0.5
        finally:
            wal.close()

    def test_audit_trail(self):
        """测试审计追踪"""
        wal = self.create_fresh_wal()
        try:
            wal.log_operation("CREATE", "/test/doc1", "内容", "main", "conv_1")
            wal.log_operation("UPDATE", "/test/doc1", "更新", "assistant", "conv_2")
            
            # 获取审计追踪
            audit = wal.get_audit_trail()
            
            assert len(audit) > 0
            # 验证审计信息完整
            assert "timestamp" in audit[0]
            assert "source_agent" in audit[0]
            assert "evidence" in audit[0]
        finally:
            wal.close()
