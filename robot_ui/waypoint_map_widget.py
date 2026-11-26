"""Shared map view without ROS or application lifecycle ownership."""
import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QImage


class MapWidget(QWidget):
    def __init__(self, map_path, yaml_data):
        super().__init__()
        self.map_image = QPixmap(map_path)
        self.resolution = float(yaml_data.get('resolution', 1.0))
        if not math.isfinite(self.resolution) or self.resolution <= 0:
            self.resolution = 1.0
        self.origin = yaml_data.get('origin', [0.0, 0.0, 0.0])
        if not isinstance(self.origin, (list, tuple)) or len(self.origin) < 2:
            self.origin = [0.0, 0.0, 0.0]
        self.robot_pose = None
        self.waypoints = {}
        self.setMinimumSize(320, 260)

    def load_map(self, path, metadata):
        image = QPixmap(path)
        resolution = float(metadata['resolution'])
        if image.isNull() or not math.isfinite(resolution) or resolution <= 0:
            raise ValueError('Ảnh bản đồ hoặc độ phân giải không hợp lệ.')
        self.map_image = image
        self.resolution = resolution
        self.origin = metadata['origin']
        self.update()

    def set_occupancy_grid(self, msg):
        width, height = msg.info.width, msg.info.height
        if not width or not height or len(msg.data) != width * height or msg.info.resolution <= 0:
            return
        pixels = bytes(205 if v < 0 else round(254 * (1 - min(v, 100) / 100))
                       for row in range(height - 1, -1, -1)
                       for v in msg.data[row * width:(row + 1) * width])
        image = QImage(pixels, width, height, width, QImage.Format.Format_Grayscale8).copy()
        self.map_image = QPixmap.fromImage(image)
        self.resolution = msg.info.resolution
        p, q = msg.info.origin.position, msg.info.origin.orientation
        yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        self.origin = [p.x, p.y, yaw]
        self.update()
        
    def set_robot_pose(self, pose):
        self.robot_pose = pose
        self.update()

    def set_waypoints(self, waypoints):
        self.waypoints = waypoints
        self.update()
        
    def world_to_pixel(self, x, y):
        dx = x - self.origin[0]
        dy = y - self.origin[1]
        origin_yaw = self.origin[2] if len(self.origin) > 2 else 0.0
        local_x = math.cos(origin_yaw) * dx + math.sin(origin_yaw) * dy
        local_y = -math.sin(origin_yaw) * dx + math.cos(origin_yaw) * dy
        px = int(local_x / self.resolution)
        py = int(self.map_image.height() - local_y / self.resolution)
        return px, py
        
    def paintEvent(self, event):
        painter = QPainter(self)

        if self.map_image.isNull():
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Chọn bản đồ hoặc bắt đầu tạo bản đồ để hiển thị",
            )
            return
        
        scaled_map = self.map_image.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        x_offset = (self.width() - scaled_map.width()) // 2
        y_offset = (self.height() - scaled_map.height()) // 2
        painter.drawPixmap(x_offset, y_offset, scaled_map)

        scale_x = scaled_map.width() / self.map_image.width()
        scale_y = scaled_map.height() / self.map_image.height()

        # Draw waypoint arrows
        for slot, wp in self.waypoints.items():
            px, py = self.world_to_pixel(wp['x'], wp['y'])
            px = int(px * scale_x + x_offset)
            py = int(py * scale_y + y_offset)
            self._draw_arrow(painter, px, py, wp.get('display_name', slot))

        if self.robot_pose:
            px, py = self.world_to_pixel(
                self.robot_pose.pose.pose.position.x,
                self.robot_pose.pose.pose.position.y
            )
            px = int(px * scale_x + x_offset)
            py = int(py * scale_y + y_offset)
            painter.setPen(QPen(QColor(255, 0, 0), 3))
            painter.setBrush(QColor(255, 0, 0))
            painter.drawEllipse(px - 5, py - 5, 10, 10)

    def _draw_arrow(self, painter, px, py, label):
        painter.setPen(QPen(QColor(252, 181, 37), 2))
        painter.setBrush(QColor(252, 181, 37))
        painter.drawLine(px, py - 20, px, py)
        from PyQt6.QtGui import QPolygon
        from PyQt6.QtCore import QPoint
        tip = QPoint(px, py)
        left = QPoint(px - 6, py - 12)
        right = QPoint(px + 6, py - 12)
        painter.drawPolygon(QPolygon([tip, left, right]))
        painter.setPen(QPen(QColor(26, 42, 94), 1))
        painter.drawText(px + 8, py - 10, label)


