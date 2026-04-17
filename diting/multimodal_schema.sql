-- =============================================
-- MFS 多模态记忆切片系统 - 数据库表结构
-- 版本：v0.4.0
-- 创建时间：2026-04-15
-- =============================================

-- 1. 多模态记忆切片主表
CREATE TABLE IF NOT EXISTS multimodal_slices (
    -- 基础标识
    slice_id TEXT PRIMARY KEY,              -- 切片 ID（UUID）
    memory_path TEXT NOT NULL,              -- 关联的记忆路径
    parent_slice_id TEXT,                   -- 父切片 ID（可选）
    
    -- 文件信息
    file_hash TEXT NOT NULL,                -- SHA256 哈希（去重）
    file_type TEXT NOT NULL,                -- 文件类型：image/jpeg, audio/ogg
    file_size INTEGER NOT NULL,             -- 文件大小（字节）
    file_extension TEXT,                    -- 文件扩展名
    storage_path TEXT NOT NULL,             -- 文件存储路径
    original_filename TEXT,                 -- 原始文件名
    
    -- AI 生成内容（核心）
    ai_summary TEXT,                        -- AI 概括内容
    ai_keywords TEXT,                       -- AI 关键词（JSON 数组）
    ai_entities TEXT,                       -- AI 识别实体（JSON 对象）
    ai_confidence REAL DEFAULT 0.0,         -- AI 置信度 0-1
    
    -- 语音特有字段
    raw_transcript TEXT,                    -- 原始转文字
    speaker_id TEXT,                        -- 说话人 ID
    duration_seconds REAL,                  -- 语音时长（秒）
    
    -- 图片特有字段
    image_width INTEGER,                    -- 图片宽度
    image_height INTEGER,                   -- 图片高度
    dominant_colors TEXT,                   -- 主色调（JSON 数组）
    objects_detected TEXT,                  -- 检测到的物体（JSON 数组）
    
    -- 温度系统字段
    temperature TEXT DEFAULT 'warm',        -- hot/warm/cold/frozen
    temperature_score INTEGER DEFAULT 50,   -- 温度分数 -100 到 100
    last_heated_at TIMESTAMP,
    freeze_reason TEXT,
    freeze_by TEXT,
    freeze_at TIMESTAMP,
    
    -- 熵系统字段（可选，默认 NULL）
    entropy INTEGER DEFAULT NULL,           -- 熵值 0-100（NULL=未启用）
    entropy_level TEXT DEFAULT NULL,        -- high/medium/low
    last_entropy_change TIMESTAMP,
    entropy_trend TEXT DEFAULT NULL,        -- increasing/stable/decreasing
    
    -- 迭代相关
    iteration_version TEXT,                 -- 版本号 v1/v2/v3
    iteration_status TEXT DEFAULT 'active', -- active/deprecated/frozen
    superseded_by TEXT,                     -- 被哪个版本替代
    
    -- 引用和访问
    reference_count INTEGER DEFAULT 0,      -- 引用计数
    last_accessed TIMESTAMP,
    last_mentioned_round INTEGER,           -- 最后提及轮次
    
    -- 搜索优化
    search_vector TEXT,                     -- FTS5 搜索向量
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_memory_path ON multimodal_slices(memory_path);
CREATE INDEX IF NOT EXISTS idx_file_hash ON multimodal_slices(file_hash);
CREATE INDEX IF NOT EXISTS idx_file_type ON multimodal_slices(file_type);
CREATE INDEX IF NOT EXISTS idx_temperature ON multimodal_slices(temperature);
CREATE INDEX IF NOT EXISTS idx_entropy ON multimodal_slices(entropy);
CREATE INDEX IF NOT EXISTS idx_iteration_status ON multimodal_slices(iteration_status);
CREATE INDEX IF NOT EXISTS idx_created ON multimodal_slices(created_at);

-- 2. FTS5 全文搜索虚拟表
CREATE VIRTUAL TABLE IF NOT EXISTS multimodal_search USING fts5(
    slice_id,
    ai_summary,
    ai_keywords,
    ai_entities,
    raw_transcript,
    objects_detected,
    search_vector,
    content='multimodal_slices',
    content_rowid='rowid'
);

-- 3. 自动同步触发器（INSERT）
CREATE TRIGGER IF NOT EXISTS multimodal_ai AFTER INSERT ON multimodal_slices BEGIN
    INSERT INTO multimodal_search(rowid, slice_id, ai_summary, ai_keywords, ai_entities, raw_transcript, objects_detected, search_vector)
    VALUES (new.rowid, new.slice_id, new.ai_summary, new.ai_keywords, new.ai_entities, new.raw_transcript, new.objects_detected, new.search_vector);
END;

-- 4. 自动同步触发器（DELETE）
CREATE TRIGGER IF NOT EXISTS multimodal_ad AFTER DELETE ON multimodal_slices BEGIN
    INSERT INTO multimodal_search(multimodal_search, rowid, slice_id, ai_summary, ai_keywords, ai_entities, raw_transcript, objects_detected, search_vector)
    VALUES ('delete', old.rowid, old.slice_id, old.ai_summary, old.ai_keywords, old.ai_entities, old.raw_transcript, old.objects_detected, old.search_vector);
END;

-- 5. 自动同步触发器（UPDATE）
CREATE TRIGGER IF NOT EXISTS multimodal_au AFTER UPDATE ON multimodal_slices BEGIN
    INSERT INTO multimodal_search(multimodal_search, rowid, slice_id, ai_summary, ai_keywords, ai_entities, raw_transcript, objects_detected, search_vector)
    VALUES ('delete', old.rowid, old.slice_id, old.ai_summary, old.ai_keywords, old.ai_entities, old.raw_transcript, old.objects_detected, old.search_vector);
    INSERT INTO multimodal_search(rowid, slice_id, ai_summary, ai_keywords, ai_entities, raw_transcript, objects_detected, search_vector)
    VALUES (new.rowid, new.slice_id, new.ai_summary, new.ai_keywords, new.ai_entities, new.raw_transcript, new.objects_detected, new.search_vector);
END;

-- 6. 温度变更日志表
CREATE TABLE IF NOT EXISTS temperature_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slice_id TEXT NOT NULL,
    old_temp TEXT,
    new_temp TEXT,
    old_score INTEGER,
    new_score INTEGER,
    reason TEXT,
    changed_by TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (slice_id) REFERENCES multimodal_slices(slice_id)
);

CREATE INDEX IF NOT EXISTS idx_temp_log_slice ON temperature_log(slice_id);
CREATE INDEX IF NOT EXISTS idx_temp_log_time ON temperature_log(changed_at);

-- 7. 熵变日志表
CREATE TABLE IF NOT EXISTS entropy_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slice_id TEXT NOT NULL,
    old_entropy INTEGER,
    new_entropy INTEGER,
    old_level TEXT,
    new_level TEXT,
    change_reason TEXT,
    triggered_by TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (slice_id) REFERENCES multimodal_slices(slice_id)
);

CREATE INDEX IF NOT EXISTS idx_entropy_log_slice ON entropy_log(slice_id);
CREATE INDEX IF NOT EXISTS idx_entropy_log_time ON entropy_log(changed_at);

-- 8. 文件存储元数据表
CREATE TABLE IF NOT EXISTS file_storage_meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    storage_path TEXT UNIQUE NOT NULL,
    file_hash TEXT UNIQUE NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    storage_type TEXT NOT NULL,  -- blob/file/external
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP,
    access_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_storage_hash ON file_storage_meta(file_hash);

-- 9. AI 调用日志表（成本追踪）
CREATE TABLE IF NOT EXISTS ai_call_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slice_id TEXT,
    call_type TEXT NOT NULL,      -- image_summary/audio_transcribe/analyze
    model_name TEXT NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd REAL DEFAULT 0.0,
    duration_ms INTEGER,
    success INTEGER DEFAULT 1,
    error_message TEXT,
    called_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (slice_id) REFERENCES multimodal_slices(slice_id)
);

CREATE INDEX IF NOT EXISTS idx_ai_log_slice ON ai_call_log(slice_id);
CREATE INDEX IF NOT EXISTS idx_ai_log_time ON ai_call_log(called_at);

-- 10. 配额管理表（可选）
CREATE TABLE IF NOT EXISTS quota_usage (
    user_id TEXT PRIMARY KEY,
    ai_calls_this_month INTEGER DEFAULT 0,
    ai_calls_limit INTEGER DEFAULT 100,
    storage_bytes INTEGER DEFAULT 0,
    storage_limit INTEGER DEFAULT 1073741824,  -- 1GB
    last_reset_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- 初始化数据
-- =============================================

-- 默认配额（如果启用配额系统）
INSERT OR IGNORE INTO quota_usage (user_id, ai_calls_this_month, ai_calls_limit) 
VALUES ('default', 0, 100);

-- =============================================
-- 备注
-- =============================================
-- 
-- 温度等级说明:
--   hot (>=70 分):   当前活跃，优先展示
--   warm (30-69 分): 最近使用，正常展示
--   cold (0-29 分):  历史归档，降低权重
--   frozen (<0 分):  明确废弃，搜索时排除
--
-- 熵级说明:
--   high (>=70):   混乱/不确定/讨论初期
--   medium (40-69): 收敛中/有方向未决策
--   low (<40):     确定/已决策/执行中
--
-- 智能触发策略:
--   - 文件名已包含足够信息 → 不调用 AI
--   - 用户标记"重要" → 调用 AI
--   - 语音文件 → 调用 AI（转文字价值高）
--   - 图片尺寸>1MB → 调用 AI（可能是重要照片）
--   - 默认：不调用 AI
--
-- =============================================
