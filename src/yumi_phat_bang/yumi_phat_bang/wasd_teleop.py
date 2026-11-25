"""Control the simulated base with W/A/S/D from a terminal."""

import select
import sys
import termios
import time
import tty

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions


def command_for_key(key, speed, turn):
    """Return a Twist for a movement key, or None for an unrelated key."""
    command = Twist()
    if key == 'w':
        command.linear.x = speed
    elif key == 's':
        command.linear.x = -speed
    elif key == 'a':
        command.angular.z = turn
    elif key == 'd':
        command.angular.z = -turn
    elif key in (' ', 'x'):
        pass
    else:
        return None
    return command


def main():
    # Keep Ctrl+C under Python's handler so the final zero command can publish.
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = Node('wasd_teleop')
    node.declare_parameter('speed', 0.15)
    node.declare_parameter('turn', 0.5)
    speed = node.get_parameter('speed').value
    turn = node.get_parameter('turn').value
    publisher = node.create_publisher(Twist, '/cmd_vel', 10)

    if not sys.stdin.isatty():
        node.get_logger().error('WASD teleop cần chạy trong terminal tương tác.')
        node.destroy_node()
        rclpy.shutdown()
        return 1

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    print('W: tiến | S: lùi | A: quay trái | D: quay phải')
    print('Space hoặc X: dừng | Q hoặc Ctrl+C: thoát')
    print(f'Tốc độ: {speed} m/s; quay: {turn} rad/s')

    try:
        tty.setcbreak(fd)
        while rclpy.ok():
            if not select.select([sys.stdin], [], [], 0.1)[0]:
                continue
            key = sys.stdin.read(1).lower()
            if key == 'q':
                break
            command = command_for_key(key, speed, turn)
            if command is not None:
                publisher.publish(command)
                print(f'Phím: {key if key != " " else "Space"}', flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        publisher.publish(Twist())
        time.sleep(0.1)
        node.destroy_node()
        rclpy.shutdown()
        print('\nĐã dừng robot.')

    return 0


if __name__ == '__main__':
    sys.exit(main())
