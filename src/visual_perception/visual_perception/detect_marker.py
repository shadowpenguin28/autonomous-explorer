import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image, CameraInfo
from std_msgs.msg import String
from cv_bridge import CvBridge
from visual_perception.config_loader import load_config

import time
import cv2
from cv2 import aruco
import numpy as np

config = load_config()

qos_profile = QoSProfile(
    depth=1, reliability=ReliabilityPolicy.BEST_EFFORT, history=HistoryPolicy.KEEP_LAST
)


class ArUco_Dectector(Node):
    def __init__(self):
        super().__init__(node_name="aruco_dectection_node")

        self.detected_markers = []  # Store IDs of markers which are already detected
        self.subscribers = {}
        self.bridge = CvBridge()
        self.aruco_dict = aruco.Dictionary_get(aruco.DICT_4X4_50)
        self.parameters = aruco.DetectorParameters_create()

        for camera in config["active_cameras"]:
            self.subscribers[f"{camera}_raw"] = self.create_subscription(
                msg_type=Image,
                topic=f"/cv2_feed/{camera}/img_color",
                callback=lambda msg, c=camera: self.marker_detector(msg, c),
                qos_profile=qos_profile
            )
        self.publisher = self.create_publisher(
            msg_type=String, topic="/visual_perception/detected_markers", qos_profile=qos_profile
        )

    def marker_detector(self, msg, c):
        # Get frame
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        corners, ids, rejected = aruco.detectMarkers(gray, self.aruco_dict, parameters=self.parameters)

        if len(corners) > 0:
            ids = ids.flatten()

            for markerCorner, markerID in zip(corners, ids):
                if markerID in self.detected_markers:
                    continue

                self.detected_markers.append(int(markerID))
                out_msg = String()
                out_msg.data = f"Found marker ID: {markerID}"
                self.publisher.publish(out_msg)
                self.get_logger().info(f"[{c}] Published marker ID: {markerID}")


def main(args=None):
    rclpy.init(args=args)

    marker_detector = ArUco_Dectector()
    rclpy.spin(marker_detector)

    marker_detector.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
