from math import sqrt

import numpy as np


def mtx_to_quat(rot: np.ndarray) -> np.ndarray:
    """
    Convert a 3x3 rotation matrix to a quaternion. Code adapted from:
    https://www.euclideanspace.com/maths/geometry/rotations/conversions/matrixToQuaternion/
    """
    tr = rot[0, 0] + rot[1, 1] + rot[2, 2]
    if tr > 0:
        s = sqrt(tr + 1.0) * 2
        qw = 0.25 * s
        qx = (rot[2, 1] - rot[1, 2]) / s
        qy = (rot[0, 2] - rot[2, 0]) / s
        qz = (rot[1, 0] - rot[0, 1]) / s
    elif (rot[0, 0] > rot[1, 1]) and (rot[0, 0] > rot[2, 2]):
        s = sqrt(1.0 + rot[0, 0] - rot[1, 1] - rot[2, 2]) * 2
        qw = (rot[2, 1] - rot[1, 2]) / s
        qx = 0.25 * s
        qy = (rot[0, 1] + rot[1, 0]) / s
        qz = (rot[0, 2] + rot[2, 0]) / s
    elif rot[1, 1] > rot[2, 2]:
        s = sqrt(1.0 + rot[1, 1] - rot[0, 0] - rot[2, 2]) * 2
        qw = (rot[0, 2] - rot[2, 0]) / s
        qx = (rot[0, 1] + rot[1, 0]) / s
        qy = 0.25 * s
        qz = (rot[1, 2] + rot[2, 1]) / s
    else:
        s = sqrt(1.0 + rot[2, 2] - rot[0, 0] - rot[1, 1]) * 2
        qw = (rot[1, 0] - rot[0, 1]) / s
        qx = (rot[0, 2] + rot[2, 0]) / s
        qy = (rot[1, 2] + rot[2, 1]) / s
        qz = 0.25 * s
    return np.array([qw, qx, qy, qz])
