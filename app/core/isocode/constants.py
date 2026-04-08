POSITION_ALIASES = {
    '10': 'B0',
    '11': 'B1',
    '12': 'B2',
    '13': 'B3',
    '14': 'B4',
    '15': 'B5',
    '16': 'B6',
    'B0': 'B0',
    'B1': 'B1',
    'B2': 'B2',
    'B3': 'B3',
    'B4': 'B4',
    'B5': 'B5',
    'B6': 'B6',
}


DUMMY_TYPES = {
    'H3': 'HYBRID III 50%',
    'HF': 'HYBRID III 5%',
    'HM': 'HYBRID III 95%',
    'TH': 'THOR 50%',
    'Q3': 'Q3 Child',
    'Q6': 'Q6 Child',
    'QA': 'Q10 Child',
    'Y6': '3YO Child',
    'Y7': '6YO Child',
    'Y8': '10YO Child',
    'WS': 'WORLDSID',
}

DATA_TYPES = {
    'AC': 'acceleration',
    'FO': 'force',
    'MO': 'moment',
    'DS': 'displacement',
    'AV': 'angular_velocity',
}

AXIS_CODES = {
    'X': 'x',
    'Y': 'y',
    'Z': 'z',
}

FILTER_CODE_TO_LABEL = {
    '0': 'Unfiltered',
    'P': 'Prefiltered',
    'A': 'CFC 1000',
    'B': 'CFC 600',
    'C': 'CFC 180',
    'D': 'CFC 60',
    # Legacy/internal aliases kept for compatibility with older datasets.
    'E': 'CFC 1000',
    'F': 'CFC 600',
    'G': 'CFC 180',
    'H': 'CFC 60',
    'Q': 'Prefiltered',
    'S': 'Special Filter',
    'V': 'Video Analysis',
    'X': 'Constant Channel',
}

FILTER_LABEL_TO_CODE = {
    'Raw': '0',
    'Unfiltered': '0',
    'Prefiltered': 'P',
    'CFC 60': 'D',
    'CFC 180': 'C',
    'CFC 600': 'B',
    'CFC 1000': 'A',
}

MAIN_LOCATION_TOKENS = {
    'HEAD': {'sensor_location': 'head'},
    'NECK': {'sensor_location': 'neck'},
    'CHST': {'sensor_location': 'chest'},
    'CHES': {'sensor_location': 'chest'},
    'PELV': {'sensor_location': 'pelvis'},
    'FEMR': {'sensor_location': 'femur'},
    'FEMU': {'sensor_location': 'femur'},
    'KNSL': {'sensor_location': 'knee'},
    'KNEE': {'sensor_location': 'knee'},
    'CLEV': {'sensor_location': 'knee'},
    'ILIA': {'sensor_location': 'iliac'},
    'ILAC': {'sensor_location': 'iliac'},
    'TIBI': {'sensor_location': 'tibia'},
}

FINE_LOCATION_SIDE = {
    'LE': 'left',
    'RI': 'right',
    'IN': 'inner',
    'OU': 'outer',
}

FINE_LOCATION_LEVEL = {
    'UP': 'upper',
    'LO': 'lower',
}
