"""Run Yumi hardware bringup and SLAM with both Ethernet LiDARs filtered and merged."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetRemap


def generate_launch_description():
    pkg = Path(get_package_share_directory('yumi_robot_pkg'))
    slam = Path(get_package_share_directory('slam_toolbox'))

    return LaunchDescription([
        DeclareLaunchArgument('start_robot', default_value='true'),
        DeclareLaunchArgument('start_slam', default_value='true'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('start_state', default_value='true'),
        DeclareLaunchArgument('publish_joint_states', default_value='true'),
        DeclareLaunchArgument('start_agent', default_value='true'),
        DeclareLaunchArgument('start_ekf', default_value='true'),
        DeclareLaunchArgument('start_lidars', default_value='true'),
        DeclareLaunchArgument('start_lidar_processing', default_value='true'),
        DeclareLaunchArgument('start_front_lidar', default_value='true'),
        DeclareLaunchArgument('start_rear_lidar', default_value='true'),
        DeclareLaunchArgument('agent_port', default_value='8888'),
        DeclareLaunchArgument('odom_topic', default_value='/odomfromSTM32'),
        DeclareLaunchArgument('front_lidar_ip', default_value='192.168.3.45'),
        DeclareLaunchArgument('front_lidar_port', default_value='8089'),
        DeclareLaunchArgument('rear_lidar_ip', default_value='192.168.2.46'),
        DeclareLaunchArgument('rear_lidar_port', default_value='8089'),
        DeclareLaunchArgument('scan_topic', default_value='/merged'),
        GroupAction(condition=IfCondition(LaunchConfiguration('start_robot')), actions=[
            IncludeLaunchDescription(PythonLaunchDescriptionSource(
                str(pkg / 'launch/yumi_hardware.launch.py')),
                launch_arguments={
                    'rviz': 'false',
                    'start_state': LaunchConfiguration('start_state'),
                    'publish_joint_states': LaunchConfiguration('publish_joint_states'),
                    'start_agent': LaunchConfiguration('start_agent'),
                    'start_ekf': LaunchConfiguration('start_ekf'),
                    'start_lidars': LaunchConfiguration('start_lidars'),
                    'start_lidar_processing': LaunchConfiguration('start_lidar_processing'),
                    'start_front_lidar': LaunchConfiguration('start_front_lidar'),
                    'start_rear_lidar': LaunchConfiguration('start_rear_lidar'),
                    'agent_port': LaunchConfiguration('agent_port'),
                    'odom_topic': LaunchConfiguration('odom_topic'),
                    'front_lidar_ip': LaunchConfiguration('front_lidar_ip'),
                    'front_lidar_port': LaunchConfiguration('front_lidar_port'),
                    'rear_lidar_ip': LaunchConfiguration('rear_lidar_ip'),
                    'rear_lidar_port': LaunchConfiguration('rear_lidar_port'),
                }.items()),
        ]),
        GroupAction(condition=IfCondition(LaunchConfiguration('start_slam')), actions=[
            SetRemap(src='/merged', dst=LaunchConfiguration('scan_topic')),
            IncludeLaunchDescription(PythonLaunchDescriptionSource(
                str(slam / 'launch/online_async_launch.py')),
                launch_arguments={
                    'use_sim_time': 'false',
                    'autostart': 'true',
                    'use_lifecycle_manager': 'false',
                    'slam_params_file': str(pkg / 'config/mapper_params_online_async.yaml'),
                }.items()),
        ]),
        Node(package='rviz2', executable='rviz2',
             condition=IfCondition(LaunchConfiguration('rviz')),
             arguments=['-d', str(pkg / 'rviz/mapping.rviz')],
             parameters=[{'use_sim_time': False}]),
    ])
