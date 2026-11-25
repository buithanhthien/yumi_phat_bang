# Quét map Gazebo bằng bàn phím

Dùng ROS 2 Jazzy và `slam_toolbox` online async, kế thừa cấu hình matching
của `view_robot`. Gazebo cung cấp `/clock`, `/odom`, TF và hai LiDAR. SLAM dùng
`/front_lidar/scan` (360°); LiDAR sau vẫn phát dữ liệu và hiển thị trong RViz.
Chưa ghép hai scan trong phase này. SLAM phát `/map` và TF `map → odom`.

## 1. Build

```bash
source /opt/ros/jazzy/setup.bash
cd /home/khoa/yumi_phat_bang
colcon build --base-paths src --packages-select yumi_phat_bang --symlink-install
source install/setup.bash
```

Package dùng `slam_toolbox`, `rclpy` và `nav2_map_server`.
Các dependency đã được thêm vào `package.xml` để rosdep nhận diện khi chuyển máy.

## 2. Terminal 1: mở world có vật cản và SLAM

Dừng launch mô phỏng cũ bằng Ctrl+C trước khi chạy launch kết hợp này.

```bash
source /opt/ros/jazzy/setup.bash
source /home/khoa/yumi_phat_bang/install/setup.bash
ros2 launch yumi_phat_bang mapping_sim.launch.py
```

World `mapping.sdf` là phòng 8 × 8 m với bốn tường, hai khối hộp, một cột tròn
và một vách ngăn. Các vật thể đều có collision và đủ cao để cắt mặt phẳng quét.
Vị trí xuất phát quanh (0, 0) được để trống.

RViz mở với Fixed Frame `map`, lớp `SLAM Map`, mô hình Yumi và hai scan.
Map cập nhật khoảng mỗi giây sau khi nhận được scan và TF hợp lệ.
Màu trắng là vùng trống đã quan sát, đen là vật cản, xám là vùng chưa biết.

Nếu muốn giữ Gazebo đang mở, chỉ thêm SLAM:

```bash
ros2 launch yumi_phat_bang slam.launch.py
# Hoặc cùng chức năng qua launch kết hợp:
ros2 launch yumi_phat_bang mapping_sim.launch.py start_simulation:=false
```

Cách gắn vào Gazebo đang mở giữ nguyên world hiện tại. World có vật cản mới chỉ
được nạp khi khởi chạy lại Gazebo bằng `mapping_sim.launch.py`.
Chỉ chạy một tiến trình SLAM trong cùng ROS domain.

Chạy không có cửa sổ:

```bash
ros2 launch yumi_phat_bang mapping_sim.launch.py headless:=true rviz:=false
```

## 3. Terminal 2: điều khiển bằng W/A/S/D

```bash
source /opt/ros/jazzy/setup.bash
source /home/khoa/yumi_phat_bang/install/setup.bash
export ROS_DOMAIN_ID=78
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 run yumi_phat_bang wasd_teleop --ros-args \
  -p speed:=0.15 -p turn:=0.5
```

Giữ focus ở terminal điều khiển:

```text
    W
  A S D
```

- `W`: tiến; `S`: lùi.
- `A` / `D`: quay trái / phải tại chỗ.
- `Space` hoặc `X`: dừng.
- `Q` hoặc Ctrl+C: thoát teleop và gửi lệnh dừng.

Robot giữ lệnh cuối sau khi nhả phím; nhấn `Space` hoặc `X` để dừng. Tốc độ thử ban đầu là
0,15 m/s và 0,5 rad/s, Gazebo còn giới hạn 0,3 m/s và 0,8 rad/s.

Lái chậm quanh các vật cản, quan sát các mặt bị che, sau đó quay về gần nơi
xuất phát để SLAM có cơ hội đóng vòng. Điều khiển tay chưa có tránh va chạm tự
động. Robot rộng khoảng 0,9 m theo footprint dự kiến, nên chừa khoảng trống khi
qua vách và xoay tại chỗ. Không kéo robot bằng công cụ Move trong Gazebo lúc
đang mapping vì odometry sẽ không phản ánh chuyển động bị dịch chuyển trực tiếp.

## 4. Terminal 3: lưu map

Giữ SLAM đang chạy, dừng robot bằng `Space` hoặc `X`, rồi chạy:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=78
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
mkdir -p /home/khoa/yumi_phat_bang/src/yumi_phat_bang/maps
ros2 run nav2_map_server map_saver_cli \
  -f /home/khoa/yumi_phat_bang/src/yumi_phat_bang/maps/yumi_gazebo \
  --ros-args -p use_sim_time:=true \
  -p map_subscribe_transient_local:=true -p save_map_timeout:=10.0
```

Kết quả gồm `yumi_gazebo.yaml` và `yumi_gazebo.pgm`, dùng được cho map_server/AMCL
ở phase sau. Lệnh này lưu occupancy map; không lưu pose graph để tiếp tục SLAM.
Đổi tên sau `-f` nếu muốn lưu nhiều lần.

## Kiểm tra khi chưa thấy map

Trong terminal đã export domain 78:

```bash
ros2 topic hz /front_lidar/scan
ros2 topic hz /odom
ros2 lifecycle get /slam_toolbox
ros2 topic info /map
ros2 run tf2_ros tf2_echo map base_link
```

SLAM phải ở trạng thái `active`; TF phải nối được
`map → odom → base_link → front_lidar_link`. Gazebo phải đang chạy thời gian.
RViz cần Fixed Frame `map` và topic `/map` có Durability `Transient Local`.

Có thể đổi nguồn scan: `slam.launch.py scan_topic:=/rear_lidar/scan`.
Nếu chạy domain khác, truyền `sim_domain_id:=...` vào launch và export cùng
`ROS_DOMAIN_ID` ở các terminal teleop/lưu map. Nếu dùng world khác, truyền cả
`world:=/đường/dẫn/world.sdf` và `world_name:=tên_world_bên_trong_sdf`.

Tham khảo: [SLAM Toolbox](https://github.com/SteveMacenski/slam_toolbox).
