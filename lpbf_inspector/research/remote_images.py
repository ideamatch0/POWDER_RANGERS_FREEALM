"""Lectures HTTP bornées pour extraire les photos publiques sans charger les archives."""
from collections import OrderedDict
import io
import time
import urllib.error
import urllib.request


class RangeReader(io.RawIOBase):
    def __init__(self,url,size,budget=1_500_000_000,block_size=65536,max_blocks=128,cache_bust=False):
        self.url=url;self.size=size;self.budget=budget;self.block_size=block_size;self.max_blocks=max_blocks
        self.pos=0;self.received=0;self.requests=0;self.cache=OrderedDict();self.cache_bust=cache_bust

    def readable(self):return True
    def seekable(self):return True
    def writable(self):return False
    def tell(self):return self.pos
    def seek(self,offset,whence=0):
        self.pos=offset+(self.pos if whence==1 else self.size if whence==2 else 0)
        if self.pos<0:raise ValueError('Position négative.')
        return self.pos

    def range(self,start,length):
        if length<=0:return b''
        end=min(self.size,start+length)-1
        if start<0 or start>=self.size or end-start+1>self.budget-self.received:
            raise ValueError('Lecture hors fichier ou budget réseau dépassé.')
        url=self.url+('&' if '?' in self.url else '?')+f'range={start}-{end}' if self.cache_bust else self.url
        for attempt in range(3):
            try:
                request=urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}','User-Agent':'Powder-Ranger/1.0','Accept-Encoding':'identity'})
                with urllib.request.urlopen(request,timeout=35) as response:
                    if response.status!=206 or response.headers.get('Content-Range')!=f'bytes {start}-{end}/{self.size}':
                        raise ValueError('Le serveur ne respecte pas la lecture partielle demandée.')
                    data=response.read(end-start+2)
                self.received+=len(data);self.requests+=1
                if len(data)!=end-start+1:raise OSError('Réponse tronquée.')
                return data
            except (OSError,TimeoutError):
                if attempt==2:raise
                time.sleep(attempt+1)

    def read(self,length=-1):
        if length<0:length=self.size-self.pos
        length=min(length,self.size-self.pos)
        if length<=0:return b''
        if length>self.budget-self.received:raise ValueError('Lecture trop grande.')
        if length>self.block_size*2:
            data=self.range(self.pos,length);self.pos+=len(data);return data
        chunks=[];end=self.pos+length
        while self.pos<end:
            block=self.pos//self.block_size
            if block not in self.cache:
                self.cache[block]=self.range(block*self.block_size,min(self.block_size,self.size-block*self.block_size))
                if len(self.cache)>self.max_blocks:self.cache.popitem(last=False)
            self.cache.move_to_end(block)
            data=self.cache[block];offset=self.pos%self.block_size
            part=data[offset:offset+min(end-self.pos,len(data)-offset)];chunks.append(part);self.pos+=len(part)
        return b''.join(chunks)

    def readinto(self,buffer):
        data=self.read(len(buffer));buffer[:len(data)]=data;return len(data)
