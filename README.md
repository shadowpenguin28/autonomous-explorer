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
and the topic  `/cv2_feed/<camera>/img_depth` (for processed depth cam image)

`<camera>` is the one of the cameras listed in `src/visual_perception/config/camera_params.yaml` in the property `active_cameras`

To run the aruco detection node:
`ros2 run visual_perception detect_marker`
