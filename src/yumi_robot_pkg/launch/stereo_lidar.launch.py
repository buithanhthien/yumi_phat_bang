#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, GroupAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import PushRosNamespace
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    sllidar_launch = PathJoinSubstitution([
        FindPackageShare('sllidar_ros2'),
        'launch',
        'sllidar_s2e_launch.py'
    ])

    # ============================================================
    # FRONT LiDAR
    # PC:
    #   192.168.3.150
    #
    # LiDAR:
    #   192.168.3.45
    # ============================================================

    front_lidar = GroupAction(condition=IfCondition(LaunchConfiguration('start_front_lidar')), actions=[
        PushRosNamespace('front_lidar'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(sllidar_launch),
            launch_arguments={
                'channel_type': 'udp',
                'udp_ip': LaunchConfiguration('front_lidar_ip'),
                'udp_port': LaunchConfiguration('front_lidar_port'),
                'frame_id': 'front_lidar_link',
                'inverted': 'false',
                'angle_compensate': 'true',
                'scan_mode': 'Sensitivity',
            }.items()
        )
    ])

    # ============================================================
    # REAR LiDAR
    # PC:
    #   192.168.2.150
    #
    # LiDAR:
    #   192.168.2.46
    # ============================================================

    rear_lidar = GroupAction(condition=IfCondition(LaunchConfiguration('start_rear_lidar')), actions=[
        PushRosNamespace('rear_lidar'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(sllidar_launch),
            launch_arguments={
                'channel_type': 'udp',
                'udp_ip': LaunchConfiguration('rear_lidar_ip'),
                'udp_port': LaunchConfiguration('rear_lidar_port'),
                'frame_id': 'rear_lidar_link',
                'inverted': 'false',
                'angle_compensate': 'true',
                'scan_mode': 'Sensitivity',
            }.items()
        )
    ])

    return LaunchDescription([
        DeclareLaunchArgument('front_lidar_ip', default_value='192.168.3.45'),
        DeclareLaunchArgument('front_lidar_port', default_value='8089'),
        DeclareLaunchArgument('rear_lidar_ip', default_value='192.168.2.46'),
        DeclareLaunchArgument('rear_lidar_port', default_value='8089'),
        DeclareLaunchArgument('start_front_lidar', default_value='true'),
        DeclareLaunchArgument('start_rear_lidar', default_value='true'),
        front_lidar,
        rear_lidar,
    ])
