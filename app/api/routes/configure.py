from app.api.deps import SessionDep
from fastapi import APIRouter
from app.api.routes.info import SUPPER_USER_ID
from app.utils.user_base_model import BaseResponse, TaskConfig

router = APIRouter(prefix="/configure", tags=["configure"])


# 模拟数据表中用户概念
global_user_config_dict = {SUPPER_USER_ID: TaskConfig()}


@router.post("/update_config", response_model=BaseResponse)
async def send_config(session: SessionDep, device_id: str, config: TaskConfig):
    """
    发送配置信息
    :param session:
    :param device_id:
    :param config:
    :return:
    """
    if device_id.empty():
        return BaseResponse(code="000001", msg="error: device_id is empty")
    global_user_config_dict[device_id] = config
    return BaseResponse(code="000000", msg="success")
