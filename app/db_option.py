import logging
import os
import queue
import hashlib
from typing import List

from sqlmodel import select, Session

from app.api.deps import SessionDep, get_db, engine
from app.db_model import File, FileCreate, DocumentChunk


def get_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def calculate_file_hash(file_path: str, chunk_size: int = 1024 * 1024) -> str:
    """
    计算大文件的 SHA256 哈希
    :param file_path: 文件路径
    :param chunk_size: 每次读取的字节数，默认 1MB
    :return: 十六进制哈希字符串
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()


def save_data(session: SessionDep, file_create: FileCreate):
    db_obj = File.model_validate(file_create)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj.id


def get_file_by_hash(session: SessionDep, file_hash: str) -> File | None:
    statement = select(File).where(File.file_hash == file_hash)
    session_file = session.exec(statement).first()
    return session_file


def get_file_by_name(session: SessionDep, filename: str) -> File | None:
    statement = select(File).where(File.filename == filename)
    session_file = session.exec(statement).first()
    return session_file


def get_all_files(session: SessionDep) -> List[str]:
    statement = select(File)
    session_files = session.exec(statement).all()
    file_name_list = []
    for session_file in session_files:
        file_name_list.append(os.path.basename(session_file.filename))
    return file_name_list


def save_doc_chunk(doc_id_list: List[str], parent_doc_id: int) -> None:
    with Session(engine) as session:
        for doc_id in doc_id_list:
            chunk = DocumentChunk(chroma_doc_id=doc_id, document_id=parent_doc_id)
            session.add(chunk)
        session.commit()
