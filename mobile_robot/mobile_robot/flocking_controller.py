#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge
import cv2
import numpy as np

class FlockingController(Node):
    def __init__(self):
        super().__init__('flocking_controller')
        
        # Subscribe to the camera topic
        self.subscription = self.create_subscription(
            Image,
            'camera/image_raw',
            self.image_callback,
            10
        )
        
        # Publisher for velocity commands
        self.cmd_vel_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        
        self.bridge = CvBridge()

        # Follower parameters
        # Decrease target area so it stops further away from the leader
        self.target_area = 15000.0  
        # Decrease the P-gain so it doesn't rush as hard
        self.kp_linear = 0.00003     
        self.kp_angular = 0.005     
        self.max_linear_speed = 0.4
        self.max_angular_speed = 1.0

        self.get_logger().info('Flocking Controller (Green Tracking) Started.')

    def image_callback(self, msg):
        try:
            # Convert ROS Image message to OpenCV image
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            self.get_logger().error(f"Failed to convert image: {e}")
            return

        # Convert BGR to HSV for robust color tracking
        hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)

        # Define color range for "Gazebo/Green" 
        # (Note: In Gazebo, basic materials might show up slightly differently under lighting)
        # These are typical ranges for a bright green object
        lower_green = np.array([40, 50, 50])
        upper_green = np.array([80, 255, 255])
        
        # Create a mask to isolate the green leader
        mask = cv2.inRange(hsv, lower_green, upper_green)

        # Find contours in the mask
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        twist = Twist()

        if contours:
            # Find the largest contour (assuming it's the leader)
            largest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_contour)
            
            if area > 500: # Ignore noise
                x, y, w, h = cv2.boundingRect(largest_contour)
                cx = x + w / 2

                height, width, _ = cv_image.shape
                image_center_x = width / 2

                # Calculate errors
                error_angular = image_center_x - cx
                error_linear = self.target_area - area

                # Compute velocities using P controllers
                angular_vel = self.kp_angular * error_angular
                linear_vel = self.kp_linear * error_linear

                # Clip velocities
                twist.linear.x = min(self.max_linear_speed, max(-self.max_linear_speed, linear_vel))
                twist.angular.z = min(self.max_angular_speed, max(-self.max_angular_speed, angular_vel))

                # Hard override: If the leader is close enough, stop. 
                # If the leader is *too* close, reverse immediately to avoid collision.
                if area > self.target_area:
                    twist.linear.x = 0.0  # Stop moving forward
                if area > self.target_area * 1.2:
                    twist.linear.x = -0.2 # Back up!

        # Publish the command
        self.cmd_vel_pub.publish(twist)

def main(args=None):
    rclpy.init(args=args)
    flocking_controller = FlockingController()
    
    try:
        rclpy.spin(flocking_controller)
    except KeyboardInterrupt:
        pass
    finally:
        # Stop the robot tightly
        stop_msg = Twist()
        flocking_controller.cmd_vel_pub.publish(stop_msg)
        flocking_controller.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
