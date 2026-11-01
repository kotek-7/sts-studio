"""One bounded serial worker. UI keeps no backlog of movement requests."""
import queue,threading
from PyQt5.QtCore import QObject,pyqtSignal

class Worker(QObject):
    done=pyqtSignal(object,object)
    failed=pyqtSignal(object,object)
    progress=pyqtSignal(object)
    trace=pyqtSignal(str,bytes)
    def __init__(self):
        super().__init__();self.queue=queue.Queue();self.cancel=threading.Event();self.closed=False
        self.thread=threading.Thread(target=self.run,name='fd-serial',daemon=True);self.thread.start()
    def submit(self,token,function):
        if self.closed:raise RuntimeError('worker closed')
        self.cancel.clear();self.queue.put((token,function))
    def run(self):
        while True:
            item=self.queue.get()
            if item is None:return
            token,fn=item
            try:self.done.emit(token,fn(self.cancel))
            except Exception as e:self.failed.emit(token,e)
    def close(self):
        self.closed=True;self.cancel.set();self.queue.put(None)
