"""Own a mapping subprocess group without touching other robot processes."""
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time


class MappingProcess:
    def __init__(self, command):
        self.output = tempfile.TemporaryFile(mode='w+b')
        try:
            self.process = subprocess.Popen(
                ['bash', '-c', command], start_new_session=True,
                stdout=self.output, stderr=subprocess.STDOUT,
            )
        except Exception:
            self.output.close()
            raise
        self.group_id = self.process.pid

    def poll(self):
        return self.process.poll()

    def error_detail(self):
        self.output.seek(0, os.SEEK_END)
        self.output.seek(max(0, self.output.tell() - 6000))
        return self.output.read().decode('utf-8', errors='replace')[-1500:].strip()

    def stop(self):
        # A launch parent may have exited while its ROS children still run.
        # Signal the owned group even when poll() reports a finished parent.
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(self.group_id, sig)
            except ProcessLookupError:
                break
            try:
                self.process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                continue
            if sig != signal.SIGKILL:
                # Allow remaining children to shut down after their parent exits.
                deadline = time.monotonic() + 0.5
                while time.monotonic() < deadline:
                    try:
                        os.killpg(self.group_id, 0)
                    except ProcessLookupError:
                        break
                    time.sleep(0.02)
        self.process.wait(timeout=1)
        self.output.close()


def stop_previous_yumi_nav2(workspace):
    """Ask an earlier Yumi launch session to shut down its own children."""
    command = [b'launch', b'yumi_robot_pkg', b'NAV2_BRINGUP.launch.py']
    workspace = Path(workspace).resolve()
    matches = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdecimal():
            continue
        pid = int(entry.name)
        try:
            if entry.stat().st_uid != os.getuid() or os.getsid(pid) != pid:
                continue
            args = (entry / 'cmdline').read_bytes().split(b'\0')
            if (len(args) >= 5 and Path(os.fsdecode(args[1])).name == 'ros2'
                    and args[2:5] == command and (entry / 'cwd').resolve(strict=True) == workspace):
                matches.append(pid)
        except (OSError, ValueError):
            continue

    if len(matches) > 1:
        raise RuntimeError('Có nhiều phiên Nav2 của Yumi. Hãy xác định phiên cần dừng.')
    if not matches:
        return None

    pid = matches[0]
    # Signal the launch parent only. ROS launch shuts down its own child nodes.
    # Re-check identity after opening the descriptor to avoid signalling a reused PID.
    with_pid = os.pidfd_open(pid)
    try:
        entry = Path('/proc') / str(pid)
        args = (entry / 'cmdline').read_bytes().split(b'\0')
        if (len(args) < 5 or Path(os.fsdecode(args[1])).name != 'ros2'
                or args[2:5] != command or (entry / 'cwd').resolve(strict=True) != workspace
                or entry.stat().st_uid != os.getuid() or os.getsid(pid) != pid):
            return None
        signal.pidfd_send_signal(with_pid, signal.SIGINT)
    finally:
        os.close(with_pid)
    return pid
