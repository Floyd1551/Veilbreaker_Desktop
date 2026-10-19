"""A read-only, capability-URL map service bound only to loopback."""
import json
import mimetypes
from pathlib import Path
import secrets
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import unquote,urlsplit
from .map_pack import inspect_pack,signature

MAX_RANGE=16*1024*1024

class MapServer:
    def __init__(self,asset_root):
        self.assets={p.relative_to(asset_root).as_posix():p.resolve() for p in Path(asset_root).rglob('*') if p.is_file() and not p.is_symlink()}
        self.token=secrets.token_urlsafe(32);self.pack=None;self.model={};self.http=None;self.thread=None
        self.pack_reads=0
    def set_model(self,model):self.model=json.loads(json.dumps(model,allow_nan=False))
    def set_pack(self,path):
        pack=inspect_pack(path) if path else None
        if pack: pack['resource']='pack-'+secrets.token_hex(16)+'.pmtiles'
        self.pack=pack
        return pack
    def start(self):
        if self.http:return self.url
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_HEAD(self):self.serve(False)
            def do_GET(self):self.serve(True)
            def serve(self,body):
                origin='http://'+self.headers.get('Host','')
                if origin!=owner.origin or self.headers.get('Origin',owner.origin)!=owner.origin:
                    self.send_error(403);return
                path=unquote(urlsplit(self.path).path)
                prefix='/'+owner.token+'/'
                if not path.startswith(prefix):self.send_error(404);return
                name=path[len(prefix):]
                stream=None
                try:
                    if name=='model.json':
                        data=json.dumps(owner.model,allow_nan=False).encode();size=len(data);mime='application/json'
                    elif owner.pack and name==owner.pack['resource']:
                        pack=owner.pack
                        if not pack or signature(pack['path'])!=pack['signature']:self.send_error(409,'Map changed or unavailable');return
                        stream=open(pack['path'],'rb')
                        # Check the handle too, closing the replacement race.
                        import os
                        s=os.fstat(stream.fileno())
                        if (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)!=pack['signature']:self.send_error(409);return
                        size=pack['size'];mime='application/vnd.pmtiles';owner.pack_reads+=1
                    elif name in owner.assets:
                        stream=owner.assets[name].open('rb');size=owner.assets[name].stat().st_size
                        mime=mimetypes.guess_type(name)[0] or 'application/octet-stream'
                        if name.endswith('.js'):mime='application/javascript'
                    else:self.send_error(404);return
                    start,end=0,size-1;partial=False
                    value=self.headers.get('Range')
                    if value:
                        import re
                        match=re.fullmatch(r'bytes=(\d*)-(\d*)',value)
                        if not match or not any(match.groups()):self.send_error(416);return
                        left,right=match.groups()
                        if left:start=int(left);end=min(int(right),size-1) if right else size-1
                        else:start=max(0,size-int(right))
                        if start<0 or start>end or start>=size or end-start+1>MAX_RANGE:self.send_error(416);return
                        partial=True
                    elif size>MAX_RANGE:self.send_error(416,'Use bounded byte ranges');return
                    length=end-start+1
                    self.send_response(206 if partial else 200)
                    self.send_header('Content-Type',mime);self.send_header('Content-Length',str(length))
                    self.send_header('Accept-Ranges','bytes');self.send_header('Cache-Control','no-store')
                    self.send_header('X-Content-Type-Options','nosniff')
                    self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; worker-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
                    if partial:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
                    self.end_headers()
                    if body:
                        if stream:
                            stream.seek(start);remaining=length
                            while remaining:
                                chunk=stream.read(min(65536,remaining))
                                if not chunk:break
                                self.wfile.write(chunk);remaining-=len(chunk)
                        else:self.wfile.write(data[start:end+1])
                except (OSError,ValueError):
                    try:self.send_error(409,'Map resource unavailable')
                    except OSError:pass
                finally:
                    if stream:stream.close()
        self.http=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.http.daemon_threads=True
        self.origin='http://127.0.0.1:'+str(self.http.server_port);self.url=self.origin+'/'+self.token+'/'
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
        return self.url
    def close(self):
        if self.http:
            self.http.shutdown();self.http.server_close();self.thread.join(timeout=2);self.http=None
