#!/usr/bin/env python3
"""Bảng điều khiển robot: bản đồ, waypoint và Nav2 trên ROS 2 Jazzy."""
import os

# Use the same ROS domain as the STM32 and inherited launch processes.
os.environ["ROS_DOMAIN_ID"] = "0"

import json
import re
import math
import time
import uuid
import signal
import subprocess
import sys
import html
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QTextEdit, QStackedWidget)
from PyQt6.QtCore import QEvent, QTimer, Qt, QSize
from PyQt6.QtGui import QFont
import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from rclpy.action import ActionClient
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, qos_profile_sensor_data
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
from rclpy.parameter_client import AsyncParameterClient
import map_utils
from action_msgs.msg import GoalStatus
from action_msgs.srv import CancelGoal
from nav2_msgs.action import NavigateToPose
from nav2_msgs.srv import LoadMap
from config import SETTINGS, SOURCE_PATH, UI_DIRECTORY, shell_source_workspace, robot_command
from map_utils import get_current_map_path, get_current_map_name, update_map_files
from waypoint_store import load_waypoint_file, resolve_waypoint, save_waypoint_file, deletion_reason, route_references
from waypoint_dialogs import DestinationDialog, WaypointPickerDialog, NewWaypointDialog, PathManagerDialog, NewPathDialog, DIALOG_STYLE
from conversation_panel import ConversationPanel, normalize_name
from startup_style import STARTUP_STYLESHEET, startup_text, repolish
from startup_icons import startup_icon
from ui_utils import confirm_dialog, setup_clock_timer, warning_dialog
from new_map_layout import NewMapUI
from load_map_dialog import LoadMapDialog
from mapping_process import MappingProcess, stop_previous_yumi_nav2
from robot_eyes import RobotEyes

class RobotUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self._closing = False
        self._closed = False
        self._latest_pose = None
        self._nav_goal_handle = None
        self._nav_pending = self._nav_cancel_requested = False
        self._navigation_generation = 0
        self._waypoint_queue = []
        self._waypoints_file = str(UI_DIRECTORY / 'waypoints.json')
        self._waypoints = self._load_waypoints()
        self._stm32_last_msg_time = self._front_lidar_last_msg_time = self._rear_lidar_last_msg_time = None
        self.prev_stm32_status = self.prev_lidar_status = self.prev_lidar_rear_status = None
        self._nav_process = self._rviz_process = None
        self._stop_requested = False
        self._cancel_all_future = None
        self._cancel_all_ok = False
        self._arbiter = None
        self._arbiter_stamp = 0.0
        self._ros_node = Node('robot_ui_node')
        self._nav_client = ActionClient(self._ros_node, NavigateToPose, SETTINGS['navigate_action'])
        self._cancel_all = self._ros_node.create_client(CancelGoal, SETTINGS['navigate_action'] + '/_action/cancel_goal')
        self._map_parameters = AsyncParameterClient(self._ros_node, SETTINGS['map_server_node'])
        self._map_loader = self._ros_node.create_client(LoadMap, SETTINGS['load_map_service'])
        self._map_query = None
        self._map_loading = False
        self._map_query_time = 0.0
        self._map_parameter_path = None
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                         reliability=ReliabilityPolicy.RELIABLE)
        self._ros_node.create_subscription(PoseWithCovarianceStamped, SETTINGS['pose_topic'], self._amcl_callback, qos)
        self._ros_node.create_subscription(Odometry, SETTINGS['odom_topic'], self._stm32_odom_callback, qos_profile_sensor_data)
        for side, key in (('front','front_scan_topic'), ('rear','rear_scan_topic')):
            self._ros_node.create_subscription(LaserScan, SETTINGS[key], lambda msg, side=side: self._lidar_callback(side), qos_profile_sensor_data)
        self._ros_node.create_subscription(String, SETTINGS['arbiter_state_topic'], self._arbiter_callback, 1)
        self.init_ui()
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.setInterval(10_000)
        self._idle_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._idle_timer.timeout.connect(self._enter_idle)
        QApplication.instance().installEventFilter(self)
        self._idle_timer.start()
        self._ros_spin_timer = QTimer(self)
        self._ros_spin_timer.timeout.connect(self._spin)
        self._ros_spin_timer.start(30)
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(500)
        self.clock_timer = setup_clock_timer(self.clock_label)

    def init_ui(self):
        self.setWindowTitle('Bảng điều khiển robot')
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.resize(1920, 1080)
        self.setStyleSheet(DIALOG_STYLE + STARTUP_STYLESHEET)
        central = QWidget()
        central.setObjectName('startup-root')
        self._dashboard = central
        self._display = QStackedWidget()
        self.setCentralWidget(self._display)
        self._display.addWidget(self._dashboard)
        self._eyes = RobotEyes()
        self._eyes.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self._display.addWidget(self._eyes)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0,0,0,0)
        sidebar = self._sidebar = QWidget()
        sidebar.setObjectName('left-panel')
        sidebar.setFixedWidth(224)
        menu = QVBoxLayout(sidebar)
        menu.setContentsMargins(16,20,16,16)
        brand = QLabel('ROBOT')
        brand.setObjectName('wordmark')
        menu.addWidget(brand)
        title = QLabel('Tổng quan')
        title.setObjectName('overview-label')
        title.setMinimumHeight(44)
        menu.addWidget(title)
        for text, icon, callback in [('Địa điểm và lộ trình','waypoints',self.open_destination_dialog),
                ('Tải bản đồ','load_map',self.load_map), ('Tạo bản đồ','new_map',self.start_new_map),
                ('Bật Nav2 và RViz','nav2',self.start_nav2),
                ('Tắt Nav2 và RViz','nav2',self.stop_nav2)]:
            button = QPushButton(text)
            button.setObjectName('mode-btn')
            button.setMinimumHeight(52)
            button.setIcon(startup_icon(icon))
            button.setIconSize(QSize(22,22))
            button.clicked.connect(callback)
            menu.addWidget(button)
        menu.addStretch()
        self.stop_button = QPushButton('■  DỪNG')
        self.stop_button.setObjectName('interrupt-btn')
        self.stop_button.setMinimumHeight(64)
        self.stop_button.clicked.connect(self.stop_robot)
        menu.addWidget(self.stop_button)
        self.resume_button = QPushButton('Cho phép chạy lại')
        self.resume_button.setMinimumHeight(48)
        self.resume_button.clicked.connect(self.resume_robot)
        menu.addWidget(self.resume_button)
        hint = QLabel('Đặt vị trí ban đầu của robot trong RViz.')
        hint.setWordWrap(True)
        menu.addWidget(hint)
        self.exit_button = QPushButton('Thoát')
        self.exit_button.setObjectName('mode-btn')
        self.exit_button.setMinimumHeight(48)
        self.exit_button.clicked.connect(self.close)
        menu.addWidget(self.exit_button)
        layout.addWidget(sidebar)
        right = QWidget()
        right.setObjectName('content-panel')
        body = QVBoxLayout(right)
        body.setContentsMargins(24,20,24,20)
        header = QHBoxLayout()
        title = QLabel('Bảng điều khiển robot')
        title.setObjectName('header-title')
        header.addWidget(title,1)
        self.clock_label = QLabel()
        self.clock_label.setObjectName('clock')
        header.addWidget(self.clock_label)
        body.addLayout(header)
        cards = QHBoxLayout()
        self.stm32_card = self._make_status_card('STM32')
        self.front_lidar_card = self._make_status_card('front')
        self.rear_lidar_card = self._make_status_card('rear')
        for card in (self.stm32_card,self.front_lidar_card,self.rear_lidar_card):
            cards.addWidget(card['widget'],1)
        body.addLayout(cards)
        self.navigation_label = QLabel('Điều hướng: chưa khởi động')
        body.addWidget(self.navigation_label)
        self._conversation = ConversationPanel(self._handle_conversation_command, self)
        self._conversation.activity_changed.connect(self._return_to_dashboard)
        body.addWidget(self._conversation, 1)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(120)
        self.log_box.document().setMaximumBlockCount(250)
        body.addWidget(self.log_box)
        layout.addWidget(right,1)

    def _idle_blocked(self):
        mapping = getattr(self, '_new_map_dialog', None)
        return (not self.isVisible() or self._conversation.busy or self._stop_requested or self._navigation_busy()
                or bool(self._arbiter and (self._arbiter.get('navigation_busy')
                                           or self._arbiter.get('emergency_stop')))
                or QApplication.activeModalWidget() is not None
                or bool(mapping and (mapping.isVisible() or mapping.mapping_process is not None)))

    def _enter_idle(self):
        if self._closing or self._closed:
            return
        if self._idle_blocked():
            self._idle_timer.start()
            return
        self._display.setCurrentWidget(self._eyes)

    def _return_to_dashboard(self):
        self._display.setCurrentWidget(self._dashboard)
        self._idle_timer.start()

    def eventFilter(self, watched, event):
        if self._closing or self._closed:
            return super().eventFilter(watched, event)
        wake_events = (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick,
                       QEvent.Type.Wheel, QEvent.Type.KeyPress, QEvent.Type.TouchBegin)
        if event.type() in wake_events:
            if self._display.currentWidget() is self._eyes:
                self._return_to_dashboard()
                # Consume the wake event so it cannot activate dashboard controls.
                event.accept()
                return True
            else:
                self._idle_timer.start()
        return super().eventFilter(watched, event)

    def _spin(self):
        if self._closing or self._closed or not rclpy.ok():
            return
        rclpy.spin_once(self._ros_node, timeout_sec=0)


    def log(self, message):
        print(message)
        if hasattr(self, 'log_box'):
            self.log_box.append(html.escape(str(message)))

    def show_stm32_diagnostics(self):
        self.log('Trạng thái STM32 được xác định từ dữ liệu odometry: ' + SETTINGS['odom_topic'])

    def _amcl_callback(self, msg):
        if msg.header.frame_id.lstrip('/') != SETTINGS['map_frame'].lstrip('/'):
            return
        self._latest_pose = msg.pose.pose

    def _arbiter_callback(self, msg):
        try:
            state = json.loads(msg.data)
            if not isinstance(state, dict) or type(state.get('emergency_stop')) is not bool:
                return
            self._arbiter = state
            self._arbiter_stamp = time.monotonic()
        except (ValueError, TypeError):
            pass

    def stop_robot(self):
        self._return_to_dashboard()
        self._stop_requested = True
        self._cancel_nav2_goals()
        self.navigation_label.setText('Đã yêu cầu hủy hành trình Nav2; PS2 được giữ nguyên.')

    def _cancel_nav2_goals(self):
        self.cancel_navigation()
        if self._cancel_all.service_is_ready():
            if self._cancel_all_future is None or self._cancel_all_future.done():
                self._cancel_all_ok = False
                self._cancel_all_future = self._cancel_all.call_async(CancelGoal.Request())
                self._cancel_all_future.add_done_callback(self._cancel_all_done)

    def resume_robot(self):
        if self._navigation_busy() or (self._cancel_all_future is not None and not self._cancel_all_future.done()):
            self.log('Chờ Nav2 xác nhận hủy trước khi cho phép chạy lại.')
            return
        self._stop_requested = False
        self.log('Đã cho phép chọn hành trình Nav2 mới. Hành trình cũ không tự chạy tiếp.')

    def _cancel_all_done(self, future):
        if future.cancelled():
            return
        try:
            result = future.result()
            self._cancel_all_ok = result.return_code in (0, 2)
            if not self._cancel_all_ok:
                self.log('Nav2 chưa xác nhận yêu cầu hủy; nhấn Dừng để thử lại.')
        except Exception as exc:
            self.log(f'Lỗi yêu cầu hủy các mục tiêu Nav2: {exc}')

    def stop_nav2(self):
        if self._nav_process is None and self._rviz_process is None:
            if self._navigation_busy() or (self._arbiter and self._arbiter.get('navigation_busy')):
                self._cancel_nav2_goals()
                self.log('Đang hủy mục tiêu. Nhấn tắt Nav2 lại sau khi đã hủy.')
                return
            try:
                pid = stop_previous_yumi_nav2(SOURCE_PATH)
                if pid is None:
                    self.log('Không tìm thấy phiên Nav2 cũ do Yumi khởi chạy trên máy này.')
                else:
                    self.log(f'Đã gửi yêu cầu tắt phiên Nav2/RViz cũ (PID {pid}). '
                             'Chờ phiên dừng rồi bấm Bật Nav2 và RViz.')
            except ProcessLookupError:
                self.log('Phiên Nav2 cũ đã thoát.')
            except (OSError, RuntimeError) as exc:
                self.log(f'Không thể tắt phiên Nav2 cũ: {exc}')
            return
        self._cancel_nav2_goals()
        if self._navigation_busy():
            self.log('Đang hủy mục tiêu. Nhấn tắt Nav2 lại sau khi đã hủy.')
            return
        try:
            for attr in ('_nav_process', '_rviz_process'):
                proc = getattr(self, attr)
                if proc is not None:
                    proc.stop()
                    setattr(self, attr, None)
            if self._cancel_all_future is not None and not self._cancel_all_future.done():
                self._cancel_all_future.cancel()
            self._cancel_all_future = None
            self._cancel_all_ok = False
            self._latest_pose = None
            self.navigation_label.setText('Điều hướng: Nav2 đã tắt')
            self.log('Đã tắt Nav2/RViz và phần cứng do giao diện khởi chạy.')
        except Exception as exc:
            self.log(f'Không thể tắt Nav2/RViz: {exc}')

    def _nav2_hardware_arguments(self):
        nodes = set(self._ros_node.get_node_names_and_namespaces())
        def enabled(flag, running):
            return f" {flag}:={'false' if running else 'true'}"
        # These components are launched as groups; do not duplicate half a group.
        groups = {
            'start_ekf': [('odom_frame_publisher', '/'), ('ekf_filter_node', '/')],
            'start_lidar_processing': [('scan_front_filter', '/'),
                                       ('scan_rear_filter', '/'), ('dual_laser_merger', '/')],
        }
        arguments = ' start_robot:=true'
        for flag, members in groups.items():
            present = [member in nodes for member in members]
            if any(present) and not all(present):
                raise RuntimeError('Nhóm phần cứng đang chạy thiếu node: ' + flag
                                   + '. Hãy dừng phiên hardware cũ rồi bấm bật Nav2 lại.')
            arguments += enabled(flag, all(present))
        arguments += enabled('start_state', ('robot_state_publisher', '/') in nodes)
        arguments += enabled('publish_joint_states', any(
            name in ('joint_state_publisher', 'joint_state_publisher_gui') for name, ns in nodes))
        arguments += enabled('start_front_lidar', self._ros_node.count_publishers(SETTINGS['front_scan_topic']) > 0)
        arguments += enabled('start_rear_lidar', self._ros_node.count_publishers(SETTINGS['rear_scan_topic']) > 0)
        # A system Agent can already own UDP 8888 while waiting for the MCU.
        agent_running = (self._ros_node.count_publishers(SETTINGS['odom_topic']) > 0
                         or ('micro_ros_agent', '/') in nodes)
        if not agent_running:
            try:
                sockets = subprocess.run(
                    ['ss', '-Hlun', 'sport = :8888'],
                    capture_output=True, check=True, timeout=0.5,
                )
                agent_running = bool(sockets.stdout.strip())
            except (OSError, subprocess.SubprocessError) as exc:
                self.log(f'Chưa kiểm tra được cổng Agent 8888: {exc}')
        arguments += enabled('start_agent', agent_running)
        arguments += enabled('start_velocity_arbiter', ('velocity_arbiter', '/') in nodes)
        return arguments

    def start_nav2(self):
        if self._nav_process is not None and self._nav_process.poll() is None:
            self.log('Nav2 do giao diện khởi chạy vẫn đang hoạt động.')
            return
        if not get_current_map_path():
            self.log('Hãy tải bản đồ trước khi bật Nav2.')
            return
        if self._nav_client.server_is_ready() or self._map_parameters.services_are_ready():
            self.log('Nav2 hoặc map_server đã chạy bên ngoài giao diện; giữ phiên hiện tại.')
            return
        mapping = getattr(self, '_new_map_dialog', None)
        if mapping is not None and mapping.mapping_process is not None:
            self.log('Hãy kết thúc tạo bản đồ trước khi bật Nav2.')
            return
        try:
            arguments = self._nav2_hardware_arguments()
            self._nav_process = MappingProcess(shell_source_workspace(
                robot_command('nav2_command', map=get_current_map_path()) + arguments))
            if not SETTINGS['nav2_opens_rviz']:
                self._rviz_process = MappingProcess(shell_source_workspace(SETTINGS['rviz_command']))
            self.log('Đã yêu cầu bật phần cứng còn thiếu, Nav2 và RViz. Đặt vị trí ban đầu trong RViz.')
        except Exception as exc:
            self.log(f'Không thể khởi chạy Nav2/RViz: {exc}')

    def closeEvent(self, event):
        if self._closed:
            event.accept()
            return
        if self._closing:
            event.ignore()
            return
        self._closing = True
        self.stop_robot()
        deadline = time.monotonic()+3.0
        while self._navigation_busy() and time.monotonic()<deadline:
            rclpy.spin_once(self._ros_node, timeout_sec=0.05)
        if self._navigation_busy():
            self.log('Chưa xác nhận Nav2 đã hủy. Chờ rồi đóng lại giao diện.')
            self._closing = False
            event.ignore()
            return
        dialog = getattr(self, '_new_map_dialog', None)
        if dialog is not None and not dialog.close():
            self._closing = False
            event.ignore()
            return
        try:
            for proc in (self._nav_process,self._rviz_process):
                if proc is not None:
                    proc.stop()
        except Exception as exc:
            self.log(f'Chưa dừng được tiến trình: {exc}')
            self._closing = False
            event.ignore()
            return
        self._conversation.shutdown()
        for timer in (self._ros_spin_timer, self.status_timer, self._idle_timer, self.clock_timer):
            timer.stop()
        QApplication.instance().removeEventFilter(self)
        self._closed = True
        self._ros_node.destroy_node()
        event.accept()

    def _stm32_odom_callback(self, msg):
        self._stm32_last_msg_time = time.monotonic()

    def _lidar_callback(self, which):
        if which == 'front':
            self._front_lidar_last_msg_time = time.monotonic()
        else:
            self._rear_lidar_last_msg_time = time.monotonic()

    def _make_status_card(self, device_name):
        card = QWidget()
        card.setObjectName("status-card")
        card.setProperty("state", "checking")
        card.setMinimumHeight(104)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(6)
        dot = QLabel()
        dot.setObjectName("device-icon")
        dot.setFixedSize(28, 28)
        dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dot.setPixmap(startup_icon(device_name, size=24).pixmap(QSize(24, 24)))
        info = QVBoxLayout()
        name = QLabel(device_name)
        name.setObjectName("device-name")
        name.setWordWrap(True)
        state = QLabel()
        state.setObjectName("device-state")
        state.setWordWrap(True)
        info.addWidget(name)
        info.addWidget(state)
        layout.addWidget(dot)
        layout.addLayout(info, 1)
        detail = None
        if device_name == "STM32":
            detail = QPushButton("i")
            detail.setObjectName("diagnostics-btn")
            detail.setFixedSize(48, 48)
            detail.clicked.connect(self.show_stm32_diagnostics)
            layout.addWidget(detail)
        result = dict(widget=card, dot=dot, state=state, name=name,
                      device=device_name, available=None, detail_btn=detail)
        self._set_card_status(result, None)
        return result

    def _set_card_status(self, card, available):
        card["available"] = available
        state = "checking" if available is None else "online" if available else "offline"
        t = startup_text()
        card["state"].setText(t[state])
        card["name"].setText(t.get(card["device"], card["device"]))
        card["widget"].setAccessibleName(card["name"].text() + ": " + t[state])
        if card["widget"].property("state") != state:
            card["widget"].setProperty("state", state)
            repolish(card["widget"])
        if card["detail_btn"] is not None:
            card["detail_btn"].setToolTip(t["diagnostics"])
            card["detail_btn"].setAccessibleName(t["diagnostics"])

    def update_status(self):
        if self._closing or self._closed or not rclpy.ok():
            return
        if self._idle_blocked():
            self._return_to_dashboard()
        now = time.monotonic()
        self._sync_active_map(now)
        ready = self._nav_client.server_is_ready()
        fresh = self._arbiter is not None and now - self._arbiter_stamp < 1.0
        nav_starting = self._nav_process is not None and self._nav_process.poll() is None
        if self._stop_requested and (ready or nav_starting):
            confirmed = (not self._navigation_busy() and self._cancel_all_future is not None
                         and self._cancel_all_future.done() and self._cancel_all_ok
                         and fresh and not self._arbiter.get('navigation_busy', True))
            message = 'Đã hủy hành trình Nav2' if confirmed else 'Đang yêu cầu dừng; chưa đủ xác nhận'
        elif fresh and self._arbiter.get('emergency_stop'):
            message = 'Đang khóa dừng tại bộ phân xử vận tốc'
        elif ready:
            message = 'Nav2 sẵn sàng'
        elif nav_starting:
            scans = (self._front_lidar_last_msg_time, self._rear_lidar_last_msg_time)
            if all(stamp is not None and now - stamp < 3.0 for stamp in scans):
                message = 'Chờ định vị: dùng 2D Pose Estimate trong RViz'
            else:
                message = 'Đang khởi chạy Nav2, chờ dữ liệu từ hai LiDAR'
        else:
            message = 'Nav2 chưa sẵn sàng'
        self.navigation_label.setText('Điều hướng: ' + message)
        for attr in ('_nav_process', '_rviz_process'):
            proc = getattr(self, attr)
            if proc is not None and proc.poll() is not None:
                self.log('Tiến trình đã kết thúc: ' + proc.error_detail())
                proc.stop()
                setattr(self, attr, None)

        stm32_available = (
            self._stm32_last_msg_time is not None and
            now - self._stm32_last_msg_time < 3.0
        )
        self._set_card_status(self.stm32_card, stm32_available)
        if self.prev_stm32_status is not None and self.prev_stm32_status != stm32_available:
            self.log("Mất kết nối STM32" if not stm32_available else "Đã khôi phục kết nối STM32")
        self.prev_stm32_status = stm32_available

        front_available = (
            self._front_lidar_last_msg_time is not None and
            now - self._front_lidar_last_msg_time < 3.0
        )
        self._set_card_status(self.front_lidar_card, front_available)
        if self.prev_lidar_status is not None and self.prev_lidar_status != front_available:
            self.log("Mất kết nối LiDAR trước" if not front_available else "Đã khôi phục kết nối LiDAR trước")
        self.prev_lidar_status = front_available

        rear_available = (
            self._rear_lidar_last_msg_time is not None and
            now - self._rear_lidar_last_msg_time < 3.0
        )
        self._set_card_status(self.rear_lidar_card, rear_available)
        if self.prev_lidar_rear_status is not None and self.prev_lidar_rear_status != rear_available:
            self.log("Mất kết nối LiDAR sau" if not rear_available else "Đã khôi phục kết nối LiDAR sau")
        self.prev_lidar_rear_status = rear_available

    def _load_waypoints(self):
        try:
            data, _ = load_waypoint_file(self._waypoints_file)

            self.log(
                f"Đã tải {len(data)} địa điểm"
            )

            return data

        except Exception as e:
            self.log(
                f"Lỗi đọc waypoints.json: {e}"
            )
            return {}

    def start_new_map(self):
        if self._map_loading or (self._nav_process is not None and self._nav_process.poll() is None) or self._nav_client.server_is_ready():
            self.log('Hãy tắt Nav2 trước khi tạo bản đồ.')
            return
        if getattr(self, '_new_map_dialog', None) is None:
            self._new_map_dialog = NewMapUI(self)
        self._new_map_dialog.show()
        self._new_map_dialog.raise_()
        self._new_map_dialog.activateWindow()

    def _sync_active_map(self, now):
        if self._map_loading or now - self._map_query_time < 2.0:
            return
        if self._map_query is not None and not self._map_query.done():
            return
        if not self._map_parameters.services_are_ready():
            return
        self._map_query_time = now
        self._map_query = self._map_parameters.get_parameters(['yaml_filename'])
        self._map_query.add_done_callback(self._active_map_received)

    def _active_map_received(self, future):
        if self._map_loading:
            return
        try:
            values = future.result().values
            path = values[0].string_value if values else ''
            if path and path != self._map_parameter_path:
                self._map_parameter_path = path
                map_utils.ACTIVE_MAP_PATH = path
                self._latest_pose = None
                self.log('Bản đồ Nav2 đang dùng: ' + path)
        except Exception as exc:
            self.log('Chưa đọc được bản đồ Nav2: ' + str(exc))

    def load_map(self):
        if self._map_loading:
            return
        mapping = getattr(self, '_new_map_dialog', None)
        if mapping is not None and mapping.mapping_process is not None:
            self.log('Hãy kết thúc tạo bản đồ trước khi đổi bản đồ.')
            return
        if self._navigation_busy() or (self._arbiter and self._arbiter.get('navigation_busy')):
            self.log('Hãy bấm DỪNG và chờ hủy mục tiêu trước khi đổi bản đồ.')
            return
        dialog = LoadMapDialog(self)
        if not dialog.exec():
            return
        name = dialog.get_selected_map()
        if not name:
            return
        if self._map_loader.service_is_ready():
            request = LoadMap.Request()
            request.map_url = str(map_utils.MAPS_DIRECTORY / (name + '.yaml'))
            self._map_loading = True
            future = self._map_loader.call_async(request)
            future.add_done_callback(lambda done: self._map_loaded(done, name))
            self.log('Đang yêu cầu Nav2 thay bản đồ: ' + name)
        elif self._nav_client.server_is_ready() or (self._nav_process and self._nav_process.poll() is None):
            self.log('Nav2 đang chạy nhưng dịch vụ tải bản đồ chưa sẵn sàng. Chưa thay bản đồ.')
        elif update_map_files(name, self.log):
            map_utils.ACTIVE_MAP_PATH = None
            self._latest_pose = None

    def _map_loaded(self, future, name):
        self._map_loading = False
        try:
            response = future.result()
            if response.result != LoadMap.Response.RESULT_SUCCESS:
                self.log('Nav2 từ chối tải bản đồ, mã lỗi: ' + str(response.result))
                return
            map_utils.ACTIVE_MAP_PATH = str(map_utils.MAPS_DIRECTORY / (name + '.yaml'))
            update_map_files(name, self.log)
            self._latest_pose = None
            self.log('Đã thay bản đồ Nav2. Hãy đặt lại vị trí ban đầu trong RViz.')
        except Exception as exc:
            self.log('Không xác nhận được tải bản đồ: ' + str(exc))

    def open_destination_dialog(self):
        if getattr(self, '_destination_dialog', None) is None:
            self._destination_dialog = DestinationDialog(self)
        self._destination_dialog.show()
        self._destination_dialog.raise_()
        self._destination_dialog.activateWindow()

    def open_waypoint_picker(self):
        self._waypoints = self._load_waypoints()
        dialog = WaypointPickerDialog(self._waypoints, get_current_map_name(), self, self.delete_waypoint)
        if dialog.exec() and dialog.get_selected_key():
            self._run_waypoint_sequence([dialog.get_selected_key()])

    def open_path_manager(self):
        path = os.path.join(str(UI_DIRECTORY), 'multi_waypoints.json')
        while True:
            current_map = get_current_map_name()
            dialog = PathManagerDialog(path, current_map, self)
            dialog.run_path_requested.connect(self._run_waypoint_sequence)
            if dialog.exec() != 2:
                break
            self._waypoints = self._load_waypoints()
            NewPathDialog(self._waypoints, current_map, path, self).exec()

    def _resolve_conversation_destination(self, kind, name, map_name):
        waypoints, _ = load_waypoint_file(self._waypoints_file)
        if kind == 'waypoint':
            candidates = {name, re.sub(r'^(?:phong|dia diem|waypoint)\s+', '', name)}
            matches = [
                (item['display_name'], [key])
                for key, item in waypoints.items()
                if item['map_name'] == map_name
                and candidates.intersection(
                    normalize_name(identity) for identity in
                    (key, item['display_name'], *item['aliases'])
                )
            ]
        else:
            path = UI_DIRECTORY / 'multi_waypoints.json'
            routes = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(routes, dict):
                raise ValueError('Invalid route file')
            matches = [
                (label, route.get('sequence'))
                for label, route in routes.items()
                if isinstance(route, dict) and route.get('map_name') == map_name
                and normalize_name(label) == name
            ]
        if len(matches) != 1:
            return None
        label, sequence = matches[0]
        if not isinstance(sequence, list) or not sequence:
            return None
        keys = [resolve_waypoint(waypoints, key, map_name) for key in sequence]
        if any(key is None for key in keys):
            return None
        return label, keys, [waypoints[key] for key in keys]

    def _handle_conversation_command(self, kind, name):
        if kind == 'stop':
            self.stop_robot()
            return 'Đã yêu cầu hủy điều hướng Nav2.'
        target_type = 'lộ trình' if kind == 'route' else 'địa điểm'
        try:
            map_name = get_current_map_name()
            destination = self._resolve_conversation_destination(kind, name, map_name)
            if destination is None:
                return f'Không tìm thấy {target_type} phù hợp duy nhất trên bản đồ hiện tại.'
            label, sequence, _ = destination
            if not confirm_dialog(self, 'Xác nhận điều hướng', f'Chạy tới {target_type}: {label}?'):
                return 'Đã hủy yêu cầu điều hướng.'
            if (self._closing or self._closed or get_current_map_name() != map_name
                    or self._resolve_conversation_destination(kind, name, map_name) != destination):
                return 'Bản đồ hoặc dữ liệu đích đã thay đổi. Hãy gửi lại lệnh.'
            mapping = getattr(self, '_new_map_dialog', None)
            if mapping is not None and mapping.mapping_process is not None:
                return 'Hãy kết thúc tạo bản đồ trước khi điều hướng.'
        except (OSError, ValueError, KeyError, TypeError):
            return 'Không đọc được bản đồ, địa điểm hoặc lộ trình đã lưu.'
        if self._run_waypoint_sequence(sequence):
            return f'Đã gửi yêu cầu điều hướng cho {target_type} {label}.'
        return 'Chưa gửi được yêu cầu điều hướng. Hãy kiểm tra Nav2 và trạng thái trên màn hình.'

    def _run_waypoint_sequence(self, sequence):
        if self._map_loading:
            self.log('Đang thay bản đồ; hãy chờ hoàn tất và đặt lại vị trí trong RViz.')
            return
        if self._stop_requested or not self._arbiter or time.monotonic()-self._arbiter_stamp > 1.0 or self._arbiter.get('emergency_stop') or not self._arbiter.get('healthy'):
            self.log('Bộ phân xử vận tốc chưa sẵn sàng hoặc đang khóa dừng.')
            return
        if self._navigation_busy():
            self.log('Đang chạy hoặc chờ hủy; hãy dừng và chờ kết quả trước khi chọn địa điểm mới.')
            return
        self._waypoints = self._load_waypoints()
        current_map = get_current_map_name()
        if (not isinstance(sequence, list) or not sequence
                or any(resolve_waypoint(self._waypoints, key, current_map) is None
                       for key in sequence)):
            warning_dialog(self, 'Không thể điều hướng',
                                'Lộ trình trống hoặc có địa điểm không thuộc bản đồ hiện tại.')
            return
        # Keep keys as a list: waypoint names may contain commas.
        self.cancel_navigation()
        self._waypoint_queue = list(sequence)
        self._send_next_waypoint()
        return self._nav_pending

    def open_new_waypoint_dialog(self):
        if self._latest_pose is None:
            warning_dialog(self, 'Chưa có vị trí',
                                'Robot chưa có vị trí AMCL. Hãy định vị robot trước khi tạo địa điểm.')
            return
        current_map = get_current_map_name()
        dialog = NewWaypointDialog(self)
        if not dialog.exec():
            return
        if self._latest_pose is None or current_map != get_current_map_name():
            warning_dialog(self, 'Không thể lưu địa điểm',
                                'Bản đồ hoặc vị trí đã thay đổi. Hãy định vị và thử lại.')
            return
        name = dialog.get_name()
        try:
            data, snapshot = load_waypoint_file(self._waypoints_file)
            if (not name or name.startswith('__')
                    or any(name.casefold() == key.casefold() for key in data)):
                raise ValueError('Tên trống, trùng tên hoặc bắt đầu bằng __. Hãy chọn tên khác.')
            pose = self._latest_pose
            data[name] = {
                'id': str(uuid.uuid4()), 'display_name': name,
                'deletable': dialog.get_deletable(), 'map_name': current_map,
                'x': pose.position.x, 'y': pose.position.y, 'z': pose.position.z,
                'qx': pose.orientation.x, 'qy': pose.orientation.y,
                'qz': pose.orientation.z, 'qw': pose.orientation.w,
            }
            self._waypoints, _ = save_waypoint_file(self._waypoints_file, data, snapshot)
        except (OSError, ValueError, UnicodeError) as exc:
            warning_dialog(self, 'Không thể lưu địa điểm', str(exc))
            return
        self.log(f'Đã lưu địa điểm mới: {name}')

    def _send_next_waypoint(self, generation=None):
        if generation is not None and generation != self._navigation_generation:
            return
        if self._stop_requested:
            self._waypoint_queue.clear()
            return
        generation = self._navigation_generation

        if not self._waypoint_queue:
            self.log(
                "[robot] Đã hoàn thành hành trình"
            )
            return

        target = self._waypoint_queue.pop(0)

        # ============================================================
        # Trường hợp quay lại vị trí lúc ra lệnh
        # ============================================================

        if target.startswith("__return_here__:"):

            try:
                values = target.split(":", 1)[1]
                x, y, qz, qw = map(
                    float,
                    values.split(";")
                )

                waypoint = {
                    "x": x,
                    "y": y,
                    "z": 0.0,
                    "qx": 0.0,
                    "qy": 0.0,
                    "qz": qz,
                    "qw": qw,
                }

                display_name = "vị trí ban đầu"

            except Exception as e:
                self.log(
                    f"Lỗi đọc __return_here__: {e}"
                )
                return

        # ============================================================
        # Waypoint bình thường
        # ============================================================

        else:

            self._waypoints = self._load_waypoints()
            key = resolve_waypoint(self._waypoints, target, get_current_map_name())
            waypoint = self._waypoints.get(key)

            if waypoint is None:
                self.log(
                    f"Không tìm thấy địa điểm: {target}"
                )
                return

            display_name = waypoint.get('display_name', target)

        # ============================================================
        # Kiểm tra Nav2
        # ============================================================

        if not self._nav_client.wait_for_server(
            timeout_sec=1.0
        ):
            self.log(
                "Nav2 chưa sẵn sàng: "
                "/navigate_to_pose không tồn tại"
            )
            return

        # ============================================================
        # Tạo goal
        # ============================================================

        goal = NavigateToPose.Goal()

        goal.pose.header.frame_id = SETTINGS['map_frame']

        goal.pose.header.stamp = (
            self._ros_node
            .get_clock()
            .now()
            .to_msg()
        )

        # Position
        goal.pose.pose.position.x = float(
            waypoint["x"]
        )

        goal.pose.pose.position.y = float(
            waypoint["y"]
        )

        goal.pose.pose.position.z = float(
            waypoint.get("z", 0.0)
        )

        # Orientation
        goal.pose.pose.orientation.x = float(
            waypoint.get("qx", 0.0)
        )

        goal.pose.pose.orientation.y = float(
            waypoint.get("qy", 0.0)
        )

        goal.pose.pose.orientation.z = float(
            waypoint["qz"]
        )

        goal.pose.pose.orientation.w = float(
            waypoint["qw"]
        )

        self.log(
            f"[robot] Đang đi tới {display_name} | "
            f"x={waypoint['x']:.2f}, "
            f"y={waypoint['y']:.2f}"
        )

        self._nav_pending = True
        self._nav_cancel_requested = False
        try:
            future = self._nav_client.send_goal_async(
                goal,
                feedback_callback=self._nav_feedback_callback
            )
        except Exception as exc:
            self._nav_pending = False
            self._waypoint_queue.clear()
            self.log(f'Lỗi gửi địa điểm: {exc}')
            return

        future.add_done_callback(
            lambda done: self._nav_goal_response_callback(done, generation)
        )

    def _nav_goal_response_callback(self, future, generation=None):
        self._nav_pending = False
        if generation is None:
            generation = self._navigation_generation

        try:
            goal_handle = future.result()
            if generation != self._navigation_generation:
                if goal_handle.accepted:
                    self._nav_goal_handle = goal_handle
                    goal_handle.get_result_async().add_done_callback(
                        lambda done: self._nav_result_callback(done, generation))
                    goal_handle.cancel_goal_async()
                return

        except Exception as e:
            self.log(
                f"Lỗi gửi mục tiêu Nav2: {e}"
            )
            self._waypoint_queue.clear()
            return

        if not goal_handle.accepted:

            self.log(
                "Nav2 từ chối địa điểm"
            )

            self._waypoint_queue.clear()
            return

        self._nav_goal_handle = goal_handle

        self.log(
            "Nav2 đã nhận địa điểm"
        )

        result_future = (
            goal_handle.get_result_async()
        )

        result_future.add_done_callback(
            lambda done: self._nav_result_callback(done, generation)
        )

    def _nav_result_callback(self, future, generation=None):
        if generation is None:
            generation = self._navigation_generation
        if generation != self._navigation_generation:
            try:
                future.result()
                self._nav_goal_handle = None
                self.log('[robot] Mục tiêu đã kết thúc sau yêu cầu hủy.')
            except Exception as exc:
                self.log(f'Chưa xác nhận waypoint dừng: {exc}')
            return

        try:
            wrapped_result = future.result()
            status = wrapped_result.status

        except Exception as e:
            self.log(
                f"Lỗi nhận kết quả Nav2: {e}"
            )

            self._waypoint_queue.clear()
            return

        self._nav_goal_handle = None

        if status == GoalStatus.STATUS_SUCCEEDED:

            self.log(
                "[robot] Đã tới địa điểm"
            )

            # Nếu người dùng yêu cầu nhiều waypoint
            # thì đi điểm tiếp theo.
            QTimer.singleShot(
                300,
                lambda: self._send_next_waypoint(generation)
            )

        elif status == GoalStatus.STATUS_ABORTED:

            # Previously ABORTED fell into the failure branch below and cleared
            # the entire route. Skip this failed destination only; cancellation
            # and unexpected results still stop the route.
            # Previous behavior: self._waypoint_queue.clear()
            if self._waypoint_queue and not self._stop_requested:
                self.log('[robot] Điểm hiện tại thất bại (aborted); bỏ qua và đi điểm tiếp theo.')
                QTimer.singleShot(
                    300,
                    lambda: self._send_next_waypoint(generation)
                )
            else:
                self._waypoint_queue.clear()
                self.log('[robot] Điểm hiện tại thất bại (aborted); không còn điểm tiếp theo hoặc đã yêu cầu dừng.')

        elif status == GoalStatus.STATUS_CANCELED:

            self.log(
                "[robot] Điều hướng đã bị hủy"
            )

            self._waypoint_queue.clear()

        else:

            self.log(
                f"[robot] Điều hướng thất bại, "
                f"status={status}"
            )

            self._waypoint_queue.clear()

    def _nav_feedback_callback(
        self,
        feedback_msg
    ):

        try:
            distance = (
                feedback_msg.feedback
                .distance_remaining
            )

            # Không log từng frame vì sẽ spam.
            # Nếu cần sau này có thể throttle.
            print(
                f"[NAV] Còn {distance:.2f} m"
            )

        except Exception:
            pass

    def cancel_navigation(self):
        self._navigation_generation += 1

        self._waypoint_queue.clear()

        if self._nav_goal_handle is None:
            self.log(
                'Đang chờ phản hồi mục tiêu để hủy.' if getattr(self, '_nav_pending', False)
                else 'Không có mục tiêu điều hướng đang chạy.'
            )
            return

        self.log(
            "[robot] Đang hủy navigation"
        )

        if not getattr(self, '_nav_cancel_requested', False):
            self._nav_cancel_requested = True
            self._nav_goal_handle.cancel_goal_async().add_done_callback(self._waypoint_cancel_response)

    def _waypoint_cancel_response(self, future):
        try:
            if not future.result().goals_canceling:
                self._nav_cancel_requested = False
                self.log('Nav2 chưa nhận hủy mục tiêu; chờ kết quả hoặc nhấn Dừng để thử lại.')
        except Exception as exc:
            self._nav_cancel_requested = False
            self.log(f'Lỗi hủy mục tiêu; chưa xác nhận dừng: {exc}')

    def _navigation_busy(self):
        return (self._nav_goal_handle is not None or getattr(self, '_nav_pending', False)
                or bool(self._waypoint_queue))

    def delete_waypoint(self, key):
        try:
            if self._navigation_busy():
                raise ValueError('Hãy dừng hành trình trước khi xóa địa điểm.')
            data, snapshot = load_waypoint_file(self._waypoints_file)
            reason = deletion_reason(key, data[key])
            if reason:
                raise ValueError(reason)
            refs = route_references(UI_DIRECTORY / 'multi_waypoints.json', key, data[key])
            if refs:
                raise ValueError('Địa điểm đang được sử dụng trong lộ trình: ' + ', '.join(refs))
            if not confirm_dialog(self, 'Xác nhận xóa', f'Xóa địa điểm {key}?'):
                return False
            del data[key]
            self._waypoints, _ = save_waypoint_file(self._waypoints_file, data, snapshot)
            return True
        except (OSError, ValueError, KeyError) as exc:
            warning_dialog(self, 'Không thể xóa', str(exc))
            return False

if __name__ == '__main__':
    # Let Qt close ROS entities before shutting down the ROS context on SIGINT.
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    app = QApplication(sys.argv)
    app.setFont(QFont('Fira Sans',12))
    window = RobotUI()
    signal.signal(signal.SIGINT, lambda *_: window.close())
    signal.signal(signal.SIGTERM, lambda *_: window.close())
    window.showFullScreen()
    try:
        sys.exit(app.exec())
    finally:
        if rclpy.ok():
            rclpy.shutdown()
