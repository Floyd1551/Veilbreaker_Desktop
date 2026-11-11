import copy
import json
import tempfile
import unittest
import uuid
from pathlib import Path

from veilbreaker.mobile_survey_import import load_mobile_survey, write_selected_capture
from veilbreaker.android_capture import load_capture


class MobileSurveyImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.capture = json.loads(Path('examples/android-cellular-v1.json').read_text(encoding='utf-8'))
        self.survey = {'format': 'veilbreaker.mobile.survey', 'schema_version': 1,
                       'survey_id': str(uuid.uuid4()), 'name': 'Field site',
                       'created_utc': self.capture['created_utc'], 'lifecycle': 'open',
                       'points': [{'attached_utc': self.capture['created_utc'], 'capture': self.capture,
                                   'operator_note': 'Concrete pillar'}]}
        self.path = self.root / 'mobile.json'

    def save(self, value=None):
        self.path.write_text(json.dumps(self.survey if value is None else value), encoding='utf-8')
        return load_mobile_survey(self.path)

    def test_preview_and_extract_preserve_capture_and_note(self):
        preview = self.save()
        self.assertEqual(preview['survey']['points'][0]['operator_note'], 'Concrete pillar')
        dest = self.root / 'capture.json'
        write_selected_capture(self.path, preview['sha256'], 0, dest)
        self.assertEqual(load_capture(dest)['envelope'], self.capture)
        self.assertEqual(json.loads(self.path.read_text()), self.survey)

    def test_rejects_changed_source_and_existing_destination(self):
        preview = self.save()
        dest = self.root / 'capture.json'
        dest.write_text('keep this')
        with self.assertRaises(FileExistsError): write_selected_capture(self.path, preview['sha256'], 0, dest)
        self.assertEqual(dest.read_text(), 'keep this')
        self.path.write_text(self.path.read_text() + ' ')
        with self.assertRaisesRegex(ValueError, 'changed'): write_selected_capture(self.path, preview['sha256'], 0, self.root / 'new.json')

    def test_rejects_duplicates_invalid_capture_and_bad_notes(self):
        for change in ('duplicate', 'capture', 'note', 'lifecycle', 'index'):
            value = copy.deepcopy(self.survey)
            if change == 'duplicate': value['points'].append(copy.deepcopy(value['points'][0]))
            if change == 'capture': value['points'][0]['capture']['schema_version'] = 999
            if change == 'note': value['points'][0]['operator_note'] = 'x' * 501
            if change == 'lifecycle': value['lifecycle'] = 'invalid'
            if change == 'index': value['points'] *= 21
            with self.assertRaises(ValueError, msg=change): self.save(value)

    def test_rejects_duplicate_json_keys_and_invalid_index(self):
        preview = self.save()
        for index in (-1, 1, True):
            with self.assertRaises(ValueError): write_selected_capture(self.path, preview['sha256'], index, self.root / 'new.json')
        self.path.write_text('{"format":"x","format":"x"}')
        with self.assertRaises(ValueError): load_mobile_survey(self.path)

    def test_equivalent_uuid_and_nonfinite_json_are_rejected(self):
        duplicate = copy.deepcopy(self.survey)
        second = copy.deepcopy(duplicate['points'][0])
        second['capture']['capture_id'] = second['capture']['capture_id'].upper()
        duplicate['points'].append(second)
        with self.assertRaises(ValueError): self.save(duplicate)
        nonfinite = copy.deepcopy(self.survey); nonfinite['extra'] = float('nan')
        with self.assertRaises(ValueError): self.save(nonfinite)
