import asyncio
import json
import os


class Queue:
    def __init__(self, path='./', name='queue.jsonl'):
        self.spath = os.path.join(path, name)
        self.q = asyncio.Queue()
        if os.path.exists(self.spath):
            with open(self.spath, 'r', encoding='utf-8') as f:
                for data in f:
                    data = data.strip()
                    if data:
                        self.put_nowait(json.loads(data))
            os.remove(self.spath)

    def get_nowait(self):
        return self.q.get_nowait()

    def put_nowait(self, item):
        self.q.put_nowait(item)

    def qsize(self):
        return self.q.qsize()

    def close(self):
        data_list = []
        while not self.q.empty():
            try:
                item = self.get_nowait()
                data_list.append(item)
            except Exception:
                pass
        if data_list:
            with open(self.spath, 'w+', encoding='utf-8') as f:
                for data in data_list:
                    f.write(json.dumps(data, ensure_ascii=False) + '\n')
