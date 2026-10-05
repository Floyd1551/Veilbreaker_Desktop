import copy
import csv
import io
import json
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from veilbreaker import core
from veilbreaker.survey import execute_survey
from veilbreaker.survey_trends import build_trend, trend_csv, saved_trend
from veilbreaker.survey_plans import rename_point, move_point, session_matches


def visit(number, value=0, status="complete"):
    return {"survey_id": f"survey-{number}", "name": f"Visit {number}", "site_id": "Site", "scenario": "field_validation",
            "created_utc": f"2026-10-{number:02}T12:00:00Z", "status": status,
            "steps": [{"label": "Roof", "run_id": f"run-{number}", "status": status, "options": {}, "metrics": {"latency_ms": value}}]}


class TrendTests(unittest.TestCase):
    def test_sorted_visits_preserve_zero_gaps_and_statistics(self):
        a,b,c,d = visit(1,0),visit(2,50,"partial"),visit(3,10),visit(4,30)
        settings = {"public_ping_target":"1.1.1.1"}
        result = build_trend(a,settings,[(d,{"public_ping_target":"8.8.8.8"}),(b,settings),(c,settings),(a,settings)],"Roof","latency_ms")
        self.assertEqual([r["value"] for r in result["rows"]],[0,50,10,30])
        self.assertEqual([r["comparable"] for r in result["rows"]],[True,False,True,False])
        self.assertEqual(result["summary"],{"visits":4,"comparable":2,"excluded":2,"minimum":0,"median":5,"maximum":10})
        self.assertIsNone(result["rows"][1]["delta"])
        self.assertEqual(result["rows"][2]["delta"],10)
        self.assertNotIn("public_ping_target",json.dumps(result))

    def test_missing_ambiguous_and_foreign_points(self):
        a,b,c,d = visit(1),visit(2),visit(3),visit(4)
        b["steps"] = []
        c["steps"] *= 2
        d["site_id"] = "Elsewhere"
        result = build_trend(a,{},[(a,{}),(b,{}),(c,{}),(d,{})],"Roof","latency_ms")
        self.assertEqual(len(result["rows"]),3)
        self.assertIsNone(result["rows"][1]["value"])
        self.assertIn("unique",result["rows"][2]["notes"])
        with self.assertRaises(ValueError):
            build_trend(c,{},[(c,{})],"Roof","latency_ms")

    def test_unknown_settings_nonnumeric_and_csv_formula_safety(self):
        a,b = visit(1),visit(2,False)
        b["name"] = "=1+1"
        result = build_trend(a,None,[(a,None),(b,None)],"Roof","latency_ms")
        self.assertEqual(result["summary"]["comparable"],0)
        self.assertIsNone(result["rows"][1]["value"])
        data = list(csv.reader(io.StringIO(trend_csv(result))))
        self.assertEqual(data[1][6],"0")
        self.assertEqual(data[2][6],"")
        self.assertEqual(data[2][1],'"=1+1"')

    def test_saved_trend_cli_and_dialog_export_are_offline(self):
        from veilbreaker.cli import main
        from veilbreaker.gui import MainWindow
        from veilbreaker.trend_ui import TrendDialog
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            cfg=core.AppConfig(data_dir=folder)
            with patch.object(core.VeilbreakerApplication,"collect_passive",side_effect=[({"latency_ms":0},[]),({"latency_ms":5},[])]):
                a=execute_survey(cfg,"Baseline",[{"label":"Roof"}])
                execute_survey(cfg,"Return",[{"label":"Roof"}])
            evidence=Path(a["evidence_zip"]).read_bytes()
            config_path=Path(folder)/"config.json"
            config_path.write_text(json.dumps(cfg.to_dict()),encoding="utf-8")
            out=io.StringIO()
            with patch("sys.stdout",out), patch.object(core.VeilbreakerApplication,"run",side_effect=AssertionError("Must remain offline")):
                self.assertEqual(main(["--config",str(config_path),"survey","--trend",a["survey_path"],"--point","Roof","--metric","latency_ms"]),0)
            self.assertEqual(json.loads(out.getvalue())["summary"]["comparable"],2)
            w=MainWindow(cfg)
            try:
                d=TrendDialog(w,a["survey_path"])
                d.resize(700,620); d.show(); app.processEvents()
                self.assertEqual(d.table.rowCount(),2)
                self.assertEqual(d.result["summary"]["minimum"],0)
                path=Path(folder)/"trend.json"
                with patch("veilbreaker.trend_ui.QFileDialog.getSaveFileName",return_value=(str(path),"")):
                    d.export("json")
                self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["point"],"Roof")
                d.close()
            finally:
                w.close()
            self.assertEqual(Path(a["evidence_zip"]).read_bytes(),evidence)


class SurveyOrganizationTests(unittest.TestCase):
    def test_editing_draft_preserves_flags_and_rejects_duplicate_labels(self):
        steps=[{"label":"Roof","options":{"sdr":True}}, {"label":"Office","options":{"active":True}}]
        moved=move_point(steps,1,-1)
        self.assertEqual(moved[0]["options"],{"active":True})
        self.assertEqual(steps[0]["label"],"Roof")
        renamed=rename_point(moved,0,"Entrance")
        self.assertEqual(renamed[0]["label"],"Entrance")
        for label in ("Roof"," ","x"*101):
            with self.assertRaises(ValueError): rename_point(moved,0,label)
        with self.assertRaises(ValueError): move_point(steps,0,-1)

    def test_session_filter_matches_site_point_and_state(self):
        session=visit(1)
        for text in ("roof","SITE","2026-10","visit 1"):
            self.assertTrue(session_matches(session,text))
        self.assertFalse(session_matches(session,"roof","paused"))
        self.assertTrue(session_matches(session,"roof","complete"))

    def test_gui_reorder_rename_and_duplicate_generation(self):
        from veilbreaker.gui import MainWindow
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            w=MainWindow(core.AppConfig(data_dir=folder))
            try:
                p=w.survey_page
                p.copies.setValue(3); p.add_steps()
                p.queue.selectRow(1); p.remove_step()
                p.copies.setValue(1); p.add_steps()
                self.assertEqual(len({s["label"] for s in p.steps}),3)
                p.queue.selectRow(2)
                with patch("veilbreaker.survey_ui.QInputDialog.getText",return_value=("Entrance",True)):
                    p.rename_queued_point()
                p.move_queued_point(-1)
                self.assertEqual(p.steps[1]["label"],"Entrance")
                p.session_cache=[(Path(folder)/"a.json",visit(1))]
                p.session_search.setText("Roof")
                self.assertEqual(p.saved.count(),1)
                p.session_filter.setCurrentText("paused")
                self.assertEqual(p.saved.count(),0)
            finally:
                w.close()


class CaseAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/"data.db"
        self.store=core.VeilbreakerStore(self.path)
        self.store.db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?)",("source","2026-10-02","Site","field_validation",'{"latency_ms":3}',"{}","","Original"))
        self.store.db.commit()
    def tearDown(self):
        self.store.close(); self.temp.cleanup()

    def test_events_idempotency_search_and_legacy_preservation(self):
        case=self.store.add_case("source","Cable fault","Replaced cable")
        self.assertTrue(self.store.withdraw_case(case,"Retest disproved cause"))
        self.assertFalse(self.store.withdraw_case(case,"second click"))
        record=self.store.case_record(case)
        self.assertEqual([e["action"] for e in record["events"]],["confirmed","withdrawn"])
        self.assertEqual(record["events"][1]["details"]["reason"],"Retest disproved cause")
        self.assertEqual(self.store.search_cases("replaced","Withdrawn")[1],1)
        self.assertEqual(self.store.search_cases("' OR 1=1")[1],0)
        self.assertEqual(self.store.get_run("source")["note"],"Original")
        self.store.db.execute("DROP TABLE case_events"); self.store.db.commit(); self.store.close()
        self.store=core.VeilbreakerStore(self.path)
        self.assertEqual(self.store.case_record(case)["events"],[])
        self.assertEqual(self.store.case_record(case)["case"]["cause"],"Cable fault")

    def test_case_and_audit_event_are_transactional(self):
        self.store.db.execute("CREATE TRIGGER fail_event BEFORE INSERT ON case_events BEGIN SELECT RAISE(ABORT,'test failure'); END")
        with self.assertRaises(sqlite3.IntegrityError): self.store.add_case("source","Fault")
        self.assertEqual(self.store.list_cases(),[])
