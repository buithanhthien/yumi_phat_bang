# Yumi Phát Bằng — ROS 2

Package mô phỏng nằm trong `src/yumi_phat_bang`. Package
`src/view_robot` giữ luồng kết nối phần cứng và dùng mô hình CAD Yumi.

Hiện có hiển thị CAD, mô phỏng base hai bánh chủ động/bốn bánh bị động,
hai LiDAR, SLAM bằng điều khiển bàn phím và lưu map. Kết nối phần cứng được
cấu hình riêng trong `yumi_robot_pkg`; AMCL và Nav2 chưa hiệu chuẩn cho Yumi.

**Quét map:** xem [hướng dẫn SLAM và teleop](docs/MAPPING.md).
Sau khi build, chạy `ros2 launch yumi_phat_bang mapping_sim.launch.py`.
Ở terminal khác, chạy `ros2 run yumi_phat_bang wasd_teleop` với
`ROS_DOMAIN_ID=78` để điều khiển bằng W/A/S/D.
Xem [lộ trình và tiêu chí nghiệm thu](docs/PHASES.md).

## Build từ gốc workspace

```bash
source /opt/ros/jazzy/setup.bash
cd /home/khoa/yumi_phat_bang
colcon build --base-paths src --packages-select yumi_phat_bang --symlink-install
source install/setup.bash
```

Các dependency được khai báo trong `package.xml`. Có thể kiểm tra dependency
bằng `rosdep check --from-paths src --ignore-src` khi môi trường rosdep đã được
khởi tạo. Package đích tên `yumi_phat_bang`, khớp URI mesh có sẵn trong CAD.

## P1: Xem mô hình CAD trong RViz

```bash
ros2 launch yumi_phat_bang view_robot.launch.py
# Điều chỉnh góc bánh bằng GUI:
ros2 launch yumi_phat_bang view_robot.launch.py use_gui:=true
```

Ở chế độ hiển thị, joint_state_publisher cung cấp trạng thái bánh mẫu.
Khi có phản hồi từ driver thật, dùng `publish_joint_states:=false`.

## P2: Mô phỏng base và hai LiDAR

```bash
ros2 launch yumi_phat_bang simulation.launch.py
# Không mở cửa sổ Gazebo/RViz:
ros2 launch yumi_phat_bang simulation.launch.py headless:=true rviz:=false
```

Mô phỏng dùng ROS domain 78, discovery localhost và Gazebo partition riêng,
kế thừa cách cách ly từ `dock_shape_sim`. Mọi terminal điều khiển/đọc mô phỏng
cần dùng cùng domain:

```bash
source /opt/ros/jazzy/setup.bash
source /home/khoa/yumi_phat_bang/install/setup.bash
export ROS_DOMAIN_ID=78
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 topic hz /front_lidar/scan
ros2 topic hz /rear_lidar/scan
ros2 topic echo /odom --once
```

Thử lệnh tiến ở terminal riêng:

```bash
export ROS_DOMAIN_ID=78
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 0.1}, angular: {z: 0.0}}'
```

Sau khi Ctrl+C, gửi lệnh dừng (bộ DiffDrive này có thể giữ lệnh cuối):

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist '{}'
```

Các topic đầu ra: `/clock`, `/joint_states`, `/odom`, `/tf`,
`/front_lidar/scan`, `/rear_lidar/scan`. Lệnh `/cmd_vel` dùng `Twist`.
Chỉ Gazebo phát TF `odom → base_link`; robot_state_publisher phát TF các link.

## Giới hạn mô hình mô phỏng

- `urdf/yumi_phat_bang.urdf` giữ nguyên file CAD ban đầu.
- `urdf/yumi_phat_bang.sim.urdf` là bản dùng riêng cho Gazebo: chuẩn hóa hai
  trục bánh về +Z, thay collision bằng primitive, bổ sung inertia LiDAR sau
  tạm bằng LiDAR trước, thêm DiffDrive và cảm biến.
- Hai bánh mô phỏng có bán kính 0,08 m, collision rộng 0,07 m và đặt tại joint;
  đây là xấp xỉ, không mô tả toàn bộ cụm bánh/động cơ trong mesh CAD.
- Khoảng cách joint bánh 0,6076 m lấy từ URDF. Track width và bán kính lăn thật
  cần đo/hiệu chuẩn; không dùng các giá trị này như thông số phần cứng đã chốt.
- Bốn bánh bị động dùng collision hình cầu ma sát thấp. Chưa mô phỏng khớp
  xoay caster, độ trượt hoặc ảnh hưởng tải. Chỉ dùng để kiểm tra giao tiếp,
  chiều chuyển động và chuỗi TF/cảm biến ban đầu.
- LiDAR 360°, 1440 mẫu, 10 Hz, tầm 0,15–16 m là thiết lập thử nghiệm.
- `config/base_geometry.yaml` ghi thông số tham khảo; thay đổi file này chưa
  tự cập nhật URDF mô phỏng. Khi chỉnh hình học, đồng bộ các giá trị tương ứng.

## Kế thừa ở phase sau

Phần cứng hiện dùng `src/yumi_robot_pkg/launch/yumi_hardware.launch.py` và
`MAP_GENERATING.launch.py`; xem [hướng dẫn phần cứng](../yumi_robot_pkg/README.md).
Các launch Nav2 và map Zackon cũ chỉ còn để tham khảo. Cần đo footprint, chỉnh
filter theo LiDAR Yumi và hiệu chuẩn động học trước khi chạy Nav2 trên robot thật.
