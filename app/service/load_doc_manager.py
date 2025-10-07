import multiprocessing
import os
import threading

from app.service.load_doc import LoadDoc
from app.utils.user_base_model import TaskConfig

process_dict = {}

cpu_count = os.cpu_count()


def manager():
    global process_dict
    process_num = min(4, cpu_count)
    print(f'start {process_num} process')
    for i in range(process_num):
        p = multiprocessing.Process(target=LoadDoc, args=(task_queue, event_queue))
        p.start()
        process_dict[i] = p


class LoadDocManager:
    def __init__(self):
        self.process_num = min(4, cpu_count)
        self.process_dict = {}
        # self.task_queue = multiprocessing.Queue()
        # self.event_queue = multiprocessing.Queue()
        self.lock = threading.Lock()
        self.running = False

    def start(self):
        if self.running:
            print("already running")
            return
        print(f'start {self.process_num} process')
        for i in range(self.process_num):
            event = multiprocessing.Event()
            event.clear()
            task_queue = multiprocessing.Queue()
            event_queue = multiprocessing.Queue()
            p = multiprocessing.Process(target=LoadDoc, args=(i, task_queue, event_queue, event))
            p.start()
            self.process_dict[i] = {"process": p, "event": event, "task_queue:": task_queue, "event_queue": event_queue}
            print(f'process {i} start')
        self.running = True

    def consume_task(self, task_config: TaskConfig):
        if not self.running:
            return False, "not running"
        find_pro = False
        with self.lock:
            for i, process_info in self.process_dict:
                if not process_info["event"].is_set():
                    process_info["event"].set()
                    process_info["process"].task_queue.put(task_config)
                    find_pro = True
                    break
        if not find_pro:
            return False, "no process available"
        return True, "success"

    def stop(self):
        self.running = False
        for i, process_info in self.process_dict:
            process_info["event"].set()
            process_info["process"].event_queue.put("stop")
            process_info["process"].join()
            print(f'process {i} stop')


load_doc_manager = LoadDocManager()