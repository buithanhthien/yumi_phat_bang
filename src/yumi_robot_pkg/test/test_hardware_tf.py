"""Regression checks for missing wheel TF and duplicate hardware launches."""
import ast
import importlib.util
from collections import Counter
from pathlib import Path
from unittest.mock import patch
import yaml
from launch import LaunchContext
from launch.actions import EmitEvent, ExecuteProcess, RegisterEventHandler, TimerAction
from launch.utilities import normalize_to_list_of_substitutions, perform_substitutions
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory as original_share

root = Path(__file__).resolve().parents[1]
def share(name):
    if name == 'yumi_robot_pkg': return str(root)
    if name in ('yumi_phat_bang', 'sllidar_ros2'):
        return str(root.parent / name)
    return original_share(name)

def graph(filename, overrides=None):
    context = LaunchContext()
    context.launch_configurations.update(overrides or {})
    nodes = []
    def subst(value):
        return perform_substitutions(context, normalize_to_list_of_substitutions(value))
    def walk(entity):
        condition = getattr(entity, 'condition', None)
        if condition is not None and not condition.evaluate(context): return
        if isinstance(entity, Node):
            nodes.append((subst(entity.node_executable), entity))
            return
        if isinstance(entity, TimerAction):
            for child in entity.actions: walk(child)
            return
        if isinstance(entity, (ExecuteProcess, EmitEvent, RegisterEventHandler)): return
        for child in entity.visit(context) or []: walk(child)
    with patch('ament_index_python.packages.get_package_share_directory', side_effect=share):
        spec=importlib.util.spec_from_file_location('checked_launch', root/'launch'/filename)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        walk(module.generate_launch_description())
    return Counter(name for name, _ in nodes), nodes


def test_default_hardware_launches_supply_wheel_joint_states():
    for filename in ('yumi_hardware.launch.py', 'MAP_GENERATING.launch.py',
                     'NAV2_BRINGUP.launch.py'):
        counts, _ = graph(filename, {'rviz': 'false'})
        for name, expected in {'joint_state_publisher': 1, 'robot_state_publisher': 1,
                               'micro_ros_agent': 1, 'ekf_node': 1,
                               'odom_frame_publisher': 1, 'sllidar_node': 2,
                               'scan_to_scan_filter_chain': 2,
                               'dual_laser_merger_node': 1}.items():
            assert counts[name] == expected, (filename, name, counts)


def test_real_joint_feedback_disables_fallback():
    for filename in ('yumi_hardware.launch.py', 'MAP_GENERATING.launch.py',
                     'NAV2_BRINGUP.launch.py'):
        counts, _ = graph(filename, {'rviz': 'false', 'publish_joint_states': 'false'})
        assert counts['joint_state_publisher'] == 0
        assert counts['robot_state_publisher'] == 1


def test_attach_mode_does_not_duplicate_hardware_or_joint_publisher():
    for filename in ('MAP_GENERATING.launch.py', 'NAV2_BRINGUP.launch.py'):
        counts, _ = graph(filename, {'rviz': 'false', 'start_robot': 'false'})
        for name in ('joint_state_publisher', 'robot_state_publisher', 'ekf_node',
                     'micro_ros_agent', 'sllidar_node', 'dual_laser_merger_node'):
            assert counts[name] == 0, (filename, name)


def test_wheel_tree_and_renamed_mesh_resources():
    import xml.etree.ElementTree as ET
    robot = ET.parse(root / 'urdf/robot_description.urdf').getroot()
    for joint_name, link in [('leftwheel_joint', 'leftwheel_link'),
                             ('rightwheel_joint', 'rightwheel_link')]:
        joint = robot.find("joint[@name='%s']" % joint_name)
        assert joint.attrib['type'] == 'continuous'
        assert joint.find('parent').attrib['link'] == 'base_link'
        assert joint.find('child').attrib['link'] == link
    prefix = 'package://yumi_robot_pkg/'
    for mesh in robot.findall('.//mesh'):
        uri = mesh.attrib['filename']
        assert uri.startswith(prefix)
        assert (root / uri[len(prefix):]).is_file(), uri


def test_merger_accepts_both_lidar_planes_and_matches_slam_topic():
    import xml.etree.ElementTree as ET
    from launch_ros.utilities import evaluate_parameters
    _, nodes = graph('merge_lidar.launch.py')
    merger = next(node for name, node in nodes if name == 'dual_laser_merger_node')
    params = evaluate_parameters(LaunchContext(), merger._Node__parameters)[0]
    assert params['target_frame'] == 'base_link'
    robot = ET.parse(root / 'urdf/robot_description.urdf').getroot()
    # Regression: the merger default min_height excludes the negative Yumi
    # laser-plane elevations, producing only infinity ranges and an empty map.
    for name in ('front_lidar_joint', 'rear_lidar_joint'):
        joint = robot.find("joint[@name='%s']" % name)
        assert joint.find('parent').attrib['link'] == params['target_frame']
        z = float(joint.find('origin').attrib['xyz'].split()[2])
        assert params['min_height'] <= z <= params['max_height'], name
    config = yaml.safe_load((root / 'config/mapper_params_online_async.yaml').read_text())
    assert params['merged_scan_topic'] == config['slam_toolbox']['ros__parameters']['scan_topic']


def test_localization_uses_saved_map_without_slam_or_navigation_commands():
    from launch_ros.utilities import evaluate_parameters
    counts, nodes = graph('LOCALIZATION.launch.py', {'rviz': 'false'})
    for name in ('amcl', 'map_server', 'joint_state_publisher', 'ekf_node',
                 'dual_laser_merger_node'):
        assert counts[name] == 1
    for name in ('async_slam_toolbox_node', 'sync_slam_toolbox_node',
                 'controller_server', 'velocity_arbiter'):
        assert counts[name] == 0
    config = yaml.safe_load((root / 'maps/X5_19102026.yaml').read_text())
    assert (root / 'maps' / config['image']).is_file()
    # Confirm the explicit file override and avoid assuming the robot starts
    # at the old map origin: localization waits for a user initial pose.
    assert (root / 'maps/X5_19102026.yaml').is_file()
    rviz = yaml.safe_load((root / 'rviz/localization.rviz').read_text())
    tools = rviz['Visualization Manager']['Tools']
    assert any(tool['Class'] == 'rviz_default_plugins/SetInitialPose' for tool in tools)


def test_localization_can_attach_to_existing_hardware():
    counts, _ = graph('LOCALIZATION.launch.py', {'rviz': 'false', 'start_robot': 'false'})
    assert counts['amcl'] == 1 and counts['map_server'] == 1
    for name in ('micro_ros_agent', 'ekf_node', 'robot_state_publisher',
                 'joint_state_publisher', 'sllidar_node', 'dual_laser_merger_node'):
        assert counts[name] == 0
