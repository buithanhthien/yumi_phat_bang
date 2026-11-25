# Lộ trình phát triển Yumi

Cấu hình đã xác nhận: ROS 2, hai LiDAR, hai bánh chủ động và bốn bánh bị động.
Máy phát triển có Jazzy. Chưa xác nhận MCU, driver động cơ, encoder, IMU,
phiên bản ROS trên máy đích, bán kính lăn thực và yêu cầu độ chính xác.

| Phase | Mô phỏng | Robot thật | Điều kiện nghiệm thu |
|---|---|---|---|
| P0 — Giao diện và thông số | Chọn topic, message, TF, quy ước dấu | Chốt MCU/driver, encoder/IMU, đo bánh và thân | Có bảng thông số, nguồn phát từng topic/TF và ngưỡng sai số |
| P1 — Mô hình | RViz, mesh, joint, collision, inertia, tiếp xúc sàn | Đối chiếu hình học, hướng bánh, vị trí LiDAR | Model đúng tỷ lệ, TF liên thông, không thiếu mesh |
| P2 — Base | Tiến/lùi, quay hai chiều, cung tròn, odometry và joint feedback | Kê robot kiểm tra dấu; chỉnh PID; chạy dưới sàn; timeout và dừng khẩn | Chuyển động đúng dấu, bám vận tốc, dừng đúng yêu cầu |
| P3 — Cảm biến/trạng thái | Hai scan, lọc thân, ghép scan, odometry/EKF | Hiệu chuẩn bánh, LiDAR, covariance và timestamp | Scan khớp môi trường, odometry đạt ngưỡng, không trùng TF |
| P4 — SLAM/AMCL | Tạo map, lưu map, định vị lại | Lập map khu thử và kiểm tra nhiều vị trí | Map dùng được, định vị ổn định khi chạy và khởi động lại |
| P5 — Nav2 | Goal, góc cua, hành lang, đường bị chặn | Chạy tốc độ thấp rồi tăng dần tải/tốc độ | Đạt tỷ lệ đến goal, sai số cuối, khoảng hở đã chốt |
| P6 — Lỗi/vận hành | Mất scan/odom, trễ dữ liệu, hủy goal, restart | Mất MCU, chuyển tay/tự động, dừng khẩn, chạy lâu | Dừng, báo lỗi và phục hồi có kiểm soát |
| P7 — Nhiệm vụ nếu cần | Waypoint, giao diện, docking | Chạy chu kỳ với môi trường và tải thật | Đạt số chu kỳ và tiêu chí nhiệm vụ |

## Trạng thái bản khởi đầu

- P0: đã ghi cấu hình biết được và topic mô phỏng; phần cứng/ngưỡng chưa chốt.
- P1: đã có package, launch RViz và mô hình Gazebo riêng. Cần người vận hành
  kiểm tra hình ảnh và đối chiếu robot thật.
- P2: đã có DiffDrive, bridge và world thử. Chưa nghiệm thu điều khiển thật.
- P3: hai scan thô và odometry mô phỏng hoạt động. Đã thêm đường
  `/odomfromSTM32` → `/odom/stm32` → EKF và launch hai LiDAR Ethernet;
  chưa xác nhận dữ liệu từ thiết bị thật hoặc hiệu chuẩn phần cứng.
- P4 mô phỏng: đã thêm SLAM, RViz hiển thị map, world có vật cản, teleop
  bàn phím và hướng dẫn lưu occupancy map. SLAM hiện dùng LiDAR trước 360°.
- P4 thực tế: đã có launch SLAM dùng LiDAR trước; chưa nghiệm thu trên robot thật.
- P5–P7: chưa triển khai cho Yumi.

## Kiểm tra theo thứ tự

1. Hiển thị CAD: đủ mesh, hai bánh chủ động, bốn bánh bị động, hai LiDAR.
2. Spawn Gazebo: robot đứng ổn định trên sàn; `/clock`, `/odom`, `/joint_states`
   và TF có dữ liệu; không chạy joint_state_publisher mẫu trong mô phỏng.
3. Hai scan: đúng `frame_id`, có tường xung quanh, tần số gần 10 Hz.
4. Lệnh `linear.x > 0`: odometry x tăng; thử tiếp lệnh âm.
5. Lệnh `angular.z > 0`: quay ngược chiều kim đồng hồ khi nhìn từ trên;
   thử tiếp lệnh âm.
6. Gửi vận tốc 0: dừng. Bổ sung watchdog trước khi nghiệm thu P2 phần cứng.
7. Ghi rosbag, kết quả và sai số cho mỗi bài thử; chốt ngưỡng trước nghiệm thu.

## Quy tắc tích hợp các phase sau

- Mô phỏng và phần cứng cung cấp cùng giao diện cho phần xử lý cấp cao.
- `/cmd_vel` là lệnh cuối tới base, `/odom` là odometry dùng cho Nav2.
- Với phần cứng hiện tại: STM32 phát `/odomfromSTM32`, node chuẩn hóa phát
  `/odom/stm32`, EKF phát `/odometry/filtered` và TF `odom → base_link`.
  Không chạy thêm `odom_tf_broadcaster` để tránh trùng TF.
- SLAM hoặc AMCL phát `map → odom`, không bật cả hai nguồn TF cùng lúc.
- SLAM Yumi hiện dùng `/front_lidar/scan`; nếu ghép hai scan, chọn một topic
  thống nhất cho SLAM/AMCL và costmap sau khi kiểm tra hình học LiDAR.
- Chỉ một nơi quản lý chọn nguồn lệnh; cấu hình điều khiển tay/tự động và
  điều kiện dừng trước khi nghiệm thu robot thật.
- Tuning controller Nav2 thực hiện sau khi vòng vận tốc bánh và odometry ổn định.
