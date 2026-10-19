import json,struct,tempfile,unittest,gzip
from pathlib import Path
from veilbreaker.map_pack import inspect_pack

def pack_bytes(metadata=None):
    meta=json.dumps(metadata or {'name':'Synthetic test map','attribution':'Synthetic fixture — no geographic data','vector_layers':[{'id':'water'},{'id':'roads'},{'id':'buildings'}]}).encode()
    # Empty water MVT layer, version 2, extent 4096. Root contains zoom-zero tile.
    tile=b'\x1a\x0c\x0a\x05water\x28\x80\x20\x78\x02'
    root=bytes([1,0,1,len(tile),1]);h=bytearray(127);h[:8]=b'PMTiles\x03'
    struct.pack_into('<8Q',h,8,127,len(root),127+len(root),len(meta),0,0,127+len(root)+len(meta),len(tile))
    h[96:102]=bytes([1,1,1,1,0,0]);struct.pack_into('<4i',h,102,-1800000000,-850000000,1800000000,850000000)
    return bytes(h)+root+meta+tile

class PackTests(unittest.TestCase):
    def test_valid_and_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.pmtiles';p.write_bytes(pack_bytes());self.assertEqual(inspect_pack(p)['name'],'Synthetic test map')
            original=p.read_bytes()
            for index,value in [(0,0),(7,2),(97,4),(98,4),(99,2)]:
                b=bytearray(original);b[index]=value;p.write_bytes(b)
                with self.assertRaises(ValueError):inspect_pack(p)
            p.write_bytes(original[:130])
            with self.assertRaises(ValueError):inspect_pack(p)
            p.write_bytes(pack_bytes({'vector_layers':[{'id':'random'}]}))
            with self.assertRaises(ValueError):inspect_pack(p)

    def test_bounded_metadata_and_offsets(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.pmtiles'
            raw=bytearray(pack_bytes());struct.pack_into('<Q',raw,24,2**63);p.write_bytes(raw)
            with self.assertRaises(ValueError):inspect_pack(p)
            raw=bytearray(pack_bytes());compressed=gzip.compress(b' '* (1024*1024+1));offset=struct.unpack_from('<Q',raw,24)[0]
            raw=raw[:offset]+compressed;raw[97]=2;struct.pack_into('<Q',raw,32,len(compressed));struct.pack_into('<2Q',raw,56,0,0);p.write_bytes(raw)
            with self.assertRaises(ValueError):inspect_pack(p)
            p.unlink()
            with self.assertRaises(OSError):inspect_pack(p)

    def test_vendored_asset_integrity(self):
        import hashlib
        root=Path('src/veilbreaker/assets/maps')
        manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        for asset in manifest['files']:
            self.assertEqual(hashlib.sha256((root/asset['file']).read_bytes()).hexdigest(),asset['sha256'],asset['file'])

    def test_malformed_layer_ids_raise_validation_error(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.pmtiles';p.write_bytes(pack_bytes({'vector_layers':[{'id':[]}]}))
            with self.assertRaises(ValueError):inspect_pack(p)
