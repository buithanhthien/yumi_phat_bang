"""Chọn bản đồ mà không sửa cấu hình hoặc build workspace robot."""
import json
from pathlib import Path
import yaml
from config import UI_DIRECTORY, MAPS_DIRECTORY, SETTINGS

ACTIVE_MAP_PATH = None

SELECTION_FILE = UI_DIRECTORY / 'selected_map.json'

def get_current_map_path():
    if ACTIVE_MAP_PATH is not None:
        return ACTIVE_MAP_PATH
    selected = SETTINGS.get('selected_map', '')
    if SELECTION_FILE.exists():
        selected = json.loads(SELECTION_FILE.read_text(encoding='utf-8'))['path']
    if not selected:
        return ''
    path = Path(selected).expanduser()
    return str(path if path.is_absolute() else MAPS_DIRECTORY / path)

def get_current_map_name():
    return Path(get_current_map_path()).stem

def load_map_yaml(path):
    with open(path, encoding='utf-8') as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict) or not all(k in data for k in ('image', 'resolution', 'origin')):
        raise ValueError('Tệp bản đồ thiếu ảnh, độ phân giải hoặc gốc tọa độ.')
    return data

def update_map_files(map_name, log_callback=None):
    path = MAPS_DIRECTORY / (map_name + '.yaml')
    try:
        data = load_map_yaml(path)
        if not (path.parent / data['image']).is_file():
            raise ValueError('Không tìm thấy ảnh bản đồ.')
        temporary = SELECTION_FILE.with_suffix('.tmp')
        temporary.write_text(json.dumps({'path': str(path)}, ensure_ascii=False), encoding='utf-8')
        temporary.replace(SELECTION_FILE)
        if log_callback:
            log_callback(f'Đã chọn bản đồ: {map_name}. ')
        return True
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        if log_callback:
            log_callback(f'Không thể chọn bản đồ: {exc}')
        return False

def list_available_maps():
    return sorted(p.stem for p in MAPS_DIRECTORY.glob('*.yaml'))
