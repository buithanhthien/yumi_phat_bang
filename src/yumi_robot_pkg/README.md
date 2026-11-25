# Yumi hardware bringup

This package now uses Yumi's CAD URDF and meshes. The original Zackon model,
RViz file and mapping configuration are retained in `../legacy_zackon_view_robot/` for
reference. The older Zackon Nav2 launch files and maps remain in this package;
their footprint, map and controller settings have not been calibrated for Yumi.

## Data path

```text
STM32 --UDP:8888--> micro_ros_agent --> /odomfromSTM32
  --> odom_frame_publisher --> /odom/stm32 --> EKF --> /odometry/filtered
                                                   + TF odom -> base_link
front Ethernet LiDAR --> /front_lidar/scan --> front filter --+
rear Ethernet LiDAR  --> /rear_lidar/scan  --> rear filter ---+
  --> dual_laser_merger --> /merged --> SLAM / AMCL / Nav2 costmaps
SLAM / AMCL --> TF map -> odom
robot_state_publisher --> TF base_link -> front_lidar_link/rear_lidar_link
```

The Agent and LiDAR defaults come from the Zackon setup: front
`192.168.3.45:8089`, rear `192.168.2.46:8089`, Agent UDP port `8888`, and STM32
topic `/odomfromSTM32`. Override them at launch if Yumi uses different values.
The PC network interfaces used by Zackon were `192.168.3.150` and
`192.168.2.150`; verify your current interface configuration before connecting.

## Build

```bash
source /opt/ros/jazzy/setup.bash
cd /home/khoaiuh/yumi_phat_bang
colcon --log-base log_yumi build --base-paths src \
  --build-base build_yumi --install-base install_yumi \
  --packages-up-to yumi_phat_bang yumi_robot_pkg --symlink-install \
  --parallel-workers 2 --cmake-args -DBUILD_TESTING=OFF \
  -DCMAKE_BUILD_TYPE=Release -DUAGENT_SUPERBUILD=OFF \
  -DUAGENT_USE_SYSTEM_FASTCDR=ON -DUAGENT_USE_SYSTEM_FASTDDS=ON \
  -DUAGENT_USE_SYSTEM_LOGGER=ON -DUAGENT_BUILD_EXECUTABLE=OFF
source install_yumi/setup.bash
```

Use a fresh terminal sourced only with ROS Jazzy before building. The separate
`build_yumi`, `install_yumi` and `log_yumi` directories avoid the broken symlinks
in the imported build. Source `install_yumi/setup.bash` in every hardware terminal.

The current STM32 firmware publishes in ROS domain 0. Use that domain in all
hardware terminals. Stop any Gazebo launch in that domain before connecting to
hardware:

```bash
export ROS_DOMAIN_ID=0
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
```

The Agent is built against the Fast DDS libraries from ROS 2 Jazzy. The
workspace includes its `microxrcedds_agent` source because the separately
installed `/usr/local` build crashed with `stack smashing detected` when STM32
created a participant. Rebuild through colcon if the Agent executable changes:

```bash
colcon --log-base log_yumi build --base-paths src \
  --build-base build_yumi --install-base install_yumi \
  --packages-up-to micro_ros_agent --symlink-install
source install_yumi/setup.bash
```

## 1. Confirm STM32 odometry

Start the Agent and model, leaving LiDAR and EKF off for the first check:

```bash
ros2 launch yumi_robot_pkg yumi_hardware.launch.py \
  start_lidars:=false start_ekf:=false
```

In another terminal with the same sourced setup and domain:

```bash
ros2 topic info /odomfromSTM32
ros2 topic echo /odomfromSTM32 --once
```

The STM32 must publish `nav_msgs/msg/Odometry`. Check its position, orientation,
twist and timestamps while the robot is stationary. This launch does not send
motor commands. If the topic or port differs, use `odom_topic:=...` or
`agent_port:=...` in the launch command.

## 2. Confirm EKF and Ethernet LiDARs

To inspect only STM32 odometry and the Yumi URDF in RViz, keep an already
running Agent on UDP 8888 and start:

```bash
ros2 launch yumi_robot_pkg yumi_hardware.launch.py \
  start_agent:=false start_lidars:=false rviz:=true publish_joint_states:=true
```

RViz opens with `Fixed Frame = odom`, the Yumi model, TF, and
`/odometry/filtered`. The robot should move relative to the grid when the
encoder odometry changes. Check `ros2 run tf2_ros tf2_echo odom base_link`
in another terminal. If the Agent is not already running, omit
`start_agent:=false`. `publish_joint_states:=true` is now the default and gives the two wheel joints
zero angles for model visualization; it does not read wheel angles from STM32.

Stop the first launch, then run:

```bash
ros2 launch yumi_robot_pkg yumi_hardware.launch.py rviz:=true
```

Check the data in another terminal:

```bash
ros2 topic echo /odometry/filtered --once
ros2 run tf2_ros tf2_echo odom base_link
ros2 topic hz /front_lidar/scan
ros2 topic hz /rear_lidar/scan
```

To test only one LiDAR, pass `start_rear_lidar:=false` or
`start_front_lidar:=false`. To change addresses, pass `front_lidar_ip:=...`,
`rear_lidar_ip:=...`, `front_lidar_port:=...` or `rear_lidar_port:=...`.

## 3. Run SLAM on the real robot

Stop the hardware-only launch first, then start the combined launch:

```bash
ros2 launch yumi_robot_pkg MAP_GENERATING.launch.py
```

It uses both Yumi LiDARs through `/merged` and `use_sim_time:=false`. To attach SLAM to an
already running hardware launch, use `start_robot:=false`. Only one Agent, EKF
and SLAM instance should run in a ROS domain. The filters publish `/scan_front_lidar_filter` and `/scan_rear_lidar_filter`;
the merger transforms both into `base_link` and publishes `/merged`.
The filter bounds and merger geometry settings follow Zackon, with Yumi's URDF
providing the sensor transforms. Verify the resulting scan against real obstacles.

`yumi_hardware.launch.py` starts this same processing pipeline by default.
Use `start_lidar_processing:=false` for raw driver inspection, or launch
`lidar_processing.launch.py` separately when raw drivers are managed externally.
For front-only SLAM:

```bash
ros2 launch yumi_robot_pkg MAP_GENERATING.launch.py \
  start_rear_lidar:=false start_lidar_processing:=false \
  scan_topic:=/front_lidar/scan
```

## 4. Navigation

```bash
ros2 launch yumi_robot_pkg NAV2_BRINGUP.launch.py
```

This includes the same hardware launch (Agent, odometry normalizer, EKF, both
LiDAR drivers, filters and merger), then AMCL and Nav2. If the hardware launch
is already running with its default processing pipeline, attach with
`start_robot:=false` to avoid duplicate drivers, filters, merger and EKF.
Use `start_agent:=false` when only the Agent is already running.
Do not run mapping and AMCL together: both publish `map -> odom`.

Check the scan consumed by navigation:

```bash
ros2 topic hz /merged
ros2 topic echo /merged --once --field header
ros2 run tf2_ros tf2_echo base_link front_lidar_link
ros2 run tf2_ros tf2_echo base_link rear_lidar_link
```

The navigation geometry and controller settings still come from Zackon. Before
enabling Nav2 or sending drive commands to Yumi, measure its wheel geometry,
verify encoder and motor signs, and set a safe footprint and velocity limits.

## Wheel TF and package migration

The active hardware package and Python module are now `yumi_robot_pkg`, located
in `src/yumi_robot_pkg`. Build and source `install_yumi`, not the imported
`install` or the previous `install_lidar`. Old `view_robot_pkg` commands may still
resolve Zackon if that workspace is sourced in the shell; use a fresh terminal.
The `legacy_zackon_view_robot` directory is an unchanged reference archive.

The expected tree is `map -> odom -> base_link -> leftwheel_link/rightwheel_link`.
SLAM or AMCL publishes `map -> odom`; EKF publishes `odom -> base_link`;
robot_state_publisher publishes wheel transforms from `/joint_states`.
The wheel joints are continuous, so their transforms require joint state messages.
Hardware, mapping and navigation now enable joint_state_publisher by default.
Its zero angles provide wheel TF for visualization, not measured wheel rotation.
When a real driver publishes both `leftwheel_joint` and `rightwheel_joint`, pass
`publish_joint_states:=false` to avoid a second joint state source.
Do not run fake_diff_drive on the real robot; it creates simulated odometry.

```bash
ros2 topic echo /joint_states --once
ros2 run tf2_ros tf2_echo base_link leftwheel_link
ros2 run tf2_ros tf2_echo base_link rightwheel_link
# With SLAM or AMCL and EKF active:
ros2 run tf2_ros tf2_echo map leftwheel_link
ros2 run tf2_ros tf2_echo map rightwheel_link
```

## Selecting Yumi in a terminal

This machine's `.bashrc` automatically sources `zackon_build_up`. To clear that
inherited environment and select only ROS Jazzy plus this Yumi build, use:

```bash
source /home/khoaiuh/yumi_phat_bang/setup_yumi.bash
export ROS_DOMAIN_ID=0
ros2 pkg prefix yumi_robot_pkg
ros2 launch yumi_robot_pkg MAP_GENERATING.launch.py
```

Stop previous robot launches first; changing a package name does not stop existing
nodes using `/tf`, `/joint_states` or `/robot_description`. The setup helper resets
ROS/Python/CMake library search paths in the current shell, without editing `.bashrc`.

## Empty map with healthy raw LiDAR scans

The Yumi LiDAR planes have negative Z in `base_link` (approximately -0.018 m
and -0.014 m). The installed dual_laser_merger defaults to a positive
`min_height`, which discards both planes. The merge launch explicitly sets
`min_height: -1.0` and `max_height: 1.0`, and uses the installed driver's
`merged_scan_topic` parameter for `/merged`. A scan containing only infinity
ranges cannot build a useful map, even while `/map` messages are being received.
After changing these launch parameters, restart the mapping launch so the
merger reads them. Check that `/merged` contains finite ranges before diagnosing
map-frame or RViz errors.

## Localization on the saved X5 map

Stop `MAP_GENERATING.launch.py` first, then run:

```bash
source /home/khoaiuh/yumi_phat_bang/setup_yumi.bash
export ROS_DOMAIN_ID=0
ros2 launch yumi_robot_pkg LOCALIZATION.launch.py \
  map:=/home/khoaiuh/yumi_phat_bang/src/yumi_robot_pkg/maps/X5_19102026.yaml
```

This starts the same hardware/EKF/merged LiDAR pipeline plus map_server and AMCL.
It loads the saved occupancy map instead of running SLAM or updating the map.
It does not start a navigation controller or velocity arbiter. In RViz, use
**2D Pose Estimate** to click the robot's current location and drag its heading.
AMCL waits for that initial pose by default (`set_initial_pose:=false`).
For hardware already running independently, use `start_robot:=false`; stop SLAM
before attaching so only AMCL publishes `map -> odom`.
A `.yaml/.pgm` occupancy map is loaded with AMCL; slam_toolbox localization needs
a serialized pose graph, so changing its mapping YAML mode alone is insufficient.

The setup helper defaults DDS discovery to `LOCALHOST`, so other robots on the
LAN in domain 0 do not overwrite `/map` or `/tf`. The local Ethernet micro-ROS
Agent continues receiving STM32 UDP traffic. For an intentional multi-host ROS
setup, export `YUMI_DISCOVERY_RANGE=SUBNET` before sourcing the helper.
If a micro-ROS Agent is already bound to UDP 8888, pass `start_agent:=false`.

## Nav2 RViz workspace

`NAV2_BRINGUP.launch.py` now opens `rviz/nav2_view.rviz` by default. The navigation
UI uses a top-down map view and includes the Navigation 2 panel, 2D Pose Estimate,
Nav2 Goal, map, robot model, selected TF axes, merged/raw LiDARs, AMCL particles,
global/local costmaps, the global path and both published costmap footprints.
The footprint outlines show the actual costmap collision geometry; costmap
coloring shows the obstacle/inflation cost fields.

```bash
source /home/khoaiuh/yumi_phat_bang/setup_yumi.bash
export ROS_DOMAIN_ID=0
ros2 launch yumi_robot_pkg NAV2_BRINGUP.launch.py start_agent:=false
```

Use `start_agent:=false` when the system micro-ROS Agent is already running.
Stop an older full robot launch before starting this one. In RViz, first set the
robot position/heading with **2D Pose Estimate**, then use **Nav2 Goal** once
localization and navigation are active. Global paths appear after a goal is sent;
costmaps/footprints appear when their lifecycle nodes are active. The Navigation 2
panel exposes navigation state and goal cancellation.

The optional **Controller Path** display is available but disabled by default:
it listens to `/local_plan`, which the current MPPI setup may not publish.
Controller visualization settings in `nav2_params.yaml` were not changed.

RViz also opens when attaching to an independently running hardware launch via
`start_robot:=false`; that option still starts localization, so do not attach it
to an already running AMCL session. Use `rviz:=false` to disable the UI or
`rviz_config:=/absolute/path/custom.rviz` to choose another configuration.

## Nav2 waits for the initial localization pose

Full `NAV2_BRINGUP.launch.py` now starts hardware, map_server, AMCL and RViz first.
The `wait_for_localization` helper waits for a fresh `map -> odom -> base_link`
transform, then starts the navigation stack. There is no initial-pose countdown:
choose **2D Pose Estimate** when ready. The Navigation 2 panel may show unknown
until the navigation servers are started, then it can report their lifecycle state.
This prevents global_costmap activation from timing out while AMCL is waiting for
the first pose. No pose or artificial map transform is generated by the helper.
Use `wait_for_localization:=false` only to restore the previous immediate startup.
The inflation and footprint parameters are unaffected by this launch change.
