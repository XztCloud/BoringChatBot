import json
import os
import queue
import uuid
from dataclasses import field, dataclass
from typing import Dict

import redis
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_openai import ChatOpenAI

from app.retriever.llm_manager import global_query_llm_cache, LLmManager
from app.retriever.load_file_thread import load_file_thread
from app.utils.user_base_model import TaskConfig, BaseManager

r = redis.from_url('redis://localhost:6379/0')


@dataclass
class StreamQuestion:
    question: str = field(metadata={"description": "问题"})
    answer_queue: queue.Queue = field(metadata={"description": "答案队列"})


def debug_logs(retrieve):
    # print(f"debug_logs: context: {retrieve}".encode("utf-8", errors="ignore").decode("utf-8"))
    return retrieve


class QueryAnswers(BaseManager):
    def __init__(self, user_id: uuid.UUID = None, title_id: uuid.UUID = None):
        self.stream_question_queue = queue.Queue()
        # 大模型
        self.llm = None
        self.template = ""
        self.retrieve = None
        self.prompt = None
        self.parse_output = StrOutputParser()
        self.native_rag_chain = None
        self.task_config = TaskConfig()
        self.user_id = user_id
        self.title_id = title_id
        self.version = self._get_remote_retriever_version()

    def load(self):
        if self.user_id in global_query_llm_cache:
            llm_manager = global_query_llm_cache[self.user_id]
        else:
            print(f'Error: global_query_llm_cache.get({self.user_id}) is None')
            llm_manager = LLmManager(self.user_id)
            llm_manager.load_llm()
        if llm_manager is None:
            print(f"global_query_llm_cache.get({self.user_id}) is None")
            return False

        if load_file_thread.retriever is None or llm_manager.llm is None:
            print("load_file_thread.retriever is None")
            raise Exception("load_file_thread.retriever is None")
        # todo:加载数据库到 task_config

        self.llm = llm_manager.llm
        self.template = """ 根据一下内容回答问题，如果没有相关内容，则回答不知道：
                {context}
                问题：{question}
                """
        self.retrieve = {
            "context": load_file_thread.retriever | (lambda docs: "\n".join([doc.page_content for doc in docs])),
            "question": RunnablePassthrough()
        }
        self.prompt = ChatPromptTemplate.from_template(self.template)
        self.parse_output = StrOutputParser()
        self.native_rag_chain = self.retrieve | RunnableLambda(debug_logs) | self.prompt | self.llm | self.parse_output

    def update_task_config(self, new_task_config: TaskConfig):
        pass

    async def query(self, question: str) -> str:
        result = await self.native_rag_chain.ainvoke(question)
        return result

    async def event_generator(self, question: str):
        async for answer in self.native_rag_chain.astream(question):
            yield f"data: {json.dumps({'data': answer}, ensure_ascii=False)}\n\n"

    def _get_remote_retriever_version(self) -> int:
        key = f"{self.user_id}_{self.title_id}_remote_retriever_version"
        # v = r.get(key)
        # return int(v) if v else 0
        return 0

    def reload_if_needed(self):
        remote = self._get_remote_retriever_version()
        if remote != self.version:
            self.version = remote
            # todo: retriever reload
            print(f"reload_if_needed: {self.user_id}, {self.title_id}, {self.version}")
            pass


# query_answers = QueryAnswers()

global_query_answers_cache: Dict[uuid.UUID, QueryAnswers] = {}
