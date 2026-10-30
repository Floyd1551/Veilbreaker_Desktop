"""Offline regional search starting points, not state boundaries or coverage."""

# Approximate centers give operators a place to start; users can edit bounds.
STATE_CENTERS = {
    'Alabama': (-86.8, 32.8), 'Arizona': (-111.9, 34.3), 'Arkansas': (-92.4, 34.9),
    'California': (-119.5, 37.2), 'Colorado': (-105.5, 39.0), 'Connecticut': (-72.7, 41.6),
    'Delaware': (-75.5, 39.0), 'Florida': (-82.0, 28.6), 'Georgia': (-83.4, 32.7),
    'Idaho': (-114.5, 44.2), 'Illinois': (-89.2, 40.0), 'Indiana': (-86.1, 40.0),
    'Iowa': (-93.5, 42.0), 'Kansas': (-98.4, 38.5), 'Kentucky': (-85.3, 37.7),
    'Louisiana': (-91.9, 31.0), 'Maine': (-69.2, 45.2), 'Maryland': (-76.6, 39.0),
    'Massachusetts': (-71.8, 42.3), 'Michigan': (-84.5, 44.3), 'Minnesota': (-94.3, 46.3),
    'Mississippi': (-89.7, 32.7), 'Missouri': (-92.5, 38.5), 'Montana': (-110.5, 47.0),
    'Nebraska': (-99.9, 41.5), 'Nevada': (-116.8, 39.3), 'New Hampshire': (-71.6, 43.8),
    'New Jersey': (-74.5, 40.0), 'New Mexico': (-106.0, 34.4), 'New York': (-75.4, 43.0),
    'North Carolina': (-79.4, 35.6), 'North Dakota': (-100.5, 47.5), 'Ohio': (-82.8, 40.4),
    'Oklahoma': (-97.5, 35.5), 'Oregon': (-120.5, 44.0), 'Pennsylvania': (-77.8, 40.9),
    'Rhode Island': (-71.5, 41.7), 'South Carolina': (-80.9, 33.8), 'South Dakota': (-100.2, 44.4),
    'Tennessee': (-86.0, 35.8), 'Texas': (-99.3, 31.5), 'Utah': (-111.7, 39.4),
    'Vermont': (-72.6, 44.1), 'Virginia': (-78.7, 37.5), 'Washington': (-120.5, 47.4),
    'West Virginia': (-80.6, 38.6), 'Wisconsin': (-89.7, 44.6), 'Wyoming': (-107.5, 43.0),
}

CONUS_BOUNDS = [-125, 24, -66, 50]  # A bounding rectangle, not a coastline or jurisdiction mask.


def starter_bounds(state):
    try:
        lon, lat = STATE_CENTERS[state]
    except (KeyError, TypeError):
        raise ValueError('Choose a contiguous U.S. state.') from None
    return [round(lon-1, 1), round(lat-1, 1), round(lon+1, 1), round(lat+1, 1)]
