import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from veilbreaker.core import AppConfig
from veilbreaker.evidence import verify_bundle
from veilbreaker.survey import create_survey, export_session, read_session, set_lifecycle
from veilbreaker.survey_observations import add_observation, remove_observation


class SurveyObservationTests(unittest.TestCase):
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
