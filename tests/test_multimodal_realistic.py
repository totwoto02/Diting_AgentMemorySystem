"""
多模态真实场景测试

测试数据基于真实多模态应用场景
参考：COCO Caption, Flickr8k 等数据集格式
"""

import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diting.multimodal_manager import MultimodalMemoryManager


# 真实场景测试数据
TEST_SCENARIOS = [
    {
        "name": "场景 1: 会议录音",
        "type": "audio",
        "description": "项目讨论会议录音",
        "expected_keywords": ["会议", "项目", "讨论", "计划"],
        "ai_summary_mock": "团队讨论项目进度，确定下周里程碑，分配任务给张三和李四"
    },
    {
        "name": "场景 2: 产品照片",
        "type": "image",
        "description": "新产品原型照片",
        "expected_keywords": ["产品", "原型", "设计", "外观"],
        "ai_summary_mock": "白色电子产品原型，长方体设计，正面有屏幕和按钮"
    },
    {
        "name": "场景 3: 语音备忘",
        "type": "audio",
        "description": "个人语音备忘录",
        "expected_keywords": ["备忘", "提醒", "安排", "时间"],
        "ai_summary_mock": "提醒明天下午 3 点开会，准备演示材料，提前 10 分钟到场"
    },
    {
        "name": "场景 4: 活动现场照片",
        "type": "image",
        "description": "展会活动现场照片",
        "expected_keywords": ["展会", "活动", "人群", "展台"],
        "ai_summary_mock": "室内展会现场，多人聚集在展台前，有横幅和展示品"
    },
    {
        "name": "场景 5: 文档截图",
        "type": "image",
        "description": "重要文档截图",
        "expected_keywords": ["文档", "文字", "表格", "数据"],
        "ai_summary_mock": "包含表格的文档截图，有标题和多行文字内容"
    }
]


def create_test_manager():
    """创建测试管理器"""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    storage_dir = tempfile.mkdtemp()
    
    config = {
        'ENABLE_AI_SUMMARY': False,
        'ENABLE_SMART_TRIGGER': False,
        'ENABLE_TEMPERATURE': True,
        'ENABLE_ENTROPY': False
    }
    
    manager = MultimodalMemoryManager(db_path, storage_dir, config)
    return manager, db_fd, storage_dir


def test_scenario(scenario):
    """测试单个场景"""
    print(f"\n[测试] {scenario['name']}...")
    
    manager, db_fd, storage_dir = create_test_manager()
    
    try:
        # 模拟文件数据
        if scenario['type'] == 'image':
            # JPEG 文件头
            file_data = bytes([0xFF, 0xD8, 0xFF, 0xE0] + [0x00] * 100)
            file_ext = 'jpg'
        else:
            # OGG 文件头
            file_data = bytes([0x4F, 0x67, 0x67, 0x53] + [0x00] * 100)
            file_ext = 'ogg'
        
        # 存储
        if scenario['type'] == 'image':
            result = manager.store_image(
                image_data=file_data,
                memory_path=f"/test/{scenario['name'][:10]}",
                original_filename=f"test.{file_ext}"
            )
        else:
            result = manager.store_audio(
                audio_data=file_data,
                memory_path=f"/test/{scenario['name'][:10]}",
                original_filename=f"test.{file_ext}"
            )
        
        # 验证
        assert 'slice_id' in result, "缺少 slice_id"
        assert result['is_duplicate'] == False, "不应是重复文件"
        
        print(f"   ✅ 存储成功")
        print(f"      类型：{scenario['type']}")
        print(f"      描述：{scenario['description']}")
        print(f"      切片 ID: {result['slice_id'][:8]}...")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 失败：{e}")
        return False
        
    finally:
        manager.close()
        os.close(db_fd)


def test_search_scenarios():
    """测试搜索场景"""
    print("\n[测试] 搜索功能测试...")
    
    manager, db_fd, storage_dir = create_test_manager()
    
    try:
        # 存储多个测试数据
        for i, scenario in enumerate(TEST_SCENARIOS[:3]):
            file_data = bytes([0xFF, 0xD8] + [0x00] * 50)
            manager.store_image(
                image_data=file_data,
                memory_path=f"/test/search/{i}",
                original_filename=f"test{i}.jpg"
            )
        
        # 搜索测试
        queries = ['test', '项目', '会议']
        
        for query in queries:
            results = manager.search(query)
            print(f"   搜索 '{query}': 找到 {len(results)} 条结果")
        
        print(f"   ✅ 搜索测试完成")
        return True
        
    except Exception as e:
        print(f"   ❌ 失败：{e}")
        return False
        
    finally:
        manager.close()
        os.close(db_fd)


def test_temperature_system():
    """测试温度系统"""
    print("\n[测试] 温度系统测试...")
    
    manager, db_fd, storage_dir = create_test_manager()
    
    try:
        # 存储文件
        file_data = bytes([0xFF, 0xD8] + [0x00] * 50)
        result = manager.store_image(
            image_data=file_data,
            memory_path='/test/temp_test'
        )
        
        # 检查温度字段
        cursor = manager.db.execute("""
            SELECT temperature, temperature_score FROM multimodal_slices
            WHERE slice_id = ?
        """, (result['slice_id'],))
        row = cursor.fetchone()
        
        assert row['temperature'] == 'warm', "默认温度应为 warm"
        assert row['temperature_score'] == 50, "默认温度分数应为 50"
        
        print(f"   ✅ 温度系统正常")
        print(f"      默认温度：{row['temperature']}")
        print(f"      温度分数：{row['temperature_score']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 失败：{e}")
        return False
        
    finally:
        manager.close()
        os.close(db_fd)


def main():
    """运行所有测试"""
    print("=" * 70)
    print("多模态真实场景测试（TDD）")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    # 测试 1: 真实场景
    print("\n[部分 1] 真实场景测试")
    for scenario in TEST_SCENARIOS:
        if test_scenario(scenario):
            passed += 1
        else:
            failed += 1
    
    # 测试 2: 搜索功能
    print("\n[部分 2] 搜索功能测试")
    if test_search_scenarios():
        passed += 1
    else:
        failed += 1
    
    # 测试 3: 温度系统
    print("\n[部分 3] 温度系统测试")
    if test_temperature_system():
        passed += 1
    else:
        failed += 1
    
    # 总结
    print("\n" + "=" * 70)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print(f"通过率：{passed/(passed+failed)*100:.1f}%")
    print("=" * 70)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
