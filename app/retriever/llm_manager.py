import os
import uuid
from dataclasses import dataclass, field
from typing import Dict

from sqlmodel import Session

from app.api.deps import SessionDep, engine
from langchain_openai import ChatOpenAI

from app.db_option import get_user_by_id, get_query_config_by_id
from app.utils.user_base_model import TaskConfig, BaseManager, LLmConfig, SummaryLLmConfig
from app.utils.utils_tools import diff_models


@dataclass
class LLMInfo:
    env: str = field(metadata={"description": "环境变量"})
    base_url: str = field(metadata={"description": "基础url"})
    model: str = field(metadata={"description": "模型"})


global_llm_info_by_name = {
    "qwen-plus": LLMInfo("DASHSCOPE_API_KEY", "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
}


class LLmManager(BaseManager):
    def __init__(self, user_id: uuid.UUID = None):
        self.llm = None
        self.llm_name = ""
        self.llm_config = None
        # todo: 增加一个专门用于总结文本的小模型，可以微调产生
        self.summary_llm = None
        self.summary_llm_name = ""
        self.task_config: TaskConfig = TaskConfig()
        self.user_id = user_id

    def load(self):
        """
        加载模型
        :return:
        """
        # todo: 从数据库中任务配置 task_config

        self.update_llm(self.task_config.llm_config)
        self.update_summary_llm(self.task_config.summary_llm_config)

    def load_llm(self):
        with Session(engine) as session:
            # 从数据库中获取 user
            user = get_user_by_id(session=session, user_id=self.user_id)
            query_config = get_query_config_by_id(session=session, user_id=self.user_id,
                                                  query_config_id=user.cur_llm_config_id)
            llm_config = LLmConfig(**query_config.dict())
            self.update_llm(llm_config)

    def update_task_config(self, new_task_config: TaskConfig):
        diffs = diff_models(self.task_config.llm_config, new_task_config.llm_config)
        if "llm_name" in diffs.keys() or "temperature" in diffs.keys():
            self.update_llm(new_task_config.llm_config)
        if "summary_llm_name" in diffs.keys() or "summary_temperature" in diffs.keys():
            self.update_summary_llm(new_task_config.summary_llm_config)
        self.task_config = new_task_config
        # todo: 保存到数据库中

    def update_llm(self, llm_config: LLmConfig):
        print(f'self.llm_name: {self.llm_name}, llm_config: {llm_config}')
        if self.llm_config is None or diff_models(self.llm_config, llm_config) != {}:
            self.llm_config = llm_config
            model_name = llm_config.llm_name
            if global_llm_info_by_name.get(model_name, None) is None:
                raise Exception(f"model_name: {model_name} not found")
            # 大模型
            self.llm = ChatOpenAI(
                api_key=os.getenv(global_llm_info_by_name[model_name].env),
                base_url=global_llm_info_by_name[model_name].base_url,
                model=global_llm_info_by_name[model_name].model,
                temperature=llm_config.temperature
            )
            print('update llm')
        else:
            print('no need update llm')

    def update_summary_llm(self, llm_config: SummaryLLmConfig):
        if llm_config is None:
            self.summary_llm_name = self.llm_name
            return
        summary_llm_name = llm_config.summary_llm_name
        # 没有则默认是用一个模型
        if global_llm_info_by_name.get(summary_llm_name, None) is None:
            print(f'warning: summary_llm_name: {summary_llm_name} not found, use sample llm')
            self.summary_llm = self.llm
        else:
            self.summary_llm = ChatOpenAI(
                api_key=os.getenv(global_llm_info_by_name[summary_llm_name].env),
                base_url=global_llm_info_by_name[summary_llm_name].base_url,
                model=global_llm_info_by_name[summary_llm_name].model,
                temperature=llm_config.summary_temperature
            )


# llm_manager = LLmManager()

global_query_llm_cache: Dict[uuid.UUID, LLmManager] = {}
