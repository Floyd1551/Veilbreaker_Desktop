import tempfile
import unittest
import zipfile
import re
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QImage, QColor
from PySide6.QtWidgets import QApplication
from veilbreaker.core import AppConfig
from veilbreaker.evidence import verify_bundle
from veilbreaker.survey import create_survey, export_session, read_session, set_lifecycle
from veilbreaker.survey_observations import add_observation
from veilbreaker.survey_observation_photos import attach_photo, remove_photo


class ObservationPhotoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = AppConfig(data_dir=self.temp.name)
        self.path = create_survey(self.config, 'Indoor', [{}])['survey_path']
        self.row = add_observation(self.config, self.path, dict(run_id=None, category='Obstruction',
            material='Concrete', description='Pillar', author=''))
        self.image = Path(self.temp.name) / 'source.png'
        image = QImage(32, 24, QImage.Format.Format_RGB32)
        image.fill(QColor('red'))
        self.assertTrue(image.save(str(self.image)))

    def test_photo_survives_source_removal_and_exports_as_operator_context(self):
        original = self.image.read_bytes()
        row = attach_photo(self.config, self.path, self.row['id'], self.image, expected_revision=0)
        self.image.unlink()
        self.assertEqual(row['revision'], 1)
        self.assertNotIn('gps', row)
        target = export_session(self.config, self.path)
        self.assertEqual(verify_bundle(target)['status'], 'verified')
        with zipfile.ZipFile(target) as archive:
            self.assertEqual(archive.read('observation-photo-' + row['photo']['asset_id'] + '.png'), original)
            html = archive.read('survey_report.html').decode()
            self.assertIn('Operator photo', html)
            self.assertIn('data:image/png;base64,', html)

    def test_invalid_images_locks_stale_revision_and_corruption(self):
        self.image.write_bytes(b'not an image')
        with self.assertRaises(ValueError): attach_photo(self.config, self.path, self.row['id'], self.image, expected_revision=0)
        image = QImage(2, 2, QImage.Format.Format_RGB32); image.fill(QColor('red')); image.save(str(self.image))
        set_lifecycle(self.config, self.path, True)
        with self.assertRaisesRegex(ValueError, 'Reopen'): attach_photo(self.config, self.path, self.row['id'], self.image, expected_revision=0)
        set_lifecycle(self.config, self.path, False)
        row = attach_photo(self.config, self.path, self.row['id'], self.image, expected_revision=0)
        with self.assertRaisesRegex(ValueError, 'changed'): remove_photo(self.config, self.path, self.row['id'], expected_revision=0)
        from veilbreaker.survey_observation_photos import asset_directory
        (asset_directory(self.config, self.path) / (row['photo']['asset_id'] + '.source')).write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'photo'): export_session(self.config, self.path)
        remove_photo(self.config, self.path, self.row['id'], expected_revision=1)
        self.assertNotIn('photo', read_session(self.config, self.path)['observations'][0])

    def test_replacement_restore_and_report_viewer(self):
        from veilbreaker.library import trash_survey, restore_entry
        from veilbreaker.report_viewer import OfflineReportBrowser, read_reports
        from veilbreaker.survey_observation_photos import asset_directory
        app = QApplication.instance() or QApplication([])
        first = attach_photo(self.config, self.path, self.row['id'], self.image, expected_revision=0)
        old = first['photo']['asset_id']
        second = attach_photo(self.config, self.path, self.row['id'], self.image, expected_revision=1)
        directory = asset_directory(self.config, self.path)
        self.assertFalse((directory / (old + '.source')).exists())
        entry = trash_survey(self.config, self.path)
        with self.assertRaisesRegex(ValueError, 'Restore'):
            remove_photo(self.config, self.path, self.row['id'], expected_revision=2)
        restore_entry(self.config, entry)
        report = dict(read_reports(export_session(self.config, self.path)))['survey_report.html'].decode()
        url = re.search(r'data:image/png;base64,[A-Za-z0-9+/=]+', report).group()
        image = OfflineReportBrowser().loadResource(0, QUrl(url))
        self.assertFalse(image.isNull())
        self.assertEqual((image.width(), image.height()), (32, 24))
        remove_photo(self.config, self.path, self.row['id'], expected_revision=2)
        self.assertFalse((directory / (second['photo']['asset_id'] + '.source')).exists())


if __name__ == '__main__': unittest.main()
