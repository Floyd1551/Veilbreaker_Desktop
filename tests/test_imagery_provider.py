import json
import unittest
from unittest.mock import patch
from veilbreaker import imagery_provider as provider


class ProviderTests(unittest.TestCase):
    def test_export_request_retains_returned_extent_and_unknown_capture_date(self):
        replies = [json.dumps({'copyrightText':'USGS / USDA'}).encode(),
                   json.dumps({'href':'https://imagery.nationalmap.gov/arcgis/rest/directories/arcgisoutput/test.jpg',
                               'extent':dict(xmin=-10800000,ymin=3700000,xmax=-10700000,ymax=3800000,
                                             spatialReference={'wkid':3857})}).encode(), b'image']
        with patch.object(provider, '_read', side_effect=replies) as read:
            raw, meta = provider.fetch_naip([-97,32,-96,33], lambda:False)
        self.assertEqual(raw,b'image')
        self.assertEqual(meta['bounds'],[-10800000,3700000,-10700000,3800000])
        self.assertIsNone(meta['imagery_date'])
        self.assertIn('bboxSR=4326', read.call_args_list[1].args[0])
        self.assertIn('size=1600%2C1000', read.call_args_list[1].args[0])

    def test_cancel_and_untrusted_provider_url(self):
        with self.assertRaisesRegex(ValueError,'cancel'):
            provider.fetch_naip([-97,32,-96,33], lambda:True)
        with self.assertRaises(ValueError):
            provider.check_url('https://example.com/map.jpg')
        with self.assertRaises(ValueError):
            provider.check_url('http://imagery.nationalmap.gov/map.jpg')
        with patch.object(provider,'_read',return_value=b'{"error":{"message":"Unavailable"}}'):
            with self.assertRaisesRegex(ValueError,'Unavailable'):
                provider.fetch_naip([-97,32,-96,33],lambda:False)

    def test_stream_limit(self):
        class Response:
            headers = {}
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,n): return b'x'*n
        with patch.object(provider.OPENER,'open',return_value=Response()):
            with self.assertRaisesRegex(ValueError,'size'):
                provider._read(provider.SERVICE,lambda:False,32)
