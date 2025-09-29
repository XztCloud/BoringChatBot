import threading
import queue
import os
import uuid
from dataclasses import dataclass, field
from typing import List

from langchain.retrievers import MultiVectorRetriever
from langchain_community.document_loaders import TextLoader
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from concurrent.futures import ThreadPoolExecutor
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.stores import InMemoryStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from unstructured.partition.pdf import partition_pdf
from app.db_option import save_doc_chunk
from app.retriever.llm_manager import llm_manager
from app.utils.user_base_model import TaskConfig, BaseManager, EmbeddingsConfig, RetrieverConfig, MultiRetrieverConfig
from app.utils.utils_tools import diff_models

PDF_PIC_DIR = 'pdf_pic'
CHROMADB_COLLECTION = 'rag_documents_collection'
CHROMADB_SUMMARY_COLLECTION = 'rag_summary_collection'
CHROMADB_DIR = 'chroma_db'
os.makedirs(CHROMADB_DIR, exist_ok=True)
os.makedirs(PDF_PIC_DIR, exist_ok=True)

global_env_name_by_model_name = {
    "text-embedding-v2": "DASHSCOPE_API_KEY"
}


@dataclass
class ParentDocumentInfo:
    file_path: str = field(metadata={"description": "文件路径"})
    file_id: int = field(metadata={"description": "文件ID"})


def get_summary_chunks(ori_doc_chunks: list[Document]) -> list[str]:
    """
    输入分段后的源文件列表，输出每段话的总结列表
    :param ori_doc_chunks:
    :return:
    """
    print(f'get_summary: {len(ori_doc_chunks)}')
    summary_model = llm_manager.summary_model
    prompt_text = """You are an assistant tasked with summarizing tables and text.              
    Give a concise summary of the table or text. Table or text chunk: {element} """
    prompt = ChatPromptTemplate.from_template(prompt_text)
    summary_chain = {"element": lambda x: x} | prompt | summary_model | StrOutputParser()
    ori_text_chunks = [doc.page_content for doc in ori_doc_chunks]
    summary_chunks = summary_chain.batch(ori_text_chunks, {"max_concurrency": 5})
    if len(summary_chunks) > 0:
        print(f'get summary chunks: {summary_chunks[0]}')
    return summary_chunks


class LoadFileThread(BaseManager):
    def __init__(self):
        # 保存文件信息队列
        self.file_path_queue = queue.Queue()
        # 向量嵌入器
        self.embeddings = None
        # txt文件切分器
        self.text_spliter = None
        # 向量数据库
        self.vectorstore = None
        # 检索器。只要数据库对象没变，Retriever 不需要重新生成；改k值时、更新数据库实例、embedding模型时，需要重新生成
        self.retriever = None
        self.split_way = "default"  # 切分文档方案
        self.stop_event = threading.Event()
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.consume_thread = threading.Thread(
            target=self.task_consumer,
            args=(self.file_path_queue, self.executor, self.stop_event),
            daemon=True
        )
        self.doc_ids = []
        self.task_config = TaskConfig()
        # 多文件检索，父文件存储器
        self.parent_store = None
        # 父子文件关联字段名
        self.id_key = "doc_id"

    def load(self):
        # todo: 从数据库加载配置，暂时使用默认值代替
        self.task_config = TaskConfig()
        print(f'load task config: {self.task_config}')
        self.update_embeddings(self.task_config.embeddings_config)
        self.update_retriever(self.task_config.retriever_config, self.task_config.multi_retriever_config)
        self.consume_thread.start()

    def update_task_config(self, new_task_config: TaskConfig):
        diffs = diff_models(self.task_config.embeddings_config, new_task_config.embeddings_config)
        if diffs:
            print(f'update embeddings config: {diffs}')
            self.update_embeddings(new_task_config.embeddings_config)
            self.task_config.embeddings_config = new_task_config.embeddings_config

        multi_retriever_change = False
        retriever_change = False
        if new_task_config.multi_retriever_config is not None:
            diffs = diff_models(self.task_config.multi_retriever_config, new_task_config.multi_retriever_config)
            if diffs:
                print(f'update multi retriever config: {diffs}')
                multi_retriever_change = True

        diffs = diff_models(self.task_config.retriever_config, new_task_config.retriever_config)
        if diffs:
            print(f'update retriever config: {diffs}')
            retriever_change = True

        # todo：分开更新
        if multi_retriever_change or retriever_change:
            self.update_retriever(new_task_config.retriever_config, new_task_config.multi_retriever_config)
        self.task_config = new_task_config
        # todo: 更新任务配置后，写入数据库

    def update_embeddings(self, embeddings_config: EmbeddingsConfig):
        # 向量嵌入模型参数
        env_name = global_env_name_by_model_name.get(embeddings_config.model_name, None)
        if env_name is None:
            print(f'Error: {embeddings_config.model_name} is not supported.')
            raise Exception(f'Error: {embeddings_config.model_name} is not supported.')

        try:
            if embeddings_config.model_name in ["text-embedding-v2", "text-embedding-v1"]:
                self.embeddings = DashScopeEmbeddings(
                    model=embeddings_config.model_name,
                    dashscope_api_key=os.getenv(env_name)
                )
            else:
                raise Exception(f'Error: {self.task_config.embeddings_config.model_name} is not supported.')
        except Exception as e:
            print(f'Error: load embeddings failed. {e}')
            raise Exception(f'Error: load embeddings failed. {e}')

    def update_retriever(self, retriever_config: RetrieverConfig, multi_retriever_config: MultiRetrieverConfig):
        try:
            # txt文件切分器
            if retriever_config.split_way == "Recursive":
                self.text_spliter = RecursiveCharacterTextSplitter(
                    chunk_size=retriever_config.split_len,
                    chunk_overlap=retriever_config.over_lap,
                    length_function=len,
                )
            else:
                raise Exception(f'Error: {self.task_config.split_way} is not supported.')

            # 检索器。只要数据库对象没变，Retriever 不需要重新生成；改k值时、更新数据库实例、embedding模型时，需要重新生成
            if multi_retriever_config is None:
                # 向量数据库
                self.vectorstore = Chroma(
                    collection_name=CHROMADB_COLLECTION,
                    embedding_function=self.embeddings,
                    persist_directory=CHROMADB_DIR
                )
                self.retriever = self.vectorstore.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": retriever_config.top_k}
                )
            else:
                if multi_retriever_config.multi_retriever_strategy == "summarize":
                    # 总结段落的向量数据库
                    self.vectorstore = Chroma(
                        collection_name=CHROMADB_SUMMARY_COLLECTION,
                        embedding_function=self.embeddings,
                        persist_directory=CHROMADB_DIR
                    )
                    # 保存父文件原始文件
                    self.parent_store = InMemoryStore()
                    self.retriever = MultiVectorRetriever(
                        vectorstore=self.vectorstore,
                        docstore=self.parent_store,
                        id_key=self.id_key,
                    )
                else:
                    raise Exception(
                        f'Error: {multi_retriever_config.multi_retriever_strategy} is not supported.')
        except Exception as e:
            print(f'Error: load embeddings failed. {e}')
            raise Exception(f'Error: load embeddings failed. {e}')

    def task_consumer(self, task_queue: queue.Queue, executor: ThreadPoolExecutor, stop_event: threading.Event):
        """
        消费者线程函数：不断从队列取任务，提交给线程池
        :param task_queue:
        :param executor:
        :param stop_event:
        :return:
        """
        while not stop_event.is_set():
            try:
                # 最多等待 1 秒取一个任务，避免永久阻塞
                document_info = task_queue.get(timeout=1)
                if not isinstance(document_info, ParentDocumentInfo):
                    print(f'check document info, error: {document_info}')
                    continue
                executor.submit(self.split_file, document_info)
                task_queue.task_done()
            except queue.Empty:
                continue

    def split_file(self, document_info: ParentDocumentInfo):
        print(f'start split file info: {document_info}')
        if document_info.file_path.endswith("txt"):
            print("1")
            loader = TextLoader(document_info.file_path, encoding="utf-8")
            print("2")
            text = loader.load()
            print("3")
            split_docs = self.text_spliter.split_documents(text)
            print("4")

        elif document_info.file_path.endswith("pdf"):
            print("1")
            try:
                raw_pdf_elements = partition_pdf(
                    strategy="fast",
                    filename=document_info.file_path,
                    # Unstructured first finds embedded image blocks
                    extract_images_in_pdf=False,
                    # Use layout model (YOLOX) to get bounding boxes (for tables) and find titles
                    # Titles are any sub-section of the document
                    infer_table_structure=True,
                    # Post processing to aggregate text once we have the title
                    chunking_strategy="by_title",
                    # Chunking params to aggregate text blocks
                    # Attempt to create a new chunk 3800 chars
                    # Attempt to keep chunks > 2000 chars
                    max_characters=4000,
                    new_after_n_chars=3800,
                    combine_text_under_n_chars=2000,
                    image_output_dir_path=PDF_PIC_DIR,
                )
            except Exception as e:
                print(f'load pdf failed, reason: {e}')
                raise f'load pdf failed, reason: {e}'
            print("2")
            split_docs = []
            counter = 0
            for element in raw_pdf_elements:
                doc = Document(
                    page_content=element.text,
                    metadata={
                        "source": document_info.file_path,
                        "doc_id": counter,
                        "type": "pdf",
                    }
                )
                counter += 1
                split_docs.append(doc)
            print("3")
            # print(split_docs)
            print("4")
        else:
            raise Exception(f'Error file type: {document_info.file_path}')

        # 多文件检索且使用了总结段落代替原始文件时
        use_multi_retriever = self.task_config.multi_retriever_config is not None and \
            self.task_config.multi_retriever_config.multi_retriever_strategy == "summarize"

        # 如果是多文件检索器
        if use_multi_retriever:
            doc_ids = [str(uuid.uuid4()) for _ in split_docs]
            summaries_chunks = get_summary_chunks(split_docs)
            # 将 doc_ids 和 原始文档 split_docs 保存到父文档存储器中
            self.retriever.docstore.mset(list(zip(doc_ids, split_docs)))
            # 将段落的总结list替换原始切分后的段落list， 并将doc_ids与总结向量一一对应
            # 形成 doc_id - summary item - ori_text item 对应关系， doc_id是主键
            split_docs = [
                Document(page_content=s, metadata={self.id_key: doc_ids[i]})
                for i, s in enumerate(summaries_chunks)
            ]

        try:
            # if self.task_config.
            print("5")
            doc_ids = self.vectorstore.add_documents(documents=split_docs)
            print(f"Successfully added {len(doc_ids)} documents from {document_info.file_path}")
            save_doc_chunk(doc_ids, document_info.file_id)

            # self.doc_ids = doc_ids
            # self.test_check_embeddings_with_id()
            print(f"save_doc_chunk end, doc_ids: {doc_ids}")
        except Exception as e:
            print(f"Error adding documents from {document_info.file_path}: {e}")
        print(f'end split file: {document_info.file_path}')

    async def delete_embeddings(self, ids: List[str], batch_size: int = 500):
        for i in range(0, len(ids), batch_size):
            batch = ids[i:i + batch_size]
            if batch:
                await self.vectorstore.adelete(ids=batch)

    def test_check_embeddings_with_id(self):
        collection = self.vectorstore._collection
        res = collection.get(ids=self.doc_ids)
        # print(res)
        if res["ids"]:
            print('embeddings exist')
        else:
            print('embeddings not exist')

    def stop(self):
        print('stop thread pool.')
        self.stop_event.set()
        self.consume_thread.join()


load_file_thread = LoadFileThread()
