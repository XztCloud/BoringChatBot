import time

from app.api.deps import SessionDep
from fastapi import APIRouter
from app.db_option import get_all_files
from app.utils.user_base_model import InfoResponse, BaseResponse

router = APIRouter(prefix="/info", tags=["info"])
SUPPER_USER_ID = "admin"
global_save_device_dict = {}


@router.get("/documents", response_model=InfoResponse)
def get_documents(session: SessionDep):
    """
    获取所有文档信息
    :param session:
    :return: InfoResponse
    """
    info_response = InfoResponse(code="000000", msg="success")
    try:
        file_list = get_all_files(session)
        info_response.extra_msg = file_list
    except Exception as e:
        info_response.code = "000001"
        info_response.msg = f"error: {e}"
    return info_response


@router.get("/heartbeat", response_model=BaseResponse)
def heartbeat(session: SessionDep, device_id: str):
    """
    心跳检测
    :param session:
    :param device_id:
    :return:
    """
    if device_id == '':
        return BaseResponse(code="000001", msg="error: device_id is empty")
    cur_time = time.time()
    if device_id in global_save_device_dict:
        if cur_time - global_save_device_dict[device_id] < 60:
            return BaseResponse(code="000002", msg="error: send heartbeat too frequently")
        global_save_device_dict[device_id] = cur_time
        return BaseResponse(code="000000", msg="success")
    global_save_device_dict[device_id] = cur_time
    return BaseResponse(code="000000", msg="success")
