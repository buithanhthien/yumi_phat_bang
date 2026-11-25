"""Exercise TF startup readiness in a separate domain, without robot drivers."""
import time
from uuid import uuid4

import pytest
import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from geometry_msgs.msg import TransformStamped
from tf2_ros import StaticTransformBroadcaster, TransformBroadcaster
from yumi_robot_pkg.wait_for_localization import WaitForLocalization


@pytest.fixture
def readiness():
    context = Context()
    rclpy.init(context=context, domain_id=127)
    helper = WaitForLocalization(context=context)
    prefix = 'readiness_' + uuid4().hex
    frames = [prefix + suffix for suffix in ('_map', '_odom', '_base')]
    helper.set_parameters([
        Parameter('map_frame', value=frames[0]),
        Parameter('odom_frame', value=frames[1]),
        Parameter('base_frame', value=frames[2]),
    ])
    publisher = Node(prefix + '_publisher', context=context)
    static = StaticTransformBroadcaster(publisher)
    dynamic = TransformBroadcaster(publisher)
    executor = SingleThreadedExecutor(context=context)
    executor.add_node(helper)
    executor.add_node(publisher)

    def transform(parent, child, seconds_old=0.0):
        msg = TransformStamped()
        msg.header.frame_id, msg.child_frame_id = parent, child
        stamp = publisher.get_clock().now().nanoseconds - int(seconds_old * 1e9)
        msg.header.stamp.sec, msg.header.stamp.nanosec = divmod(stamp, 10**9)
        msg.transform.rotation.w = 1.0
        return msg

    def spin(seconds, action=None, until=None):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if action is not None:
                action()
            executor.spin_once(timeout_sec=0.05)
            if until is not None and until():
                return True
        return False

    yield helper, frames, static, dynamic, transform, spin
    executor.shutdown()
    helper.destroy_node()
    publisher.destroy_node()
    context.shutdown()


def test_waits_for_initial_pose_then_accepts_fresh_localization(readiness):
    helper, frames, static, dynamic, transform, spin = readiness
    map_frame, odom, base = frames
    spin(0.8, lambda: dynamic.sendTransform(transform(odom, base)))
    assert not helper.ready, 'Odometry alone must not start navigation'
    static.sendTransform(transform(map_frame, odom))
    assert spin(4.0, lambda: dynamic.sendTransform(transform(odom, base)),
                until=lambda: helper.ready)


def test_stale_tf_does_not_start_navigation(readiness):
    helper, frames, static, dynamic, transform, spin = readiness
    map_frame, odom, base = frames
    static.sendTransform(transform(map_frame, odom))
    spin(1.2, lambda: dynamic.sendTransform(transform(odom, base, seconds_old=3.0)))
    assert helper.buffer.can_transform(map_frame, base, rclpy.time.Time())
    assert not helper.ready, 'Stale cached odometry must not start navigation'
