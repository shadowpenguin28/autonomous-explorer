import rclpy
import tf2_ros
from tf2_geometry_msgs import do_transform_pose_stamped  # registers PoseStamped with tf1
from geometry_msgs.msg import PoseStamped
from visual_perception_msgs.msg import DetectedMarker
from scipy.spatial.transform import Rotation

from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
from visual_perception.config_loader import load_config
import cv2
from cv2 import aruco
import numpy as np
config = load_config()

qos_profile = QoSProfile(
    depth=1, reliability=ReliabilityPolicy.BEST_EFFORT, history=HistoryPolicy.KEEP_LAST
)
latched_qos = QoSProfile(
    depth=1,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    history=HistoryPolicy.KEEP_LAST,
)

class ArUco_Dectector(Node):
    def __init__(self):
        super().__init__(node_name="aruco_dectection_node")

        self.detected_markers = []  # Store IDs of markers which are already detected
        self.subscribers = {}
        self.bridge = CvBridge()
        self.aruco_dict = aruco.Dictionary_get(aruco.DICT_4X4_50)
        self.parameters = aruco.DetectorParameters_create()
        self.tf2_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf2_buffer, self)

        self.camera_info = {}

        for camera in config["active_cameras"]:
            self.subscribers[f"{camera}_raw"] = self.create_subscription(
                msg_type=Image,
                topic=f"/cv2_feed/{camera}/img_color",
                callback=lambda msg, c=camera: self.marker_detector(msg, c),
                qos_profile=qos_profile
            )
            self.subscribers[f"{camera}_info"] = self.create_subscription(
                msg_type=CameraInfo,
                topic=f"/cv2_feed/{camera}/camera_info",
                qos_profile = latched_qos,
                callback=lambda msg, c=camera: self.info_callback(msg, c)
            )
        
        self.publisher = self.create_publisher(
            msg_type=DetectedMarker, topic="/visual_perception/detected_markers", qos_profile=qos_profile
        )

    def marker_detector(self, msg, c):

        if c not in self.camera_info:
            return  # waiting for camera intrinsics from preprocessor
     
        # Get frame
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        corners, ids, rejected = aruco.detectMarkers(gray, self.aruco_dict, parameters=self.parameters)

        if len(corners) > 0:
            K = np.array(self.camera_info[c].k).reshape(3, 3)  # flat 9-element list → 3x3
            D = np.array(self.camera_info[c].d)  # flat list → 1D array
            marker_size = 0.15  # TODO: get actual marker size from competition specs

            rvecs, tvecs, _ = aruco.estimatePoseSingleMarkers(corners, marker_size, K, D)

            for i, marker_id in enumerate(ids.flatten()):
                if marker_id not in self.detected_markers:
                    rvec = rvecs[i]
                    tvec = tvecs[i]

                    rot_matrix, _ = cv2.Rodrigues(rvec)
                    r = Rotation.from_matrix(rot_matrix)
                    qx, qy, qz, qw = r.as_quat()
                
                    pose_camera = PoseStamped()
                    pose_camera.header.stamp = msg.header.stamp
                    pose_camera.header.frame_id = f"{c}_color_optical_frame"
                    pose_camera.pose.position.x = tvec[0][0]
                    pose_camera.pose.position.y = tvec[0][1]
                    pose_camera.pose.position.z = tvec[0][2]
                    pose_camera.pose.orientation.x = qx
                    pose_camera.pose.orientation.y = qy
                    pose_camera.pose.orientation.z = qz
                    pose_camera.pose.orientation.w = qw

                    try:
                        pose_map = self.tf2_buffer.transform(pose_camera, "map", timeout=rclpy.duration.Duration(seconds=0.1))
                    except (tf2_ros.LookupException, tf2_ros.ExtrapolationException) as e:
                        self.get_logger().warn(f"TF transform failed: {e}")
                        # Fall back: publish in camera frame, the nav team can still use it
                        pose_map = pose_camera
                    
                    det = DetectedMarker()
                    det.header.stamp = self.get_clock().now().to_msg()
                    det.header.frame_id = pose_map.header.frame_id  # "map" if TF worked, camera frame if fallback
                    det.marker_id = int(marker_id)
                    det.pose = pose_map
                    det.camera_source = c
                    det.confidence = 1.0  # TODO: Add a confidence system which the navigation stack can use

                    self.detected_markers.append(int(marker_id))
                    self.publisher.publish(det)
                    self.get_logger().info(f"[{c}] Found and publshed marker: {marker_id}")
    
    def info_callback(self, msg: CameraInfo, c: str):
        self.camera_info[c] = msg

        self.get_logger().info(f"{c}: Stored new camera intrinsics")

        self.destroy_subscription(self.subscribers[f"{c}_info"])
        del self.subscribers[f"{c}_info"]
        self.get_logger().info(f"{c}: unsubscribed from camera_info")

def main(args=None):
    rclpy.init(args=args)

    marker_detector = ArUco_Dectector()
    rclpy.spin(marker_detector)

    marker_detector.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
