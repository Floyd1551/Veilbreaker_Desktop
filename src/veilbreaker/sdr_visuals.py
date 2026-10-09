"""Dependency-free embedded PNG plots from saved spectrum and CSV records."""
import base64
import csv
import math
import struct
import zlib

WIDTH, HEIGHT = 720, 200
BACKGROUND = (232, 237, 243)


def png(pixels, width=WIDTH, height=HEIGHT):
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))
    raw = b''.join(b'\0' + bytes(pixels[y*width*3:(y+1)*width*3]) for y in range(height))
    data = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', width, height, 8, 2, 0, 0, 0))
    data += chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')
    return 'data:image/png;base64,' + base64.b64encode(data).decode('ascii')


def build_visuals(path, points, low, high):
    # Repeated frequency intervals mark the next observed sweep.
    records = []
    sweeps = []
    current = []
    seen = set()
    truncated = False
    with path.open(encoding='utf-8', errors='replace', newline='') as stream:
        for row in csv.reader(stream):
            if len(row) < 7:
                continue
            try:
                start, width = float(row[2])/1e6, float(row[4])/1e6
                if not math.isfinite(start) or not math.isfinite(width) or width <= 0:
                    continue
                bins = []
                for i, value in enumerate(row[6:]):
                    try:
                        power = float(value)
                    except ValueError:
                        continue
                    left, right = start+i*width, start+(i+1)*width
                    if math.isfinite(power) and right > low and left < high:
                        bins.append((max(low, left), min(high, right), power))
                if bins:
                    keys = {(a, b) for a, b, _ in bins}
                    if seen.intersection(keys):
                        sweeps.append(current)
                        current, seen = [], set()
                        if len(sweeps) == 128:
                            truncated = True
                            break
                    current.extend(bins)
                    seen.update(keys)
                    if len(records) < 128:
                        records.append(bins)
            except (ValueError, OverflowError):
                continue
    if current:
        sweeps.append(current)
    values = [v for p in points for v in p[1:]] + [b[2] for r in records for b in r]
    floor, ceiling = math.floor(min(values))-2, math.ceil(max(values))+2
    def x(freq):
        return max(0, min(WIDTH-1, int((freq-low)/(high-low)*(WIDTH-1))))
    def y(power):
        return max(0, min(HEIGHT-1, int((ceiling-power)/(ceiling-floor)*(HEIGHT-1))))
    def canvas():
        return bytearray(BACKGROUND * (WIDTH*HEIGHT))
    def dot(data, px, py, color):
        offset = (py*WIDTH+px)*3
        data[offset:offset+3] = bytes(color)
    spectrum = canvas()
    for gy in range(0, HEIGHT, 40):
        for gx in range(WIDTH):
            dot(spectrum, gx, gy, (199, 209, 219))
    # Connect only adjacent bins at the smallest observed width; never bridge gaps.
    bin_width = min((b[1]-b[0] for r in records for b in r), default=0)
    for left, right in zip(points, points[1:]):
        if right[0]-left[0] > bin_width*1.01:
            continue
        for column, color in ((2, (181, 104, 0)), (1, (0, 111, 100))):
            ax, ay, bx, by = x(left[0]), y(left[column]), x(right[0]), y(right[column])
            length = max(abs(bx-ax), abs(by-ay), 1)
            for step in range(length+1):
                dot(spectrum, round(ax+(bx-ax)*step/length), round(ay+(by-ay)*step/length), color)
    for freq, median, maximum in points:
        for value, color in ((maximum, (181, 104, 0)), (median, (0, 111, 100))):
            for px in range(max(0,x(freq)-1), min(WIDTH,x(freq)+2)):
                for py in range(max(0,y(value)-1), min(HEIGHT,y(value)+2)):
                    dot(spectrum, px, py, color)
    water_height = 320
    waterfall = bytearray((30, 34, 43) * (WIDTH*water_height))
    powers = sorted(b[2] for sweep in sweeps for b in sweep)
    water_floor = powers[int((len(powers)-1)*0.05)] if powers else floor
    water_top = powers[int((len(powers)-1)*0.99)] if powers else ceiling
    water_top = max(water_floor+10, water_top)
    palette = [(4, 7, 30), (20, 30, 110), (0, 115, 195), (0, 210, 190), (245, 220, 50), (255, 85, 25)]
    def color(power):
        position = max(0, min(1, (power-water_floor)/(water_top-water_floor))) * (len(palette)-1)
        index = min(len(palette)-2, int(position))
        blend = position-index
        return tuple(round(a+(b-a)*blend) for a,b in zip(palette[index], palette[index+1]))
    for index, bins in enumerate(reversed(sweeps)):
        # Maximum power per display column preserves narrow peaks when downsampling.
        columns = [None]*WIDTH
        for left, right, power in bins:
            start = max(0, min(WIDTH-1, int((left-low)/(high-low)*WIDTH)))
            stop = max(start+1, min(WIDTH, math.ceil((right-low)/(high-low)*WIDTH)))
            for px in range(start, stop):
                columns[px] = power if columns[px] is None else max(columns[px], power)
        row = b''.join(bytes(color(p)) if p is not None else bytes((30,34,43)) for p in columns)
        for py in range(index*water_height//len(sweeps), (index+1)*water_height//len(sweeps)):
            waterfall[py*WIDTH*3:(py+1)*WIDTH*3] = row
    legend = bytearray()
    for _ in range(16):
        for px in range(WIDTH):
            legend.extend(color(water_floor+(water_top-water_floor)*px/(WIDTH-1)))
    return {'spectrum_png': png(spectrum), 'waterfall_png': png(waterfall, WIDTH, water_height),
            'legend_png': png(legend, WIDTH, 16), 'water_floor_db': water_floor, 'water_top_db': water_top,
            'sweep_count': len(sweeps), 'floor_db': floor, 'ceiling_db': ceiling,
            'record_count': len(records), 'truncated': truncated,
            'min_mhz': low, 'max_mhz': high}


def visuals_html(v):
    axis = f'<p>Frequency (MHz): {v["min_mhz"]:g} (left) — {(v["min_mhz"]+v["max_mhz"])/2:g} (center) — {v["max_mhz"]:g} (right)</p>'
    return (f'<h3>Spectrum readout</h3><p>Relative dB: {v["ceiling_db"]:g} (top) to {v["floor_db"]:g} (bottom). '
            'Teal: median · Amber: maximum. Traces are not joined across frequency gaps.</p>'
            f'<img width="720" height="200" alt="Median and maximum spectrum" src="{v["spectrum_png"]}">' + axis +
            '<h3>Capture waterfall</h3><p>Newest sweep at top · oldest at bottom. '
            'Sweep boundaries inferred from repeated frequency bins; not a calibrated time axis. Dark gray means missing data.</p>'
            f'<img width="720" height="320" alt="Frequency versus reconstructed sweep progression" src="{v["waterfall_png"]}">' + axis +
            f'<img width="720" height="16" alt="Relative power color scale" src="{v["legend_png"]}">'
            f'<p>Relative power: {v["water_floor_db"]:.1f} dB (left, dark blue) → {v["water_top_db"]:.1f} dB (right, orange). '
            'Contrast spans the 5th–99th sample percentiles (at least 10 dB); outliers are color-clipped, not removed. '
            f'{v["sweep_count"]} reconstructed sweeps. ' + ('Limited to first 128 sweeps; newest displayed sweep at top. ' if v['truncated'] else '') +
            ('Only one sweep is available; no temporal variation can be shown. ' if v['sweep_count'] == 1 else '') +
            'Partial sweeps retain gaps. Frequency columns use maximum power when multiple bins share a pixel.</p>')
