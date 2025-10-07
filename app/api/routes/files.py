import hashlib
import os
import uuid

from app.api.deps import SessionDep, CurrentTitle, CurrentFile
from fastapi import UploadFile, APIRouter, File
from app.db_model import FileCreate, FileStatus
from app.retriever.load_file_thread import load_file_thread, ParentDocumentInfo
from app.db_option import get_file_by_hash, get_file_by_name, create_file
from app.utils.user_base_model import BaseResponse

router = APIRouter(prefix="/files", tags=["files"])

UPLOAD_DIR = 'upload_files'
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_PROCESSING_FILE_COUNT = 3


@router.post("/{title_id}/upload_file")
async def upload(session: SessionDep, title: CurrentTitle, file: UploadFile = File(...)):
    """
    上传文档到数据库，用作资料库
    :param title:
    :param session:
    :param file:
    :return:
    """
    response_model = BaseResponse(code="000000", msg="success")
    if load_file_thread.file_path_queue.qsize() > MAX_PROCESSING_FILE_COUNT:
        response_model.code = "000003"
        response_model.msg = "system is busy."
        return response_model

    # 检查文件类型
    if not (file.filename.endswith("pdf") or file.filename.endswith("txt")):
        response_model.code = "000001"
        response_model.msg = "file type error, support txt and pdf file."
        return response_model

    file_path = os.path.join(UPLOAD_DIR, str(title.user_id), str(title.id), file.filename)
    if not os.path.exists(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    if get_file_by_name(session=session, filename=file_path, title_id=title.id) is not None:
        response_model.code = "000002"
        response_model.msg = "file exists, check filename."
        return response_model

    # 保存文件 计算hash值
    sha256 = hashlib.sha256()
    with open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            sha256.update(chunk)
            f.write(chunk)
        # shutil.copyfileobj(file.file, f)
    file_hash = sha256.hexdigest()

    if get_file_by_hash(session=session, file_hash=file_hash, title_id=title.id) is None:
        print(f'title ')
        file_data = FileCreate(filename=file_path, file_hash=str(file_hash), title_id=title.id,
                               status=FileStatus.LOADED.value, load_config_id=title.load_config_id)
        print(f'file_data is {file_data}')
        file = create_file(session, file_data)
        print(f'file_id: {file.id}')
        load_file_thread.file_path_queue.put(ParentDocumentInfo(file_path=file_path, file_id=file.id))
        return file
    else:
        response_model.code = "000002"
        response_model.msg = "file exists."
    return response_model


@router.delete("/{title_id}/{file_id}", response_model=BaseResponse)
async def delete_file(session: SessionDep, file: CurrentFile):
    """
    删除指定文件
    :param file:
    :param session:
    :return:
    """
    file_path = file.filename
    response_model = BaseResponse(code="000000", msg="success")

    if not os.path.exists(file_path):
        response_model.code = '000001'
        response_model.msg = f'file: {file_path} not exists.'
        return response_model

    if not os.path.isfile(file_path):
        response_model.code = '000002'
        response_model.msg = f'path: {file_path} not file.'
        return response_model

    try:
        os.remove(file_path)
    except PermissionError:
        response_model.code = '000003'
        response_model.msg = f'file not permission'
        return response_model
    except Exception as e:
        response_model.code = '000004'
        response_model.msg = f'file delete failed. {str(e)}'
        return response_model

    print(f'find {file_path} in db.')
    ids = []
    for chunk in file.chunks:
        ids.append(chunk.chroma_doc_id)
    print(f'find sub doc ids len: {len(ids)}')
    await load_file_thread.delete_embeddings(ids)
    print(f'delete {file_path} in db.')
    session.delete(file)
    session.commit()
    return response_model
