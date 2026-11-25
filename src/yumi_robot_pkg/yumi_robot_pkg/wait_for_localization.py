"""Wait for a fresh AMCL/EKF transform before starting Nav2 lifecycle nodes."""
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformException, TransformListener


class WaitForLocalization(Node):
    def __init__(self, **node_options):
        super().__init__('wait_for_localization', **node_options)
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('max_tf_age', 1.0)
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        self.ready = False
        self.last_notice = float('-inf')
        self.timer = self.create_timer(0.25, self.check)

    def check(self):
        map_frame = self.get_parameter('map_frame').value
        odom_frame = self.get_parameter('odom_frame').value
        base_frame = self.get_parameter('base_frame').value
        try:
            # Require both edges: an unrelated map frame alone is insufficient.
            self.buffer.lookup_transform(map_frame, odom_frame, Time())
            self.buffer.lookup_transform(odom_frame, base_frame, Time())
            transform = self.buffer.lookup_transform(map_frame, base_frame, Time())
            stamp = Time.from_msg(transform.header.stamp)
            age = (self.get_clock().now() - stamp).nanoseconds / 1e9
            if stamp.nanoseconds and abs(age) <= self.get_parameter('max_tf_age').value:
                self.ready = True
                self.get_logger().info('Localization TF ready; starting navigation.')
                self.timer.cancel()
                return
        except TransformException:
            pass
        if time.monotonic() - self.last_notice >= 10.0:
            self.get_logger().info(
                'Waiting for fresh map -> odom -> base_link TF. '
                'Set the robot location and heading with RViz 2D Pose Estimate.')
            self.last_notice = time.monotonic()


def main(args=None):
    rclpy.init(args=args)
    node = WaitForLocalization()
    result = 130
    try:
        while rclpy.ok() and not node.ready:
            rclpy.spin_once(node, timeout_sec=0.5)
        if node.ready:
            result = 0
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    raise SystemExit(result)


if __name__ == '__main__':
    main()
