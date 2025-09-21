from datetime import datetime
from typing import Optional, List

from sqlalchemy import func
from sqlmodel import SQLModel, Field, Relationship


class FileBase(SQLModel):
    filename: str = Field(nullable=False, max_length=512)


class FileCreate(FileBase):
    file_hash: str = Field(nullable=False, unique=True, index=True, max_length=64)


class File(FileBase, table=True):
    __tablename__ = "files"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    file_hash: str = Field(nullable=False, unique=True, index=True, max_length=64)
    create_at: datetime = Field(default=None, sa_column_kwargs={"server_default": func.now()})

    # 关系字段：一对多关系，一个 Document 对应多个 chunks
    chunks: List["DocumentChunk"] = Relationship(back_populates="file", cascade_delete=True)


class DocumentChunk(SQLModel, table=True):
    __tablename__ = "document_chunks"

    id: Optional[int] = Field(default=None, primary_key=True)
    # 外键约束，确保 document_id 的值在 documents 表中存在
    document_id: int = Field(foreign_key="files.id", index=True, ondelete="CASCADE")
    chroma_doc_id: str = Field(index=True)

    # 关系字段：多对一关系，一个 chunk 对应一个 Document
    file: Optional[File] = Relationship(back_populates="chunks")
