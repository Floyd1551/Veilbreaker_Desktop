import tempfile,unittest,urllib.request,urllib.error
from pathlib import Path
from test_map_pack import pack_bytes
from veilbreaker.map_server import MapServer

class ServerTests(unittest.TestCase):
    def test_ranges_allowlist_and_lifecycle(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'index.html').write_text('test',encoding='utf-8');p=root/'test.pmtiles';p.write_bytes(pack_bytes())
            server=MapServer(root);url=server.start();server.set_pack(p)
            try:
                self.assertEqual(urllib.request.urlopen(url+'index.html').read(),b'test')
                head=urllib.request.urlopen(urllib.request.Request(url+'index.html',method='HEAD'));self.assertEqual(head.read(),b'');self.assertEqual(head.headers['Content-Length'],'4')
                with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(server.origin+'/wrong/index.html')
                for value,expected in [('bytes=0-6',b'PMTiles'),('bytes=-2',p.read_bytes()[-2:]),('bytes=127-',p.read_bytes()[127:])]:
                    r=urllib.request.urlopen(urllib.request.Request(url+'pack.pmtiles',headers={'Range':value}));self.assertEqual(r.status,206);self.assertEqual(r.read(),expected)
                for name,headers in [('missing',{}),('../index.html',{}),('pack.pmtiles',{'Range':'bytes=9-1'}),('pack.pmtiles',{'Range':'bytes=0-1,4-5'}),('index.html',{'Origin':'https://example.com'}),('index.html',{'Host':'evil.test'}),('pack.pmtiles',{'Range':'bytes=-0'}),('pack.pmtiles',{'Range':'bytes=999999999999999-'}),('%2e%2e/index.html',{})]:
                    with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(urllib.request.Request(url+name,headers=headers))
                with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(urllib.request.Request(url+'index.html',data=b'x'))
                p.write_bytes(pack_bytes()+b'changed')
                with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(url+'pack.pmtiles')
            finally:server.close()
            with self.assertRaises(OSError):urllib.request.urlopen(url,timeout=1)
