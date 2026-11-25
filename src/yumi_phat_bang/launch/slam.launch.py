"""Attach SLAM Toolbox and mapping RViz to the running Yumi simulation."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, GroupAction,
                            IncludeLaunchDescription, SetEnvironmentVariable)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetRemap


def generate_launch_description():
    pkg = Path(get_package_share_directory('yumi_phat_bang'))
    slam_pkg = Path(get_package_share_directory('slam_toolbox'))
    return LaunchDescription([
        DeclareLaunchArgument('sim_domain_id', default_value='78'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('scan_topic', default_value='/front_lidar/scan',
                              description='Single LaserScan topic consumed by SLAM'),
        DeclareLaunchArgument('slam_params_file',
                              default_value=str(pkg / 'config/slam_sim.yaml')),
        SetEnvironmentVariable('ROS_DOMAIN_ID', LaunchConfiguration('sim_domain_id')),
        SetEnvironmentVariable('ROS_AUTOMATIC_DISCOVERY_RANGE', 'LOCALHOST'),
        GroupAction([
            SetRemap(src='/front_lidar/scan', dst=LaunchConfiguration('scan_topic')),
            IncludeLaunchDescription(PythonLaunchDescriptionSource(
                str(slam_pkg / 'launch/online_async_launch.py')),
                launch_arguments={'use_sim_time': 'true', 'autostart': 'true',
                                  'use_lifecycle_manager': 'false',
                                  'slam_params_file': LaunchConfiguration('slam_params_file')}.items()),
        ]),
        Node(package='rviz2', executable='rviz2',
             condition=IfCondition(LaunchConfiguration('rviz')),
             arguments=['-d', str(pkg / 'rviz/mapping.rviz')],
             parameters=[{'use_sim_time': True}]),
    ])
