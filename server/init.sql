-- PatPat-Inconsistency-Hunter 数据库初始化脚本
-- 创建必要的表结构

-- 文档表
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(64) UNIQUE NOT NULL,
    title VARCHAR(256),
    content TEXT NOT NULL,
    content_json JSONB DEFAULT '{}',
    content_html TEXT DEFAULT '',
    content_length INTEGER NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    doc_metadata JSONB DEFAULT '{}',
    status VARCHAR(32) DEFAULT 'pending',
    progress FLOAT DEFAULT 0.0,
    error_message TEXT,
    total_chunks INTEGER DEFAULT 0,
    total_facts INTEGER DEFAULT 0,
    total_conflicts INTEGER DEFAULT 0,
    analysis_time FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- 事实记录表
CREATE TABLE IF NOT EXISTS facts (
    id SERIAL PRIMARY KEY,
    fact_id VARCHAR(64) UNIQUE NOT NULL,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    fact_type VARCHAR(32) NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    source_text TEXT NOT NULL,
    source_start INTEGER NOT NULL,
    source_end INTEGER NOT NULL,
    chapter VARCHAR(64),
    section VARCHAR(64),
    chunk_id VARCHAR(64) NOT NULL,
    -- 图片来源相关字段
    is_image_source BOOLEAN DEFAULT FALSE,
    image_id VARCHAR(64),
    image_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 冲突记录表
CREATE TABLE IF NOT EXISTS conflicts (
    id SERIAL PRIMARY KEY,
    conflict_id VARCHAR(64) UNIQUE NOT NULL,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    fact_a_id VARCHAR(64) NOT NULL,
    fact_b_id VARCHAR(64) NOT NULL,
    conflict_type VARCHAR(32) NOT NULL,
    severity FLOAT NOT NULL,
    description TEXT NOT NULL,
    suggestion TEXT,
    is_verified BOOLEAN DEFAULT FALSE,
    correct_fact TEXT,
    verification_reasoning TEXT,
    verification_confidence FLOAT,
    source_description TEXT,
    -- 图片冲突标记
    is_image_conflict BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP
);

-- 分析历史表
CREATE TABLE IF NOT EXISTS analysis_history (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL,
    step_name VARCHAR(64) NOT NULL,
    step_status VARCHAR(32) NOT NULL,
    step_detail TEXT,
    input_data JSONB,
    output_data JSONB,
    duration FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) UNIQUE NOT NULL,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(128) UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    display_name VARCHAR(64),
    avatar_color VARCHAR(16) DEFAULT '#6366f1',
    avatar_url VARCHAR(512),
    bio TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户文档表（用户保存的个人文档）
CREATE TABLE IF NOT EXISTS user_documents (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(64) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(256) NOT NULL,
    content TEXT DEFAULT '',
    content_json JSONB DEFAULT '{}',
    content_html TEXT DEFAULT '',
    status VARCHAR(32) DEFAULT 'draft',
    version INTEGER DEFAULT 1,
    word_count INTEGER DEFAULT 0,
    last_analysis_task_id VARCHAR(64),
    last_analysis_at TIMESTAMP,
    analysis_count INTEGER DEFAULT 0,
    source_type VARCHAR(32) DEFAULT 'manual',
    source_room_id VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 文档图片资源表
CREATE TABLE IF NOT EXISTS document_images (
    id SERIAL PRIMARY KEY,
    image_id VARCHAR(64) UNIQUE NOT NULL,
    document_id INTEGER REFERENCES user_documents(id) ON DELETE CASCADE,
    task_id VARCHAR(64) REFERENCES documents(task_id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    room_id VARCHAR(64),
    file_name VARCHAR(256) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    file_url VARCHAR(512) NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type VARCHAR(64) NOT NULL,
    width INTEGER,
    height INTEGER,
    -- 视觉模型提取的描述
    description TEXT,
    description_extracted_at TIMESTAMP,
    alt_text VARCHAR(256),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 协作房间表
CREATE TABLE IF NOT EXISTS collaboration_rooms (
    id SERIAL PRIMARY KEY,
    room_id VARCHAR(64) UNIQUE NOT NULL,
    room_name VARCHAR(128) NOT NULL,
    document_title VARCHAR(256) DEFAULT '未命名文档',
    mode VARCHAR(32) NOT NULL,
    content TEXT DEFAULT '',
    content_json JSONB DEFAULT '{}',
    chapters JSONB DEFAULT '[]',
    owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    invite_code VARCHAR(16) UNIQUE,
    description TEXT,
    source_document_id INTEGER REFERENCES user_documents(id) ON DELETE SET NULL,
    max_members INTEGER DEFAULT 10,
    is_public BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_ended BOOLEAN DEFAULT FALSE,
    ended_at TIMESTAMP,
    is_detecting BOOLEAN DEFAULT FALSE,
    last_detection_at TIMESTAMP,
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 房间成员关系表
CREATE TABLE IF NOT EXISTS room_memberships (
    id SERIAL PRIMARY KEY,
    room_id INTEGER REFERENCES collaboration_rooms(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(32) DEFAULT 'editor',
    color VARCHAR(16),
    is_online BOOLEAN DEFAULT FALSE,
    current_chapter VARCHAR(64),
    cursor_position INTEGER,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(room_id, user_id)
);

-- 编辑历史表
CREATE TABLE IF NOT EXISTS edit_histories (
    id SERIAL PRIMARY KEY,
    room_id INTEGER REFERENCES collaboration_rooms(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(32) NOT NULL,
    chapter_id VARCHAR(64),
    content_before TEXT,
    content_after TEXT,
    content_diff TEXT,
    extra_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 章节锁定记录表
CREATE TABLE IF NOT EXISTS chapter_lock_records (
    id SERIAL PRIMARY KEY,
    room_id INTEGER REFERENCES collaboration_rooms(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    chapter_id VARCHAR(64) NOT NULL,
    locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    released_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- 检测锁表
CREATE TABLE IF NOT EXISTS detection_locks (
    id SERIAL PRIMARY KEY,
    target_type VARCHAR(32) NOT NULL,
    target_id VARCHAR(64) NOT NULL,
    locked_by VARCHAR(64) NOT NULL,
    locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    released_at TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_documents_task_id ON documents(task_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_facts_document_id ON facts(document_id);
CREATE INDEX IF NOT EXISTS idx_facts_fact_type ON facts(fact_type);
CREATE INDEX IF NOT EXISTS idx_conflicts_document_id ON conflicts(document_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_conflict_type ON conflicts(conflict_type);
CREATE INDEX IF NOT EXISTS idx_analysis_history_task_id ON analysis_history(task_id);

-- 用户和协作相关索引
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_user_documents_user_id ON user_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_user_documents_document_id ON user_documents(document_id);
CREATE INDEX IF NOT EXISTS idx_document_images_document_id ON document_images(document_id);
CREATE INDEX IF NOT EXISTS idx_document_images_task_id ON document_images(task_id);
CREATE INDEX IF NOT EXISTS idx_document_images_user_id ON document_images(user_id);
CREATE INDEX IF NOT EXISTS idx_document_images_room_id ON document_images(room_id);
CREATE INDEX IF NOT EXISTS idx_rooms_room_id ON collaboration_rooms(room_id);
CREATE INDEX IF NOT EXISTS idx_rooms_owner_id ON collaboration_rooms(owner_id);
CREATE INDEX IF NOT EXISTS idx_rooms_invite_code ON collaboration_rooms(invite_code);
CREATE INDEX IF NOT EXISTS idx_memberships_room_id ON room_memberships(room_id);
CREATE INDEX IF NOT EXISTS idx_memberships_user_id ON room_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_edit_histories_room_id ON edit_histories(room_id);
CREATE INDEX IF NOT EXISTS idx_locks_room_id ON chapter_lock_records(room_id);
CREATE INDEX IF NOT EXISTS idx_detection_locks_target ON detection_locks(target_type, target_id);

-- 为已存在的表添加新字段（如果需要迁移）
DO $$
BEGIN
    -- 为 users 表添加 avatar_url 和 bio 字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'avatar_url') THEN
        ALTER TABLE users ADD COLUMN avatar_url VARCHAR(512);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'bio') THEN
        ALTER TABLE users ADD COLUMN bio TEXT;
    END IF;
    
    -- 为 collaboration_rooms 表添加新字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'collaboration_rooms' AND column_name = 'invite_code') THEN
        ALTER TABLE collaboration_rooms ADD COLUMN invite_code VARCHAR(16) UNIQUE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'collaboration_rooms' AND column_name = 'description') THEN
        ALTER TABLE collaboration_rooms ADD COLUMN description TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'collaboration_rooms' AND column_name = 'content_json') THEN
        ALTER TABLE collaboration_rooms ADD COLUMN content_json JSONB DEFAULT '{}';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'collaboration_rooms' AND column_name = 'is_ended') THEN
        ALTER TABLE collaboration_rooms ADD COLUMN is_ended BOOLEAN DEFAULT FALSE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'collaboration_rooms' AND column_name = 'ended_at') THEN
        ALTER TABLE collaboration_rooms ADD COLUMN ended_at TIMESTAMP;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'collaboration_rooms' AND column_name = 'is_detecting') THEN
        ALTER TABLE collaboration_rooms ADD COLUMN is_detecting BOOLEAN DEFAULT FALSE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'collaboration_rooms' AND column_name = 'last_detection_at') THEN
        ALTER TABLE collaboration_rooms ADD COLUMN last_detection_at TIMESTAMP;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'collaboration_rooms' AND column_name = 'source_document_id') THEN
        ALTER TABLE collaboration_rooms ADD COLUMN source_document_id INTEGER REFERENCES user_documents(id) ON DELETE SET NULL;
    END IF;
    
    -- 为 document_images 表添加 task_id 字段（关联 documents.task_id）
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'document_images' AND column_name = 'task_id') THEN
        ALTER TABLE document_images ADD COLUMN task_id VARCHAR(64);
        CREATE INDEX IF NOT EXISTS idx_document_images_task_id ON document_images(task_id);
        -- 添加外键约束（如果 documents 表存在）
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'documents') THEN
            -- 先检查外键约束是否已存在
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE table_name = 'document_images' 
                AND constraint_name = 'fk_document_images_task_id'
            ) THEN
                ALTER TABLE document_images ADD CONSTRAINT fk_document_images_task_id 
                    FOREIGN KEY (task_id) REFERENCES documents(task_id) ON DELETE CASCADE;
            END IF;
        END IF;
    END IF;
    
    -- 为 documents 表添加富文本字段（兼容已存在的数据库）
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'documents' AND column_name = 'content_json') THEN
        ALTER TABLE documents ADD COLUMN content_json JSONB DEFAULT '{}';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'documents' AND column_name = 'content_html') THEN
        ALTER TABLE documents ADD COLUMN content_html TEXT DEFAULT '';
    END IF;
    
    -- 为 document_images 表添加视觉模型描述字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'document_images' AND column_name = 'description') THEN
        ALTER TABLE document_images ADD COLUMN description TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'document_images' AND column_name = 'description_extracted_at') THEN
        ALTER TABLE document_images ADD COLUMN description_extracted_at TIMESTAMP;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'document_images' AND column_name = 'alt_text') THEN
        ALTER TABLE document_images ADD COLUMN alt_text VARCHAR(256);
    END IF;
    
    -- 为 facts 表添加图片来源字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'facts' AND column_name = 'is_image_source') THEN
        ALTER TABLE facts ADD COLUMN is_image_source BOOLEAN DEFAULT FALSE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'facts' AND column_name = 'image_id') THEN
        ALTER TABLE facts ADD COLUMN image_id VARCHAR(64);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'facts' AND column_name = 'image_description') THEN
        ALTER TABLE facts ADD COLUMN image_description TEXT;
    END IF;
    
    -- 为 conflicts 表添加图片冲突标记
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'conflicts' AND column_name = 'is_image_conflict') THEN
        ALTER TABLE conflicts ADD COLUMN is_image_conflict BOOLEAN DEFAULT FALSE;
    END IF;
END $$;
