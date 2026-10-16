import tempfile
import unittest
from veilbreaker import core
from veilbreaker.survey import create_survey, append_steps, set_lifecycle, list_sessions, read_session
from veilbreaker.library import trash_survey, restore_entry
class LifecycleTests(unittest.TestCase):
 def test_create_complete_reopen_append_and_trash(self):
  with tempfile.TemporaryDirectory() as folder:
   cfg=core.AppConfig(data_dir=folder)
   result=create_survey(cfg,'Field',[{'label':'A'}])
   path=result['survey_path']
   self.assertEqual(result['survey']['status'],'paused')
   done=set_lifecycle(cfg,path,True)
   self.assertEqual(done['lifecycle'],'completed')
   self.assertEqual(done['steps'][0]['status'],'not_run')
   with self.assertRaises(ValueError): append_steps(cfg,path,[{'label':'B'}])
   set_lifecycle(cfg,path,False)
   self.assertEqual(len(append_steps(cfg,path,[{'label':'B'}])['steps']),2)
   with self.assertRaises(ValueError): append_steps(cfg,path,[{}]*19)
   removal=trash_survey(cfg,path)
   self.assertEqual(list_sessions(cfg),[])
   restore_entry(cfg,removal)
   self.assertEqual(len(list_sessions(cfg)),1)

 def test_future_settings_preserve_completed_test_and_busy_rejects(self):
  import json
  import os
  from pathlib import Path
  from veilbreaker.survey import update_survey
  with tempfile.TemporaryDirectory() as folder:
   cfg=core.AppConfig(data_dir=folder); result=create_survey(cfg,'Field',[{},{}]); path=Path(result['survey_path'])
   data=json.loads(path.read_text(encoding='utf-8')); data['steps'][0]['status']='complete'
   first=data['steps'][0]['settings'];path.write_text(json.dumps(data),encoding='utf-8')
   changed=cfg.to_dict();changed['site_id']='different';changed['ping_count']=7
   update_survey(cfg,path,{'settings':changed})
   updated=json.loads(path.read_text(encoding='utf-8'))
   self.assertEqual(updated['steps'][0]['settings'],first)
   self.assertEqual(updated['steps'][1]['settings']['site_id'],cfg.site_id)
   updated['status']='running';updated['pid']=os.getpid();path.write_text(json.dumps(updated),encoding='utf-8')
   with self.assertRaises(ValueError): set_lifecycle(cfg,path,True)
   with self.assertRaises(ValueError): trash_survey(cfg,path)
