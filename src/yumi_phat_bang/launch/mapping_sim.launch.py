"""Start the obstacle world and SLAM; keyboard control runs in another terminal."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg = Path(get_package_share_directory('yumi_phat_bang'))
    return LaunchDescription([
        DeclareLaunchArgument('start_simulation', default_value='true',
                              description='Set false to attach to an existing simulation'),
        DeclareLaunchArgument('headless', default_value='false'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('sim_domain_id', default_value='78'),
        DeclareLaunchArgument('gz_partition', default_value='yumi_mapping'),
        DeclareLaunchArgument('world', default_value=str(pkg / 'worlds/mapping.sdf')),
        DeclareLaunchArgument('world_name', default_value='yumi_mapping'),
        DeclareLaunchArgument('scan_topic', default_value='/front_lidar/scan'),
        # Keep simulation's rviz=false local; mapping keeps the user's rviz option.
        GroupAction([IncludeLaunchDescription(PythonLaunchDescriptionSource(
            str(pkg / 'launch/simulation.launch.py')),
            condition=IfCondition(LaunchConfiguration('start_simulation')),
            launch_arguments={
                'headless': LaunchConfiguration('headless'), 'rviz': 'false',
                'sim_domain_id': LaunchConfiguration('sim_domain_id'),
                'gz_partition': LaunchConfiguration('gz_partition'),
                'world': LaunchConfiguration('world'),
                'world_name': LaunchConfiguration('world_name')}.items())]),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(
            str(pkg / 'launch/slam.launch.py')),
            launch_arguments={'rviz': LaunchConfiguration('rviz'),
                              'sim_domain_id': LaunchConfiguration('sim_domain_id'),
                              'scan_topic': LaunchConfiguration('scan_topic')}.items()),
    ])
