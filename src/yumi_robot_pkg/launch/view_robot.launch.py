"""Adapted from yumi_robot_pkg; joint publishers are optional for live feedback."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg = Path(get_package_share_directory('yumi_robot_pkg'))
    sim_time = ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)
    publish = LaunchConfiguration('publish_joint_states')
    gui = LaunchConfiguration('use_gui')
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('publish_joint_states', default_value='true'),
        DeclareLaunchArgument('use_gui', default_value='false'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('rviz_config', default_value=str(pkg / 'rviz/default_view.rviz')),
        DeclareLaunchArgument('urdf', default_value=str(pkg / 'urdf/robot_description.urdf')),
        # Read an explicitly selected URDF at launch execution time.
        _description_nodes(pkg, sim_time, publish, gui),
    ])


def _description_nodes(pkg, sim_time, publish, gui):
    from launch.actions import OpaqueFunction

    def create(context):
        description = Path(LaunchConfiguration('urdf').perform(context)).read_text()
        params = [{'robot_description': description, 'use_sim_time': sim_time}]
        return [
            Node(package='robot_state_publisher', executable='robot_state_publisher',
                 parameters=params, output='screen'),
            Node(package='joint_state_publisher', executable='joint_state_publisher',
                 condition=IfCondition(PythonExpression([
                     "'", publish, "'.lower() == 'true' and '", gui,
                     "'.lower() != 'true'"])), parameters=[{'use_sim_time': sim_time}]),
            Node(package='joint_state_publisher_gui', executable='joint_state_publisher_gui',
                 condition=IfCondition(PythonExpression([
                     "'", publish, "'.lower() == 'true' and '", gui,
                     "'.lower() == 'true'"])), parameters=[{'use_sim_time': sim_time}]),
            Node(package='rviz2', executable='rviz2',
                 condition=IfCondition(LaunchConfiguration('rviz')),
                 arguments=['-d', LaunchConfiguration('rviz_config')],
                 parameters=[{'use_sim_time': sim_time}]),
        ]
    return OpaqueFunction(function=create)
