import asyncio
import multiprocessing

from app.utils.user_base_model import TaskConfig


class LoadDoc:
    def __init__(self,
                 process_id: int,
                 task_queue: multiprocessing.Queue,
                 event_queue: multiprocessing.Queue,
                 event: multiprocessing.Event):
        self.process_id = process_id
        self.task_queue = task_queue
        self.event_queue = event_queue
        self.is_busy = event
        self.running = True

    async def task_loop(self):
        while self.running:
            task = await self.task_queue.get(timeout=0.1)
            if isinstance(task, TaskConfig):
                print(f"load_doc: task is TaskConfig: {task}")
                await self.load_document(task)

            await asyncio.sleep(0.01)

    async def event_loop(self):
        while self.running:
            event = self.event_queue.get(timeout=0.1)
            if event == "stop":
                print(f"load_doc: event is stop")
                self.running = False
                self.is_busy.set()
            await asyncio.sleep(0.01)

    async def load_document(self, task_config: TaskConfig):
        pass
