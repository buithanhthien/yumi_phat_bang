"""Filter and merge Yumi's two LiDARs using the Zackon topic pipeline."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    pkg = Path(get_package_share_directory('yumi_robot_pkg'))
    return LaunchDescription([
        IncludeLaunchDescription(PythonLaunchDescriptionSource(
            str(pkg / 'launch' / filename)))
        for filename in ('front_lidar_filter.launch.py',
                         'rear_lidar_filter.launch.py', 'merge_lidar.launch.py')
    ])
