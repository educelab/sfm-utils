import json
from enum import auto, Enum
from os import PathLike
from pathlib import Path
from typing import Union

import numpy as np

from sfm_utils.alicevision import scene_to_alicevision
from sfm_utils.openmvg import scene_to_openmvg, __OPENMVG_DEFAULT_COB
from sfm_utils.sfm import Scene


class Format(Enum):
    """
    SfM file formats
    """
    OPEN_MVG = auto()
    ALICE_VISION = auto()


def export_scene(path: Union[str, bytes, PathLike], scene: Scene,
                 fmt: Format = Format.OPEN_MVG,
                 cob_matrix: Union[np.ndarray, None] = None):
    """
    Export Scene to a project file

    Parameters
    ----------
    path: str, bytes, or PathLike
        Path to the output file
    scene: Scene
        Scene to export
    fmt: Format
        Export format (default: Format.OPEN_MVG)
    cob_matrix: np.ndarray, None, optional
        If not None, then a change of basis will be performed by pre-multiplying
        the Scene's rotation matrices with the provided matrix. If None, a
        format-specific default change of basis will be performed. To disable,
        provide a 3x3 identity matrix. (default: None)
    """
    if fmt == Format.OPEN_MVG:
        if cob_matrix is None:
            cob_matrix = __OPENMVG_DEFAULT_COB
        data = scene_to_openmvg(scene, cob_matrix=cob_matrix)
    elif fmt == Format.ALICE_VISION:
        data = scene_to_alicevision(scene, cob_matrix=cob_matrix)
    else:
        raise ValueError('Unknown scene format')

    # Write to disk
    output_file = Path(path)
    with output_file.open(mode='w') as f:
        json.dump(data, f, indent=4)
