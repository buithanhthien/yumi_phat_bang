# Pkg: view_robot_pkg 

---
## 1.
Cấp quyền truy cập cho port 
sudo chmod 777 /dev/ttyUSB*
sudo chmod 777 /dev/ttyACM0
sudo chmod 777 /dev/input/js*
## 2.
Run this command:

```bash
ros2 launch view_robot_pkg launch_zackon.launch.py
```

## Dependencies
```bash
sudo apt install ros-${ROS_DISTRO}-rviz2 \
                 ros-${ROS_DISTRO}-joint-state-publisher-gui \
                 ros-${ROS_DISTRO}-robot-state-publisher
```
## Related YouTube Video
#### Explains how to convert SolidWorks to URDF for ROS2 & How to use this package.
#### Link: https://www.youtube.com/watch?v=JdZJP3tGcA4&feature=youtu.be




## Lập bản đồ tự động / Automatic mapping

Trong cửa sổ **Bản đồ mới** có chế độ **Thủ công** và **Tự động khám phá**.
Xem [hướng dẫn, điều kiện hoàn tất và kiểm thử](../../docs/automatic-map-exploration.md).
