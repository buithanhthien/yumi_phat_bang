"""Check effective RViz startup without running Gazebo or opening windows."""
import importlib.util
from pathlib import Path
import unittest

from launch import LaunchContext
from launch.actions import EmitEvent, ExecuteProcess, RegisterEventHandler
from launch.utilities import normalize_to_list_of_substitutions, perform_substitutions
from launch_ros.actions import Node


def planned_nodes(overrides):
    path = Path(__file__).resolve().parents[1] / 'launch/mapping_sim.launch.py'
    spec = importlib.util.spec_from_file_location('yumi_mapping_launch', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    context = LaunchContext()
    context.launch_configurations.update(overrides)
    nodes = []

    def walk(entity):
        condition = getattr(entity, 'condition', None)
        if condition is not None and not condition.evaluate(context):
            return
        if isinstance(entity, Node):
            nodes.append(perform_substitutions(context, normalize_to_list_of_substitutions(entity.node_package)))
            return
        if isinstance(entity, (ExecuteProcess, EmitEvent, RegisterEventHandler)):
            return
        for child in entity.visit(context) or []:
            walk(child)

    walk(module.generate_launch_description())
    return nodes


class MappingLaunchTest(unittest.TestCase):
    def test_default_starts_one_mapping_rviz(self):
        self.assertEqual(planned_nodes({}).count('rviz2'), 1)

    def test_rviz_can_be_disabled(self):
        self.assertEqual(planned_nodes({'rviz': 'false'}).count('rviz2'), 0)

    def test_attach_mode_starts_rviz_without_simulation(self):
        nodes = planned_nodes({'start_simulation': 'false'})
        self.assertEqual(nodes.count('rviz2'), 1)
        self.assertIn('slam_toolbox', nodes)
        self.assertNotIn('ros_gz_sim', nodes)
        self.assertNotIn('robot_state_publisher', nodes)


if __name__ == '__main__':
    unittest.main()
