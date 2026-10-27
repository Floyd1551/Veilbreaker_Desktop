"""Explicit handoffs between offline calculations, with source provenance."""
import math

from .field_tools import calculate


def fspl_to_link_budget(snapshot):
    """Prepare a link-budget path-loss input from a valid FSPL calculation."""
    if not isinstance(snapshot, dict) or snapshot.get('tool_id') != 'fspl' or snapshot.get('version') != 1:
        raise ValueError('A current Free-space path loss calculation is required.')
    inputs = snapshot.get('inputs')
    if not isinstance(inputs, dict) or set(inputs) != {'frequency', 'distance'}:
        raise ValueError('Free-space path loss inputs are missing or invalid.')
    expected = calculate('fspl', inputs)
    outputs = snapshot.get('outputs')
    key = 'Free-space path loss (dB)'
    if (snapshot.get('kind') != 'calculated estimate' or not isinstance(outputs, dict)
            or set(outputs) != {key} or not isinstance(outputs[key], (float, int))
            or isinstance(outputs[key], bool) or not math.isfinite(outputs[key])
            or not math.isclose(outputs[key], expected['outputs'][key], rel_tol=1e-12, abs_tol=1e-9)):
        raise ValueError('Free-space path loss result does not match its inputs.')
    source = {'kind': 'calculated estimate', 'tool_id': 'fspl', 'title': expected['title'],
              'version': expected['version'], 'inputs': expected['inputs'],
              'output': key, 'value': expected['outputs'][key],
              'method': expected['method'], 'limitations': expected['limitations']}
    return {'tool_id': 'link_budget', 'inputs': {'path_loss': expected['outputs'][key]}, 'source': source}
