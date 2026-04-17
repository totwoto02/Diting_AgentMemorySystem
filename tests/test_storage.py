"""
对象存储系统测试（TDD）
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diting.storage_backend import StorageManager, LocalStorage


def test_local_storage():
    """测试本地存储"""
    print("\n[测试] 本地存储...")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 创建本地存储
        storage = LocalStorage(temp_dir)
        
        # 测试保存
        data = b"Hello, World!"
        path = storage.save('test/file.txt', data)
        assert os.path.exists(path)
        print(f"   ✅ 保存文件")
        
        # 测试加载
        loaded_data = storage.load('test/file.txt')
        assert loaded_data == data
        print(f"   ✅ 加载文件")
        
        # 测试存在检查
        exists = storage.exists('test/file.txt')
        assert exists == True
        print(f"   ✅ 存在检查")
        
        # 测试删除
        storage.delete('test/file.txt')
        exists = storage.exists('test/file.txt')
        assert exists == False
        print(f"   ✅ 删除文件")
        
        print("   🎉 本地存储测试通过")
        return True
        
    except Exception as e:
        print(f"   ❌ 失败：{e}")
        return False
        
    finally:
        shutil.rmtree(temp_dir)


def test_storage_manager():
    """测试存储管理器"""
    print("\n[测试] 存储管理器...")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 创建存储管理器
        config = {
            'backend': 'local',
            'local': {'root_path': temp_dir}
        }
        storage = StorageManager(config)
        
        # 测试保存
        data = b"Test data"
        path = storage.save('manager/test.bin', data)
        assert path is not None
        print(f"   ✅ 管理器保存")
        
        # 测试加载
        loaded = storage.load('manager/test.bin')
        assert loaded == data
        print(f"   ✅ 管理器加载")
        
        # 测试多文件
        for i in range(5):
            storage.save(f'file_{i}.txt', f'Data {i}'.encode())
        
        # 检查文件存在
        for i in range(5):
            assert storage.exists(f'file_{i}.txt')
        print(f"   ✅ 多文件存储")
        
        print("   🎉 存储管理器测试通过")
        return True
        
    except Exception as e:
        print(f"   ❌ 失败：{e}")
        return False
        
    finally:
        shutil.rmtree(temp_dir)


def main():
    """运行所有测试"""
    from pathlib import Path
    
    print("=" * 60)
    print("对象存储系统测试（TDD）")
    print("=" * 60)
    
    tests = [
        test_local_storage,
        test_storage_manager
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ❌ 异常：{e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print(f"通过率：{passed/(passed+failed)*100:.1f}%")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
