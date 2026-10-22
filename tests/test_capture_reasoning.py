import copy
import unittest
import json
import tempfile
from pathlib import Path
from test_android_capture import fixture


def capture(values):
    data = fixture()
    template = data['observations'][0]
    data['observations'] = []
    for i, value in enumerate(values):
        obs = copy.deepcopy(template)
        obs['observation_id'] = str(i)
        obs['elapsed_realtime_ms'] += i * 3000
        obs['cells'][0]['age_ms'] = 100
        obs['cells'][0]['signal']['rsrp']['value'] = value
        data['observations'].append(obs)
    return data


class CaptureReasoningTests(unittest.TestCase):
    def test_saved_evidence_contains_phone_and_sdr_findings(self):
        from veilbreaker import core
        from veilbreaker.evidence import verify_bundle
        from veilbreaker.sdr_report import build_sdr_report, report_html
        from dataclasses import asdict
        with tempfile.TemporaryDirectory() as folder:
            cfg = core.AppConfig(data_dir=folder)
            run_dir = cfg.artifacts_dir / 'patterns'
            run_dir.mkdir(parents=True)
            (run_dir / 'android-capture.json').write_text(json.dumps(capture([-120] * 5)), encoding='utf-8')
            path = run_dir / 'sweep.csv'
            path.write_text(('d,t,100000000,110000000,1000000,10,' + ','.join(['-80'] * 9 + ['-50']) + '\n') * 5, encoding='utf-8')
            summary = core.HackRFCollector.summarize('test', core.SDRRange('test',100,110), core.HackRFCollector.parse_sweep_csv(path), path)
            missing = build_sdr_report([asdict(summary)], {})
            self.assertFalse(missing['ranges'][0]['capture_diagnostics']['findings'])
            path.with_suffix('.capture.json').write_text(json.dumps(dict(returncode=0, settings=asdict(cfg.sdr))), encoding='utf-8')
            sdr = build_sdr_report([asdict(summary)], {})
            self.assertIn('Persistent sampled spectrum activity', report_html(sdr))
            self.assertIn('109 to 110', report_html(sdr))
            report = core.ProfessionalVeilbreakerEngine().analyze({})
            bundle = core.write_evidence_pack(cfg, 'patterns', {}, report, [], [summary], {})
            saved = json.loads((run_dir / 'report.json').read_text(encoding='utf-8'))
            titles = [f['title'] for f in saved['findings']]
            self.assertTrue(any('repeated weak coverage' in t for t in titles))
            self.assertTrue(any('Persistent sampled' in t for t in titles))
            self.assertEqual(verify_bundle(bundle)['status'], 'verified')

    def test_gaps_missing_identity_and_other_sims_do_not_join(self):
        from veilbreaker.capture_reasoning import cellular_patterns
        data = capture([-120] * 5)
        for i, obs in enumerate(data['observations']): obs['elapsed_realtime_ms'] += i * 60000
        self.assertFalse(cellular_patterns(data)['findings'])
        data = capture([-120] * 5)
        for obs in data['observations']: obs['cells'][0]['identity'].pop('cell_id')
        self.assertEqual(cellular_patterns(data)['qualified_samples'], 0)
        data = capture([-120] * 5)
        data['subscriptions'].append({'key':'sim-2'})
        for i, obs in enumerate(data['observations']):
            obs['subscription_key'] = 'sim-1' if i % 2 else 'sim-2'
        self.assertFalse(cellular_patterns(data)['findings'])

    def test_cellular_report_and_engine_integration(self):
        from veilbreaker.cellular_report import build_report, report_html
        from veilbreaker.capture_reasoning import apply_patterns
        from veilbreaker import core
        report = build_report(capture([-120] * 5))
        self.assertIn('repeated weak coverage', report_html(report))
        engine_report = core.ProfessionalVeilbreakerEngine().analyze({})
        original_health = engine_report.health_score
        apply_patterns(engine_report, report['capture_diagnostics'], 'Phone capture')
        self.assertTrue(any('repeated weak coverage' in f.title for f in engine_report.findings))
        self.assertEqual(engine_report.health_score, original_health)

    def test_weak_samples_require_fresh_independent_observations(self):
        from veilbreaker.capture_reasoning import cellular_patterns
        data = capture([-120] * 5)
        self.assertIn('CELL-SUSTAINED', [f['id'] for f in cellular_patterns(data)['findings']])
        for i, obs in enumerate(data['observations']):
            obs['cells'][0]['age_ms'] = 100 + i * 3000
        result = cellular_patterns(data)
        self.assertFalse(result['findings'])
        self.assertEqual(result['qualified_samples'], 1)

    def test_cell_changes_are_not_neighbor_or_secondary_changes(self):
        from veilbreaker.capture_reasoning import cellular_patterns
        data = capture([-90] * 6)
        for i, obs in enumerate(data['observations']):
            obs['cells'][0]['identity']['cell_id'] = str(i % 2)
        self.assertIn('CELL-CHANGES', [f['id'] for f in cellular_patterns(data)['findings']])
        for obs in data['observations']:
            obs['cells'][0]['connection_status'] = 'secondary'
        self.assertNotIn('CELL-CHANGES', [f['id'] for f in cellular_patterns(data)['findings']])

    def test_optional_identity_metadata_does_not_create_cell_changes(self):
        from veilbreaker.capture_reasoning import cellular_patterns
        data = capture([-90] * 6)
        for i, obs in enumerate(data['observations']):
            obs['cells'][0]['identity']['tac'] = 10 if i % 2 else None
        self.assertNotIn('CELL-CHANGES', [f['id'] for f in cellular_patterns(data)['findings']])

    def test_out_of_order_primary_samples_cannot_create_changes(self):
        from veilbreaker.capture_reasoning import cellular_patterns
        data = capture([-90] * 7)
        for i, (obs, stamp) in enumerate(zip(data['observations'], [9900,4000,15900,10000,21900,16000,27900])):
            obs['cells'][0]['identity']['cell_id'] = str(i % 2)
            obs['cells'][0]['age_ms'] = obs['elapsed_realtime_ms'] - stamp
        self.assertNotIn('CELL-CHANGES', [f['id'] for f in cellular_patterns(data)['findings']])

    def test_duplicate_callbacks_do_not_erase_primary_history(self):
        from veilbreaker.capture_reasoning import cellular_patterns
        data = capture([-90] * 8)
        for i, obs in enumerate(data['observations']):
            stamp = 9900 + (i // 2) * 6000
            obs['cells'][0]['identity']['cell_id'] = str((i // 2) % 2)
            obs['cells'][0]['age_ms'] = obs['elapsed_realtime_ms'] - stamp
        result = cellular_patterns(data)
        self.assertEqual(result['qualified_samples'], 4)
        self.assertIn('CELL-CHANGES', [f['id'] for f in result['findings']])

    def test_recovered_quality_drop_and_unknown_age(self):
        from veilbreaker.capture_reasoning import cellular_patterns
        data = capture([-90] * 5)
        for obs, value in zip(data['observations'], [-9, -9, -20, -9, -9]):
            obs['cells'][0]['signal']['rsrq']['value'] = value
        self.assertIn('CELL-DIP', [f['id'] for f in cellular_patterns(data)['findings']])
        for obs in data['observations']: obs['cells'][0]['age_ms'] = None
        self.assertFalse(cellular_patterns(data)['findings'])

    def test_sdr_persistence_bursts_floor_and_gaps(self):
        from veilbreaker.capture_reasoning import spectrum_patterns
        sweeps = [[(j, j+1, -50 if j == 9 else -80) for j in range(10)] for _ in range(5)]
        self.assertIn('SDR-PERSISTENT', [f['id'] for f in spectrum_patterns(sweeps, 0, 10)['findings']])
        for i in (0, 1, 3, 4): sweeps[i][-1] = (9, 10, -80)
        self.assertIn('SDR-BURST', [f['id'] for f in spectrum_patterns(sweeps, 0, 10)['findings']])
        shifted = [[(j, j+1, -80 + (12 if i >= 3 else 0)) for j in range(10)] for i in range(6)]
        self.assertIn('SDR-FLOOR', [f['id'] for f in spectrum_patterns(shifted, 0, 10)['findings']])
        shifted[-1].pop()
        self.assertFalse(spectrum_patterns(shifted, 0, 10)['findings'])
        self.assertFalse(spectrum_patterns(sweeps[:1], 0, 10)['findings'])
