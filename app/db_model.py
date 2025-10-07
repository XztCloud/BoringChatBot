import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import EmailStr
from sqlalchemy import func
from sqlmodel import SQLModel, Field, Relationship
from app.utils.user_base_model import EmbeddingsConfig, RetrieverConfig, MultiRetrieverConfig, HistoryConfig, \
    SummaryLLmConfig, LLmConfig


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(SQLModel):
    sub: str | None = None


class FileStatus(Enum):
    LOADING = "LOADING"
    LOADED = "LOADED"
    SPLITTING = "SPLITTING"
    HAS_SPLIT = "HAS_SPLIT"
    EMBEDDING = "EMBEDDING"
    COMPLETE = "COMPLETE"


class UserBase(SQLModel):
    email: EmailStr = Field(index=True, max_length=256)
    is_active: bool = Field(default=True, index=True)
    is_superuser: bool = Field(default=False, index=True)
    full_name: Optional[str] = Field(default=None, max_length=256)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=64)


class UserRegister(SQLModel):
    email: EmailStr = Field(index=True, max_length=256)
    password: str = Field(min_length=8, max_length=64)
    full_name: Optional[str] = Field(default=None, max_length=256)


class UserUpdate(UserBase):
    email: Optional[EmailStr] = Field(default=None, max_length=256)
    password: Optional[str] = Field(default=None, min_length=8, max_length=64)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class User(UserBase, table=True):
    __tablename__ = "users"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    titles: List["Title"] = Relationship(back_populates="user", cascade_delete=True)
    # 当前user使用的查询配置
    cur_llm_config_id: Optional[uuid.UUID] = Field(default=None)
    query_config: List["QueryConfig"] = Relationship(
        back_populates="user",
        cascade_delete=True)
    load_config: List["LoadConfig"] = Relationship(
        back_populates="user",
        cascade_delete=True
    )


class UserPublic(UserBase):
    id: uuid.UUID


class QueryConfigCreate(LLmConfig):
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")


class QueryConfig(LLmConfig, table=True):
    __tablename__ = "query_configs"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    config_name: Optional[str] = Field(default=None, max_length=256)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")
    user: Optional[User] = Relationship(back_populates="query_config")


class LoadConfigBase(SummaryLLmConfig, EmbeddingsConfig, RetrieverConfig, MultiRetrieverConfig, HistoryConfig):
    def __hash__(self):
        def safe_hash(obj):
            if obj is None:
                return None
            if hasattr(obj, "__hash__"):
                return hash(obj)
            if isinstance(obj, SQLModel):
                # 把字段都拿出来组成元组再哈希
                values = tuple((k, getattr(obj, k)) for k in obj.model_fields.keys())
                return hash(values)
            if isinstance(obj, (list, tuple)):
                return hash(tuple(safe_hash(i) for i in obj))
            if isinstance(obj, dict):
                return hash(tuple(sorted((k, safe_hash(v)) for k, v in obj.items())))
            return hash(obj)

        values = tuple(
            (k, safe_hash(getattr(self, k)))
            for k in self.model_fields.keys()
        )
        return hash(values)


class LoadConfigUserUpdate(LoadConfigBase):
    config_name: Optional[str] = Field(default=None, max_length=256)


class LoadConfigCreate(LoadConfigBase):
    config_name: Optional[str] = Field(default=None, max_length=256)
    config_hash: str = Field(nullable=False, max_length=64, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")


class LoadConfig(LoadConfigBase, table=True):
    __tablename__ = "load_configs"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    config_name: Optional[str] = Field(default=None, max_length=256)
    config_hash: str = Field(nullable=False, max_length=64, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")
    user: Optional[User] = Relationship(back_populates="load_config")


class TitleBase(SQLModel):
    title_name: str = Field(nullable=False, max_length=256, index=True)


class TitleCreate(TitleBase):
    description: Optional[str] = Field(default=None, max_length=1024)


class TitleInfoUpdate(TitleCreate):
    id: uuid.UUID = Field(nullable=False)


class TitleUpdate(TitleCreate):
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")


class Title(TitleBase, table=True):
    __tablename__ = "titles"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title_name: str = Field(nullable=False, max_length=256, index=True)
    create_at: datetime = Field(default=None, sa_column_kwargs={"server_default": func.now()})
    description: Optional[str] = Field(default=None, max_length=1024)
    # 当前title使用的加载配置
    load_config_id: Optional[uuid.UUID] = Field(default=None)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")
    user: Optional[User] = Relationship(back_populates="titles")
    files: List["File"] = Relationship(back_populates="title", cascade_delete=True)


class FileBase(SQLModel):
    filename: str = Field(nullable=False, max_length=512)


class FileCreate(FileBase):
    file_hash: str = Field(nullable=False, unique=True, index=True, max_length=64)
    title_id: Optional[uuid.UUID] = Field(foreign_key="titles.id", index=True, ondelete="CASCADE")
    status: str = Field(nullable=False, default=FileStatus.LOADING.value, max_length=16)
    load_config_id: uuid.UUID = Field(foreign_key="load_configs.id", index=True)


class File(FileBase, table=True):
    __tablename__ = "files"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    file_hash: str = Field(nullable=False, unique=True, index=True, max_length=64)
    create_at: datetime = Field(default=None, sa_column_kwargs={"server_default": func.now()})
    status: str = Field(nullable=False, default=FileStatus.LOADING.value, max_length=16)
    load_config_id: uuid.UUID = Field(foreign_key="load_configs.id", index=True)
    title_id: Optional[uuid.UUID] = Field(foreign_key="titles.id", index=True, ondelete="CASCADE")
    title: Optional[Title] = Relationship(back_populates="files")

    # 关系字段：一对多关系，一个 Document 对应多个 chunks
    chunks: List["DocumentChunk"] = Relationship(back_populates="file", cascade_delete=True)


class DocumentChunk(SQLModel, table=True):
    __tablename__ = "document_chunks"

    id: Optional[int] = Field(default=None, primary_key=True)
    # 外键约束，确保 document_id 的值在 documents 表中存在
    document_id: uuid.UUID = Field(foreign_key="files.id", index=True, ondelete="CASCADE")
    chroma_doc_id: str = Field(index=True)

    # 关系字段：多对一关系，一个 chunk 对应一个 Document
    file: Optional[File] = Relationship(back_populates="chunks")
