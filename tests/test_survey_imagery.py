import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage, QColor
from PySide6.QtWidgets import QApplication
from veilbreaker.core import AppConfig
from veilbreaker import survey_imagery as im


def image_bytes(width=600, height=400):
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor('white'))
    out = QBuffer()
    out.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(out, 'PNG')
    return bytes(out.data())


def metadata():
    return dict(schema_version=1, bounds=[-97, 32, -96, 33], crs='EPSG:4326',
                source='Fixture aerial', attribution='Synthetic <test>', imagery_date=None)


class ImageryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_validation_and_projection(self):
        self.assertEqual(im.validate_metadata(metadata())['crs'], 'EPSG:4326')
        for bounds in ([0, 0, 0, 1], [0, 2, 1, 1], [float('nan'), 0, 1, 1], [-181, 0, 1, 1]):
            with self.assertRaises(ValueError):
                im.validate_metadata(dict(metadata(), bounds=bounds))
        with self.assertRaises(ValueError):
            im.validate_metadata(dict(metadata(), crs='EPSG:9999'))
        self.assertEqual(im.pixel_position(-96.5, 32.5, metadata(), 600, 400), (300, 200))
        with self.assertRaises(ValueError):
            im.decode_image(b'not an image')
        with self.assertRaises(ValueError):
            im.decode_image(image_bytes(2049, 2))

    def test_render_and_outside_extent(self):
        points = [dict(number=1, lon=-96.5, lat=32.5, run_id='r', label='Center')]
        result = im.render_image(image_bytes(), metadata(), points)
        image = QImage.fromData(result)
        self.assertLessEqual(image.width(), 1440)
        self.assertNotEqual(image.pixelColor(image.width()//2+8, image.height()//2+4), QColor('white'))
        with self.assertRaisesRegex(ValueError, 'outside'):
            im.render_image(image_bytes(), metadata(), [dict(points[0], lon=-95)])

    def test_storage_integrity_staleness_and_failed_replacement(self):
        with tempfile.TemporaryDirectory() as folder:
            config = AppConfig(data_dir=folder)
            journal = config.root / 'surveys' / 'survey-test.json'
            journal.parent.mkdir(parents=True)
            journal.write_text(json.dumps(dict(schema_version=1, survey_id='survey-test',
                status='planned', steps=[], name='Test')), encoding='utf-8')
            with patch.object(im, 'survey_points', return_value=[]):
                saved = im.save_imagery(config, journal, image_bytes(), metadata(), [])
                context = im.report_context(config, journal)
                self.assertTrue(context['image'])
                self.assertFalse(context['stale'])
                original = journal.read_text(encoding='utf-8')
                changed = json.loads(original)
                changed['steps'] = [dict(run_id='new-no-gps', label='New')]
                journal.write_text(json.dumps(changed),encoding='utf-8')
                self.assertTrue(im.report_context(config,journal)['stale'])
                journal.write_text(original,encoding='utf-8')
                before = journal.read_bytes()
                with self.assertRaises(ValueError):
                    im.save_imagery(config, journal, b'bad', metadata(), [])
                self.assertEqual(journal.read_bytes(), before)
                self.assertEqual(im.load_imagery(config, journal)['sha256'], saved['sha256'])
            with patch.object(im, 'survey_points', return_value=[dict(number=1, run_id='new', lat=32.5, lon=-96.5)]):
                self.assertTrue(im.report_context(config, journal)['stale'])
            root = im.asset_directory(config, journal, saved['asset_id'])
            (root / 'overlay.png').write_bytes(b'corrupt')
            self.assertIn('unavailable', im.report_context(config, journal)['warning'].lower())
            with self.assertRaises(ValueError):
                im.asset_directory(config, journal, '../escape')

    def test_portable_export_contains_verified_assets_and_embedded_image(self):
        import zipfile
        from veilbreaker.survey import export_session
        from veilbreaker.evidence import verify_bundle
        from veilbreaker.report_viewer import OfflineReportBrowser
        from PySide6.QtCore import QUrl
        import base64
        with tempfile.TemporaryDirectory() as folder:
            config = AppConfig(data_dir=folder)
            journal = config.root/'surveys'/'survey-export.json'
            journal.parent.mkdir(parents=True)
            journal.write_text(json.dumps(dict(schema_version=1,survey_id='survey-export',
                site_id='Test',status='planned',steps=[],name='Export')),encoding='utf-8')
            with patch.object(im,'survey_points',return_value=[]):
                im.save_imagery(config,journal,image_bytes(),metadata(),[])
                target = export_session(config,journal)
            self.assertEqual(verify_bundle(target)['status'],'verified')
            with zipfile.ZipFile(target) as archive:
                png = archive.read('survey-map.png')
                html = archive.read('survey_report.html')
                self.assertIn(base64.b64encode(png),html)
                self.assertIn('survey-map-source.image',archive.namelist())
            browser = OfflineReportBrowser()
            decoded = browser.loadResource(2,QUrl('data:image/png;base64,'+base64.b64encode(png).decode()))
            self.assertFalse(decoded.isNull())
            self.assertTrue(browser.loadResource(2,QUrl('https://example.com/map.png')).isEmpty())
            self.assertTrue(browser.loadResource(2,QUrl('file:///private.png')).isEmpty())
