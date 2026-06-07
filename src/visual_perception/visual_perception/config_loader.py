import os
import yaml
from ament_index_python.packages import get_package_share_directory

def load_config():
    pkg_share = get_package_share_directory("visual_perception")
    config_path = os.path.join(pkg_share, "config", "camera_params.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)

types = ['color', 'depth']
'''
camera topics:
/front_cam/color/camera_info
/front_cam/color/image_raw
/front_cam/depth/camera_info
/front_cam/depth/color/points
/front_cam/depth/image_rect_raw
/left_cam/color/camera_info
/left_cam/color/image_raw
/left_cam/depth/camera_info
/left_cam/depth/color/points
/left_cam/depth/image_rect_raw
/rear_cam/color/camera_info
/rear_cam/color/image_raw
/rear_cam/depth/camera_info
/rear_cam/depth/color/points
/rear_cam/depth/image_rect_raw
/right_cam/color/camera_info
/right_cam/color/image_raw
/right_cam/depth/camera_info
/right_cam/depth/color/points
/right_cam/depth/image_rect_raw
'''