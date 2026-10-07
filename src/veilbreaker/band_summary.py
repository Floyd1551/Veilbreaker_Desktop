"""Descriptive per-band measurements, preserving partial coverage and provenance."""
import csv
import io
import statistics


def summarize_bands(points, intervals, plan, low, high):
    rows = []
    for band in plan['bands']:
        start, stop = band['min_mhz'], band['max_mhz']
        if start == stop or start >= high or stop <= low:
            continue
        overlap = min(stop, high)-max(start, low)
        covered, end = 0.0, start
        for a, b in intervals:
            a, b = max(a, start), min(b, stop)
            if b > a:
                covered += max(0, b-max(a, end))
                end = max(end, b)
        bins = [p for p in points if start <= p[0] < stop]
        peak = max(bins, key=lambda p: p[2]) if bins else None
        rows.append({
            'label': band['label'], 'carrier': band.get('carrier', 'Not specified'),
            'direction': band.get('direction', 'Not specified'), 'source': band['source'],
            'min_mhz': start, 'max_mhz': stop,
            'inspected_min_mhz': max(start, low), 'inspected_max_mhz': min(stop, high),
            'full_band_coverage_pct': round(min(100, covered/(stop-start)*100), 2),
            'requested_overlap_coverage_pct': round(min(100, covered/overlap*100), 2),
            'bin_count': len(bins),
            'median_bin_power_db': statistics.median(p[1] for p in bins) if bins else None,
            'maximum_db': peak[2] if peak else None,
            'peak_frequency_mhz': peak[0] if peak else None,
            'coverage_status': ('no bin centers in band' if not bins else
                                'partial band' if covered < (stop-start)*0.9999 else 'full band'),
        })
    return rows


def band_csv(report):
    """One row per overlapping band/range; overlapping references are not additive."""
    output = io.StringIO(newline='')
    columns = ['run_id', 'site_id', 'range', 'capture_status', 'band', 'carrier', 'direction',
               'min_mhz', 'max_mhz', 'inspected_min_mhz', 'inspected_max_mhz',
               'full_band_coverage_pct', 'requested_overlap_coverage_pct', 'coverage_status',
               'bin_count', 'median_bin_power_db', 'maximum_db', 'peak_frequency_mhz',
               'reference_name', 'reference_version', 'source', 'csv_path', 'sha256', 'capture_settings_json']
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    import json
    for capture in report['ranges']:
        for band in capture.get('band_summaries', []):
            row = {k: band.get(k, '') for k in columns}
            row.update(run_id=report['metadata'].get('run_id', ''), site_id=report['metadata'].get('site_id', ''),
                       range=capture['label'], capture_status=capture['status'], band=band['label'],
                       reference_name=report['band_plan']['name'], reference_version=report['band_plan']['version'],
                       csv_path=capture['csv_path'], sha256=capture['sha256'],
                       capture_settings_json=json.dumps((capture.get('capture') or {}).get('settings'), ensure_ascii=False))
            # Keep imported reference labels as text when opened in a spreadsheet.
            for key, value in row.items():
                if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
                    row[key] = "'" + value
            writer.writerow(row)
    return output.getvalue()
