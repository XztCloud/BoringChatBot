import threading
import queue
import os
from dataclasses import dataclass, field
from typing import List

from langchain_community.document_loaders import TextLoader
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from concurrent.futures import ThreadPoolExecutor

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from unstructured.partition.pdf import partition_pdf
from app.db_option import save_doc_chunk
from app.utils.user_base_model import RagConfig

PDF_PIC_DIR = 'pdf_pic'
CHROMADB_COLLECTION = 'rag_documents_collection'
CHROMADB_DIR = 'chroma_db'
os.makedirs(CHROMADB_DIR, exist_ok=True)
os.makedirs(PDF_PIC_DIR, exist_ok=True)


@dataclass
class ParentDocumentInfo:
    file_path: str = field(metadata={"description": "文件路径"})
    file_id: int = field(metadata={"description": "文件ID"})


class LoadFileThread:

    def __init__(self):
        # 保存文件信息队列
        self.file_path_queue = queue.Queue()
        # 向量
        self.embeddings = DashScopeEmbeddings(
            model="text-embedding-v2",
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
        )
        # txt文件切分器
        self.text_spliter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        # 向量数据库
        self.vectorstore = Chroma(
            collection_name=CHROMADB_COLLECTION,
            embedding_function=self.embeddings,
            persist_directory=CHROMADB_DIR
        )
        # 检索器。只要数据库对象没变，Retriever 不需要重新生成；改k值时、更新数据库实例、embedding模型时，需要重新生成
        self.retriever = self.vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})

        self.split_way = "default"  # 切分文档方案
        self.stop_event = threading.Event()
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.consume_thread = threading.Thread(
            target=self.task_consumer,
            args=(self.file_path_queue, self.executor, self.stop_event),
            daemon=True
        )
        self.consume_thread.start()
        self.doc_ids = []
        self.rag_config = RagConfig()

    def load(self):
        self.rag_config = RagConfig()

    def update_rag_config(self, rag_config: RagConfig):
        differences = {}
        src_rag_config = self.rag_config.dict()
        new_rag_config = rag_config.dict()
        all_fields = set(src_rag_config.keys()).union(set(new_rag_config.keys()))
        for _field in all_fields:
            src_value = src_rag_config.get(_field, "MISSING")
            new_value = new_rag_config.get(_field, "MISSING")
            if src_value != new_value:
                differences[_field] = new_value

    # 消费者线程函数：不断从队列取任务，提交给线程池
    def task_consumer(self, task_queue: queue.Queue, executor: ThreadPoolExecutor, stop_event: threading.Event):
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
            if self.split_way == "default":
                # 默认切分方式
                pass
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

        try:
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




