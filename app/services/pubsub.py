import json
import queue
import threading

class PubSubService:
    def __init__(self):
        self._subs: dict[str, list[queue.Queue]] = {}
        self._lock = threading.Lock()

    def subscribe(self, topic: str) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=500)
        with self._lock:
            if topic not in self._subs:
                self._subs[topic] = []
            self._subs[topic].append(q)
        return q

    def unsubscribe(self, topic: str, q: queue.Queue):
        with self._lock:
            if topic in self._subs:
                try:
                    self._subs[topic].remove(q)
                except ValueError:
                    pass

    def emit(self, topic: str, event: dict):
        msg = json.dumps(event)
        with self._lock:
            subs = list(self._subs.get(topic, []))
        for q in subs:
            try:
                q.put_nowait(msg)
            except queue.Full:
                pass

pubsub = PubSubService()
