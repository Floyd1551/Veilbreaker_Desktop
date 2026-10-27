import io
import json
import unittest

from veilbreaker.usgs_terrain_catalog import search_terrain_products


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class TerrainCatalogTests(unittest.TestCase):
    def test_regional_search_retains_provider_dates_size_and_url(self):
        payload = {'total': 2, 'items': [
            dict(title='USGS 1/3 Arc Second n33w097 20260406', publicationDate='2026-04-06',
                 format='GeoTIFF', sizeInBytes=441789691,
                 downloadURL='https://prd-tnm.s3.amazonaws.com/elevation/n33w097.tif'),
            dict(title='Unsupported', publicationDate='2026-04-06', format='IMG', sizeInBytes=1,
                 downloadURL='https://prd-tnm.s3.amazonaws.com/other.img')]}
        seen = []
        def opener(request, timeout):
            seen.append(request.full_url)
            return Response(json.dumps(payload).encode())
        result = search_terrain_products([-97.1, 32.8, -96.8, 33.1], opener=opener)
        self.assertEqual(len(result['products']), 1)
        self.assertEqual(result['products'][0]['source_date'], '2026-04-06')
        self.assertEqual(result['products'][0]['bytes'], 441789691)
        self.assertEqual(result['products'][0]['url'], 'https://prd-tnm.s3.amazonaws.com/elevation/n33w097.tif')
        self.assertIn('tnmaccess.nationalmap.gov/api/v1/products?', seen[0])
        self.assertEqual(result['total'], 2)

    def test_rejects_global_area_and_untrusted_product_links(self):
        with self.assertRaises(ValueError):
            search_terrain_products([-180, -90, 180, 90], opener=lambda *args, **kwargs: Response(b'{}'))
        payload = {'total': 1, 'items': [dict(title='Bad', publicationDate='2026-01-01', format='GeoTIFF',
                                              sizeInBytes=100, downloadURL='http://example.org/remote.tif')]}
        result = search_terrain_products([-97.1, 32.8, -96.8, 33.1],
                                         opener=lambda *args, **kwargs: Response(json.dumps(payload).encode()))
        self.assertEqual(result['products'], [])


if __name__ == '__main__':
    unittest.main()
