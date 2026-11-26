"""Cấu hình robot dùng chung cho giao diện ROS 2 Jazzy."""
import json
import shlex
from pathlib import Path

UI_DIRECTORY = Path(__file__).resolve().parent
CONFIG_PATH = UI_DIRECTORY / 'robot_config.json'
SETTINGS = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
SOURCE_PATH = str(Path(SETTINGS['workspace']).expanduser().resolve())
MAPS_DIRECTORY = Path(SETTINGS['maps_directory']).expanduser()
if not MAPS_DIRECTORY.is_absolute():
    MAPS_DIRECTORY = Path(SOURCE_PATH) / MAPS_DIRECTORY

def shell_source_workspace(command):
    setup = Path(SOURCE_PATH) / 'setup_yumi.bash'
    return (f'source {shlex.quote(str(setup))} && '
            f'cd {shlex.quote(SOURCE_PATH)} && {command}')

def robot_command(key, **values):
    return SETTINGS[key].format(**{k: shlex.quote(str(v)) for k, v in values.items()})
