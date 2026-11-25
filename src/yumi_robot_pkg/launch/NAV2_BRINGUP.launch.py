"""Bring up Yumi hardware, merged LiDAR localization, and navigation."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, TimerAction, RegisterEventHandler, LogInfo
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


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
        'rviz_config': str(pkg / 'rviz/nav2_view.rviz'),
    }
    hardware = include('yumi_hardware.launch.py', {
        name: LaunchConfiguration(name) for name in hardware_defaults if name != 'rviz'} | {'rviz': 'false'})
    common = {name: LaunchConfiguration(name)
              for name in ('use_sim_time', 'params_file')}
    localization = include('yumi_localization.launch.py', {
        **common, 'map': LaunchConfiguration('map')})
    navigation = include('yumi_navigation.launch.py', {
        **common, 'start_velocity_arbiter': LaunchConfiguration('start_velocity_arbiter')})

    readiness = Node(
        package='yumi_robot_pkg', executable='wait_for_localization',
        name='wait_for_localization', output='screen',
        parameters=[{'use_sim_time': ParameterValue(
            LaunchConfiguration('use_sim_time'), value_type=bool)}])

    def navigation_after_localization(event, context):
        if context.is_shutdown:
            return []
        if event.returncode == 0:
            return [navigation]
        return [LogInfo(msg='Localization readiness check stopped; navigation was not started.')]

    return LaunchDescription([
        DeclareLaunchArgument('start_robot', default_value='true',
                              description='False when yumi_hardware is already running'),
        DeclareLaunchArgument('start_velocity_arbiter', default_value='true'),
        DeclareLaunchArgument('wait_for_localization', default_value='true',
                              description='Start navigation after a fresh AMCL/EKF TF is available'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('map', default_value=str(pkg / 'maps/X5_19102026.yaml')),
        DeclareLaunchArgument('params_file', default_value=str(pkg / 'config/nav2_params.yaml')),
        DeclareLaunchArgument('ekf_startup_delay', default_value='0.0',
                              description='Delay localization/navigation startup; not a TF readiness check'),
        *[DeclareLaunchArgument(name, default_value=value)
          for name, value in hardware_defaults.items()],
        GroupAction(condition=IfCondition(LaunchConfiguration('start_robot')),
                    actions=[hardware]),
        # RViz belongs to the navigation UI, including attach-to-hardware mode.
        Node(package='rviz2', executable='rviz2', name='rviz', output='screen',
             condition=IfCondition(LaunchConfiguration('rviz')),
             arguments=['-d', LaunchConfiguration('rviz_config')],
             parameters=[{'use_sim_time': ParameterValue(
                 LaunchConfiguration('use_sim_time'), value_type=bool)}]),
        TimerAction(period=LaunchConfiguration('ekf_startup_delay'),
                    actions=[
                        localization,
                        GroupAction(condition=IfCondition(LaunchConfiguration('wait_for_localization')),
                            actions=[RegisterEventHandler(OnProcessExit(
                                target_action=readiness,
                                on_exit=navigation_after_localization)), readiness]),
                        GroupAction(condition=UnlessCondition(LaunchConfiguration('wait_for_localization')),
                            actions=[navigation]),
                    ]),
    ])
