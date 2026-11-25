"""Bring up Yumi's STM32 odometry and Ethernet LiDARs without motor commands."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg = Path(get_package_share_directory('yumi_robot_pkg'))
    state_launch = str(pkg / 'launch/view_robot.launch.py')
    lidar_launch = str(pkg / 'launch/stereo_lidar.launch.py')

    return LaunchDescription([
        DeclareLaunchArgument('agent_port', default_value='8888'),
        DeclareLaunchArgument('odom_topic', default_value='/odomfromSTM32'),
        DeclareLaunchArgument('front_lidar_ip', default_value='192.168.3.45'),
        DeclareLaunchArgument('front_lidar_port', default_value='8089'),
        DeclareLaunchArgument('rear_lidar_ip', default_value='192.168.2.46'),
        DeclareLaunchArgument('rear_lidar_port', default_value='8089'),
        DeclareLaunchArgument('start_state', default_value='true'),
        DeclareLaunchArgument('start_agent', default_value='true'),
        DeclareLaunchArgument('start_ekf', default_value='true'),
        DeclareLaunchArgument('start_lidars', default_value='true'),
        DeclareLaunchArgument('start_lidar_processing', default_value='true'),
        DeclareLaunchArgument('start_front_lidar', default_value='true'),
        DeclareLaunchArgument('start_rear_lidar', default_value='true'),
        DeclareLaunchArgument('rviz', default_value='false'),
        DeclareLaunchArgument('rviz_config', default_value=str(pkg / 'rviz/odom_view.rviz')),
        DeclareLaunchArgument('publish_joint_states', default_value='true',
                              description='Publish zero wheel angles for TF; disable with real joint feedback'),

        GroupAction(condition=IfCondition(LaunchConfiguration('start_state')), actions=[
            IncludeLaunchDescription(PythonLaunchDescriptionSource(state_launch),
                launch_arguments={
                    'use_sim_time': 'false',
                    'publish_joint_states': LaunchConfiguration('publish_joint_states'),
                    'rviz': LaunchConfiguration('rviz'),
                    'rviz_config': LaunchConfiguration('rviz_config'),
                }.items()),
        ]),
        Node(package='micro_ros_agent', executable='micro_ros_agent',
             name='micro_ros_agent', output='screen',
             condition=IfCondition(LaunchConfiguration('start_agent')),
             arguments=['udp4', '--port', LaunchConfiguration('agent_port')]),
        GroupAction(condition=IfCondition(LaunchConfiguration('start_ekf')), actions=[
            Node(package='yumi_robot_pkg', executable='odom_frame_publisher',
                 name='odom_frame_publisher', output='screen',
                 parameters=[{
                     'input_topic': LaunchConfiguration('odom_topic'),
                     'output_topic': '/odom/stm32',
                     'frame_id': 'odom',
                     'child_frame_id': 'base_link',
                 }]),
            Node(package='robot_localization', executable='ekf_node',
                 name='ekf_filter_node', output='screen',
                 parameters=[str(pkg / 'config/ekf.yaml')]),
        ]),
        GroupAction(condition=IfCondition(LaunchConfiguration('start_lidars')), actions=[
            IncludeLaunchDescription(PythonLaunchDescriptionSource(lidar_launch),
                launch_arguments={
                    'front_lidar_ip': LaunchConfiguration('front_lidar_ip'),
                    'front_lidar_port': LaunchConfiguration('front_lidar_port'),
                    'rear_lidar_ip': LaunchConfiguration('rear_lidar_ip'),
                    'rear_lidar_port': LaunchConfiguration('rear_lidar_port'),
                    'start_front_lidar': LaunchConfiguration('start_front_lidar'),
                    'start_rear_lidar': LaunchConfiguration('start_rear_lidar'),
                }.items()),
            GroupAction(condition=IfCondition(LaunchConfiguration('start_lidar_processing')),
                actions=[IncludeLaunchDescription(PythonLaunchDescriptionSource(
                    str(pkg / 'launch/lidar_processing.launch.py')))]),
        ]),
    ])
