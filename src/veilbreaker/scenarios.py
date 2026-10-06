"""User-facing descriptions backed by the active diagnostic profiles."""
from . import core

SCENARIOS = {
    'field_validation': ('Field validation', 'General site acceptance and troubleshooting. Suggested tests: Ping + DNS, then relevant device telemetry.'),
    'cellular_fwa': ('Cellular / fixed wireless', 'Investigate a modem or fixed wireless connection. Suggested tests: Cellular and Ping + DNS.'),
    'private_apn': ('Private APN', 'Investigate private cellular routing and reachability. Suggested tests: Cellular and Ping + DNS against your private targets. This does not configure the APN.'),
    'realtime_voice': ('Real-time voice', 'Check delay-sensitive voice links with stricter latency, jitter and loss thresholds. Suggested tests: Ping + DNS during representative use.'),
    'remote_telemetry': ('Remote telemetry', 'Assess low-bandwidth sensor and remote monitoring links with more tolerant delay and throughput thresholds. Suggested tests: Ping + DNS; optional Throughput.'),
    'satellite_wan': ('Satellite WAN', 'Assess satellite links with more tolerant latency and jitter thresholds. Suggested tests: Starlink and Ping + DNS.'),
}


def scenario_help(name):
    profile = core.profile_for_scenario(name)
    title, description = SCENARIOS.get(name, (name, 'Custom diagnostic context.'))
    shared = ' Uses the same thresholds as Field validation.' if name in ('field_validation', 'cellular_fwa', 'private_apn') else ''
    return (f'{title}: {description}{shared} Warning thresholds: latency {profile.latency_warn_ms:g} ms '
            f'(critical {profile.latency_critical_ms:g} ms), jitter {profile.jitter_warn_ms:g} ms, '
            f'loss {profile.loss_warn_pct:g}%. Throughput targets: down {profile.min_dl_mbps:g} / up {profile.min_ul_mbps:g} Mbps. '
            'Scenario selects diagnostic thresholds and baseline history; it does not enable collectors or start tests. Choose tests below.')
