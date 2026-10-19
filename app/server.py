"""Private Tinfoil connection. Secrets never enter MCP, URLs or logs."""
import hmac
import json
import os
import secrets
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get('DATA_DIR', ROOT / '.data'))
PORT = os.environ.get('PORT', '18803')
LOCK = threading.RLock()
TYPES = {'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript'}
def csv(k): return {v.strip().lower() for v in os.environ.get(k,'').split(',') if v.strip()}
HOSTS = csv('WIZARD_TRUSTED_HOSTS') | {f'127.0.0.1:{PORT}',f'localhost:{PORT}',f'wizard-tinfoil:{PORT}'}
ORIGINS = csv('WIZARD_TRUSTED_ORIGINS') | {'http://'+h for h in HOSTS if h.startswith(('localhost:','127.0.0.1:'))}

def atomic(name, obj):
    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DATA,0o700)
    fd, tmp = tempfile.mkstemp(dir=DATA, prefix='.pending-')
    try:
        with os.fdopen(fd,'w') as f:
            os.fchmod(f.fileno(),0o600)
            json.dump(obj,f); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, DATA/name)
        d = os.open(DATA,os.O_DIRECTORY)
        try: os.fsync(d)
        finally: os.close(d)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def stored():
    try: return json.loads((DATA/'connection.json').read_text())
    except FileNotFoundError: return None

def status():
    # Atomic replace makes this a safe snapshot; never wait behind network verification.
    s = stored()
    return {'contract':'wizard.ai-connection/1','provider':'tinfoil','name':'Tinfoil','status':'connected' if s and s.get('authenticated') else 'not_connected','credentialStored':bool(s),'credentialVerified':bool(s and s.get('authenticated')),'plan':None,'account':None,'usage':None,'error':None,'models':s['models'] if s else [],'verification':{'mode':'official-sdk-attestation','sdk':'tinfoil==0.14.0','lastVerifiedAt':s['verifiedAt'] if s else None},'chatIntegration':'not_registered'}

def worker(action, key, payload=None):
    # Kill on timeout; no upstream exception/headers/body may reach logs or clients.
    result = subprocess.run([sys.executable,str(ROOT/'app/provider.py'),action],input=json.dumps({'key':key,'payload':payload}),text=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=45 if action=='verify' else 180)
    if result.returncode: raise ValueError('Verification or provider request failed. Saved connection unchanged.')
    return json.loads(result.stdout)

def key_ok(k): return isinstance(k,str) and 16 <= len(k) <= 512 and all(33<=ord(c)<=126 for c in k)

TOOLS = [{'name':'connection_status','description':'Read Tinfoil connection and attestation status. Never returns credentials. To connect, the owner enters a key in the Tinfoil app; do not request keys in chat.','inputSchema':{'type':'object','properties':{},'additionalProperties':False},'annotations':{'readOnlyHint':True}}]
def rpc(m):
    i=m.get('id'); method=m.get('method'); p=m.get('params') or {}
    if 'id' not in m: return None
    if method=='initialize': r={'protocolVersion':'2025-06-18','capabilities':{'tools':{}},'serverInfo':{'name':'wizard-tinfoil','version':'0.1.0'}}
    elif method=='tools/list': r={'tools':TOOLS}
    elif method=='ping': r={}
    elif method=='tools/call' and p.get('name')=='connection_status' and not p.get('arguments'):
        s=status(); r={'content':[{'type':'text','text':json.dumps(s)}],'structuredContent':s,'isError':False}
    else: return {'jsonrpc':'2.0','id':i,'error':{'code':-32602,'message':'Unknown method, tool or arguments.'}}
    return {'jsonrpc':'2.0','id':i,'result':r}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def send(self,code,obj=None,kind='application/json'):
        b=obj if isinstance(obj,bytes) else json.dumps(obj).encode()
        self.send_response(code)
        for k,v in {'Content-Type':kind,'Content-Length':str(len(b)),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'self' "+' '.join(sorted(ORIGINS))}.items(): self.send_header(k,v)
        self.end_headers()
        if self.command!='HEAD': self.wfile.write(b)
    def refused(self,path,write=False):
        if self.headers.get('Host','').lower() not in HOSTS: self.send(403,{'error':'Untrusted host.'}); return True
        origin=self.headers.get('Origin','').lower()
        if origin and origin not in ORIGINS or self.headers.get('Sec-Fetch-Site')=='cross-site': self.send(403,{'error':'Cross-site request refused.'}); return True
        if path=='/mcp' or path=='/api/connection' or path.startswith('/v1/'):
            if any(k.lower() in {'tailscale-user-login','x-forwarded-for','forwarded','x-real-ip'} or k.lower().startswith('cf-') for k in self.headers): self.send(403,{'error':'Box-only endpoint.'}); return True
        if write and path.startswith('/api/') and (origin not in ORIGINS or self.headers.get('X-Wizard-Request')!='1'): self.send(403,{'error':'Use the trusted connection page.'}); return True
        if path.startswith('/v1/'):
            token=json.loads((DATA/'gateway-token.json').read_text())['token']
            if origin or not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+token): self.send(401,{'error':'Local gateway credential required.'}); return True
        return False
    def do_HEAD(self): self.do_GET()
    def do_GET(self):
        path=urlsplit(self.path).path
        if self.refused(path): return
        if path=='/healthz': return self.send(200,{'ok':True,'app':'wizard-tinfoil','version':'0.1.0'})
        if path=='/api/connection': return self.send(200,status())
        if path=='/v1/models': return self.send(200,{'object':'list','data':[{'id':x,'object':'model','owned_by':'tinfoil'} for x in status()['models']]})
        if path=='/openapi.json': return self.send(200,(ROOT/'openapi.json').read_bytes())
        name='index.html' if path=='/' else path[1:]
        if '/' not in name and not name.startswith('.') and Path(name).suffix in TYPES and (ROOT/'web'/name).is_file(): return self.send(200,(ROOT/'web'/name).read_bytes(),TYPES[Path(name).suffix])
        self.send(404,{'error':'Not found.'})
    def do_POST(self):
        path=urlsplit(self.path).path
        if self.refused(path,True): return
        try:
            if self.headers.get('Content-Type','').split(';')[0]!='application/json': return self.send(415,{'error':'Use application/json.'})
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=1048576: return self.send(413,{'error':'Invalid body size.'})
            body=json.loads(self.rfile.read(n))
            if not isinstance(body,dict): raise ValueError()
            if path=='/mcp':
                r=rpc(body); return self.send(202 if r is None else 200,r)
            if path=='/api/connect':
                if set(body)!={'apiKey'} or not key_ok(body['apiKey']): return self.send(400,{'error':'Enter a valid API key (16–512 non-space ASCII characters).'})
                with LOCK:
                    result=worker('verify',body['apiKey'])
                    atomic('connection.json',{'key':body['apiKey'],'authenticated':False,**result})
                return self.send(200,status())
            if path=='/api/test':
                if body: raise ValueError()
                with LOCK:
                    s=stored()
                    if not s: return self.send(409,{'error':'Connect an API key first.'})
                    result=worker('verify',s['key']); atomic('connection.json',{**s,**result})
                return self.send(200,status())
            if path=='/api/disconnect':
                if body: raise ValueError()
                with LOCK:
                    (DATA/'connection.json').unlink(missing_ok=True)
                    atomic('gateway-token.json',{'token':secrets.token_urlsafe(48)})
                return self.send(200,status())
            if path=='/v1/chat/completions':
                s=stored()
                if not s: return self.send(409,{'error':'Tinfoil is not connected.'})
                if not isinstance(body.get('messages'),list) or not body['messages'] or body.get('model') not in s['models']: return self.send(400,{'error':'Choose a connected Tinfoil model and supply messages.'})
                # SDK owns transport; callers cannot override enclave, URL, headers or key.
                allowed={'model','messages','temperature','top_p','max_tokens','max_completion_tokens','tools','tool_choice','parallel_tool_calls','stop','response_format','stream','stream_options','seed','presence_penalty','frequency_penalty'}
                if set(body)-allowed or body.get('stream') not in (None,False,True): raise ValueError()
                result=worker('infer',s['key'],body)
                with LOCK:
                    current=stored()
                    if current and hmac.compare_digest(current['key'],s['key']): atomic('connection.json',{**current,'authenticated':True})
                if body.get('stream'):
                    return self.send(200,result['sse'].encode(),'text/event-stream')
                return self.send(200,result)
            self.send(404,{'error':'Not found.'})
        except (ValueError,TypeError,KeyError,json.JSONDecodeError): self.send(400,{'error':'Invalid request or provider verification failed. Saved connection unchanged.'})
        except subprocess.TimeoutExpired: self.send(504,{'error':'Provider verification timed out. Saved connection unchanged.'})
        except Exception: self.send(503,{'error':'Connection unavailable. No unverified fallback was used.'})

def initialize():
    os.umask(0o077)
    DATA.mkdir(mode=0o700,parents=True,exist_ok=True); os.chmod(DATA,0o700)
    if not (DATA/'gateway-token.json').exists(): atomic('gateway-token.json',{'token':secrets.token_urlsafe(48)})

if __name__=='__main__':
    initialize()
    ThreadingHTTPServer((os.environ.get('BIND','0.0.0.0'),int(PORT)),Handler).serve_forever()
