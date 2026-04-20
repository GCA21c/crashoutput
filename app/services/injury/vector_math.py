import numpy as np


def compute_resultant_xyz(x, y, z):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)
    return np.sqrt(np.square(x) + np.square(y) + np.square(z))
