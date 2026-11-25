"""Localize Yumi on the saved X5 map using AMCL and both LiDARs."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg = Path(get_package_share_directory('yumi_robot_pkg'))

    def include(filename, arguments):
        return IncludeLaunchDescription(PythonLaunchDescriptionSource(
            str(pkg / 'launch' / filename)), launch_arguments=arguments.items())

    hardware_defaults = {
        'start_state': 'true', 'start_agent': 'true', 'start_ekf': 'true',
        'start_lidars': 'true', 'start_lidar_processing': 'true',
        'start_front_lidar': 'true', 'start_rear_lidar': 'true',
        'agent_port': '8888', 'odom_topic': '/odomfromSTM32',
        'front_lidar_ip': '192.168.3.45', 'front_lidar_port': '8089',
        'rear_lidar_ip': '192.168.2.46', 'rear_lidar_port': '8089',
        'rviz': 'true', 'publish_joint_states': 'true',
        'rviz_config': str(pkg / 'rviz/localization.rviz'),
    }
    hardware = include('yumi_hardware.launch.py', {
        name: LaunchConfiguration(name) for name in hardware_defaults})
    common = {name: LaunchConfiguration(name)
              for name in ('use_sim_time', 'params_file')}
    localization = include('yumi_localization.launch.py', {
        **common, 'map': LaunchConfiguration('map'),
        'set_initial_pose': LaunchConfiguration('set_initial_pose')})

    return LaunchDescription([
        DeclareLaunchArgument('start_robot', default_value='true',
                              description='False when yumi_hardware is already running'),
        DeclareLaunchArgument('set_initial_pose', default_value='false',
                              description='Wait for RViz 2D Pose Estimate by default'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('map', default_value=str(pkg / 'maps/X5_19102026.yaml')),
        DeclareLaunchArgument('params_file', default_value=str(pkg / 'config/nav2_params.yaml')),
        DeclareLaunchArgument('ekf_startup_delay', default_value='0.0',
                              description='Delay localization startup; not a TF readiness check'),
        *[DeclareLaunchArgument(name, default_value=value)
          for name, value in hardware_defaults.items()],
        GroupAction(condition=IfCondition(LaunchConfiguration('start_robot')),
                    actions=[hardware]),
        TimerAction(period=LaunchConfiguration('ekf_startup_delay'),
                    actions=[localization]),
    ])
