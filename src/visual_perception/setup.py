from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'visual_perception'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # add config file to 'install/build' directory
        (os.path.join('share', package_name, 'config'), glob("config/*.yaml")),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ishan-kumar',
    maintainer_email='ishan-kumar@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            "camera_preprocessor = visual_perception.preprocessor:main",
            "detect_marker = visual_perception.detect_marker:main",
        ],
    },
)
