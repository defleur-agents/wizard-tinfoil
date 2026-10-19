"""Controlled transport doubles. These tests are NOT enclave security proof."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
s=load('connection_server',ROOT/'app/server.py')
p=load('provider_worker',ROOT/'app/provider.py')
KEY='synthetic-test-key-not-a-real-secret'
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();s.DATA=Path(cls.temp.name);s.initialize()
        cls.http=s.ThreadingHTTPServer(('127.0.0.1',0),s.Handler)
        cls.port=cls.http.server_address[1];cls.base=f'http://127.0.0.1:{cls.port}'
        s.HOSTS.add(f'127.0.0.1:{cls.port}');s.ORIGINS.add(cls.base)
        threading.Thread(target=cls.http.serve_forever,daemon=True).start()
    @classmethod
    def tearDownClass(cls):cls.http.shutdown();cls.http.server_close();cls.temp.cleanup()
    def call(self,path,body=None,headers=None):
        h={'Content-Type':'application/json','Origin':self.base,'X-Wizard-Request':'1'};h.update(headers or {})
        req=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers=h)
        try:
            with urllib.request.urlopen(req,timeout=5) as r:return r.status,r.read()
        except urllib.error.HTTPError as e:return e.code,e.read()
    def test_01_connect_persist_error_disconnect(self):
        with patch.object(s,'worker',return_value={'models':['test-model'],'verifiedAt':'2026-10-19T00:00:00+00:00'}):
            code,body=self.call('/api/connect',{'apiKey':KEY});self.assertEqual(code,200);self.assertNotIn(KEY.encode(),body)
            self.assertTrue(json.loads(body)['credentialStored']);self.assertEqual(json.loads(body)['status'],'not_connected')
        file=s.DATA/'connection.json';before=file.read_bytes();self.assertEqual(file.stat().st_mode&0o777,0o600)
        self.assertEqual(s.DATA.stat().st_mode&0o777,0o700)
        # Reload service module simulates process restart with the same data.
        other=load('restarted',ROOT/'app/server.py');other.DATA=s.DATA
        self.assertTrue(other.status()['credentialStored'])
        with patch.object(s,'worker',side_effect=ValueError(KEY)):
            code,body=self.call('/api/connect',{'apiKey':KEY+'bad'});self.assertEqual(code,400);self.assertNotIn(KEY.encode(),body)
            self.assertEqual(file.read_bytes(),before)
        old=(s.DATA/'gateway-token.json').read_bytes()
        self.assertEqual(self.call('/api/disconnect',{})[0],200)
        self.assertFalse(file.exists());self.assertNotEqual(old,(s.DATA/'gateway-token.json').read_bytes())
        self.assertEqual(other.status()['status'],'not_connected')
    def test_02_guards(self):
        for header in ['tailscale-user-login','x-forwarded-for','forwarded','x-real-ip','cf-ray']:
            for path in ['/mcp','/api/connection','/v1/models']:
                self.assertEqual(self.call(path,{'id':1,'method':'tools/list'} if path=='/mcp' else None,{header:'test'})[0],403)
        self.assertEqual(self.call('/api/disconnect',{}, {'Origin':'https://evil.invalid'})[0],403)
        self.assertEqual(self.call('/api/disconnect',{}, {'Host':'evil.invalid'})[0],403)
        self.assertEqual(self.call('/api/disconnect',{}, {'Origin':''})[0],403)
        self.assertEqual(self.call('/api/disconnect',{}, {'Sec-Fetch-Site':'cross-site'})[0],403)
        self.assertEqual(self.call('/v1/models',None,{'Origin':''})[0],401)
        self.assertEqual(self.call('/connection.json')[0],404)
    def test_03_mcp_and_gateway(self):
        code,b=self.call('/mcp',{'jsonrpc':'2.0','id':1,'method':'tools/list'});self.assertEqual(code,200)
        self.assertEqual([t['name'] for t in json.loads(b)['result']['tools']],['connection_status'])
        code,b=self.call('/mcp',{'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'connection_status'}});self.assertEqual(code,200);self.assertNotIn(KEY.encode(),b)
        token=json.loads((s.DATA/'gateway-token.json').read_text())['token'];h={'Origin':'','Authorization':'Bearer '+token}
        self.assertEqual(self.call('/v1/models',None,h)[0],200)
        self.assertEqual(self.call('/v1/chat/completions',{'model':'test-model','messages':[]},h)[0],409)
        s.atomic('connection.json',{'key':KEY,'models':['test-model'],'verifiedAt':'test'})
        with patch.object(s,'worker',return_value={'object':'chat.completion','choices':[]}):
            self.assertEqual(self.call('/v1/chat/completions',{'model':'test-model','messages':[{'role':'user','content':'synthetic'}]},h)[0],200)
            self.assertEqual(self.call('/v1/chat/completions',{'model':'test-model','messages':[{}],'base_url':'https://evil.invalid'},h)[0],400)
        self.call('/api/disconnect',{})
    def test_04_sdk_fail_closed(self):
        calls=[]
        def blocked(**kwargs):calls.append('attestation');raise RuntimeError('simulated attestation failure')
        for action in ['verify','infer']:
            with self.assertRaises(RuntimeError):p.run(action,{'key':KEY,'payload':{'model':'test-model','messages':[]}},factory=blocked)
        self.assertEqual(calls,['attestation','attestation'])
    def test_05_sdk_verified_transport_used(self):
        from types import SimpleNamespace as NS
        events=[]
        class Client:
            def __init__(self,**kw):
                events.append('verified-constructor')
                self.client=NS(models=NS(list=lambda: NS(data=[NS(id='test-model')])),close=lambda: events.append('close'))
                self.chat=NS(completions=NS(create=lambda **kw: NS(model_dump=lambda **kw:{'object':'chat.completion'})))
        self.assertEqual(p.run('verify',{'key':KEY},Client)['models'],['test-model'])
        self.assertEqual(p.run('infer',{'key':KEY,'payload':{'model':'test-model','messages':[]}},Client)['object'],'chat.completion')
        self.assertEqual(events,['verified-constructor','close','verified-constructor','close'])
if __name__=='__main__':unittest.main(verbosity=2)
