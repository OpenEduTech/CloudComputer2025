"""
PatPat-Inconsistency-Hunter 数据库模型定义
使用SQLAlchemy ORM定义数据库表结构
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, 
    Integer, 
    String, 
    Text, 
    Float, 
    Boolean, 
    DateTime, 
    ForeignKey,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """SQLAlchemy 基类"""
    pass


class Document(Base):
    """文档表"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), unique=True, nullable=False, index=True, comment="任务ID")
    title = Column(String(256), nullable=True, comment="文档标题")
    content = Column(Text, nullable=False, comment="文档内容（纯文本）")
    content_json = Column(JSON, default={}, comment="富文本JSON格式（TipTap格式）")
    content_html = Column(Text, default="", comment="HTML格式内容")
    content_length = Column(Integer, nullable=False, comment="文档长度")
    content_hash = Column(String(64), nullable=False, comment="内容哈希")
    doc_metadata = Column(JSON, default={}, comment="文档元数据")
    
    status = Column(String(32), default="pending", comment="处理状态")
    progress = Column(Float, default=0.0, comment="处理进度")
    error_message = Column(Text, nullable=True, comment="错误信息")
    
    total_chunks = Column(Integer, default=0, comment="分块数量")
    total_facts = Column(Integer, default=0, comment="事实数量")
    total_conflicts = Column(Integer, default=0, comment="冲突数量")
    
    analysis_time = Column(Float, default=0.0, comment="分析耗时（秒）")
    
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    
    # 关联关系
    facts = relationship("FactRecord", back_populates="document", cascade="all, delete-orphan")
    conflicts = relationship("ConflictRecord", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document(task_id={self.task_id}, title={self.title})>"


class FactRecord(Base):
    """事实记录表"""
    __tablename__ = "facts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    fact_id = Column(String(64), unique=True, nullable=False, index=True, comment="事实ID")
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    content = Column(Text, nullable=False, comment="事实内容")
    fact_type = Column(String(32), nullable=False, comment="事实类型")
    confidence = Column(Float, default=1.0, comment="提取置信度")
    
    source_text = Column(Text, nullable=False, comment="原文文本")
    source_start = Column(Integer, nullable=False, comment="原文起始位置")
    source_end = Column(Integer, nullable=False, comment="原文结束位置")
    chapter = Column(String(64), nullable=True, comment="所属章节")
    section = Column(String(64), nullable=True, comment="所属小节")
    
    chunk_id = Column(String(64), nullable=False, comment="分块ID")
    
    # 图片来源相关
    is_image_source = Column(Boolean, default=False, comment="是否来自图片")
    image_id = Column(String(64), nullable=True, comment="来源图片ID")
    image_description = Column(Text, nullable=True, comment="图片描述")
    
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    
    # 关联关系
    document = relationship("Document", back_populates="facts")
    
    def __repr__(self):
        return f"<FactRecord(fact_id={self.fact_id}, type={self.fact_type})>"


class ConflictRecord(Base):
    """冲突记录表"""
    __tablename__ = "conflicts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conflict_id = Column(String(64), unique=True, nullable=False, index=True, comment="冲突ID")
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    fact_a_id = Column(String(64), nullable=False, comment="事实A的ID")
    fact_b_id = Column(String(64), nullable=False, comment="事实B的ID")
    
    conflict_type = Column(String(32), nullable=False, comment="冲突类型")
    severity = Column(Float, nullable=False, comment="严重程度")
    description = Column(Text, nullable=False, comment="冲突描述")
    suggestion = Column(Text, nullable=True, comment="修正建议")
    
    # 验证信息
    is_verified = Column(Boolean, default=False, comment="是否已验证")
    correct_fact = Column(Text, nullable=True, comment="正确的事实")
    verification_reasoning = Column(Text, nullable=True, comment="验证推理")
    verification_confidence = Column(Float, nullable=True, comment="验证置信度")
    source_description = Column(Text, nullable=True, comment="来源描述")
    
    # 图片冲突标记
    is_image_conflict = Column(Boolean, default=False, comment="是否涉及图片冲突")
    
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    verified_at = Column(DateTime, nullable=True, comment="验证时间")
    
    # 关联关系
    document = relationship("Document", back_populates="conflicts")
    
    def __repr__(self):
        return f"<ConflictRecord(conflict_id={self.conflict_id}, type={self.conflict_type})>"


class AnalysisHistory(Base):
    """分析历史表"""
    __tablename__ = "analysis_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), nullable=False, index=True, comment="任务ID")
    
    step_name = Column(String(64), nullable=False, comment="步骤名称")
    step_status = Column(String(32), nullable=False, comment="步骤状态")
    step_detail = Column(Text, nullable=True, comment="步骤详情")
    
    input_data = Column(JSON, nullable=True, comment="输入数据")
    output_data = Column(JSON, nullable=True, comment="输出数据")
    
    duration = Column(Float, default=0.0, comment="耗时（秒）")
    
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    
    def __repr__(self):
        return f"<AnalysisHistory(task_id={self.task_id}, step={self.step_name})>"


# ==================== 用户和协作相关表 ====================

class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), unique=True, nullable=False, index=True, comment="用户唯一标识")
    username = Column(String(64), unique=True, nullable=False, index=True, comment="用户名")
    email = Column(String(128), unique=True, nullable=True, index=True, comment="邮箱")
    password_hash = Column(String(256), nullable=False, comment="密码哈希")
    display_name = Column(String(64), nullable=True, comment="显示名称")
    avatar_color = Column(String(16), default="#6366f1", comment="头像颜色")
    
    is_active = Column(Boolean, default=True, comment="是否激活")
    is_admin = Column(Boolean, default=False, comment="是否管理员")
    
    # 新增：用户头像和个人信息
    avatar_url = Column(String(512), nullable=True, comment="头像URL")
    bio = Column(Text, nullable=True, comment="个人简介")
    
    last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联关系
    owned_rooms = relationship("CollaborationRoom", back_populates="owner", foreign_keys="CollaborationRoom.owner_id")
    memberships = relationship("RoomMembership", back_populates="user", cascade="all, delete-orphan")
    edit_histories = relationship("EditHistory", back_populates="user")
    user_documents = relationship("UserDocument", back_populates="user", cascade="all, delete-orphan")
    uploaded_images = relationship("DocumentImage", back_populates="uploader")
    
    def __repr__(self):
        return f"<User(user_id={self.user_id}, username={self.username})>"


class CollaborationRoom(Base):
    """协作房间表"""
    __tablename__ = "collaboration_rooms"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(String(64), unique=True, nullable=False, index=True, comment="房间唯一标识")
    room_name = Column(String(128), nullable=False, comment="房间名称")
    document_title = Column(String(256), default="未命名文档", comment="文档标题")
    
    mode = Column(String(32), nullable=False, comment="协作模式: realtime/chapter_lock")
    content = Column(Text, default="", comment="文档内容（纯文本）")
    content_json = Column(JSON, default={}, comment="富文本JSON格式")
    chapters = Column(JSON, default=[], comment="章节列表")
    
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="房主ID")
    
    # 新增：邀请码和房间设置
    invite_code = Column(String(16), unique=True, nullable=True, index=True, comment="邀请码")
    description = Column(Text, nullable=True, comment="房间描述")
    source_document_id = Column(Integer, ForeignKey("user_documents.id", ondelete="SET NULL"), nullable=True, comment="来源文档ID")
    
    max_members = Column(Integer, default=10, comment="最大成员数")
    is_public = Column(Boolean, default=False, comment="是否公开")
    is_active = Column(Boolean, default=True, comment="是否活跃")
    is_ended = Column(Boolean, default=False, comment="是否已结束")
    ended_at = Column(DateTime, nullable=True, comment="结束时间")
    
    # 检测锁状态
    is_detecting = Column(Boolean, default=False, comment="是否正在检测")
    last_detection_at = Column(DateTime, nullable=True, comment="上次检测时间")
    
    last_activity_at = Column(DateTime, default=func.now(), comment="最后活动时间")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联关系
    owner = relationship("User", back_populates="owned_rooms", foreign_keys=[owner_id])
    memberships = relationship("RoomMembership", back_populates="room", cascade="all, delete-orphan")
    edit_histories = relationship("EditHistory", back_populates="room", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<CollaborationRoom(room_id={self.room_id}, name={self.room_name})>"


class RoomMembership(Base):
    """房间成员关系表"""
    __tablename__ = "room_memberships"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey("collaboration_rooms.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    role = Column(String(32), default="editor", comment="角色: owner/editor/viewer")
    color = Column(String(16), comment="用户在房间中的颜色")
    
    is_online = Column(Boolean, default=False, comment="是否在线")
    current_chapter = Column(String(64), nullable=True, comment="当前编辑的章节")
    cursor_position = Column(Integer, nullable=True, comment="光标位置")
    
    last_active_at = Column(DateTime, default=func.now(), comment="最后活跃时间")
    joined_at = Column(DateTime, default=func.now(), comment="加入时间")
    
    # 关联关系
    room = relationship("CollaborationRoom", back_populates="memberships")
    user = relationship("User", back_populates="memberships")
    
    def __repr__(self):
        return f"<RoomMembership(room_id={self.room_id}, user_id={self.user_id}, role={self.role})>"


class EditHistory(Base):
    """编辑历史表"""
    __tablename__ = "edit_histories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey("collaboration_rooms.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    action = Column(String(32), nullable=False, comment="操作类型: create/update/delete")
    chapter_id = Column(String(64), nullable=True, comment="章节ID（如果是章节操作）")
    
    content_before = Column(Text, nullable=True, comment="修改前内容")
    content_after = Column(Text, nullable=True, comment="修改后内容")
    content_diff = Column(Text, nullable=True, comment="内容差异")
    
    extra_data = Column(JSON, default={}, comment="额外元数据")
    
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    
    # 关联关系
    room = relationship("CollaborationRoom", back_populates="edit_histories")
    user = relationship("User", back_populates="edit_histories")
    
    def __repr__(self):
        return f"<EditHistory(room_id={self.room_id}, action={self.action})>"


class ChapterLockRecord(Base):
    """章节锁定记录表"""
    __tablename__ = "chapter_lock_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey("collaboration_rooms.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(String(64), nullable=False, comment="章节ID")
    
    locked_at = Column(DateTime, default=func.now(), comment="锁定时间")
    expires_at = Column(DateTime, nullable=False, comment="过期时间")
    released_at = Column(DateTime, nullable=True, comment="释放时间")
    
    is_active = Column(Boolean, default=True, comment="是否活跃")
    
    def __repr__(self):
        return f"<ChapterLockRecord(room_id={self.room_id}, chapter_id={self.chapter_id})>"


# ==================== 用户文档和资源管理 ====================

class UserDocument(Base):
    """用户文档表 - 用户保存的所有文档"""
    __tablename__ = "user_documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(64), unique=True, nullable=False, index=True, comment="文档唯一标识")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户")
    
    title = Column(String(256), nullable=False, comment="文档标题")
    content = Column(Text, default="", comment="纯文本内容")
    content_json = Column(JSON, default={}, comment="富文本JSON格式（TipTap/Quill格式）")
    content_html = Column(Text, default="", comment="HTML格式内容")
    
    # 文档状态
    status = Column(String(32), default="draft", comment="状态: draft/published/archived")
    version = Column(Integer, default=1, comment="版本号")
    word_count = Column(Integer, default=0, comment="字数统计")
    
    # 分析相关
    last_analysis_task_id = Column(String(64), nullable=True, comment="最近分析任务ID")
    last_analysis_at = Column(DateTime, nullable=True, comment="最近分析时间")
    analysis_count = Column(Integer, default=0, comment="分析次数")
    
    # 来源
    source_type = Column(String(32), default="manual", comment="来源: manual/upload/collaboration")
    source_room_id = Column(String(64), nullable=True, comment="来源协作房间ID")
    
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联关系
    user = relationship("User", back_populates="user_documents")
    images = relationship("DocumentImage", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<UserDocument(document_id={self.document_id}, title={self.title})>"


class DocumentImage(Base):
    """文档图片资源表"""
    __tablename__ = "document_images"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(String(64), unique=True, nullable=False, index=True, comment="图片唯一标识")
    document_id = Column(Integer, ForeignKey("user_documents.id", ondelete="CASCADE"), nullable=True, comment="所属文档（用户文档）")
    task_id = Column(String(64), ForeignKey("documents.task_id", ondelete="CASCADE"), nullable=True, index=True, comment="所属任务（分析任务文档）")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="上传用户")
    room_id = Column(String(64), nullable=True, index=True, comment="协作房间ID（如果是协作上传）")
    
    file_name = Column(String(256), nullable=False, comment="原始文件名")
    file_path = Column(String(512), nullable=False, comment="存储路径")
    file_url = Column(String(512), nullable=False, comment="访问URL")
    file_size = Column(Integer, nullable=False, comment="文件大小（字节）")
    mime_type = Column(String(64), nullable=False, comment="MIME类型")
    
    width = Column(Integer, nullable=True, comment="图片宽度")
    height = Column(Integer, nullable=True, comment="图片高度")
    
    # 视觉模型提取的描述
    description = Column(Text, nullable=True, comment="视觉模型提取的图片描述")
    description_extracted_at = Column(DateTime, nullable=True, comment="描述提取时间")
    alt_text = Column(String(256), nullable=True, comment="图片替代文本")
    
    uploaded_at = Column(DateTime, default=func.now(), comment="上传时间")
    
    # 关联关系
    document = relationship("UserDocument", back_populates="images")
    uploader = relationship("User", back_populates="uploaded_images")
    
    def __repr__(self):
        return f"<DocumentImage(image_id={self.image_id}, file_name={self.file_name})>"


class DetectionLock(Base):
    """文档检测锁表 - 防止同一文档并发检测"""
    __tablename__ = "detection_locks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    target_type = Column(String(32), nullable=False, comment="目标类型: document/room")
    target_id = Column(String(64), nullable=False, index=True, comment="目标ID")
    
    locked_by = Column(String(64), nullable=False, comment="锁定者（任务ID）")
    locked_at = Column(DateTime, default=func.now(), comment="锁定时间")
    expires_at = Column(DateTime, nullable=False, comment="过期时间")
    
    is_active = Column(Boolean, default=True, comment="是否有效")
    released_at = Column(DateTime, nullable=True, comment="释放时间")
    
    def __repr__(self):
        return f"<DetectionLock(target={self.target_type}:{self.target_id})>"

