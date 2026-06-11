## SETUP INSTRUCTIONS
Go through problem.md to setup the workspace, this fork lists the setup instructions for specific packages

Compiled those insturctions into `build.sh` and `launch.sh`
### Visual Perception package
Prerequisite: setup husarion_ws (by following the instructions in https://github.com/CRISS-Robotics-Recruitments-2026/probation_challenge/blob/main/README.md)

Run the following commands after that
```
cd ~/husarion_ws
source /opt/ros/$ROS_DISTRO/setup.bash
colcon build --symlink-install --packages-select visual_perception
```

`--packages-select visual_perception` — builds only your package (fast)
`--symlink-install` — symlinks Python files so you can edit without rebuilding (mostly)
After building, source the overlay:
`source install/setup.bash`

Now run the preprocessor node 
`ros2 run visual_perception camera_preprocessor`
One can use the topics `/cv2_feed/<camera>/img_color` (for processed rgb image)
and the topic  `/cv2_feed/<camera>/img_depth` (for processed depth cam image) \

The topic: `/cv2_feed/<camera>/camera_info` can be utilised to get updated camera intrinsics after undistortion (so the distortion coefficients are now zero) and the camera matrix is different
`IMPORTANT` DO NOT USE RAW IMG ALONG WITH UPDATED CAMERA INTRINSICS OR THE PROCESSED IMG WITH RAW CAMERA INTRINSICS \

`<camera>` is the one of the cameras listed in `src/visual_perception/config/camera_params.yaml` in the property `active_cameras`
_____
To run the aruco detection node: \
`ros2 run visual_perception detect_marker`

The visual perception module detects ArUco markers, calculates their 3D pose in the world, and publishes them.

Publishes on topic: `/visual_perception/detected_markers` \
Message Type: *visual_perception_msgs/msg/DetectedMarker*

**Message Structure**
```yaml
std_msgs/Header header
int32 marker_id
geometry_msgs/PoseStamped pose
string camera_source
float32 confidence
```
marker_id: The ID read from the ArUco tag. According to the rules, these are numbered sequentially clockwise around the boundary. \
pose: A standard geometry_msgs/PoseStamped.
**IMPORTANT**: The pose is already transformed into the map frame.
It represents the 3D center of the marker in the world. \
**camera_source**: e.g., front_cam, rear_cam. Useful for debugging. \
**confidence**: Currently defaults to 1.0. Future updates will scale this based on distance/reprojection error for the Nav stack. \
The detection node also expects a **map frame**, so complete a tf tree for : \
`map -> odom -> base_link -> body_link -> ... -> {camera}_color_optical_frame` \
Otherwise the pose transformation step will not work. \

**Testing Without SLAM**
If you want to test the perception output before SLAM is fully integrated, you can fake the SLAM transform by running:

```bash
ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 map base_link
```
_____
