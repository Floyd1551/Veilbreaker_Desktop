import tempfile
import unittest
from veilbreaker import core
from veilbreaker.library import trash_run, list_trash, restore_entry
class LibraryTests(unittest.TestCase):
 def test_remove_restore_keeps_evidence_and_hides_active_queries(self):
  with tempfile.TemporaryDirectory() as folder:
   cfg=core.AppConfig(data_dir=folder); store=core.VeilbreakerStore(cfg.db_path)
   report=core.ProfessionalVeilbreakerEngine().analyze({'rsrp':-100})
   store.save_run('one','default','field_validation',{'rsrp':-100},report)
   entry=trash_run(cfg,'one')
   self.assertEqual(store.list_runs(),[])
   self.assertEqual(store.search_runs()[1],0)
   self.assertEqual(len(list_trash(cfg)),1)
   self.assertEqual(store.db.execute('SELECT count(*) FROM runs').fetchone()[0],1)
   restore_entry(cfg,entry)
   self.assertEqual(len(store.list_runs()),1)
   store.close()
 def test_case_reference_blocks_delete(self):
  with tempfile.TemporaryDirectory() as folder:
   cfg=core.AppConfig(data_dir=folder); store=core.VeilbreakerStore(cfg.db_path)
   store.save_run('one','default','field_validation',{},core.ProfessionalVeilbreakerEngine().analyze({}))
   store.add_case('one','coverage')
   with self.assertRaisesRegex(ValueError,'referenced'): trash_run(cfg,'one')
   store.close()

 def test_survey_restore_refuses_independently_removed_test(self):
  from veilbreaker.survey import create_survey
  from veilbreaker.library import trash_survey
  with tempfile.TemporaryDirectory() as folder:
   cfg=core.AppConfig(data_dir=folder)
   survey=create_survey(cfg,'S',[{}])
   run=survey['survey']['steps'][0]['run_id']
   store=core.VeilbreakerStore(cfg.db_path)
   store.save_run(run,'default','field_validation',{},core.ProfessionalVeilbreakerEngine().analyze({}))
   entry=trash_survey(cfg,survey['survey_path'])
   child=trash_run(cfg,run)
   with self.assertRaisesRegex(ValueError,'independently'): restore_entry(cfg,entry)
   restore_entry(cfg,child); restore_entry(cfg,entry)
   self.assertIsNotNone(store.get_run(run))
   store.close()

 def test_owned_child_conflict_rolls_back_entire_restore(self):
  from veilbreaker.survey import create_survey
  from veilbreaker.library import trash_survey
  with tempfile.TemporaryDirectory() as folder:
   cfg=core.AppConfig(data_dir=folder); result=create_survey(cfg,'S',[{}])
   run=result['survey']['steps'][0]['run_id']
   store=core.VeilbreakerStore(cfg.db_path)
   try:
    store.save_run(run,'default','field_validation',{},core.ProfessionalVeilbreakerEngine().analyze({}))
    entry=trash_survey(cfg,result['survey_path'],True)
    store.db.execute('UPDATE runs SET note=? WHERE run_id=?',('changed',run));store.db.commit()
    with self.assertRaisesRegex(ValueError,'conflict'): restore_entry(cfg,entry)
    self.assertEqual(len(list_trash(cfg)),2)
    self.assertIsNone(store.get_run(run))
   finally: store.close()
