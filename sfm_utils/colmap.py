"""
PySfMUtils
Copyright (C) 2021  EduceLab

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from os import PathLike
from pathlib import Path
from typing import Union

import numpy as np

from sfm_utils.sfm import Intrinsic, IntrinsicBrownT2, IntrinsicRadialK3, IntrinsicType, Pose, Scene, View
from sfm_utils.utils import mtx_to_quat

__COLMAP_INTRINSIC_NAME_MAP = {
    IntrinsicType.PINHOLE: 'SIMPLE_PINHOLE',
    IntrinsicType.RADIAL_K3: 'RADIAL',
    IntrinsicType.BROWN_T2: 'OPENCV'
}


def scene_to_colmap(scene: Scene, path: Union[str, bytes, PathLike]):
    """
    Save a Scene as a COLMAP sparse model
    """

    def colmap_intrinsic(intrinsic: Intrinsic) -> str:
        # Index and intrinsic type
        result = f'{intrinsic.id + 1} ' + __COLMAP_INTRINSIC_NAME_MAP[intrinsic.type]
        # Image size
        result += f' {intrinsic.width} {intrinsic.height} '

        # Basic pinhole
        if intrinsic.type == IntrinsicType.PINHOLE:
            result += f'{intrinsic.focal_length_as_pixels} {intrinsic.ppx} {intrinsic.ppy}'

        # Radial K3 (only keeps K1, K1)
        elif intrinsic.type == IntrinsicType.RADIAL_K3:
            result += f'{intrinsic.focal_length_as_pixels} {intrinsic.ppx} {intrinsic.ppy} '
            result += f'{intrinsic.dist_params[0]} {intrinsic.dist_params[1]}'

        # Brown T2 (only keeps K1, K2, P1, P2)
        elif intrinsic.type == IntrinsicType.BROWN_T2:
            result += f'{intrinsic.focal_length_as_pixels} {intrinsic.focal_length_as_pixels} '
            result += f'{intrinsic.ppx} {intrinsic.ppy} '
            result += " ".join(str(d) for d in intrinsic.dist_params[:4])
        return result

    def colmap_view(view: View) -> str:
        # Index
        result = f'{view.id + 1} '
        # Rotation as quaternion
        q = mtx_to_quat(view.pose.rotation).tolist()
        result += " ".join(str(d) for d in q) + " "
        # Position
        result += " ".join(str(d) for d in view.pose.center) + " "
        # Camera ID
        result += str(view.intrinsic.id + 1) + " "
        # image
        result += str(view.path.name)
        return result

    # setup output directory
    sparse_dir = Path(path) / "sparse" / "0"
    sparse_dir.mkdir(parents=True, exist_ok=True)

    # points3D.txt - empty file
    (sparse_dir / "points3D.txt").touch()

    # cameras.txt
    with (sparse_dir / "cameras.txt").open('w') as cam_file:
        for intr in scene.intrinsics:
            cam_file.write(colmap_intrinsic(intr))
            cam_file.write('\n')

    # images.txt
    with (sparse_dir / "images.txt").open('w') as img_file:
        for view in scene.views:
            img_file.write(colmap_view(view))
            img_file.write('\n\n')


def main():
    # Create scene
    scene = Scene()
    scene.root_dir = '.'

    # Construct a view
    view = View()
    view.path = "path/to/view.jpg"
    view.width = 100
    view.height = 100
    view.camera_make = 'PySfMUtils'
    view.camera_model = 'Test Camera'
    scene.add_view(view)

    # Add the view intrinsic
    intrinsic = Intrinsic()
    intrinsic.width = view.width
    intrinsic.height = view.height
    intrinsic.focal_length = 10
    intrinsic.sensor_width = 10
    view.intrinsic = scene.add_intrinsic(intrinsic)

    intrinsic = IntrinsicRadialK3()
    intrinsic.width = view.width
    intrinsic.height = view.height
    intrinsic.focal_length = 15
    intrinsic.dist_params = [1.0, 0.0, 3.0]
    scene.add_intrinsic(intrinsic)

    intrinsic = IntrinsicBrownT2()
    intrinsic.width = view.width
    intrinsic.height = view.height
    intrinsic.focal_length = 15
    intrinsic.dist_params = [1.0, 2.0, 3.0, 4.0, 5.0]
    scene.add_intrinsic(intrinsic)

    # Add the view pose
    pose = Pose()
    pose.rotation = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]], dtype=float)
    view.pose = scene.add_pose(pose)

    scene_to_colmap(scene, "colmap")


if __name__ == '__main__':
    main()
