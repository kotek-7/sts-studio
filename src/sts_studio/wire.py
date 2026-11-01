"""Bounded, resynchronizing byte transport. All callers are serialized by the controller."""
import time
import serial
from .catalog import PROTOCOL

class LinkError(Exception):pass
class Timeout(LinkError):pass
class StatusError(LinkError):
    def __init__(self,bits):
        self.bits=bits
        labels=['電圧','センサー','温度','電流','角度','過負荷','命令']
        super().__init__('サーボ異常 0x%02X: '%bits+' / '.join(x for i,x in enumerate(labels) if bits&(1<<i)))

def frame(sid,instruction,parameters=b''):
    if not 0<=sid<=254 or len(parameters)>243:raise ValueError('パケットのID・長さが不正です')
    body=bytes((sid,len(parameters)+2,instruction))+bytes(parameters)
    return b'\xff\xff'+body+bytes((~sum(body)&255,))

class Parser:
    def __init__(self):self.buffer=bytearray()
    def feed(self,data):
        self.buffer.extend(data);frames=[]
        while len(self.buffer)>=4:
            head=self.buffer.find(b'\xff\xff')
            if head<0:self.buffer[:]=self.buffer[-1:];break
            if head:del self.buffer[:head]
            if len(self.buffer)<4:break
            n=self.buffer[3]+4
            if self.buffer[2]>254 or not 6<=n<=250:del self.buffer[0];continue
            if len(self.buffer)<n:break
            raw=bytes(self.buffer[:n])
            if sum(raw[2:])&255!=255:del self.buffer[0];continue
            del self.buffer[:n];frames.append(raw)
        return frames

class SerialLink:
    def __init__(self,path,baud=1000000,parity='N',timeout_ms=50,trace=None):
        if not 5<=timeout_ms<=5000:raise ValueError('タイムアウトは5〜5000 msです')
        self.timeout=timeout_ms/1000;self.trace=trace or (lambda *x:None);self.tx_bytes=0;self.rx_bytes=0
        self.port=serial.Serial(port=None,baudrate=baud,parity=parity,timeout=.002,write_timeout=.3,exclusive=True)
        self.port.rts=False;self.port.dtr=False;self.port.port=path;self.port.open()
    @property
    def baud(self):return self.port.baudrate
    @baud.setter
    def baud(self,value):self.port.baudrate=value
    def close(self):self.port.close()
    def exchange(self,sid,ins,params=b'',expected=0,wait=True):
        tx=frame(sid,ins,params);self.port.reset_input_buffer();self.trace('TX',tx)
        if self.port.write(tx)!=len(tx):raise LinkError('送信が完了しませんでした')
        self.port.flush();self.tx_bytes+=len(tx)
        if not wait or sid==254:
            time.sleep(.003);return b'',0
        parser=Parser();end=time.monotonic()+self.timeout
        while time.monotonic()<end:
            data=self.port.read(max(1,self.port.in_waiting));self.rx_bytes+=len(data)
            for rx in parser.feed(data):
                self.trace('RX',rx)
                if rx==tx or rx[2]!=sid:continue
                if rx[3]-2!=expected:
                    if rx[4] and len(rx)==6:raise StatusError(rx[4])
                    continue
                return rx[5:-1],rx[4]
        raise Timeout(f'ID {sid}: 応答なし ({self.timeout*1000:g} ms)')

class Bus:
    def __init__(self,link):self.link=link
    def read(self,sid,address,length):
        if not 0<=sid<=253 or not 0<=address<256 or not 1<=length<=240 or address+length>256:raise ValueError('読取範囲が不正です')
        return self.link.exchange(sid,2,bytes((address,length)),expected=length)
    def send(self,sid,address,data,registered=False):
        if not 0<=sid<=253 or not 0<=address<256 or not data or address+len(data)>256:raise ValueError('書込範囲が不正です')
        self.link.exchange(sid,4 if registered else 3,bytes((address,))+bytes(data),wait=False)
    def sync(self,address,entries):
        if not entries:raise ValueError('同期書き込み先がありません')
        size=len(entries[0][1]);ids=[sid for sid,_ in entries]
        if len(ids)!=len(set(ids)) or any(not 0<=sid<=253 or len(data)!=size for sid,data in entries):raise ValueError('重複IDまたはデータ長の不一致です')
        params=bytes((address,size))+b''.join(bytes((sid,))+data for sid,data in entries)
        self.link.exchange(254,131,params,wait=False)
    def action(self):self.link.exchange(254,5,wait=False)
    def reset(self,sid):self.link.exchange(sid,6,wait=False)
