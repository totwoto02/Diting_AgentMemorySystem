"""
知识图谱模块

自动从记忆内容提取概念并构建关联
"""

import json
import re
import os
from typing import Dict, List, Any, Optional
from collections import defaultdict


class KnowledgeGraph:
    """
    知识图谱
    
    自动从记忆内容提取概念，计算共现频率构建关联
    """

    def __init__(self, graph_path: Optional[str] = None):
        """
        初始化知识图谱

        Args:
            graph_path: 图谱文件路径，None 则使用内存存储
        """
        self.graph_path = graph_path
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        
        if graph_path:
            self.load()

    def extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """
        从文本提取关键词（简化版：按 2-4 字连续词提取）

        Args:
            text: 输入文本
            top_k: 返回前 K 个关键词

        Returns:
            关键词列表
        """
        # 移除标点和停用词
        text_clean = re.sub(r'[，。！？；：、\s]+', ' ', text)
        words = text_clean.split()
        
        # 过滤停用词
        stopwords = {'的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '特别', '这个', '角色', '类型'}
        filtered_words = [
            w for w in words 
            if len(w) >= 2 and len(w) <= 4 and w not in stopwords
        ]
        
        # 统计词频
        word_freq = defaultdict(int)
        for word in filtered_words:
            word_freq[word] += 1
        
        # 按频率排序
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        return [word for word, freq in sorted_words[:top_k]]

    def add_memory(self, v_path: str, content: str, keywords: Optional[List[str]] = None):
        """
        添加记忆到图谱

        Args:
            v_path: 记忆路径
            content: 记忆内容
            keywords: 可选的关键词列表，None 则自动提取
        """
        if keywords is None:
            keywords = self.extract_keywords(content)
        
        # 添加节点
        for kw in keywords:
            if kw not in self.nodes:
                self.nodes[kw] = {
                    "type": "concept",
                    "count": 1,
                    "paths": [v_path]
                }
            else:
                self.nodes[kw]["count"] += 1
                if v_path not in self.nodes[kw]["paths"]:
                    self.nodes[kw]["paths"].append(v_path)
        
        # 添加边（共现关系）
        for i, kw1 in enumerate(keywords):
            for kw2 in keywords[i+1:]:
                # 检查边是否已存在
                edge_exists = False
                for edge in self.edges:
                    if (edge["from"] == kw1 and edge["to"] == kw2) or \
                       (edge["from"] == kw2 and edge["to"] == kw1):
                        edge["weight"] += 1
                        edge_exists = True
                        break
                
                if not edge_exists:
                    self.edges.append({
                        "from": kw1,
                        "to": kw2,
                        "weight": 1
                    })

    def get_related_concepts(self, keyword: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        获取相关概念

        Args:
            keyword: 查询关键词
            top_k: 返回前 K 个相关概念

        Returns:
            相关概念列表
        """
        if keyword not in self.nodes:
            return []
        
        # 找到所有关联边
        related = []
        for edge in self.edges:
            if edge["from"] == keyword:
                related.append({
                    "concept": edge["to"],
                    "weight": edge["weight"]
                })
            elif edge["to"] == keyword:
                related.append({
                    "concept": edge["from"],
                    "weight": edge["weight"]
                })
        
        # 按权重排序
        related.sort(key=lambda x: x["weight"], reverse=True)
        
        return related[:top_k]

    def search_with_expansion(self, query: str) -> Dict[str, Any]:
        """
        搜索并扩展相关概念

        Args:
            query: 搜索词

        Returns:
            搜索结果和扩展建议
        """
        related = self.get_related_concepts(query)
        
        return {
            "query": query,
            "found": query in self.nodes,
            "related_concepts": [r["concept"] for r in related],
            "suggestion": f"搜索 '{query}' 时，可能也关心：{', '.join([r['concept'] for r in related[:3]])}" if related else None
        }

    def save(self):
        """保存图谱到文件"""
        if not self.graph_path:
            return
        
        data = {
            "nodes": self.nodes,
            "edges": self.edges
        }
        
        with open(self.graph_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self):
        """从文件加载图谱"""
        if not self.graph_path or not os.path.exists(self.graph_path):
            return
        
        with open(self.graph_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.nodes = data.get("nodes", {})
        self.edges = data.get("edges", [])

    def get_stats(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "avg_edges_per_node": len(self.edges) / len(self.nodes) if self.nodes else 0
        }
