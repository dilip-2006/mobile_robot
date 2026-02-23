import os
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, LogInfo, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    pkg_name = 'mobile_robot'
    pkg_share = get_package_share_directory(pkg_name)
    xacro_file = os.path.join(pkg_share, 'urdf', 'robot.urdf.xacro')

    # Start Gazebo Classic
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('gazebo_ros'), 'launch', 'gazebo.launch.py')
        ),
    )

    entities = []

    # --- Leader Robot ---
    # Green color to be easily tracked by followers
    leader_doc = xacro.process_file(xacro_file, mappings={'robot_color': 'Gazebo/Green'})
    leader_desc = {'robot_description': leader_doc.toxml()}

    leader_state_pub = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        namespace='leader',
        output='screen',
        parameters=[leader_desc, {'frame_prefix': 'leader/'}],
    )

    leader_spawner = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-topic', '/leader/robot_description', 
            '-entity', 'leader_bot', 
            '-robot_namespace', 'leader',
            '-x', '0.0', '-y', '0.0', '-z', '0.5'
        ],
        output='screen',
    )
    
    entities.extend([leader_state_pub, leader_spawner])


    # --- Follower Robot 1 ---
    # Blue color
    follower_doc = xacro.process_file(xacro_file, mappings={'robot_color': 'Gazebo/Blue'})
    follower_desc = {'robot_description': follower_doc.toxml()}

    follower1_state_pub = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        namespace='follower_1',
        output='screen',
        parameters=[follower_desc, {'frame_prefix': 'follower_1/'}],
    )

    follower1_spawner = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-topic', '/follower_1/robot_description', 
            '-entity', 'follower_1_bot', 
            '-robot_namespace', 'follower_1',
            '-x', '-1.0', '-y', '0.0', '-z', '0.5' # Spawned behind the leader
        ],
        output='screen',
    )
    
    entities.extend([follower1_state_pub, follower1_spawner])

    cv_follower_node = Node(
        package='mobile_robot',
        executable='flocking_controller',
        namespace='follower_1', # Important: puts the node in the follower's namespace
        output='screen',
    )
    
    gesture_leader_node = Node(
        package='mobile_robot',
        executable='gesture_control',
        namespace='leader', # Important: puts the gesture node in the leader's namespace
        output='screen',
    )

    # Welcome message
    welcome_msg = LogInfo(msg="""
=========================================================
  Swarm Mobile Robots starting in Gazebo!
  - 1x Leader (Green)   [/leader/cmd_vel]
  - 1x Follower (Blue)  [/follower_1/cmd_vel]
=========================================================
""")

    return LaunchDescription([
        welcome_msg,
        gazebo,
        cv_follower_node,
        gesture_leader_node
    ] + entities)
