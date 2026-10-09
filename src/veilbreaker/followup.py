"""Conservative setup guidance for diagnostic recommendations."""
CELLULAR = {'TEST-RF-SNAPSHOT', 'TEST-RF-A-B', 'TEST-BAND-CELL', 'TEST-NSA-ANCHOR',
            'TEST-MODEM-THERMAL', 'TEST-CELL-STABILITY'}


def guidance(test_id):
    if test_id in CELLULAR:
        return ({'cellular'}, 'A connected supported modem and the correct port/backend in Settings.',
                'Prepares one read-only modem snapshot. Repeat captures or use a survey for A/B and time-series observations; this does not continuously sample the modem or change its bands.')
    if test_id in {'TEST-STARLINK-SKY', 'TEST-STARLINK-PATH', 'TEST-STARLINK-TERMINAL'}:
        return ({'starlink', 'active'} if test_id != 'TEST-STARLINK-TERMINAL' else {'starlink'},
                'A reachable Starlink terminal/backend; verify network targets before active tests.',
                'Prepares one terminal snapshot, with bounded ping/DNS where requested. Repeated snapshots, sky-view changes and additional endpoint checks remain operator steps.')
    if test_id == 'TEST-DNS':
        return ({'active'}, 'Review the public ping target and DNS hostname in Settings.',
                'Prepares bounded ping and configured-resolver DNS checks. Testing an alternate resolver remains a manual step.')
    if test_id == 'TEST-THROUGHPUT-REPEAT':
        return ({'active', 'throughput'}, 'An approved reachable iperf3 server and port configured in Settings.',
                'Prepares one throughput and ping/DNS run. Use a survey for repeated tests; configure alternate targets separately. This generates network traffic.')
    if test_id == 'TEST-NSA-NR':
        return ({'cellular', 'active', 'throughput'}, 'A supported modem and approved iperf3 server configured in Settings.',
                'Prepares modem telemetry plus throughput/ping/DNS. Collection is sequential, not continuous or guaranteed simultaneous. Repeat at the alternate location separately.')
    if test_id == 'TEST-WIFI-WIRED':
        return ({'active'}, 'Connect the desired interface and confirm the active route before each run.',
                'Prepares bounded ping/DNS. Veilbreaker does not bind this run to an interface; switching to Ethernet and checking the route remain manual steps.')
    return (set(), 'Follow the recommendation below; use Tools & readiness to inspect dependencies.',
            'Manual workflow. No run options are prepared for this recommendation. For SDR comparisons, use Tools to review the receive preset and match the saved antenna, range, gain and bin width. For path/MTU tests, use the existing CLI or your approved network tools.')


def details(test):
    flags, requirements, scope = guidance(test.get('test_id', ''))
    return '\n\n'.join([test.get('title', 'Follow-up'),
        'Why\n' + test.get('purpose', 'Not supplied'),
        'Recommended procedure\n' + test.get('action', 'Not supplied'),
        'What to look for\n' + test.get('expected_signal', 'Not supplied'),
        'Requirements\n' + requirements,
        'What Veilbreaker prepares\n' + scope,
        'Preparation uses the current site, scenario and saved settings. Review them before Run. A recommendation is a hypothesis test, not a confirmed cause.'])
