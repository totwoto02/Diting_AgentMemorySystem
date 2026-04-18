#!/usr/bin/env python3
"""
生成 100 段 OpenClaw 模拟对话和工作场景，用于 DITING_ 系统压力测试
"""

import json
import random
from datetime import datetime, timedelta

# 场景配置
SCENARIOS = {
    "个人记忆": 30,
    "工作记录": 30,
    "学习笔记": 20,
    "事件记录": 20
}

# 长度配置（记忆内容长度）
CONTENT_LENGTHS = {
    "短": (100, 500, 30),
    "中": (500, 2000, 40),
    "长": (2000, 5000, 20),
    "超长": (5000, 10000, 10)
}

# 对话长度配置（按消息总字数和消息数量）
DIALOG_LENGTHS = {
    "短对话": (100, 500, 2, 4, 30),      # 字数范围，消息数范围，数量
    "中对话": (500, 2000, 4, 8, 40),
    "长对话": (2000, 5000, 8, 15, 20),
    "超长对话": (5000, 10000, 15, 30, 10)
}

# 人物资料库
PERSONS = [
    "测试用户", "小明", "张三", "李四", "王五", "赵六", "钱七", "孙八", "周九", "吴十",
    "Alice", "Bob", "Charlie", "David", "Emma", "Frank", "Grace", "Henry", "Ivy", "Jack",
    "田中", "山田", "佐藤", "鈴木", "高橋", "Иван", "Анна", "محمد", "فاطمة", "김민수"
]

# 项目资料库
PROJECTS = [
    "DITING_ 记忆系统", "OpenClaw 核心", "Clawdbot", "智能助手 v2", "知识图谱引擎",
    "WAL 日志系统", "向量数据库", "语义搜索引擎", "多模态 RAG", "Agent 协调框架",
    "Feishu 集成", "QQBot 插件", "企业微信 MCP", "语音合成服务", "图像处理管道"
]

# 技术栈
TECH_STACK = [
    "Python", "TypeScript", "Rust", "Go", "Java", "Node.js", "React", "Vue",
    "PostgreSQL", "MongoDB", "Redis", "Elasticsearch", "Docker", "Kubernetes",
    "GraphQL", "REST API", "WebSocket", "gRPC", "MessageQueue", "EventStream"
]

# 会议主题
MEETING_TOPICS = [
    "周例会", "项目评审", "技术分享", "需求讨论", "代码审查",
    "架构设计", "性能优化", "安全审计", "用户反馈", "产品规划"
]

# 特殊字符和 Unicode 测试内容
SPECIAL_CHARS = [
    "→", "←", "↑", "↓", "★", "☆", "●", "○", "■", "□",
    "αβγδε", "λμπΣΩ", "∑∏∫∂∇", "∀∃∅∈∉", "∧∨¬⇒⇔",
    "你好", "世界", "测试", "数据", "系统",
    "🚀", "💡", "🔧", "📊", "🎯", "✅", "❌", "⚠️", "📝", "🔍",
    "émojis: 😀😃😄😁😆😅😂🤣",
    "数学公式：E = mc², ∫₀^∞ e^(-x²)dx = √π/2",
    "代码片段：function test() { return 'hello'; }",
    "路径：C:\\Users\\test\\file.txt, /home/user/.config/app.json",
    "URL: https://example.com/path?query=value&foo=bar#anchor"
]

def generate_content(scenario, length_type, conv_id):
    """生成记忆内容"""
    min_len, max_len, _ = CONTENT_LENGTHS[length_type]
    target_len = random.randint(min_len, max_len)
    
    content_parts = []
    
    if scenario == "个人记忆":
        person = random.choice(PERSONS)
        content_parts.append(f"关于{person}的个人资料：")
        content_parts.append(f"姓名：{person}")
        content_parts.append(f"联系方式：{person.lower().replace(' ', '')}@example.com")
        content_parts.append(f"电话：+86-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}")
        content_parts.append(f"地址：{''.join(random.choices('北京市朝阳区上海市广州市深圳市', k=random.randint(10, 30)))}")
        content_parts.append(f"偏好：{random.choice(['喜欢', '讨厌', '擅长', '关注'])}{random.choice(['编程', '音乐', '运动', '阅读', '旅行', '美食'])}")
        content_parts.append(f"备注：{random.choice(SPECIAL_CHARS)}")
        content_parts.append(f"最后更新：{datetime.now().isoformat()}")
        
        # 添加更多细节以达到目标长度
        while len(''.join(content_parts)) < target_len:
            content_parts.append(f"相关记录：{random.choice(['项目合作', '朋友关系', '同事', '客户', '供应商'])} - {random.choice(SPECIAL_CHARS)}")
    
    elif scenario == "工作记录":
        project = random.choice(PROJECTS)
        content_parts.append(f"项目：{project}")
        content_parts.append(f"状态：{random.choice(['进行中', '已完成', '暂停', '规划中', '测试中'])}")
        content_parts.append(f"优先级：{random.choice(['P0', 'P1', 'P2', 'P3'])}")
        content_parts.append(f"技术栈：{', '.join(random.sample(TECH_STACK, random.randint(2, 5)))}")
        content_parts.append(f"负责人：{random.choice(PERSONS)}")
        content_parts.append(f"开始日期：{(datetime.now() - timedelta(days=random.randint(1, 365))).strftime('%Y-%m-%d')}")
        content_parts.append(f"描述：{random.choice(SPECIAL_CHARS)}")
        
        # 添加代码块
        if random.random() > 0.5:
            content_parts.append("\n```python")
            content_parts.append(f"def {project.replace(' ', '_').lower()}_main():")
            content_parts.append(f"    # TODO: 实现{project}核心逻辑")
            content_parts.append(f"    config = load_config('{project}.yaml')")
            content_parts.append(f"    result = process(config)")
            content_parts.append(f"    return result")
            content_parts.append("```")
        
        # 添加更多细节
        while len(''.join(content_parts)) < target_len:
            content_parts.append(f"\n里程碑：{random.choice(['需求分析', '设计评审', '开发完成', '测试通过', '上线部署'])} - {random.choice(SPECIAL_CHARS)}")
    
    elif scenario == "学习笔记":
        topic = random.choice(TECH_STACK)
        content_parts.append(f"学习主题：{topic}")
        content_parts.append(f"学习日期：{datetime.now().strftime('%Y-%m-%d')}")
        content_parts.append(f"难度等级：{random.choice(['入门', '初级', '中级', '高级', '专家'])}")
        content_parts.append(f"关键概念：")
        
        for i in range(random.randint(3, 8)):
            content_parts.append(f"  - 概念{i+1}: {random.choice(SPECIAL_CHARS)}")
        
        content_parts.append(f"\n核心要点：")
        content_parts.append(f"1. {random.choice(SPECIAL_CHARS)}")
        content_parts.append(f"2. {random.choice(SPECIAL_CHARS)}")
        content_parts.append(f"3. {random.choice(SPECIAL_CHARS)}")
        
        # 添加代码示例
        content_parts.append(f"\n示例代码：")
        content_parts.append(f"```{random.choice(['python', 'javascript', 'rust', 'go'])}")
        content_parts.append(f"// {topic} 示例")
        content_parts.append(f"const example = new {topic}();")
        content_parts.append(f"example.init();")
        content_parts.append(f"```")
        
        while len(''.join(content_parts)) < target_len:
            content_parts.append(f"\n参考资料：https://example.com/{topic.lower()}/docs/{random.randint(1, 100)}")
    
    else:  # 事件记录
        topic = random.choice(MEETING_TOPICS)
        content_parts.append(f"事件：{topic}")
        content_parts.append(f"类型：{random.choice(['会议', '约会', '活动', '提醒', '截止日期'])}")
        content_parts.append(f"时间：{(datetime.now() + timedelta(days=random.randint(-30, 30))).strftime('%Y-%m-%d %H:%M')}")
        content_parts.append(f"地点：{random.choice(['线上', '北京办公室', '上海会议室', '广州分部', '深圳研发中心', random.choice(SPECIAL_CHARS)])}")
        content_parts.append(f"参与者：{', '.join(random.sample(PERSONS, random.randint(2, 6)))}")
        content_parts.append(f"议程：")
        
        for i in range(random.randint(2, 5)):
            content_parts.append(f"  {i+1}. {random.choice(SPECIAL_CHARS)}")
        
        content_parts.append(f"\n会议纪要：{random.choice(SPECIAL_CHARS)}")
        content_parts.append(f"行动项：{random.choice(SPECIAL_CHARS)}")
        
        while len(''.join(content_parts)) < target_len:
            content_parts.append(f"\n后续跟进：{random.choice(['已完成', '进行中', '待开始', '已取消'])} - {random.choice(SPECIAL_CHARS)}")
    
    return '\n'.join(content_parts)

def generate_messages(scenario, content, person=None, project=None, dialog_length_type="中对话"):
    """生成对话消息"""
    messages = []
    
    # 根据对话长度类型确定消息数量
    _, _, min_msgs, max_msgs, _ = DIALOG_LENGTHS[dialog_length_type]
    num_message_pairs = random.randint(min_msgs // 2, max_msgs // 2)
    
    if scenario == "个人记忆":
        person = person or random.choice(PERSONS)
        user_msgs = [
            f"记住{person}的个人信息",
            f"更新{person}的联系方式",
            f"查找{person}的所有记录",
            f"{person}的偏好是什么？",
            f"删除{person}的过期信息",
            f"{person}最近有什么变化？",
            f"帮我整理{person}的档案",
            f"{person}的生日是什么时候？"
        ]
        ai_msgs = [
            f"好的，已记录{person}的信息到/person/{person}/profile",
            f"已更新{person}的联系方式，旧信息已归档",
            f"找到{person}的{random.randint(1, 5)}条相关记录",
            f"{person}的偏好已记录在/person/{person}/preferences",
            f"已清理{person}的过期数据，保留最近{random.randint(3, 12)}个月的记录",
            f"{person}最近在{random.choice(['工作', '生活', '学习'])}方面有新的动态",
            f"已整理{person}的完整档案，包含{random.randint(5, 20)}个项目",
            f"{person}的生日是{random.randint(1, 12)}月{random.randint(1, 28)}日"
        ]
    
    elif scenario == "工作记录":
        project = project or random.choice(PROJECTS)
        user_msgs = [
            f"创建{project}的项目文档",
            f"更新{project}的进度状态",
            f"搜索{project}相关的代码",
            f"{project}的负责人是谁？",
            f"归档已完成的{project}",
            f"{project}的技术栈是什么？",
            f"列出{project}的所有任务",
            f"{project}的截止日期是什么时候？"
        ]
        ai_msgs = [
            f"已创建{project}的文档到/work/{project.replace(' ', '_')}/docs",
            f"已更新{project}的状态为{random.choice(['进行中', '已完成', '暂停'])}",
            f"在/work/{project.replace(' ', '_')}下找到{random.randint(1, 10)}个相关文件",
            f"{project}的负责人是{random.choice(PERSONS)}",
            f"已将{project}归档到/work/archive/{datetime.now().strftime('%Y')}",
            f"{project}使用{', '.join(random.sample(TECH_STACK, 3))}等技术",
            f"{project}共有{random.randint(5, 30)}个任务，其中{random.randint(1, 10)}个待处理",
            f"{project}的截止日期是{(datetime.now() + timedelta(days=random.randint(7, 90))).strftime('%Y-%m-%d')}"
        ]
    
    elif scenario == "学习笔记":
        topic = random.choice(TECH_STACK)
        user_msgs = [
            f"记录{topic}的学习笔记",
            f"整理{topic}的知识点",
            f"搜索{topic}相关的资料",
            f"导出{topic}的学习总结",
            f"删除过时的{topic}笔记",
            f"{topic}的核心概念是什么？",
            f"推荐{topic}的学习路径",
            f"{topic}有哪些常见应用场景？"
        ]
        ai_msgs = [
            f"已将{topic}笔记保存到/learning/{topic}/notes",
            f"已整理{topic}的知识图谱，包含{random.randint(5, 20)}个节点",
            f"找到{random.randint(1, 8)}篇关于{topic}的文章",
            f"已生成{topic}学习总结，共{random.randint(500, 2000)}字",
            f"已清理{random.randint(1, 5)}条过时的{topic}笔记",
            f"{topic}的核心概念包括{random.choice(['基础原理', '核心算法', '架构设计'])}",
            f"建议按{random.choice(['入门→进阶→实战', '理论→实践→优化'])}的路径学习{topic}",
            f"{topic}常用于{random.choice(['Web 开发', '数据分析', '人工智能', '系统架构'])}等领域"
        ]
    
    else:  # 事件记录
        topic = random.choice(MEETING_TOPICS)
        user_msgs = [
            f"安排{topic}会议",
            f"修改会议时间",
            f"查询下周的会议",
            f"取消{topic}",
            f"发送会议提醒",
            f"{topic}的参与者有哪些？",
            f"准备{topic}的议程",
            f"记录{topic}的会议纪要"
        ]
        ai_msgs = [
            f"已创建{topic}会议，时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"会议时间已更新，已通知所有参与者",
            f"下周共有{random.randint(3, 10)}场会议，详情见/events/2026-W15",
            f"已取消{topic}，并通知相关人员",
            f"已设置会议提醒，提前{random.choice([15, 30, 60])}分钟通知",
            f"{topic}的参与者包括{', '.join(random.sample(PERSONS, random.randint(2, 5)))}",
            f"已生成{topic}议程，共{random.randint(3, 8)}个议题",
            f"已记录{topic}的会议纪要，包含{random.randint(2, 10)}个行动项"
        ]
    
    # 生成消息对
    for i in range(num_message_pairs):
        # 用户消息
        messages.append({
            "role": "user",
            "content": random.choice(user_msgs)
        })
        # AI 回复
        messages.append({
            "role": "assistant",
            "content": random.choice(ai_msgs)
        })
    
    return messages

def generate_operations(scenario, path, content, op_type=None):
    """生成操作记录"""
    if op_type is None:
        op_type = random.choice(["CREATE", "UPDATE", "SEARCH", "DELETE"])
    
    operations = []
    
    if op_type == "CREATE":
        operations.append({
            "type": "CREATE",
            "path": path,
            "content": content,
            "confidence": round(random.uniform(0.8, 1.0), 2)
        })
    elif op_type == "UPDATE":
        operations.append({
            "type": "UPDATE",
            "path": path,
            "content": content,
            "confidence": round(random.uniform(0.7, 1.0), 2),
            "previous_version": f"{path}@v{random.randint(1, 10)}"
        })
    elif op_type == "SEARCH":
        operations.append({
            "type": "SEARCH",
            "path": path.replace('/profile', '').replace('/preferences', ''),
            "content": f"查询条件：{content[:100]}...",
            "confidence": round(random.uniform(0.5, 0.9), 2),
            "results_count": random.randint(1, 20)
        })
    else:  # DELETE
        operations.append({
            "type": "DELETE",
            "path": path,
            "content": f"删除原因：{random.choice(['过期', '重复', '错误', '用户请求'])}",
            "confidence": round(random.uniform(0.9, 1.0), 2),
            "archived": random.choice([True, False])
        })
    
    # 有时会添加关联操作
    if random.random() > 0.7:
        related_path = path.rsplit('/', 1)[0] + '/metadata'
        operations.append({
            "type": random.choice(["CREATE", "UPDATE"]),
            "path": related_path,
            "content": f"元数据更新：{datetime.now().isoformat()}",
            "confidence": round(random.uniform(0.8, 1.0), 2)
        })
    
    return operations

def generate_path(scenario, person=None, project=None):
    """生成记忆路径"""
    if scenario == "个人记忆":
        person = person or random.choice(PERSONS)
        path_type = random.choice(["profile", "preferences", "contact", "notes", "history"])
        return f"/person/{person}/{path_type}"
    elif scenario == "工作记录":
        project = project or random.choice(PROJECTS)
        project_slug = project.replace(' ', '_').lower()
        path_type = random.choice(["docs", "code", "tasks", "meetings", "decisions"])
        return f"/work/{project_slug}/{path_type}"
    elif scenario == "学习笔记":
        topic = random.choice(TECH_STACK)
        path_type = random.choice(["notes", "summary", "examples", "references", "questions"])
        return f"/learning/{topic.lower()}/{path_type}"
    else:  # 事件记录
        event_type = random.choice(["meeting", "appointment", "activity", "reminder", "deadline"])
        date_str = datetime.now().strftime('%Y-%m-%d')
        return f"/events/{event_type}/{date_str}/{random.randint(1, 100)}"

def generate_tags(scenario, length_type):
    """生成标签"""
    tags = [scenario, f"{length_type}长度"]
    
    # 添加额外标签
    extra_tags = {
        "个人记忆": ["人物关系", "联系方式", "偏好设置", "历史记录"],
        "工作记录": ["项目文档", "代码片段", "任务管理", "决策记录"],
        "学习笔记": ["知识点", "代码示例", "参考资料", "问题记录"],
        "事件记录": ["会议", "约会", "提醒", "截止日期"]
    }
    
    tags.append(random.choice(extra_tags[scenario]))
    
    if random.random() > 0.5:
        tags.append(random.choice(["含特殊字符", "含代码块", "含 Unicode", "含链接"]))
    
    if random.random() > 0.7:
        tags.append("关联概念")
    
    return tags

def main():
    conversations = []
    
    # 分配长度类型到各个场景
    total_convs = sum(SCENARIOS.values())
    length_distribution = {
        "短": 30,
        "中": 50,
        "长": 20
    }
    
    # 为每个场景分配长度
    scenario_lengths = {}
    remaining = length_distribution.copy()
    
    for scenario, count in SCENARIOS.items():
        scenario_lengths[scenario] = []
        for length_type, total_count in length_distribution.items():
            # 按比例分配
            allocated = int(count * total_count / total_convs)
            scenario_lengths[scenario].extend([length_type] * allocated)
        
        # 补齐不足
        while len(scenario_lengths[scenario]) < count:
            length_type = random.choice(list(remaining.keys()))
            scenario_lengths[scenario].append(length_type)
        
        # 截断超出
        scenario_lengths[scenario] = scenario_lengths[scenario][:count]
    
    # 生成对话
    conv_id = 0
    tracked_paths = {}  # 用于跟踪路径，以便创建更新操作
    
    for scenario, count in SCENARIOS.items():
        for i in range(count):
            conv_id += 1
            
            # 选择长度类型
            length_type = scenario_lengths[scenario][i] if i < len(scenario_lengths[scenario]) else "中"
            
            # 生成内容
            content = generate_content(scenario, length_type, conv_id)
            
            # 生成路径
            path = generate_path(scenario)
            
            # 决定是否使用已有路径（创建更新操作）
            if random.random() > 0.6 and path in tracked_paths:
                op_type = "UPDATE"
            else:
                op_type = None
                tracked_paths[path] = True
            
            # 生成消息
            messages = generate_messages(scenario, content)
            
            # 生成操作
            operations = generate_operations(scenario, path, content, op_type)
            
            # 生成标签
            tags = generate_tags(scenario, length_type)
            
            conversation = {
                "conversation_id": f"conv_{conv_id:03d}",
                "messages": messages,
                "operations": operations,
                "tags": tags,
                "metadata": {
                    "scenario": scenario,
                    "length_type": length_type,
                    "content_length": len(content),
                    "generated_at": datetime.now().isoformat()
                }
            }
            
            conversations.append(conversation)
    
    # 打乱顺序
    random.shuffle(conversations)
    
    # 重新编号
    for i, conv in enumerate(conversations, 1):
        conv["conversation_id"] = f"conv_{i:03d}"
    
    # 保存到文件
    output_path = "/root/.openclaw/workspace/projects/Diting/tests/mock_conversations.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)
    
    # 生成统计报告
    print("=" * 60)
    print("DITING_ 系统压力测试 - 模拟对话生成完成")
    print("=" * 60)
    
    # 场景统计
    print("\n📊 场景分布统计:")
    scenario_counts = {}
    for conv in conversations:
        scenario = conv["metadata"]["scenario"]
        scenario_counts[scenario] = scenario_counts.get(scenario, 0) + 1
    
    for scenario, expected in SCENARIOS.items():
        actual = scenario_counts.get(scenario, 0)
        status = "✅" if actual == expected else "⚠️"
        print(f"  {status} {scenario}: {actual} (目标：{expected})")
    
    # 长度统计
    print("\n📏 长度分布统计:")
    length_counts = {}
    for conv in conversations:
        length_type = conv["metadata"]["length_type"]
        length_counts[length_type] = length_counts.get(length_type, 0) + 1
    
    for length_type, (min_len, max_len, expected) in LENGTHS.items():
        actual = length_counts.get(length_type, 0)
        status = "✅" if actual == expected else "⚠️"
        print(f"  {status} {length_type} ({min_len}-{max_len}字): {actual} (目标：{expected})")
    
    # 操作类型统计
    print("\n🔧 操作类型统计:")
    op_counts = {}
    for conv in conversations:
        for op in conv["operations"]:
            op_type = op["type"]
            op_counts[op_type] = op_counts.get(op_type, 0) + 1
    
    for op_type, count in sorted(op_counts.items()):
        print(f"  {op_type}: {count}")
    
    # 内容特征统计
    print("\n✨ 内容特征统计:")
    special_char_count = sum(1 for conv in conversations if any(tag in conv["tags"] for tag in ["含特殊字符", "含代码块", "含 Unicode", "含链接"]))
    related_concept_count = sum(1 for conv in conversations if "关联概念" in conv["tags"])
    update_count = sum(1 for conv in conversations if any(op["type"] == "UPDATE" for op in conv["operations"]))
    
    print(f"  含特殊内容：{special_char_count} 段")
    print(f"  含关联概念：{related_concept_count} 段")
    print(f"  含更新操作：{update_count} 段")
    
    # 长度范围统计
    print("\n📐 实际长度范围:")
    all_lengths = [conv["metadata"]["content_length"] for conv in conversations]
    print(f"  最短：{min(all_lengths)} 字")
    print(f"  最长：{max(all_lengths)} 字")
    print(f"  平均：{sum(all_lengths) / len(all_lengths):.1f} 字")
    
    # 验证 JSON 格式
    print("\n✅ JSON 格式验证:")
    try:
        with open(output_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        print(f"  文件格式有效，共 {len(loaded)} 段对话")
    except Exception as e:
        print(f"  ❌ 验证失败：{e}")
    
    print("\n" + "=" * 60)
    print(f"输出文件：{output_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
