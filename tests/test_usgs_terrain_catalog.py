import io
import json
import unittest

from veilbreaker.usgs_terrain_catalog import search_terrain_products, plan_terrain_products


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class TerrainCatalogTests(unittest.TestCase):
    def test_all_state_starters_fit_the_search_limit_despite_float_rounding(self):
        from veilbreaker.conus_terrain_areas import STATE_CENTERS, starter_bounds
        self.assertEqual(len(STATE_CENTERS),48)
        for state in STATE_CENTERS:
            with self.subTest(state=state):
                result=search_terrain_products(starter_bounds(state),opener=lambda request,timeout:Response(b'{"items": [], "total": 0}'))
                self.assertEqual(result['total'],0)

    def test_plan_finds_adjacent_tiles_and_suppresses_older_duplicates(self):
        def tile(name,date,bounds,size=100):
            return dict(title=name,source_date=date,reported_bounds_wgs84=bounds,bytes=size,url='https://example.com/'+name+'.tif')
        products=[tile('n35w087 old','2020-01-01',[0,0,1,1]),tile('n35w087 new','2026-01-01',[0,0,1,1]),
                  tile('n35w088 new','2025-01-01',[1,0,2,1])]
        plan=plan_terrain_products([0,0,2,1],products)
        self.assertEqual({p['title'] for p in plan['products']},{'n35w087 new','n35w088 new'})
        self.assertEqual(plan['duplicate_count'],1)
        self.assertEqual(plan['gap_count'],0)
        self.assertEqual(plan['bytes'],200)

    def test_plan_reports_gaps_unknown_bounds_and_empty_results(self):
        products=[dict(title='known',source_date='2026-01-01',reported_bounds_wgs84=[0,0,1,1],bytes=100),
                  dict(title='unknown',source_date='2026-01-01',reported_bounds_wgs84=None,bytes=100)]
        plan=plan_terrain_products([0,0,2,1],products)
        self.assertEqual(plan['gap_count'],1)
        self.assertEqual(plan['unknown_bounds'],1)
        self.assertEqual(plan['gaps'],[[1.0,0.0,2.0,1.0]])

    def test_nearby_extent_is_not_discarded_when_it_covers_an_edge(self):
        products=[dict(title='new',source_date='2026-01-01',reported_bounds_wgs84=[0,0,1,1],bytes=100),
                  dict(title='old',source_date='2025-01-01',reported_bounds_wgs84=[0,0,1.001,1],bytes=100)]
        plan=plan_terrain_products([0,0,1.001,1],products)
        self.assertEqual(plan['gap_count'],0)
        self.assertIn('old',[item['title'] for item in plan['products']])

    def test_suggestion_prefers_newer_tile_when_old_extra_edge_is_already_covered(self):
        products=[dict(title='south',source_date='2026-01-01',reported_bounds_wgs84=[0,0,2,1.0005],bytes=100),
                  dict(title='north new',source_date='2026-01-01',reported_bounds_wgs84=[0,0.9995,2,2],bytes=100),
                  dict(title='north old',source_date='2019-01-01',reported_bounds_wgs84=[0,0.9994,2,2],bytes=1)]
        plan=plan_terrain_products([0,0,2,2],products)
        self.assertEqual(plan['gap_count'],0)
        self.assertEqual({item['title'] for item in plan['products']},{'south','north new'})

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

    def test_catalog_indicates_incomplete_page_when_total_exceeds_returned(self):
        payload={'total': 200, 'items': []}
        result=search_terrain_products([0,0,1,1],opener=lambda *args,**kwargs:Response(json.dumps(payload).encode()))
        self.assertTrue(result['truncated'])


if __name__ == '__main__':
    unittest.main()
