"""Source-scoped phone RF evidence; never joins desktop transport measurements."""
import hashlib
import json
from dataclasses import asdict
from .android_capture import validate_capture, normalize_selection, SIGNALS


def build_phone_assessments(envelope, selection=None):
    from . import core
    validate_capture(envelope)
    groups = {}
    stamps = set()
    for obs in envelope['observations']:
        if not selection:
            for previous in groups.values():
                if previous['subscription'] == obs['subscription_key']:
                    previous['present_in_latest'] = False
                    for measurement in previous['measurements'].values(): measurement['current'] = False
        for index, cell in enumerate(obs['cells']):
            if selection and (obs['observation_id'], index) != selection:
                continue
            if cell.get('registered') is not True or cell['radio'] not in {'LTE', 'NR'}:
                continue
            identity = {k:cell['identity'].get(k) for k in ('cell_id','pci','tac','earfcn','nrarfcn','mcc','mnc')}
            key = json.dumps([obs['subscription_key'],cell['radio'],identity],sort_keys=True)
            receiver = groups.setdefault(key, dict(receiver_id=hashlib.sha256(key.encode()).hexdigest()[:16],
                source='phone', radio=cell['radio'], subscription=obs['subscription_key'], identity=identity,
                measurements={}, findings=[], availability={}))
            receiver['present_in_latest'] = True
            stamp = (key, obs['elapsed_realtime_ms'] - cell['age_ms']) if cell.get('age_ms') is not None else None
            receiver['repeated'] = stamp in stamps if stamp is not None else False
            age = cell.get('age_ms')
            receiver['freshness'] = 'unknown age' if age is None else ('cached' if receiver['repeated'] else ('older than 10 seconds' if age > 10000 else 'recent'))
            if stamp is not None: stamps.add(stamp)
            for value in receiver['measurements'].values():
                value['current'] = False
                value['latest_exposed'] = False
            receiver['availability'] = {name:'not_reported' for name in SIGNALS}
            for name, quantity in cell['signal'].items():
                if name not in SIGNALS: continue
                receiver['availability'][name] = 'exposed' if quantity.get('value') is not None else quantity.get('reason','not_reported')
                if quantity.get('value') is not None:
                    receiver['measurements'][name] = dict(value=quantity['value'], unit=quantity['unit'],
                        received_utc=obs['received_utc'], age_ms=cell.get('age_ms'), latest_exposed=True, freshness=receiver['freshness'], current=receiver['freshness']=='recent')
            selected = normalize_selection(envelope, obs['observation_id'], index)
            engine = core.ProfessionalVeilbreakerEngine()
            findings, evidence = [], []
            engine._cellular_rf(selected['metrics'], findings, evidence)
            # RSSNR and CSI are assessed under their own names, never aliased to SS-SINR.
            for metric, threshold in (('rssnr',0),('csi_rsrp',-110),('csi_rsrq',-15),('csi_sinr',0)):
                value = cell['signal'].get(metric,{}).get('value')
                if value is not None and value <= threshold:
                    engine._finding(findings, 'PHONE-'+metric, core.Severity.NOTICE, core.Domain.CELLULAR_RF,
                        metric.upper().replace('_','-') + ' warrants a repeat measurement',
                        f"Reported {metric}: {value} {SIGNALS[metric][0]}.",
                        'This reported quantity suggests limited RF margin or quality; it does not identify interference or service failure.',
                        'Repeat at the same position and another position, preserving the serving cell and sample-age context.',
                        0.65, [metric])
            receiver['findings'] = [asdict(f) for f in findings]
            receiver['hypotheses'] = [asdict(h) for h in engine._rank_hypotheses(evidence)]
            receiver['received_utc'] = obs['received_utc']
            receiver['age_ms'] = cell.get('age_ms')
    return list(groups.values())


def apply_phone_assessments(report, assessments):
    from . import core
    report.normalized_metrics['receiver_assessments'] = assessments
    # Existing general coverage refers to the desktop receiver, not the phone.
    for finding in report.findings:
        if finding.finding_id == 'DATA-002':
            finding.title = 'Desktop measurements: limited diagnostic coverage'
            finding.observation = 'Desktop receiver/path only. ' + finding.observation
    for receiver in assessments:
        label = 'Phone ' + receiver['subscription'] + ' ' + receiver['radio'] + ' cell ' + str(receiver['identity'].get('cell_id') or receiver['identity'].get('pci') or 'unknown')
        qualifier = 'historical' if not receiver['present_in_latest'] else receiver['freshness']
        for item in receiver['findings']:
            values = dict(item)
            values['finding_id'] = 'PHONE-' + receiver['receiver_id'] + '-' + values['finding_id']
            values['title'] = label + (' (' + qualifier + ')' if qualifier != 'recent' else '') + ': ' + values['title']
            if receiver.get('repeated'): values['observation'] += ' Repeated modem sample; no fresh RF update confirmed.'
            values['observation'] += ' Received ' + receiver['received_utc'] + '; modem sample age ' + str(receiver['age_ms']) + ' ms (unknown when None).'
            values['evidence_keys'] = ['receiver_assessments.' + receiver['receiver_id'] + '.' + k for k in values['evidence_keys']]
            report.findings.append(core.Finding(**values))
        for item in receiver.get('hypotheses', []):
            values = dict(item)
            values['hypothesis_id'] = 'PHONE-' + receiver['receiver_id'] + '-' + values['hypothesis_id']
            values['title'] = label + ' (' + qualifier + '): ' + values['title']
            values['evidence'] = [core.Evidence(**dict(ev, statement=ev['statement'] + ' Phone sample freshness: ' + qualifier + '; received ' + receiver['received_utc'])) for ev in values['evidence']]
            report.hypotheses.append(core.Hypothesis(**values))
        current = [name for name,state in receiver['availability'].items() if state=='exposed']
        report.summary.append(label + ': exposed ' + (', '.join(current) or 'no RF measurements') + '; sample freshness: ' + qualifier + '. Phone RF is assessed independently of desktop connectivity; see Cellular for sample freshness and trends.')
    if not assessments:
        report.summary.append('Phone RF: no registered LTE/NR cells available for assessment.')
    # Do not average receiver scores into a desktop service-health score.
    report.summary.append('Overall health and quality scores describe desktop measurements; phone RF findings are separately source-labelled.')
