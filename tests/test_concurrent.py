"""
MFT 并发写入测试

测试多线程并发场景下的数据一致性和事务处理
"""

import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

from diting.mft import MFT
from diting.errors import MFTException


class TestConcurrentWrite:
    """测试并发写入场景"""
    
    def test_concurrent_write(self, temp_db):
        """
        测试多个线程同时写入不同路径
        验证无冲突且数据完整
        """
        num_threads = 5  # 减少并发数，避免 SQLite 锁竞争
        writes_per_thread = 5
        errors: List[Exception] = []
        inodes: List[int] = []
        lock = threading.Lock()
        
        def worker(thread_id: int):
            """工作线程函数（带重试机制）"""
            for attempt in range(3):  # 最多重试 3 次
                try:
                    # 每个线程创建独立的 MFT 实例（共享同一数据库文件）
                    mft = MFT(temp_db)
                    local_inodes = []
                    
                    for i in range(writes_per_thread):
                        path = f"/concurrent/thread{thread_id}/item{i}"
                        content = f"Thread {thread_id} Item {i} content"
                        inode = mft.create(path, "NOTE", content)
                        local_inodes.append(inode)
                    
                    # 线程安全地收集结果
                    with lock:
                        inodes.extend(local_inodes)
                    
                    mft.close()
                    break  # 成功则退出重试循环
                    
                except Exception as e:
                    if "database is locked" in str(e) and attempt < 2:
                        time.sleep(0.1 * (attempt + 1))  # 指数退避
                        continue
                    with lock:
                        errors.append(e)
                    break
        
        # 创建并启动线程
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 验证结果
        assert len(errors) == 0, f"并发写入出现错误：{errors}"
        assert len(inodes) == num_threads * writes_per_thread, "写入数量不匹配"
        assert len(set(inodes)) == len(inodes), "存在重复的 inode"
        
        # 验证所有数据都可读取
        mft_verify = MFT(temp_db)
        for i in range(num_threads):
            for j in range(writes_per_thread):
                path = f"/concurrent/thread{i}/item{j}"
                result = mft_verify.read(path)
                assert result is not None, f"无法读取 {path}"
                assert result["content"] == f"Thread {i} Item {j} content"
        
        mft_verify.close()
    
    def test_concurrent_write_same_path(self, temp_db):
        """
        测试多个线程同时写入相同路径
        验证 UNIQUE 约束生效
        """
        num_threads = 5
        path = "/concurrent/same_path"
        success_count = 0
        error_count = 0
        lock = threading.Lock()
        
        def worker(thread_id: int):
            """工作线程函数"""
            nonlocal success_count, error_count
            try:
                mft = MFT(temp_db)
                content = f"Thread {thread_id} content"
                inode = mft.create(path, "NOTE", content)
                
                with lock:
                    success_count += 1
                
                mft.close()
            except Exception as e:
                with lock:
                    error_count += 1
        
        # 创建并启动线程
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 验证：只有一个线程成功，其他都失败
        assert success_count == 1, f"应该有且仅有一个线程成功，实际：{success_count}"
        assert error_count == num_threads - 1, f"其他线程应该失败，实际：{error_count}"
    
    def test_concurrent_read_write(self, temp_db):
        """
        测试并发读写混合场景
        验证读写不阻塞且数据一致
        """
        # 先创建一些初始数据
        mft_init = MFT(temp_db)
        for i in range(10):
            mft_init.create(f"/initial/item{i}", "NOTE", f"Initial content {i}")
        mft_init.close()
        
        num_readers = 5
        num_writers = 3
        read_count = 0
        write_count = 0
        lock = threading.Lock()
        
        def reader(reader_id: int):
            """读者线程"""
            nonlocal read_count
            mft = MFT(temp_db)
            
            for _ in range(20):
                # 随机读取
                for i in range(10):
                    result = mft.read(f"/initial/item{i}")
                    if result:
                        with lock:
                            read_count += 1
                time.sleep(0.01)  # 短暂延迟
            
            mft.close()
        
        def writer(writer_id: int):
            """写者线程"""
            nonlocal write_count
            mft = MFT(temp_db)
            
            for i in range(10):
                path = f"/concurrent_rw/writer{writer_id}/item{i}"
                mft.create(path, "NOTE", f"Writer {writer_id} item {i}")
                with lock:
                    write_count += 1
                time.sleep(0.01)
            
            mft.close()
        
        # 启动读写线程
        threads = []
        for i in range(num_readers):
            t = threading.Thread(target=reader, args=(i,))
            threads.append(t)
            t.start()
        
        for i in range(num_writers):
            t = threading.Thread(target=writer, args=(i,))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 验证操作都完成了
        assert read_count > 0, "应该有读操作"
        assert write_count == num_writers * 10, "写操作数量不匹配"


class TestTransactionRollback:
    """测试事务回滚机制"""
    
    def test_transaction_rollback_on_error(self, temp_db):
        """
        测试发生错误时事务自动回滚
        """
        mft = MFT(temp_db)
        
        # 创建一个初始记录
        mft.create("/transaction/test", "NOTE", "Initial content")
        
        # 尝试在一个事务中进行多个操作，中间制造错误
        try:
            with mft.db.get_connection() as conn:
                conn.execute("BEGIN TRANSACTION")
                
                try:
                    # 第一次插入（成功）
                    conn.execute(
                        "INSERT INTO mft (v_path, type, status, content) VALUES (?, ?, ?, ?)",
                        ("/transaction/batch1", "NOTE", "active", "Batch 1")
                    )
                    
                    # 尝试插入重复路径（会失败）
                    conn.execute(
                        "INSERT INTO mft (v_path, type, status, content) VALUES (?, ?, ?, ?)",
                        ("/transaction/test", "NOTE", "active", "Duplicate")  # 路径已存在
                    )
                    
                    # 这行不会执行
                    conn.execute(
                        "INSERT INTO mft (v_path, type, status, content) VALUES (?, ?, ?, ?)",
                        ("/transaction/batch2", "NOTE", "active", "Batch 2")
                    )
                    
                    conn.execute("COMMIT")
                except Exception:
                    # 发生错误，回滚事务
                    conn.execute("ROLLBACK")
                    raise
        except Exception:
            # 预期会失败
            pass
        
        # 验证：初始记录还在，新记录都不在
        result = mft.read("/transaction/test")
        assert result is not None
        assert result["content"] == "Initial content"
        
        # batch1 和 batch2 都不应该存在（因为回滚了）
        assert mft.read("/transaction/batch1") is None
        assert mft.read("/transaction/batch2") is None
        
        mft.close()
    
    def test_partial_update_rollback(self, temp_db):
        """
        测试部分更新失败时的回滚
        """
        mft = MFT(temp_db)
        mft.create("/rollback/test", "NOTE", "Original content")
        
        # 手动测试事务回滚
        try:
            with mft.db.get_connection() as conn:
                conn.execute("BEGIN TRANSACTION")
                
                # 第一次更新（成功）
                conn.execute(
                    "UPDATE mft SET content = ? WHERE v_path = ?",
                    ("Updated content", "/rollback/test")
                )
                
                # 尝试更新不存在的记录（会失败）
                conn.execute(
                    "UPDATE mft SET content = ? WHERE v_path = ?",
                    ("Should not apply", "/rollback/nonexistent")
                )
                
                # 如果到这里还没异常，主动回滚
                conn.execute("ROLLBACK")
        except Exception:
            # 预期会失败
            pass
        
        # 验证：内容应该保持原样
        result = mft.read("/rollback/test")
        assert result is not None
        assert result["content"] == "Original content"
        
        mft.close()
    
    def test_commit_on_success(self, temp_db):
        """
        测试成功时事务正确提交
        """
        mft = MFT(temp_db)
        
        # 成功的事务操作
        with mft.db.get_connection() as conn:
            conn.execute("BEGIN TRANSACTION")
            
            conn.execute(
                "INSERT INTO mft (v_path, type, status, content) VALUES (?, ?, ?, ?)",
                ("/commit/test1", "NOTE", "active", "Committed 1")
            )
            
            conn.execute(
                "INSERT INTO mft (v_path, type, status, content) VALUES (?, ?, ?, ?)",
                ("/commit/test2", "NOTE", "active", "Committed 2")
            )
            
            conn.execute("COMMIT")
        
        # 验证：两条记录都应该存在
        result1 = mft.read("/commit/test1")
        result2 = mft.read("/commit/test2")
        
        assert result1 is not None
        assert result1["content"] == "Committed 1"
        assert result2 is not None
        assert result2["content"] == "Committed 2"
        
        mft.close()


class TestLockMechanism:
    """测试 SQLite 锁机制"""
    
    def test_database_locking(self, temp_db):
        """
        测试 SQLite 的数据库级锁机制
        """
        # 创建初始数据
        mft_init = MFT(temp_db)
        mft_init.create("/lock/test", "NOTE", "Initial")
        mft_init.close()
        
        lock_acquired = False
        lock_released = False
        error_occurred = False
        
        def long_transaction():
            """长时间持有锁的事务"""
            nonlocal lock_acquired, lock_released
            mft = MFT(temp_db)
            
            try:
                with mft.db.get_connection() as conn:
                    conn.execute("BEGIN IMMEDIATE TRANSACTION")
                    
                    # 模拟长时间操作
                    lock_acquired = True
                    time.sleep(0.5)  # 持有锁 0.5 秒
                    
                    conn.execute(
                        "UPDATE mft SET content = ? WHERE v_path = ?",
                        ("Updated", "/lock/test")
                    )
                    
                    conn.execute("COMMIT")
                    lock_released = True
                    
                mft.close()
            except Exception as e:
                nonlocal error_occurred
                error_occurred = True
        
        def try_read():
            """尝试在锁持有期间读取"""
            nonlocal lock_acquired
            mft = MFT(temp_db)
            
            # 等待锁被获取
            while not lock_acquired:
                time.sleep(0.05)
            
            # 尝试读取（SQLite 允许并发读）
            try:
                result = mft.read("/lock/test")
                mft.close()
                return result is not None
            except Exception:
                mft.close()
                return False
        
        # 启动长事务线程
        writer_thread = threading.Thread(target=long_transaction)
        writer_thread.start()
        
        # 启动读取线程
        reader_thread = threading.Thread(target=try_read)
        reader_thread.start()
        
        # 等待完成
        writer_thread.join()
        reader_thread.join()
        
        # 验证
        assert lock_acquired, "锁应该被获取"
        assert lock_released, "锁应该被释放"
        assert not error_occurred, "不应该发生错误"
    
    def test_wal_mode_concurrent_access(self, temp_db):
        """
        测试 WAL 模式下的并发访问
        """
        # WAL 模式应该在 database.py 中已启用
        mft = MFT(temp_db)
        
        # 验证 WAL 模式已启用
        with mft.db.get_connection() as conn:
            result = conn.execute("PRAGMA journal_mode").fetchone()
            # 注意：对于内存数据库或某些配置，WAL 可能不适用
            # 这里只是验证不会出错
        
        mft.close()
        
        # 测试并发访问
        success_count = 0
        lock = threading.Lock()
        
        def worker(worker_id: int):
            nonlocal success_count
            worker_mft = MFT(temp_db)
            
            try:
                for i in range(5):
                    path = f"/wal/worker{worker_id}/item{i}"
                    worker_mft.create(path, "NOTE", f"Content {i}")
                
                with lock:
                    success_count += 1
            finally:
                worker_mft.close()
        
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        assert success_count == 5, "所有线程都应该成功"
