from typing import Any, Optional

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    code: str
    msg: str = ""


class InfoResponse(BaseResponse):
    extra_msg: Any = Field(default=None)


class LLmConfig(BaseModel):
    llm_name: str = Field(default="qwen-plus", description="大模型")
    temperature: float = Field(default=0.0, description="温度")


class RagConfig(BaseModel):
    split_len: int = Field(default=1000, description="文本分段长度")
    split_way: str = Field(default="Recursive", description="文本分段方式")
    top_k: int = Field(default=3, description="检索 top k")


class MultiRetrieverConfig(BaseModel):
    use_multi_retriever: bool = Field(default=False, description="是否使用多检索器")
    multi_retriever_strategy: str = Field(default="summarize", description="多检索器策略")


class HistoryConfig(BaseModel):
    save_history: bool = Field(default=False, description="是否保存对话历史")
    history_times: int = Field(default=10, description="对话历史次数")
    history_max_tokens: int = Field(default=1000, description="对话历史最大token数")


class TaskConfig(BaseModel):
    llm_config: LLmConfig = Field(default=LLmConfig(), description="大模型配置")
    multi_retriever_config: Optional[MultiRetrieverConfig] = Field(default=None, description="多检索器配置")
    history_config: Optional[HistoryConfig] = Field(default=None, description="对话历史配置")
    rag_config: RagConfig = Field(default=RagConfig(), description="rag配置")
