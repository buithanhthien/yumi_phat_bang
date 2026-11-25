"""Session-private navigation; shared robot drivers and arbiter stay outside."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, RegisterEventHandler, EmitEvent
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_nodes(context):
    namespace = LaunchConfiguration('namespace').perform(context)
    params = LaunchConfiguration('params_file').perform(context)
    nodes = [('nav2_collision_monitor', 'collision_monitor'),
             ('nav2_velocity_smoother', 'velocity_smoother'),
             ('nav2_planner', 'planner_server'),
             ('nav2_controller', 'controller_server'),
             ('nav2_bt_navigator', 'bt_navigator')]
    actions = []
    for package, executable in nodes:
        remaps = []
        if executable == 'controller_server':
            remaps = [('cmd_vel', 'cmd_vel_nav')]
        elif executable == 'velocity_smoother':
            remaps = [('cmd_vel', 'cmd_vel_nav')]
        actions.append(Node(package=package, executable=executable, name=executable,
                            namespace=namespace, parameters=[params], remappings=remaps,
                            output='screen'))
    actions.append(Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
                        name='lifecycle_manager', namespace=namespace, output='screen',
                        parameters=[{'autostart': True, 'bond_timeout': 4.0,
                                     'node_names': [name for _, name in nodes]}]))
    # A failed lifecycle child must not leave a healthy-looking launch parent.
    handlers = [RegisterEventHandler(OnProcessExit(
        target_action=action,
        on_exit=[EmitEvent(event=Shutdown(reason='Owned exploration node exited'))]))
        for action in actions]
    return actions + handlers


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('namespace'), DeclareLaunchArgument('params_file'),
        OpaqueFunction(function=launch_nodes),
    ])
