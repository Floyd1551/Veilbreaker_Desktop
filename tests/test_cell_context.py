import json
import tempfile
import unittest
from pathlib import Path
from veilbreaker.core import AppConfig
from veilbreaker import cell_context as ctx

class ContextTests(unittest.TestCase):
    def test_integrity_and_report_escaping(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg=AppConfig(data_dir=tmp); path=cfg.root/'surveys'/'survey-context.json'
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(dict(schema_version=1,survey_id='survey-context',status='planned',steps=[],name='Test')))
            value=dict(rows=[dict(status='not found',radio='LTE',carrier='<script>',identity={},candidates=[])])
            ctx.save_context(cfg,path,value)
            self.assertEqual(ctx.load_context(cfg,path)['context'],value)
            self.assertIn('&lt;script&gt;',ctx.context_html(value))
            self.assertNotIn('<script>',ctx.context_html(value))
            asset=next((cfg.root/'survey-assets').rglob('cell-context.json'))
            asset.write_text('{}')
            with self.assertRaises(ValueError):ctx.load_context(cfg,path)

    def test_portable_export_contains_saved_context(self):
        import zipfile
        from veilbreaker.survey import export_session
        from veilbreaker.evidence import verify_bundle
        with tempfile.TemporaryDirectory() as tmp:
            cfg=AppConfig(data_dir=tmp);path=cfg.root/'surveys'/'survey-export.json'
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(dict(schema_version=1,survey_id='survey-export',site_id='Test',status='planned',steps=[],name='Test')))
            ctx.save_context(cfg,path,dict(rows=[],dataset=dict(attribution='Synthetic reference credit')))
            target=export_session(cfg,path)
            self.assertEqual(verify_bundle(target)['status'],'verified')
            with zipfile.ZipFile(target) as archive:
                self.assertIn('cell-context.json',archive.namelist())
                self.assertIn('Synthetic reference credit',archive.read('survey_report.html').decode())
