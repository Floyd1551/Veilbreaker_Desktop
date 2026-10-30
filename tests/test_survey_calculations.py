import copy
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from veilbreaker.core import AppConfig
from veilbreaker.evidence import verify_bundle
from veilbreaker.field_tools import calculate
from veilbreaker.survey import create_survey, export_session, read_session, set_lifecycle
from veilbreaker.survey_calculations import attach_calculation, remove_calculation, read_snapshot


class SurveyCalculationTests(unittest.TestCase):
    def test_snapshot_is_detached_associated_and_exported(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg=AppConfig(data_dir=folder);survey=create_survey(cfg,'Walk',[{'label':'Lobby'}]);path=survey['survey_path']
            run=survey['survey']['steps'][0]['run_id']
            snapshot=calculate('fspl',{'frequency':5800,'distance':2})
            before=Path(path).read_bytes()
            attached=attach_calculation(cfg,path,snapshot,run_id=run,notes='Donor estimate')
            snapshot['inputs']['distance']=42
            self.assertNotEqual(Path(path).read_bytes(),before)
            session=read_session(cfg,path)
            row=session['calculations'][0]
            self.assertEqual(row['id'],attached['id'])
            self.assertEqual(row['snapshot']['inputs']['distance'],2)
            self.assertEqual(row['kind'],'operator calculation')
            self.assertEqual(row['run_id'],run)
            self.assertEqual(session['steps'][0]['metrics'],{})
            bundle=export_session(cfg,path)
            self.assertEqual(verify_bundle(bundle)['status'],'verified')
            with zipfile.ZipFile(bundle) as archive:
                html=archive.read('survey_report.html').decode('utf-8')
                self.assertIn('Calculated estimate',html)
                self.assertIn('Calculator version: 1',html)
                self.assertIn('Donor estimate',html)
                self.assertIn('Lobby',html)
                self.assertEqual(json.loads(archive.read('calculations.json'))['calculations'][0]['id'],row['id'])
            remove_calculation(cfg,path,row['id'])
            self.assertTrue(read_session(cfg,path)['calculations'][0]['deleted_utc'])
            with zipfile.ZipFile(export_session(cfg,path)) as archive:
                self.assertNotIn('calculations.json',archive.namelist())
                self.assertNotIn('Donor estimate',archive.read('survey_report.html').decode('utf-8'))

    def test_report_escapes_untrusted_notes_and_handles_old_journals(self):
        from veilbreaker.survey_report import report_html
        snapshot=calculate('fspl',{'frequency':5800,'distance':2})
        html=report_html({'steps':[],'calculations':[{'kind':'operator calculation','notes':'<script>alert(1)</script>',
            'snapshot':snapshot}]})
        self.assertNotIn('<script>',html)
        self.assertIn('&lt;script&gt;',html)
        self.assertIn('not measured evidence',html)
        self.assertIn('No numeric measurements',report_html({'steps':[]}))

    def test_link_budget_handoff_retains_validated_source(self):
        from veilbreaker.tool_handoff import fspl_to_link_budget
        with tempfile.TemporaryDirectory() as folder:
            cfg=AppConfig(data_dir=folder);survey=create_survey(cfg,'Walk',[{}]);path=survey['survey_path']
            fspl=calculate('fspl',{'frequency':5800,'distance':2});handoff=fspl_to_link_budget(fspl)
            from veilbreaker.field_tools import REGISTRY
            inputs={field.key:field.default for field in REGISTRY['link_budget'].fields}
            inputs['path_loss']=handoff['inputs']['path_loss']
            snapshot=calculate('link_budget',inputs);snapshot['source']=handoff['source']
            row=attach_calculation(cfg,path,snapshot)
            self.assertEqual(row['snapshot']['source']['tool_id'],'fspl')
            with zipfile.ZipFile(export_session(cfg,path)) as archive:
                html=archive.read('survey_report.html').decode('utf-8')
                self.assertIn('Calculation input source',html)
                self.assertIn('Free-space path loss',html)
            bad=copy.deepcopy(snapshot);bad['source']['value']+=1
            with self.assertRaises(ValueError):attach_calculation(cfg,path,bad)

    def test_trashed_survey_blocks_attachment_and_restore_preserves_it(self):
        from veilbreaker.library import trash_survey,restore_entry
        with tempfile.TemporaryDirectory() as folder:
            cfg=AppConfig(data_dir=folder);survey=create_survey(cfg,'Walk',[{}]);path=survey['survey_path']
            snapshot=calculate('fspl',{'frequency':5800,'distance':2});row=attach_calculation(cfg,path,snapshot)
            entry=trash_survey(cfg,path)
            with self.assertRaisesRegex(ValueError,'Restore'):attach_calculation(cfg,path,snapshot)
            restore_entry(cfg,entry)
            self.assertEqual(read_session(cfg,path)['calculations'][0]['id'],row['id'])

    def test_existing_diagnostic_evidence_is_not_modified(self):
        from unittest.mock import patch
        from veilbreaker import core
        from veilbreaker.survey import execute_survey
        with tempfile.TemporaryDirectory() as folder:
            cfg=AppConfig(data_dir=folder)
            with patch.object(core.VeilbreakerApplication,'collect_passive',return_value=({'latency_ms':12},[])):
                made=execute_survey(cfg,'Walk',[{'label':'Lobby'}])
            evidence=Path(made['survey']['steps'][0]['evidence_zip']);before=evidence.read_bytes()
            run=made['survey']['steps'][0]['run_id']
            set_lifecycle(cfg,made['survey_path'],False)
            attach_calculation(cfg,made['survey_path'],calculate('fspl',{'frequency':5800,'distance':2}),run_id=run)
            self.assertEqual(evidence.read_bytes(),before)
            self.assertEqual(read_session(cfg,made['survey_path'])['steps'][0]['metrics']['latency_ms'],12)

    def test_wrong_or_invalid_values_and_completed_survey_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg=AppConfig(data_dir=folder);survey=create_survey(cfg,'Walk',[{}]);path=survey['survey_path']
            snapshot=calculate('fspl',{'frequency':5800,'distance':2})
            for change in ('output','version','extra','nan','method'):
                bad=copy.deepcopy(snapshot)
                if change=='output':bad['outputs']['Free-space path loss (dB)']+=1
                elif change=='version':bad['version']=99
                elif change=='extra':bad['inputs']['other']=1
                elif change=='nan':bad['outputs']['Free-space path loss (dB)']=float('nan')
                else:bad['method']='incorrect formula'
                with self.assertRaises(ValueError):attach_calculation(cfg,path,bad)
            with self.assertRaises(ValueError):attach_calculation(cfg,path,snapshot,run_id='wrong')
            from veilbreaker.survey import session_lock
            with session_lock(path):
                with self.assertRaisesRegex(ValueError,'another worker'):
                    attach_calculation(cfg,path,snapshot)
            set_lifecycle(cfg,path,True)
            with self.assertRaisesRegex(ValueError,'Reopen'):attach_calculation(cfg,path,snapshot)

    def test_json_snapshot_size_and_format(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'snapshot.json';snap=calculate('fspl',{'frequency':5800,'distance':2})
            path.write_text(json.dumps(snap),encoding='utf-8')
            self.assertEqual(read_snapshot(path)['tool_id'],'fspl')
            path.write_text('{'+' '*300000,encoding='utf-8')
            with self.assertRaises(ValueError):read_snapshot(path)

    def test_all_calculator_default_snapshots_validate(self):
        from veilbreaker.field_tools import TOOLS
        from veilbreaker.survey_calculations import validate_snapshot
        for tool in TOOLS:
            with self.subTest(tool=tool.key):
                saved=calculate(tool.key,{field.key:field.default for field in tool.fields})
                self.assertEqual(validate_snapshot(saved)['tool_id'],tool.key)

    def test_matching_saved_float_is_preserved_without_silent_replacement(self):
        from veilbreaker.survey_calculations import validate_snapshot
        saved=calculate('fspl',{'frequency':5800,'distance':2})
        key='Free-space path loss (dB)'
        saved['outputs'][key]+=1e-10
        self.assertEqual(validate_snapshot(saved)['outputs'][key],saved['outputs'][key])

    def test_small_nonzero_output_cannot_be_replaced_with_zero(self):
        from veilbreaker.survey_calculations import validate_snapshot
        saved=calculate('power_dbm',{'power':-90})
        self.assertGreater(saved['outputs']['Power (W)'],0)
        saved['outputs']['Power (W)']=0
        with self.assertRaisesRegex(ValueError,'do not match'):
            validate_snapshot(saved)


if __name__=='__main__':unittest.main()
