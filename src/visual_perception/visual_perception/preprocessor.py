import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
from visual_perception.config_loader import load_config

import time
import cv2
import numpy as np

qos_profile = QoSProfile(
    depth=1, reliability=ReliabilityPolicy.BEST_EFFORT, history=HistoryPolicy.KEEP_LAST
)
# Use TRANSIENT_LOCAL so late-joining subscribers (like pose estimator) still receive it
latched_qos = QoSProfile(
    depth=1,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    history=HistoryPolicy.KEEP_LAST,
)
# depth=1 for latest frame
# BEST_EFFORT for matching the camera feed publisher's reliability policy

config = load_config()


# topic: /{camera}/{type}/<image_raw/camera_info>
class CameraPreProcessor(Node):
    def __init__(self):
        super().__init__(node_name="camera_pre_processor")
        self.bridge = CvBridge()

        self.subs = {}
        self.pubs = {}
        self.camera_info = {}
        self.undistort_maps = {}  # precomputed maps for faster undistortion
        self.last_publish_time = {}
        self.min_interval = 1.0 / config["target_fps"]

        for camera in config["active_cameras"]:
            self.last_publish_time[f"{camera}_raw"] = 0.0
            self.last_publish_time[f"{camera}_depth"] = 0.0

            # ---------------- IMAGES -----------------------
            self.subs[f"{camera}_raw"] = (
                self.create_subscription(  # for raw color image
                    msg_type=Image,
                    topic=f"/{camera}/color/image_raw",
                    qos_profile=qos_profile,
                    callback=lambda msg, c=camera: self.raw_callback(msg, c),
                )
            )

            self.subs[f"{camera}_depth"] = self.create_subscription(  # for depth cam
                msg_type=Image,
                topic=f"/{camera}/depth/image_rect_raw",
                qos_profile=qos_profile,
                callback=lambda msg, c=camera: self.depth_callback(msg, c),
            )
            self.pubs[f"{camera}_raw"] = (
                self.create_publisher(  # publish processed color image for pipelines
                    msg_type=Image,
                    topic=f"/cv2_feed/{camera}/img_color",
                    qos_profile=qos_profile,
                )
            )

            self.pubs[f"{camera}_depth"] = (
                self.create_publisher(  # publish processed depth color for pipelines
                    msg_type=Image,
                    topic=f"/cv2_feed/{camera}/img_depth",
                    qos_profile=qos_profile,
                )
            )
            # ------------------- CAMERA INFO ------------------
            self.subs[f"{camera}_info"] = self.create_subscription(
                msg_type=CameraInfo,
                topic=f"/{camera}/color/camera_info",
                qos_profile=qos_profile,
                callback=lambda msg, c=camera: self.info_callback(msg, c),
            )

            self.pubs[f"{camera}_info"] = self.create_publisher(
                msg_type=CameraInfo,
                topic=f"/cv2_feed/{camera}/camera_info",
                qos_profile=latched_qos,
            )

    def raw_callback(self, msg, camera):
        now = time.monotonic()
        key = f"{camera}_raw"
        if now - self.last_publish_time[key] < self.min_interval:
            return  # drop this frame

        # otherwise continue => throttled to min interval
        frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")

        # PROCESS IMG
        if config["enable_undistortion"] and camera in self.undistort_maps:
            map1, map2 = self.undistort_maps[camera]
            frame = cv2.remap(frame, map1, map2, interpolation=cv2.INTER_AREA)
        else:
            # Resize img to config["target_resolution"]
            target = config["target_resolution"]
            frame = cv2.resize(frame, tuple(target), interpolation=cv2.INTER_AREA)

        out_msg = self.bridge.cv2_to_imgmsg(frame, "bgr8")
        out_msg.header = msg.header
        self.pubs[f"{camera}_raw"].publish(out_msg)
        self.last_publish_time[key] = time.monotonic()

    def depth_callback(self, msg, camera):
        now = time.monotonic()
        key = f"{camera}_depth"
        if now - self.last_publish_time[key] < self.min_interval:
            return  # drop this frame

        # otherwise continue => throttled to min interval
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")

        target = config["target_resolution"]
        frame = cv2.resize(frame, tuple(target), interpolation=cv2.INTER_NEAREST)
        out_msg = self.bridge.cv2_to_imgmsg(frame, encoding="passthrough")
        out_msg.header = msg.header
        self.pubs[f"{camera}_depth"].publish(out_msg)
        self.last_publish_time[key] = time.monotonic()

    def info_callback(self, msg, camera):
        if camera in self.undistort_maps:
            return  # safety guard in case of race condition

        # Extract camera matrix (K) and distortion coefficients (D)
        K = np.array(msg.k).reshape(3, 3)
        D = np.array(msg.d)

        # Compute undistortion maps (do this ONCE, not per frame)
        target = config["target_resolution"]
        new_K, _ = cv2.getOptimalNewCameraMatrix(
            K, D, (msg.width, msg.height), 0, (target[0], target[1])
        )
        map1, map2 = cv2.initUndistortRectifyMap(
            K, D, None, new_K, (target[0], target[1]), cv2.CV_16SC2
        )

        self.undistort_maps[camera] = (map1, map2)
        self.camera_info[camera] = msg
        self.get_logger().info(f"{camera}: undistortion maps computed")

        new_info = CameraInfo()
        new_info.header = msg.header
        new_info.width = target[0]
        new_info.height = target[1]
        new_info.distortion_model = "plumb_bob"
        new_info.k = (
            new_K.flatten().tolist()
        ) 
        new_info.d = [0.0, 0.0, 0.0, 0.0, 0.0]  # distortion already removed
        new_info.r = msg.r  
        # Projection matrix P: [new_K | 0] as a flat 12-element list
        new_info.p = [
            new_K[0, 0],
            new_K[0, 1],
            new_K[0, 2],
            0.0,
            new_K[1, 0],
            new_K[1, 1],
            new_K[1, 2],
            0.0,
            new_K[2, 0],
            new_K[2, 1],
            new_K[2, 2],
            0.0,
        ]

        self.pubs[f"{camera}_info"].publish(new_info)
        self.get_logger().info(
            f"{camera}: published updated CameraInfo to /cv2_feed/{camera}/camera_info"
        )

        # Unsubscribe after computing the undistortion map
        self.destroy_subscription(self.subs[f"{camera}_info"])
        del self.subs[f"{camera}_info"]
        self.get_logger().info(f"{camera}: unsubscribed from camera_info")


def main(args=None):
    rclpy.init(args=args)
    pre_processor = CameraPreProcessor()
    rclpy.spin(pre_processor)

    pre_processor.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
