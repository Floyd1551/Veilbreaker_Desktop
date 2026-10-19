import tempfile,unittest,urllib.request,urllib.error
from pathlib import Path
from test_map_pack import pack_bytes
from veilbreaker.map_server import MapServer

class ServerTests(unittest.TestCase):
    def test_ranges_allowlist_and_lifecycle(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'index.html').write_text('test',encoding='utf-8');p=root/'test.pmtiles';p.write_bytes(pack_bytes())
            server=MapServer(root);url=server.start();resource=server.set_pack(p)['resource']
            try:
                self.assertEqual(urllib.request.urlopen(url+'index.html').read(),b'test')
                head=urllib.request.urlopen(urllib.request.Request(url+'index.html',method='HEAD'));self.assertEqual(head.read(),b'');self.assertEqual(head.headers['Content-Length'],'4')
                with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(server.origin+'/wrong/index.html')
                for value,expected in [('bytes=0-6',b'PMTiles'),('bytes=-2',p.read_bytes()[-2:]),('bytes=127-',p.read_bytes()[127:])]:
                    r=urllib.request.urlopen(urllib.request.Request(url+resource,headers={'Range':value}));self.assertEqual(r.status,206);self.assertEqual(r.read(),expected)
                for name,headers in [('missing',{}),('../index.html',{}),(resource,{'Range':'bytes=9-1'}),(resource,{'Range':'bytes=0-1,4-5'}),('index.html',{'Origin':'https://example.com'}),('index.html',{'Host':'evil.test'}),(resource,{'Range':'bytes=-0'}),(resource,{'Range':'bytes=999999999999999-'}),('%2e%2e/index.html',{})]:
                    with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(urllib.request.Request(url+name,headers=headers))
                with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(urllib.request.Request(url+'index.html',data=b'x'))
                p.write_bytes(pack_bytes()+b'changed')
                with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(url+resource)
            finally:server.close()
            with self.assertRaises(OSError):urllib.request.urlopen(url,timeout=1)

    def test_pack_import_uses_new_resource_identity(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'a.pmtiles';p.write_bytes(pack_bytes());q=root/'b.pmtiles';q.write_bytes(pack_bytes()+b'other')
            server=MapServer(root);url=server.start()
            try:
                a=server.set_pack(p)['resource'];b=server.set_pack(q)['resource']
                self.assertNotEqual(a,b)
                with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(url+a)
                self.assertEqual(urllib.request.urlopen(url+b).read(),q.read_bytes())
            finally:server.close()
