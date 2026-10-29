import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from veilbreaker.core import AppConfig
from veilbreaker.evidence import verify_bundle
from veilbreaker.survey import create_survey, export_session, read_session, set_lifecycle
from veilbreaker.survey_observations import add_observation, remove_observation, update_observation


class SurveyObservationTests(unittest.TestCase):
    def test_edit_retains_identity_time_history_and_export(self):
        with tempfile.TemporaryDirectory() as folder:
            config=AppConfig(data_dir=folder);created=create_survey(config,'DAS',[{'label':'Lobby'},{'label':'Hall'}]);path=created['survey_path']
            runs=[row['run_id'] for row in created['survey']['steps']]
            original={'run_id':runs[0],'category':'Obstruction','material':'Concrete','description':'Pillar','author':'Floyd'}
            first=add_observation(config,path,original)
            new=dict(original,run_id=runs[1],material='Reinforced concrete',description='Pillar beside door')
            updated=update_observation(config,path,first['id'],new,expected_revision=0)
            self.assertEqual(updated['id'],first['id'])
            self.assertEqual(updated['recorded_utc'],first['recorded_utc'])
            self.assertEqual(updated['source'],'operator')
            self.assertEqual(updated['revision'],1)
            self.assertEqual(updated['history'][0]['previous']['description'],'Pillar')
            self.assertEqual(updated['history'][0]['updated']['run_id'],runs[1])
            again=update_observation(config,path,first['id'],new,expected_revision=1)
            self.assertEqual(again['revision'],1)
            with self.assertRaisesRegex(ValueError,'changed'):
                update_observation(config,path,first['id'],original,expected_revision=0)
            with zipfile.ZipFile(export_session(config,path)) as bundle:
                row=json.loads(bundle.read('survey.json'))['observations'][0]
                self.assertEqual(row['history'][0]['previous']['material'],'Concrete')
                self.assertIn('Pillar beside door',bundle.read('survey_report.html').decode('utf-8'))

    def test_edit_rejects_removed_invalid_or_locked_observations(self):
        with tempfile.TemporaryDirectory() as folder:
            config=AppConfig(data_dir=folder);created=create_survey(config,'Survey',[{}]);path=created['survey_path']
            values={'run_id':None,'category':'Other','material':'Unknown','description':'Observed','author':''}
            row=add_observation(config,path,values)
            for change in ({'run_id':'not-a-point'}, {'description':' '}, {'material':'Unrecognized'}):
                with self.assertRaises(ValueError):update_observation(config,path,row['id'],dict(values,**change),expected_revision=0)
            set_lifecycle(config,path,True)
            with self.assertRaisesRegex(ValueError,'Reopen'):update_observation(config,path,row['id'],values,expected_revision=0)
            set_lifecycle(config,path,False)
            remove_observation(config,path,row['id'])
            with self.assertRaisesRegex(ValueError,'removed'):update_observation(config,path,row['id'],values,expected_revision=0)

    def test_edit_preserves_original_diagnostic_evidence_and_trash_guard(self):
        from veilbreaker import core
        from veilbreaker.library import trash_survey, restore_entry
        from veilbreaker.survey import execute_survey
        with tempfile.TemporaryDirectory() as folder:
            config=AppConfig(data_dir=folder)
            with patch.object(core.VeilbreakerApplication,'collect_passive',return_value=({'latency_ms':1},[])):
                made=execute_survey(config,'Walk',[{}],manual=True)
            path=made['survey_path'];step=made['survey']['steps'][0]
            set_lifecycle(config,path,False)
            evidence=Path(step['evidence_zip']);original=evidence.read_bytes()
            values={'run_id':step['run_id'],'category':'Other','material':'Unknown','description':'First','author':''}
            row=add_observation(config,path,values)
            update_observation(config,path,row['id'],dict(values,description='Corrected'),expected_revision=0)
            self.assertEqual(evidence.read_bytes(),original)
            entry=trash_survey(config,path)
            with self.assertRaisesRegex(ValueError,'Restore'):
                update_observation(config,path,row['id'],values,expected_revision=1)
            restore_entry(config,entry)
            self.assertEqual(read_session(config,path)['observations'][0]['description'],'Corrected')

    def test_stale_delete_does_not_remove_a_newer_revision(self):
        with tempfile.TemporaryDirectory() as folder:
            config=AppConfig(data_dir=folder);created=create_survey(config,'Survey',[{}]);path=created['survey_path']
            values={'run_id':None,'category':'Other','material':'Unknown','description':'First','author':''}
            row=add_observation(config,path,values)
            update_observation(config,path,row['id'],dict(values,description='Updated'),expected_revision=0)
            with self.assertRaisesRegex(ValueError,'changed'):
                remove_observation(config,path,row['id'],expected_revision=0)
            self.assertNotIn('deleted_utc',read_session(config,path)['observations'][0])

    def test_save_reopen_and_export_operator_observation(self):
        with tempfile.TemporaryDirectory() as folder:
            config=AppConfig(data_dir=folder)
            created=create_survey(config,'DAS walk',[{'label':'Lobby'}]);path=created['survey_path']
            run=created['survey']['steps'][0]['run_id']
            record=add_observation(config,path,{'run_id':run,'category':'Obstruction','material':'Reinforced concrete',
                'description':'Pillar <near> antenna','author':'Field engineer'})
            saved=read_session(config,path)['observations'][0]
            self.assertEqual(saved['id'],record['id'])
            self.assertEqual(saved['source'],'operator')
            self.assertEqual(saved['run_id'],run)
            self.assertNotIn('gps',saved)
            bundle=export_session(config,path)
            self.assertEqual(verify_bundle(bundle)['status'],'verified')
            with zipfile.ZipFile(bundle) as archive:
                html=archive.read('survey_report.html').decode('utf-8')
                self.assertIn('Pillar &lt;near&gt; antenna',html)
                self.assertIn('Operator observation',html)
                self.assertIn(record['id'],html)
                data=json.loads(archive.read('survey.json'))
                self.assertEqual(data['observations'][0]['id'],record['id'])
            remove_observation(config,path,record['id'])
            self.assertTrue(read_session(config,path)['observations'][0]['deleted_utc'])
            with zipfile.ZipFile(export_session(config,path)) as archive:
                self.assertNotIn('Pillar &lt;near&gt; antenna',archive.read('survey_report.html').decode('utf-8'))

    def test_trashed_survey_blocks_edits_and_restore_keeps_observation(self):
        from veilbreaker.library import trash_survey, restore_entry
        with tempfile.TemporaryDirectory() as folder:
            config=AppConfig(data_dir=folder);created=create_survey(config,'Walk',[{}]);path=created['survey_path']
            values={'run_id':None,'category':'Other','material':'Unknown','description':'Uncertain obstruction','author':''}
            record=add_observation(config,path,values)
            entry=trash_survey(config,path)
            with self.assertRaisesRegex(ValueError,'Restore'):
                add_observation(config,path,values)
            restore_entry(config,entry)
            self.assertEqual(read_session(config,path)['observations'][0]['id'],record['id'])

    def test_invalid_point_blank_description_and_completed_survey_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            config=AppConfig(data_dir=folder);created=create_survey(config,'Survey',[{}]);path=created['survey_path']
            valid={'run_id':None,'category':'Other','material':'Unknown','description':'Observed','author':''}
            for change in ({'run_id':'outside'}, {'description':'  '}, {'category':'invented'}, {'material':'invented'}):
                with self.assertRaises(ValueError):add_observation(config,path,dict(valid,**change))
            set_lifecycle(config,path,True)
            with self.assertRaisesRegex(ValueError,'Reopen'):
                add_observation(config,path,valid)


if __name__ == '__main__': unittest.main()
