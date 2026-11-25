from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='dual_laser_merger',
            executable='dual_laser_merger_node',
            name='dual_laser_merger',
            output='screen',
            parameters=[{
                'laser_1_topic': '/scan_front_lidar_filter',
                'laser_2_topic': '/scan_rear_lidar_filter',

                'merged_scan_topic': '/merged',

                'target_frame': 'base_link',

                # CAD base_link is above both laser planes (z about -0.018 m).
                # The merger's default min_height is positive and drops every
                # point in this model unless a negative lower bound is set.
                'min_height': -1.0,
                'max_height': 1.0,

                'angle_min': -3.1415926535,
                'angle_max':  3.1415926535,
                'angle_increment': 0.003482897,

                'range_min': 0.15,
                'range_max': 16.0,

                'use_inf': True
            }]
        )
    ])