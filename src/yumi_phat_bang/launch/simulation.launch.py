"""Gazebo base smoke test; no hardware drivers, SLAM or Nav2 are started."""
import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            RegisterEventHandler, EmitEvent, SetEnvironmentVariable)
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg = Path(get_package_share_directory('yumi_phat_bang'))
    gz_launch = str(Path(get_package_share_directory('ros_gz_sim')) / 'launch/gz_sim.launch.py')
    world = LaunchConfiguration('world')
    urdf = str(pkg / 'urdf/yumi_phat_bang.sim.urdf')
    spawn = Node(package='ros_gz_sim', executable='create', output='screen',
                 arguments=['-world', LaunchConfiguration('world_name'), '-file', urdf,
                            '-name', 'yumi', '-z', '0.165'])
    return LaunchDescription([
        DeclareLaunchArgument('headless', default_value='false'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('sim_domain_id', default_value='78'),
        DeclareLaunchArgument('world', default_value=str(pkg / 'worlds/base_test.sdf')),
        DeclareLaunchArgument('world_name', default_value='yumi_base_test'),
        DeclareLaunchArgument('gz_partition', default_value='yumi_base_test'),
        SetEnvironmentVariable('ROS_DOMAIN_ID', LaunchConfiguration('sim_domain_id')),
        SetEnvironmentVariable('ROS_AUTOMATIC_DISCOVERY_RANGE', 'LOCALHOST'),
        SetEnvironmentVariable('GZ_PARTITION', LaunchConfiguration('gz_partition')),
        SetEnvironmentVariable('GZ_SIM_RESOURCE_PATH', [
            str(pkg.parent), os.pathsep,
            EnvironmentVariable('GZ_SIM_RESOURCE_PATH', default_value='')]),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(gz_launch),
            condition=UnlessCondition(LaunchConfiguration('headless')),
            launch_arguments={'gz_args': ['-r ', world], 'on_exit_shutdown': 'true'}.items()),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(gz_launch),
            condition=IfCondition(LaunchConfiguration('headless')),
            launch_arguments={'gz_args': ['-r -s --headless-rendering ', world],
                              'on_exit_shutdown': 'true'}.items()),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(pkg / 'launch/view_robot.launch.py')),
            launch_arguments={'use_sim_time': 'true', 'publish_joint_states': 'false',
                              'urdf': urdf, 'rviz': LaunchConfiguration('rviz')}.items()),
        Node(package='ros_gz_bridge', executable='parameter_bridge', output='screen',
             parameters=[{'config_file': str(pkg / 'config/sim_bridge.yaml'),
                          'use_sim_time': True}]),
        RegisterEventHandler(OnProcessExit(target_action=spawn,
            on_exit=lambda event, context: [EmitEvent(event=Shutdown(reason='Robot spawn failed'))]
            if event.returncode != 0 else [])),
        spawn,
    ])
