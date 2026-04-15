#!/bin/bash
set -e

echo "Downloading patches..."
curl -L -o patches.zip "https://github.com/CRISS-Robotics-Recruitments-2026/husarion-patches/releases/download/1.0.0/patches.zip"

echo "Extracting patches..."
unzip -o patches.zip -d /tmp/marsyard_patches
rm patches.zip

echo "Placing models and worlds..."
mkdir -p src/husarion_gz_worlds/models
mkdir -p src/husarion_gz_worlds/worlds

cp -r /tmp/marsyard_patches/patches/aruco_pole_textures src/husarion_gz_worlds/models/
cp -r /tmp/marsyard_patches/patches/mars_yard src/husarion_gz_worlds/models/
cp -r /tmp/marsyard_patches/patches/landmarks src/husarion_gz_worlds/models/
cp /tmp/marsyard_patches/patches/mars_yard.sdf src/husarion_gz_worlds/worlds/

echo "Replacing components.yaml and gz_sim.launch.py..."
cp /tmp/marsyard_patches/patches/components.yaml src/husarion_ugv_ros/husarion_ugv_description/config/
cp /tmp/marsyard_patches/patches/gz_sim.launch.py src/husarion_gz_worlds/launch/

# Clean up
rm -rf /tmp/marsyard_patches

echo "Setup Complete!"
