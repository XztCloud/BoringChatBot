import hashlib
import os

from app.api.deps import SessionDep
from fastapi import UploadFile, APIRouter, File
from app.db_model import FileCreate
from app.retriever.load_file_thread import load_file_thread, ParentDocumentInfo
from app.db_option import save_data, get_file_by_hash, get_file_by_name
from app.utils.user_base_model import BaseResponse

router = APIRouter(prefix="/files", tags=["files"])

UPLOAD_DIR = 'upload_files'
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_PROCESSING_FILE_COUNT = 3


@router.post("/upload", response_model=BaseResponse)
async def upload(session: SessionDep, file: UploadFile = File(...)):
    """
    上传文档到数据库，用作资料库
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

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    if get_file_by_name(session, file_path) is not None:
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

    if get_file_by_hash(session, file_hash) is None:
        file_data = FileCreate(filename=file_path, file_hash=file_hash)
        file_id = save_data(session, file_data)
        print(f'file_id: {file_id}')
        load_file_thread.file_path_queue.put(ParentDocumentInfo(file_path=file_path, file_id=file_id))
    else:
        response_model.code = "000002"
        response_model.msg = "file exists."
    return response_model


@router.delete("/{file_name}", response_model=BaseResponse)
async def delete_file(session: SessionDep, file_name: str):
    """
    删除指定文件
    :param session:
    :param file_name:
    :return:
    """
    file_path = os.path.join(UPLOAD_DIR, file_name)
    response_model = BaseResponse(code="000000", msg="success")

    if not os.path.exists(file_path):
        response_model.code = '000001'
        response_model.msg = f'file: {file_name} not exists.'
        return response_model

    if not os.path.isfile(file_path):
        response_model.code = '000002'
        response_model.msg = f'path: {file_name} not file.'
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

    current_file = get_file_by_name(session, file_path)
    if current_file is not None:
        print(f'find {file_name} in db.')
        ids = []
        for chunk in current_file.chunks:
            ids.append(chunk.chroma_doc_id)
        print(f'find sub doc ids len: {len(ids)}')
        await load_file_thread.delete_embeddings(ids)
        print(f'delete {file_name} in db.')
        session.delete(current_file)
        session.commit()

        # load_file_thread.test_check_embeddings_with_id()
    return response_model
