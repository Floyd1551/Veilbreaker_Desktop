"""Exercise a selected survey receiver through a real terrain assessment."""
import json
import os
import tempfile
import unittest
import uuid
import zipfile
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
try:
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
except ImportError:
    rasterio = None

from veilbreaker.cell_context import load_context
from veilbreaker.core import AppConfig
from veilbreaker.map_sources import load_survey_map_data
from veilbreaker.map_ui import MapWindow
from veilbreaker.nearby_structures_ui import _search_job, _verify_job, receiver_endpoint_context
from veilbreaker.path_assessment_ui import assessment_job
from veilbreaker.regional_packs import RegionalPackStore
from veilbreaker.survey import create_survey, export_session
from veilbreaker.survey_mobile_evidence import attach_mobile_survey


@unittest.skipIf(rasterio is None, 'terrain dependency unavailable')
class StructureWorkflowIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_selected_gps_to_structure_terrain_assessment_reopens_and_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = AppConfig(data_dir=tmp)
            survey_path = create_survey(config, 'Field survey', [{}])['survey_path']
            capture = json.loads(Path('examples/android-cellular-v1.json').read_text(encoding='utf-8'))
            capture['observations'][0]['location'] = dict(
                status='available', source='phone', provider='gps', fix_utc=capture['created_utc'],
                latitude_deg=32.995, longitude_deg=-96.999, horizontal_accuracy_m=5,
                fix_age_ms=1000, mock=False)
            mobile_path = root / 'mobile.json'
            mobile_path.write_text(json.dumps(dict(format='veilbreaker.mobile.survey', schema_version=1,
                survey_id=str(uuid.uuid4()), name='Mobile', created_utc=capture['created_utc'], lifecycle='open',
                points=[dict(attached_utc=capture['created_utc'], capture=capture)])), encoding='utf-8')
            attach_mobile_survey(config, survey_path, mobile_path)

            structures = root / 'structures.geojson'
            structures.write_text(json.dumps(dict(type='FeatureCollection', features=[dict(type='Feature',
                geometry=dict(type='Point', coordinates=[-96.991, 32.995]),
                properties=dict(structure_id='fixture-structure', owner='Fixture owner', height_agl_m=35))])), encoding='utf-8')
            store = RegionalPackStore(config.root / 'regional-packs')
            pack = store.install_local('structures', structures, dict(name='Fixture structures',
                source='Fixture registry', source_date='2026-11-18', license='Test fixture',
                bounds_wgs84=[-97.1, 32.9, -96.9, 33.1]), lambda: False)

            dem = root / 'terrain.tif'
            with rasterio.open(dem, 'w', driver='GTiff', width=100, height=100, count=1, dtype='float32',
                               crs='EPSG:4326', transform=from_origin(-97, 33, .0001, .0001), nodata=-9999) as dataset:
                dataset.write(np.full((100, 100), 100, dtype='float32'), 1)

            model = load_survey_map_data(config, survey_path)
            row = next(row for row in model['rows'] if row.get('mobile_capture_id'))
            window = MapWindow(None, model, None, enable_web=False, restore_pack=False, config=config)
            try:
                window.select_feature(row['id'])
                self.assertTrue(window.structures_button.isEnabled())
                receiver = dict(window.selected)
                self.assertTrue(receiver['quality']['qualified'])
                result = _search_job(config.root / 'regional-packs', receiver['latitude_deg'],
                                     receiver['longitude_deg'], 10, lambda: False, lambda _: None)['result']
                self.assertEqual(len(result['candidates']), 1)
                candidate = result['candidates'][0]
                self.assertEqual(candidate['sha256'], pack['sha256'])
                verified = _verify_job(config.root / 'regional-packs', candidate, 'assess',
                                       lambda: False, lambda _: None)['candidate']
                context = receiver_endpoint_context(receiver, verified)
                self.assertEqual(context['observation']['position_source'], 'qualified_location')
                self.assertEqual(context['candidate']['selection_method'], 'operator_selected')
                assessment = assessment_job(str(dem), dict(source='Synthetic terrain', vertical_datum='NAVD88', units='m'),
                                            context, 2, 10, 1800, 4 / 3, lambda: False, lambda _: None)
                self.assertGreater(len(assessment['terrain']['distances_m']), 3)
                self.assertTrue(all(elevation == 100 for elevation in assessment['terrain']['elevations_m']))
                self.assertEqual(assessment['terrain']['endpoints'], [[-96.999, 32.995], [-96.991, 32.995]])
                self.assertIn('saved', window.save_structure_assessment(assessment))
            finally:
                window.close()

            reopened = load_context(config, survey_path)
            self.assertFalse(reopened['stale'])
            saved = reopened['context']['assessments'][0]
            self.assertEqual(saved['endpoint_context']['candidate']['structure_id'], 'fixture-structure')
            self.assertEqual(saved['endpoint_context']['candidate']['source'], 'Fixture registry')
            self.assertEqual(saved['terrain']['dem']['source'], 'Synthetic terrain')
            with zipfile.ZipFile(export_session(config, survey_path)) as archive:
                exported = json.loads(archive.read('cell-context.json'))['assessments'][0]
                report = archive.read('survey_report.html').decode('utf-8')
                self.assertEqual(exported['terrain']['endpoints'], saved['terrain']['endpoints'])
                self.assertIn('fixture-structure', report)
                self.assertIn('Fixture registry', report)
                self.assertIn('serving cell', report.lower())


if __name__ == '__main__':
    unittest.main()
