"""Pure scheduling/statistics models; no I/O and no sleeping inside the UI thread."""
from dataclasses import dataclass,field
import time

class Pattern:
    def __init__(self,start,end,step=None,clamp=True):
        if start==end:raise ValueError('StartとEndは異なる値にしてください')
        if step is not None and step<=0:raise ValueError('Stepは1以上です')
        self.clamp=clamp;self.start=start;self.end=end;self.step=step;self.value=start;self.direction=1 if end>start else -1;self.first=True
    def next(self):
        if self.first:
            self.first=False
            if self.clamp or self.step is None:return self.value
        if self.step is None:self.value=self.end if self.value==self.start else self.start;return self.value
        target=self.end if self.direction==(1 if self.end>self.start else -1) else self.start
        candidate=self.value+self.direction*self.step
        self.value=(min(candidate,target) if self.direction>0 else max(candidate,target)) if self.clamp else candidate
        if (self.direction>0 and self.value>=target) or (self.direction<0 and self.value<=target):self.direction*=-1
        return self.value

@dataclass
class CommunicationStats:
    start:float=field(default_factory=time.monotonic)
    attempts:int=0
    success:int=0
    timeouts:int=0
    errors:int=0
    total_us:float=0.0
    min_us:float=float("inf")
    max_us:float=0.0
    bytes_total:int=0
    def add(self,seconds,bytes_count,kind='success'):
        self.attempts+=1;self.bytes_total+=bytes_count
        if kind=='success':
            self.success+=1;value=seconds*1e6;self.total_us+=value;self.min_us=min(self.min_us,value);self.max_us=max(self.max_us,value)
        elif kind=='timeout':self.timeouts+=1
        else:self.errors+=1
    def report(self):
        elapsed=max(.000001,time.monotonic()-self.start)
        return dict(attempts=self.attempts,success=self.success,timeouts=self.timeouts,errors=self.errors,min_us=self.min_us if self.success else 0,mean_us=self.total_us/self.success if self.success else 0,max_us=self.max_us,kbps=self.bytes_total*8/elapsed/1000)
