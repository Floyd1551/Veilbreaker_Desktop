"""Qualification of relative receiver comparisons."""
FIELDS = ('receiver','ranges','bin_width','lna','vga','antenna_power','amp')
def compare_capture_context(current, baseline):
    reasons = [key for key in FIELDS if current.get(key) is None or baseline.get(key) is None or current[key] != baseline[key]]
    return {'compatible':not reasons, 'reasons':reasons}

def capture_context(config, metrics):
    return dict(receiver=metrics.get('sdr_serial'), ranges=[vars(r) for r in config.ranges],
                bin_width=config.bin_width_hz, lna=config.lna_gain_db, vga=config.vga_gain_db,
                antenna_power=config.antenna_power, amp=config.amp_enable)
