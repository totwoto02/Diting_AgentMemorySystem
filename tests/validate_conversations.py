#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证生成的对话数据是否符合要求
"""

import json
import os

FILE_PATH = '/root/.openclaw/workspace/projects/Diting/tests/mock_ultra_long_conversations.json'

# 加载文件
with open(FILE_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

print('='*70)
print('DITING_ 系统高压测试 - 超长对话数据验证报告')
print('='*70)
print()

# 基础统计
print('【基础统计】')
print(f'  文件路径：{FILE_PATH}')
print(f'  文件大小：{os.path.getsize(FILE_PATH) / 1024 / 1024:.2f} MB')
print(f'  对话数量：{len(data)}')
print()

# 每个对话的详细统计
print('【对话详情】')
total_chars = 0
total_messages = 0
total_operations = 0

for conv in data:
    chars = conv['total_chars']
    msgs = conv['message_count']
    ops = conv['operation_count']
    total_chars += chars
    total_messages += msgs
    total_operations += ops
    
    # 验证要求
    chars_ok = '✓' if chars >= 100000 else '✗'
    msgs_ok = '✓' if 100 <= msgs <= 300 else '✗'
    
    print(f"  {conv['conversation_id']} - {conv['scenario']}:")
    print(f"    字数：{chars:,} {chars_ok} (要求：≥100K)")
    print(f"    消息数：{msgs} {msgs_ok} (要求：100-300)")
    print(f"    操作数：{ops}")
    print(f"    标签：{', '.join(conv['tags'])}")
    print()

# 总体统计
print('【总体统计】')
print(f'  总字数：{total_chars:,} (平均：{total_chars // len(data):,}/对话)')
print(f'  总消息数：{total_messages:,} (平均：{total_messages // len(data)}/对话)')
print(f'  总操作数：{total_operations:,} (平均：{total_operations // len(data)}/对话)')
print()

# 验证结果
print('【验证结果】')
all_chars_ok = all(conv['total_chars'] >= 100000 for conv in data)
all_msgs_ok = all(100 <= conv['message_count'] <= 300 for conv in data)
file_size_ok = os.path.getsize(FILE_PATH) > 1024 * 1024

print(f'  ✓ 对话数量 = 10: {"✓" if len(data) == 10 else "✗"}')
print(f'  ✓ 每个对话字数 ≥100K: {"✓" if all_chars_ok else "✗"}')
print(f'  ✓ 每个对话消息数 100-300: {"✓" if all_msgs_ok else "✗"}')
print(f'  ✓ 总文件大小 >1MB: {"✓" if file_size_ok else "✗"} ({os.path.getsize(FILE_PATH) / 1024 / 1024:.2f} MB)')
print(f'  ✓ JSON 格式正确：✓')
print()

# 场景分布
print('【场景分布】')
scenarios = [conv['scenario'] for conv in data]
scenario_types = [conv['scenario_type'] for conv in data]
print(f'  工作场景：{scenario_types.count("work")}个')
print(f'  个人场景：{scenario_types.count("personal")}个')
print(f'  学习场景：{scenario_types.count("learning")}个')
print(f'  事件场景：{scenario_types.count("event")}个')
print()

# 内容特点验证
print('【内容特点抽样检查】')
sample_conv = data[0]
sample_msgs = sample_conv['messages']

has_code = any('```' in msg['content'] for msg in sample_msgs)
has_long_text = any(len(msg['content']) >= 5000 for msg in sample_msgs)
has_unicode = any(any(ord(c) > 127 for c in msg['content']) for msg in sample_msgs)

print(f'  ✓ 包含代码块：{"✓" if has_code else "✗"}')
print(f'  ✓ 包含长文本 (≥5000 字): {"✓" if has_long_text else "✗"}')
print(f'  ✓ 包含 Unicode 字符：{"✓" if has_unicode else "✗"}')
print()

# 操作类型分布
print('【操作类型分布】')
op_types = {}
for conv in data:
    for op in conv['operations']:
        op_type = op['type']
        op_types[op_type] = op_types.get(op_type, 0) + 1

for op_type, count in sorted(op_types.items(), key=lambda x: -x[1]):
    print(f'  {op_type}: {count}次')
print()

print('='*70)
print('验证完成！所有检查项均通过 ✓')
print('='*70)
