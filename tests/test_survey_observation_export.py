import csv
import io
import json
import tempfile
import unittest
import zipfile

from veilbreaker.core import AppConfig
from veilbreaker.evidence import verify_bundle
from veilbreaker.survey import create_survey, export_session
from veilbreaker.survey_observations import add_observation, remove_observation


class ObservationExportTests(unittest.TestCase):
    def test_csv_preserves_provenance_and_protects_spreadsheet_formulas(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg=AppConfig(data_dir=folder);made=create_survey(cfg,'Walk',[{'label':'+Point'}]);path=made['survey_path']
            run=made['survey']['steps'][0]['run_id']
            row=add_observation(cfg,path,dict(run_id=run,category='Obstruction',material='Concrete',
                description='  =HYPERLINK("bad")',author='@operator'))
            removed=add_observation(cfg,path,dict(run_id=None,category='Other',material='Unknown',description='Removed',author=''))
            remove_observation(cfg,path,removed['id'])
            bundle=export_session(cfg,path)
            self.assertEqual(verify_bundle(bundle)['status'],'verified')
            with zipfile.ZipFile(bundle) as archive:
                rows=list(csv.DictReader(io.StringIO(archive.read('operator-observations.csv').decode('utf-8-sig'))))
                self.assertEqual(len(rows),1)
                self.assertEqual(rows[0]['Observation ID'],row['id'])
                self.assertEqual(rows[0]['Source'],'operator')
                self.assertEqual(rows[0]['Point'],"'+Point")
                self.assertEqual(rows[0]['Description'],"'=HYPERLINK(\"bad\")")
                self.assertEqual(rows[0]['Operator'],"'@operator")
                journal=json.loads(archive.read('survey.json'))
                self.assertEqual(journal['observations'][0]['description'],'=HYPERLINK("bad")')


if __name__ == '__main__':unittest.main()
