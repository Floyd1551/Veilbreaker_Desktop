"""Pure sampled-terrain clearance, not a propagation or connectivity prediction."""
import math

RADIUS=6371008.8

def finite(value):return type(value) in (int,float) and math.isfinite(value)


def assess_profile(distances_m,elevations_m,receiver_agl_m,site_agl_m,frequency_mhz=None,earth_factor=1.0,fresnel_fraction=.6):
    distances=list(distances_m);elevations=list(elevations_m)
    if not 3<=len(distances)<=4096 or len(elevations)!=len(distances):raise ValueError('Use 3–4096 paired terrain samples.')
    if not all(finite(x) for x in distances) or distances[0]!=0 or not 0<distances[-1]<=100000 or any(b<=a for a,b in zip(distances,distances[1:])):
        raise ValueError('Terrain distances must increase from zero to at most 100 km.')
    if not all(finite(h) and 0<=h<=10000 for h in (receiver_agl_m,site_agl_m)):raise ValueError('Supply finite nonnegative antenna heights above ground.')
    if not finite(earth_factor) or earth_factor not in (1.,4/3):raise ValueError('Select geometric Earth or the explicit 4/3 refraction assumption.')
    if frequency_mhz is not None and (not finite(frequency_mhz) or not 0<frequency_mhz<=1000000):raise ValueError('Frequency must be positive and at most 1 THz.')
    if not finite(fresnel_fraction) or not 0<=fresnel_fraction<=1:raise ValueError('Invalid Fresnel clearance fraction.')
    missing=any(e is None or not finite(e) for e in elevations)
    result=dict(calculation_version=1,distances_m=distances,elevations_m=[e if finite(e) else None for e in elevations],
                receiver_agl_m=receiver_agl_m,site_agl_m=site_agl_m,frequency_mhz=frequency_mhz,
                earth_factor=earth_factor,earth_radius_m=RADIUS,fresnel_fraction=fresnel_fraction,
                status='incomplete',fresnel_status='incomplete',minimum_clearance_m=None,first_obstruction_m=None,
                clearance_m=[],line_m=[],terrain_effective_m=[],fresnel_radius_m=[])
    if missing:return result
    length=distances[-1];start=elevations[0]+receiver_agl_m;end=elevations[-1]+site_agl_m
    for x,z in zip(distances,elevations):
        line=start+(end-start)*x/length
        terrain=z+x*(length-x)/(2*earth_factor*RADIUS)
        radius=math.sqrt((299792458/(frequency_mhz*1e6))*x*(length-x)/length) if frequency_mhz is not None else None
        result['line_m'].append(line);result['terrain_effective_m'].append(terrain)
        result['clearance_m'].append(line-terrain);result['fresnel_radius_m'].append(radius)
    inner=result['clearance_m'][1:-1]
    result['minimum_clearance_m']=min(inner)
    result['first_obstruction_m']=next((x for x,c in zip(distances[1:-1],inner) if c<=0),None)
    result['status']='sampled terrain obstructed' if min(inner)<=0 else 'no sampled terrain obstruction'
    result['fresnel_status']='unknown frequency' if frequency_mhz is None else ('insufficient clearance' if any(c<fresnel_fraction*r for c,r in zip(inner,result['fresnel_radius_m'][1:-1])) else 'selected clearance met')
    return result
