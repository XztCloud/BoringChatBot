import uuid
from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel, Field
from sqlmodel import SQLModel


class BaseResponse(BaseModel):
    code: str
    msg: str = ""


class InfoResponse(BaseResponse):
    extra_msg: Any = Field(default=None)


class LLmConfig(SQLModel):
    config_name: Optional[str] = Field(default=None, max_length=256)
    llm_name: str = Field(default="qwen-plus", description="大模型")
    temperature: float = Field(default=0.0, description="温度")


class SummaryLLmConfig(SQLModel):
    summary_llm_name: Optional[str] = Field(default=None, description="用于总结大模型")
    summary_temperature: float = Field(default=0.0, description="温度")


class EmbeddingsConfig(SQLModel):
    model_name: str = Field(default="text-embedding-v2", description="嵌入模型名称")
    vector_dimensions: Optional[int] = Field(default=None, description="向量维度")


class RetrieverConfig(SQLModel):
    split_len: int = Field(default=1000, description="文本分段长度")
    over_lap: int = Field(default=200, description="文本重叠长度")
    split_way: str = Field(default="Recursive", description="文本分段方式")
    top_k: int = Field(default=3, description="检索 top k")


class MultiRetrieverConfig(SQLModel):
    use_multi_retriever: bool = Field(default=False, description="是否使用多检索器")
    multi_retriever_strategy: str = Field(default="summarize", description="多检索器策略")


class HistoryConfig(SQLModel):
    save_history: bool = Field(default=False, description="是否保存对话历史")
    history_times: int = Field(default=10, description="对话历史次数")
    history_max_tokens: int = Field(default=1000, description="对话历史最大token数")


class TaskConfig(SQLModel):
    task_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="任务ID")
    llm_config: LLmConfig = Field(default=LLmConfig(), description="大模型配置")
    summary_llm_config: Optional[SummaryLLmConfig] = Field(default=None, description="文本总结模型配置")
    embeddings_config: EmbeddingsConfig = Field(default=EmbeddingsConfig(), description="嵌入模型信息")
    multi_retriever_config: Optional[MultiRetrieverConfig] = Field(default=None, description="多检索器配置")
    history_config: Optional[HistoryConfig] = Field(default=None, description="对话历史配置")
    retriever_config: RetrieverConfig = Field(default=RetrieverConfig(), description="检索器配置")


class BaseManager(ABC):
    @abstractmethod
    def load(self):
        pass

    @abstractmethod
    def update_task_config(self, task_config: TaskConfig):
        pass




