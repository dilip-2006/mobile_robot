import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, IncludeLaunchDescription, RegisterEventHandler, LogInfo
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
import xacro

def generate_launch_description():
    pkg_name = 'mobile_robot'
    pkg_share = get_package_share_directory(pkg_name)
    
    # Process URDF
    xacro_file = os.path.join(pkg_share, 'urdf', 'robot.urdf.xacro')
    doc = xacro.parse(open(xacro_file))
    xacro.process_doc(doc)
    robot_description = {'robot_description': doc.toxml()}

    # Gazebo Classic
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('gazebo_ros'), 'launch', 'gazebo.launch.py')
        ),
    )

    # Robot State Publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[robot_description],
    )

    # Spawn Robot in Gazebo Classic
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', 'robot_description', '-entity', 'my_bot', '-z', '0.5'],
        output='screen',
    )
    
    # Gesture Control Node
    gesture_node = Node(
        package='mobile_robot',
        executable='gesture_control',
        output='screen',
    )

    welcome_msg = LogInfo(msg="""
=========================================================
  __  __  ___  ____ ___ _     _____
 |  \/  |/ _ \| __ )_ _| |   | ____|
 | |\/| | | | |  _ \| || |   |  _|
 | |  | | |_| | |_) | || |___| |___
 |_|  |_|\___/|____/___|_____|_____|

  ____  ____  ____   ___ _____
 |  _ \/  _ \| __ ) / _ \_   _|
 | |_) | | | |  _ \| | | || |
 |  _ <| |_| | |_) | |_| || |
 |_| \_\\___/|____/ \___/ |_|

  Gesture Controlled  Robot in Gazebo
  By Dilip Kumar
============================================================
""")

    return LaunchDescription([
        welcome_msg,
        gazebo,
        robot_state_publisher,
        spawn_entity,
        gesture_node,
    ])
