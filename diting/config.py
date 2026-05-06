"""
配置管理模块
"""

import os
from pathlib import Path
from typing import Optional


class Config:
    """MFS 配置类"""

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化配置

        Args:
            db_path: SQLite 数据库路径，默认为 ~/.diting/memory.db
        """
        if db_path is None:
            home_dir = Path.home()
            diting_dir = home_dir / ".diting"
            diting_dir.mkdir(exist_ok=True)
            self.db_path = str(diting_dir / "memory.db")
        else:
            self.db_path = db_path

        db_dir = Path(self.db_path).parent
        db_dir.mkdir(exist_ok=True)

        self.llm_provider = os.getenv("DITING_LLM_PROVIDER", "dashscope")
        self.llm_api_key = os.getenv("DITING_LLM_API_KEY", "")
        self.llm_model = os.getenv("DITING_LLM_MODEL", "qwen-turbo")
        self.llm_base_url = os.getenv("DITING_LLM_BASE_URL", "")
        self.semantic_scoring_enabled = (
            os.getenv("DITING_SEMANTIC_SCORING", "true").lower() == "true"
        )
        self.semantic_cache_ttl = int(os.getenv("DITING_SEMANTIC_CACHE_TTL", "3600"))
        self.semantic_max_candidates = int(
            os.getenv("DITING_SEMANTIC_MAX_CANDIDATES", "20")
        )
        self.semantic_timeout = int(os.getenv("DITING_SEMANTIC_TIMEOUT", "10"))
        self.llm_weight = float(os.getenv("DITING_LLM_WEIGHT", "0.75"))

    def get_llm_config(self) -> dict:
        """获取 LLM 配置字典"""
        return {
            "llm_provider": self.llm_provider,
            "llm_api_key": self.llm_api_key,
            "llm_model": self.llm_model,
            "llm_base_url": self.llm_base_url,
            "cache_enabled": self.semantic_scoring_enabled,
            "cache_ttl": self.semantic_cache_ttl,
            "max_candidates": self.semantic_max_candidates,
            "timeout": self.semantic_timeout,
            "llm_weight": self.llm_weight,
        }

    def __repr__(self) -> str:
        return f"Config(db_path='{self.db_path}', llm_provider='{self.llm_provider}')"
