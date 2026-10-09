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
    # Record order is explicit: a CSV record is not necessarily a complete sweep.
    records = []
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
                    if len(records) == 128:
                        truncated = True
                        break
                    records.append(bins)
            except (ValueError, OverflowError):
                continue
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
    waterfall = canvas()
    for index, bins in enumerate(records):
        for left, right, power in bins:
            level = max(0, min(1, (power-floor)/(ceiling-floor)))
            color = (int(245*level), int(45+180*level), int(160-120*level))
            for py in range(index*HEIGHT//len(records), (index+1)*HEIGHT//len(records)):
                for px in range(x(left), min(WIDTH, max(x(left)+1,x(right)))):
                    dot(waterfall, px, py, color)
    return {'spectrum_png': png(spectrum), 'waterfall_png': png(waterfall),
            'floor_db': floor, 'ceiling_db': ceiling, 'record_count': len(records), 'truncated': truncated,
            'min_mhz': low, 'max_mhz': high}


def visuals_html(v):
    axis = f'<p>Frequency (MHz): {v["min_mhz"]:g} (left) — {(v["min_mhz"]+v["max_mhz"])/2:g} (center) — {v["max_mhz"]:g} (right)</p>'
    return (f'<h3>Spectrum readout</h3><p>Relative dB: {v["ceiling_db"]:g} (top) to {v["floor_db"]:g} (bottom). '
            'Teal: median · Amber: maximum. Traces are not joined across frequency gaps.</p>'
            f'<img width="720" height="200" alt="Median and maximum spectrum" src="{v["spectrum_png"]}">' + axis +
            '<h3>Capture waterfall</h3><p>CSV record progression, earliest at top; each row can cover only part of a sweep. '
            'Not a calibrated time axis. Gray means no sample in that record, not low power.</p>'
            f'<img width="720" height="200" alt="Frequency versus CSV record progression" src="{v["waterfall_png"]}">' + axis +
            f'<p>Color scale: <span style="color:#002da0">blue {v["floor_db"]:g} dB</span> → '
            f'<span style="color:#a87920">yellow {v["ceiling_db"]:g} dB</span> (relative). '
            f'{v["record_count"]} records displayed. ' + ('Limited to first 128 records; spectrum uses the full saved trace.' if v['truncated'] else '') + '</p>')
