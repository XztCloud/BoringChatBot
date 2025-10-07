from celery import Celery

celery_app = Celery('app.service.embeddings_pro.tasks',
                    broker='redis://localhost:6379/1',
                    backend='redis://localhost:6379/2')
celery_app.conf.task_routes = {'tasks.*': {'queue': 'vectorize'}}
