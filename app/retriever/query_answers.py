import os
import queue
import threading

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

from app.retriever.load_file_thread import load_file_thread


class QueryAnswers:
    def __init__(self):
        self.question_queue = queue.Queue()
        # 大模型
        self.llm = ChatOpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen-plus",  # ✅ 用通义千问提供的模型名，比如 qwen-plus / qwen-max / qwen-turbo
            temperature=0
        )
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
        self.native_rag_chain = self.retrieve | self.prompt | self.llm | self.parse_output

        self.stop_event = threading.Event()
        self.answer_thread = threading.Thread(target=self.query_thread)
        self.answer_thread.start()

    def query_thread(self):
        while not self.stop_event.is_set():
            question = self.question_queue.get()
            self.native_rag_chain.invoke(question)

    async def query(self, question: str) -> str:
        result = await self.native_rag_chain.ainvoke(question)
        return result

    def stop(self):
        self.stop_event.set()
        self.answer_thread.join()


query_answers = QueryAnswers()
