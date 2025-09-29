import os
from dataclasses import dataclass, field

from langchain_openai import ChatOpenAI

from app.utils.user_base_model import TaskConfig, BaseManager, LLmConfig
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
    def __init__(self):
        self.llm = None
        self.llm_name = ""
        # todo: 增加一个专门用于总结文本的小模型，可以微调产生
        self.summary_llm = None
        self.summary_llm_name = ""
        self.task_config: TaskConfig = TaskConfig()

    def load(self):
        """
        加载模型
        :return:
        """
        # todo: 从数据库中任务配置 task_config
        self.update_llm(self.task_config.llm_config)
        self.update_summary_llm(self.task_config.llm_config)

    def update_task_config(self, new_task_config: TaskConfig):
        diffs = diff_models(self.task_config.llm_config, new_task_config.llm_config)
        if "llm_name" in diffs.keys() or "temperature" in diffs.keys():
            self.update_llm(new_task_config.llm_config)
        if "summary_llm_name" in diffs.keys() or "summary_temperature" in diffs.keys():
            self.update_summary_llm(new_task_config.llm_config)
        self.task_config = new_task_config
        # todo: 保存到数据库中

    def update_llm(self, llm_config:LLmConfig):
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

    def update_summary_llm(self, llm_config:LLmConfig):
        summary_llm_name = llm_config.summary_llm_name
        # 没有则默认是用一个模型
        if summary_llm_name is not None:
            self.summary_llm = self.llm
        elif global_llm_info_by_name.get(summary_llm_name, None) is None:
            print(f'warning: summary_llm_name: {summary_llm_name} not found, use sample llm')
            self.summary_llm = self.llm
        else:
            self.summary_llm = ChatOpenAI(
                api_key=os.getenv(global_llm_info_by_name[summary_llm_name].env),
                base_url=global_llm_info_by_name[summary_llm_name].base_url,
                model=global_llm_info_by_name[summary_llm_name].model,
                temperature=llm_config.summary_temperature
            )


llm_manager = LLmManager()
