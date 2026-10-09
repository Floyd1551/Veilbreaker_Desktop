"""Selected-run prerequisite checks; never acquire telemetry or send test traffic."""
import platform
import tempfile
from . import core


def check_selected(config, options):
    rows = []
    def add(item, state, detail):
        rows.append({'item': item, 'state': state, 'detail': detail})
    def executable(name):
        add(name, 'Available' if core.command_exists(name) else 'Missing',
            'Local executable lookup only; no command executed.')
    try:
        config.root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=config.root) as stream:
            stream.write(b'check')
        add('Evidence storage', 'Available', str(config.root))
    except OSError as exc:
        add('Evidence storage', 'Missing', str(exc))
    add('Host platform', 'Available' if platform.system() in ('Windows', 'Linux') else 'Untested', platform.system())
    if options.get('active') or options.get('guided'):
        executable('ping')
        add('Ping / DNS targets', 'Configured' if config.public_ping_target and config.dns_test_host else 'Missing',
            f'Ping: {config.public_ping_target or "unset"}; DNS: {config.dns_test_host or "unset"}. Reachability and DNS resolution untested.')
    if options.get('throughput'):
        executable('iperf3')
        add('Throughput server', 'Configured' if config.iperf3_server else 'Missing',
            f'{config.iperf3_server or "Set server in Settings"}:{config.iperf3_port}. Server reachability and permission untested.')
    if options.get('sdr'):
        collector = core.HackRFCollector(config.sdr, config.artifacts_dir / 'readiness')
        for name in ('hackrf_info', 'hackrf_sweep'):
            path = collector.tool_path(name)
            add(name, 'Available' if path else 'Missing', path or 'Set HackRF tools directory in Settings.')
        add('SDR ranges', 'Configured' if config.sdr.ranges else 'Missing',
            ', '.join(f'{r.label}: {r.min_mhz}–{r.max_mhz} MHz' for r in config.sdr.ranges) or 'Configure receive ranges.')
        add('HackRF connection', 'Untested', 'Use Discover HackRF in Tools; verify antenna and receiver settings. No device opened by this checklist.')
    if options.get('cellular'):
        available = core._pyserial_available() or platform.system() == 'Linux'
        add('Modem serial support', 'Available' if available else 'Missing', 'pyserial or Linux serial fallback; driver/device compatibility untested.')
        add('Modem configuration', 'Configured', f'Port: {config.cellular.port}; backend: {config.cellular.backend}. Review Settings.')
        add('Modem connection', 'Untested', 'No port probed. Verify the connected modem and selected port before acquisition.')
    if options.get('starlink'):
        availability = core.StarlinkCollector(config.starlink).backend_availability()
        backend = config.starlink.backend
        available = any(availability.values()) if backend == 'auto' else bool(availability.get(backend))
        add('Starlink backend', 'Available' if available else 'Missing', f'Selected: {backend}. Review backend dependencies in Settings.')
        add('Starlink endpoint', 'Untested', f'{config.starlink.host}:{config.starlink.port}. No management request sent.')
    add('Scope', 'Information', 'Only selected diagnostic prerequisites were checked. Unselected hardware is optional. Available/configured does not mean connected or qualified. Recheck after changing settings or devices.')
    return {'checked_utc': core.utcnow_iso(), 'site_id': config.site_id, 'scenario': config.scenario,
            'selected': sorted(k for k,v in options.items() if v), 'rows': rows}
