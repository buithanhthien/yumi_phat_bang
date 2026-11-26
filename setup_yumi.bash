# Source this file to select the independent Yumi ROS workspace.
# This resets inherited ROS/Python/CMake library paths (including Zackon).
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    echo "Use: source /home/khoaiuh/yumi_phat_bang/setup_yumi.bash" >&2
    exit 1
fi
_yumi_workspace_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -f "${_yumi_workspace_root}/install/local_setup.bash" ]]; then
    echo "Build install first; see ${_yumi_workspace_root}/README.md" >&2
    unset _yumi_workspace_root
    return 1
fi
unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH LD_LIBRARY_PATH PYTHONPATH
source /opt/ros/jazzy/setup.bash || return $?
source "${_yumi_workspace_root}/install/local_setup.bash"
_yumi_setup_status=$?
# Keep unrelated ROS domain-0 robots from supplying /map or /tf. The STM32
# still connects by Ethernet to the local micro-ROS Agent on UDP 8888.
export ROS_AUTOMATIC_DISCOVERY_RANGE="${YUMI_DISCOVERY_RANGE:-LOCALHOST}"
unset _yumi_workspace_root
return "${_yumi_setup_status}"
