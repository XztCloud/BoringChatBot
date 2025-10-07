from typing import List

import redis

from app.service.embeddings_pro.celery_main import celery_app

redis = redis.from_url('redis://localhost:6379/0')


@celery_app.task(bind=True)
def process_document(self, user_id: str, title_id: str, file_path_list: List[str]):
    print(f'process_document: {user_id}, {title_id}, {file_path_list}')
    for file_path in file_path_list:
        print(f'process_document: {file_path}')
