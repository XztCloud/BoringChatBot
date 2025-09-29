from typing import Dict, Any
from pydantic import BaseModel


def diff_models(a: BaseModel, b: BaseModel, prefix: str = "") -> Dict[str, Any]:
    """
    比较两个 BaseModel 对象，返回不同字段及其值
    :param a: BaseModel 实例
    :param b: BaseModel 实例
    :param prefix: 字段前缀（递归时使用）
    :return: dict {字段路径: (a的值, b的值)}
    """
    diffs = {}
    fields = set(a.__fields__.keys()) | set(b.__fields__.keys())

    for field in fields:
        val_a = getattr(a, field, None)
        val_b = getattr(b, field, None)
        field_name = f"{prefix}{field}"

        if isinstance(val_a, BaseModel) and isinstance(val_b, BaseModel):
            # 递归比较子 BaseModel
            sub_diffs = diff_models(val_a, val_b, prefix=field_name + ".")
            diffs.update(sub_diffs)
        else:
            # 直接比较（包括 Optional[str] 等）
            if val_a != val_b:
                diffs[field_name] = (val_a, val_b)

    return diffs
