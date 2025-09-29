import json
import os
import queue
from dataclasses import field, dataclass
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_openai import ChatOpenAI

from app.retriever.llm_manager import llm_manager
from app.retriever.load_file_thread import load_file_thread
from app.utils.user_base_model import TaskConfig, BaseManager


@dataclass
class StreamQuestion:
    question: str = field(metadata={"description": "问题"})
    answer_queue: queue.Queue = field(metadata={"description": "答案队列"})


def debug_logs(retrieve):
    print(f"debug_logs: context: {retrieve}")
    return retrieve


class QueryAnswers(BaseManager):
    def __init__(self):
        self.stream_question_queue = queue.Queue()
        # 大模型
        self.llm = None
        self.template = ""
        self.retrieve = None
        self.prompt = None
        self.parse_output = StrOutputParser()
        self.native_rag_chain = None
        self.task_config = TaskConfig()

    def load(self):
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


query_answers = QueryAnswers()
