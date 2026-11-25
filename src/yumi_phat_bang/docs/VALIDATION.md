# Kiểm tra bản khởi đầu — 2026-10-08

Môi trường: ROS 2 Jazzy, Gazebo Sim 8; ROS domain 78 và Gazebo partition riêng.

Đã kiểm tra:

- `colcon build`: package được nhận diện là `ros.ament_python`, build thành công.
- `ros2 launch ... --show-args`: hai launch nạp được.
- `check_urdf`: mô hình mô phỏng parse thành công.
- Chuyển URDF sang SDF: giữ được hai cảm biến LiDAR.
- Gazebo headless: spawn thành công và tạo đủ bridge.
- Hai topic scan nhận được dữ liệu với frame `front_lidar_link` và
  `rear_lidar_link`, mỗi scan 1440 mẫu; tại thời điểm đọc mỗi scan có
  1431 giá trị hữu hạn.
- Thử tiến 0,1 m/s khoảng 3 giây: `/odom` tăng x khoảng 0,2903 m; gửi
  vận tốc 0 sau bài thử. Đây là odometry của mô phỏng, chưa đo sai số
  chuyển động vật lý hay hiệu chuẩn phần cứng.
- URDF CAD gốc được đối chiếu byte và giữ nguyên.

Chưa nghiệm thu: hình ảnh RViz, quay/lùi, hình học tiếp xúc chính xác,
động lực học caster, firmware/PID, timeout phần cứng, AMCL, Nav2. SLAM được kiểm tra bổ sung bên dưới.
Các cảnh báo `gz_frame_id` từ sdformat không ngăn cảm biến xuất đúng frame;
KDL cảnh báo inertia ở root link CAD, robot_state_publisher vẫn khởi chạy.

## Bổ sung SLAM mô phỏng — 2026-10-08

Chạy độc lập ở ROS domain 79, Gazebo partition `yumi_mapping_test`, headless.

- `mapping_sim.launch.py` tự khởi chạy Gazebo, bridge và lifecycle SLAM Toolbox.
- Nhận được `/map`, `/odom`, cả hai scan và TF `map → base_link`.
- Map ban đầu 155 × 134 ô, độ phân giải 0,05 m/ô.
- Kiểm thử node `teleop_twist_keyboard` bằng pseudo-terminal: `i` rồi `k`
  cho độ dịch chuyển odometry khoảng 0,8914 m; `j` rồi `k` cho yaw
  khoảng 1,4990 rad. Robot dừng sau `k`.
- Nhận 15 lần cập nhật map; tại thời điểm kiểm tra có 1009 ô occupied
  và 10015 ô free.
- `nav2_map_server map_saver_cli` lưu thành công map 163 × 158 ô
  thành YAML và PGM ở `/tmp/yumi_mapping_stage/test_map/`.
- Chưa kiểm tra trực quan RViz hoặc nghiệm thu độ chính xác bản đồ.
  Chưa ghép hai scan; SLAM dùng LiDAR trước.
