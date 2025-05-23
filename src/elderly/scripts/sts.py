#!/usr/bin/env python3

import subprocess
import yaml

import rospy
from sensor_msgs.msg import Joy


class PololuJrkG2MotorControllerInterface:
    """
    Documentation: https://www.pololu.com/docs/pdf/0J73/jrk_g2_motor_controller.pdf
    """
    """
    Middle-level command for sending low-level CLI to communicate with Pololu Jrk G2
    """

    def __init__(self,):
        self.devices = None

    def jrk2cmd(self, *args):
        return subprocess.check_output(["jrk2cmd"] + list(args))

    def add_devices(self, devices: dict):
        self.devices = devices
    
    def get_devices_list(self):
        out_raw = self.jrk2cmd("--list")
        out_list = out_raw.decode().strip().replace(" ", "").split("\n")
        out_list = [s.split(",") for s in out_list]
        # [ ["serial_number", "model"], ... ]
        # len(out_list) is the number of devices
        return out_list

    def get_status(self, device: str):
        out = self.jrk2cmd("-d", device, "--status", "--full")
        return yaml.safe_load(out)

    def set_target(self, device: str, target: str):
        self.jrk2cmd("-d", device, "--target", target)
        return [device, target]

    def set_stop(self, device: str):
        self.jrk2cmd("-d", device, "--stop")
        return [device, "stop"]


class STSRobot:
    def __init__(self):

        # initialize node
        rospy.init_node("stsrobot", log_level=rospy.DEBUG)
        rospy.loginfo("STS Robot is initialized!")

        # serial number of motor controllers
        self.devices = {
            "lf": "00372080",  # left front
            "rf": "00372247",  # right front
            "lb": "00372251",  # left back
            "rb": "00372242",  # right back
            "md": "00343198",  # middle
        }

        # motor controller interface
        self.interface = PololuJrkG2MotorControllerInterface()

        # subscribers
        rospy.Subscriber("/buttons/left", Joy, self.button_left_cb)
        rospy.Subscriber("/buttons/right", Joy, self.button_right_cb)

        # attributes
        self.stage = 0  # 0, 1, 2, 3
        self.buttons = [0, 0]  # [l, r]
        self.initialize_targets_poses()

    def initialize_targets_poses(self):

        """
        lf / rf / lb / rb   :       0 is full retract       4000 is full extend
        md                  :       0 is full extend        4000 is full retract
        """

        self.targets_pose_startup = {  # startup pose
            "lf": "500",
            "rf": "500",
            "lb": "500",
            "rb": "500",
            "md": "4000"
        }
        self.targets_pose0 = {  # neutral pose (startup pose, but only arms)
            "lf": "500",
            "rf": "500",
            "lb": "500",
            "rb": "500",
        }
        self.targets_pose1 = {  # move arm to user (prepare to lift up)
            "lf": "2500",
            "rf": "2500",
            "lb": "3900",            
            "rb": "3900",
        }
        self.targets_pose2 = {  # lift up to stand
            "lf": "300",
            "rf": "300",
            "lb": "3800",
            "rb": "3800",
        }
        self.targets_pose3 = {  # bring down to sit
            "lf": "300",
            "rf": "300",
            "lb": "2000",            
            "rb": "2000",
        }
        self.targets_md_sit = {
            "md": "4000"
        }
        self.targets_md_stand = {
            "md": "300"
        }

    def button_left_cb(self, msg):
        self.buttons[0] = msg.buttons[1]

    def button_right_cb(self, msg):
        self.buttons[1] = msg.buttons[0]

    def initialize_communication(self):

        # get devices list
        found_devices_list = self.interface.get_devices_list()
        found_devices_list = [row[0] for row in found_devices_list]
        n_found_devices = len(found_devices_list)
        rospy.loginfo(f"Found {n_found_devices} devices.")

        # find found devices
        if n_found_devices == 5:
            rospy.loginfo(f"All devices are found.")

        elif n_found_devices < 5:
            rospy.logwarn(f"Not found {5 - n_found_devices} devices.")

            # find the key of not found devices
            not_found_devices_key = []
            for k, v in self.devices.items():
                if v not in found_devices_list:
                    not_found_devices_key.append(k)

            # remove that devices from dict
            for k in not_found_devices_key:
                self.devices.pop(k)

        # initialize the interface
        self.interface.add_devices(devices=self.devices)

        # get status
        for name, device in self.devices.items():
            out = self.interface.get_status(device)
            rospy.loginfo(out)

    def move_stop(self):
        out = [self.interface.set_stop(device) for name, device in self.devices.items()]
        rospy.logdebug(out)
        return out
    
    def move_targets_pose(self, targets_pose: dict):
        out = [None] * len(targets_pose)
        for i, (name, target) in enumerate(targets_pose.items()):
            device = self.devices.get(name, None)
            if device is not None:
                out[i] = self.interface.set_target(self.devices[name], target)
            elif device is None:
                out[i] = [name, "Not Found"]
        rospy.logdebug(out)
        return out

    def run(self):

        # intialization
        self.initialize_communication()  # find devices
        self.move_targets_pose(self.targets_pose_startup)  # move to home pose

        # robot operating loop
        rate = rospy.Rate(500)  # hz
        while not rospy.is_shutdown():

            # idle case: buttons are not pressed, all linear actuators are stopped
            if self.buttons == [0, 0]:
                out = self.move_stop()

            # active case: one button is pressed, middle linear actuator is moved
            elif self.buttons == [1, 0] or self.buttons == [0, 1]:
                
                    # stand-up case: left button is pressed, moved up
                    if self.buttons == [1, 0]:
                        self.move_targets_pose(self.targets_md_stand)

                    # sit-down case: right button is pressed, moved down
                    elif self.buttons == [0, 1]:
                        self.move_targets_pose(self.targets_md_sit)
                
            # active case: both buttons are pressed, arm linear actuators are moved
            elif self.buttons == [1, 1]:
                
                # pose 0 to 1: prepare to lift up
                if self.stage == 0:
                    rospy.loginfo(f"stage: {self.stage}")
                    self.move_targets_pose(self.targets_pose1)
                    rospy.sleep(3)
                    self.stage += 1

                # pose 1 to 2: lift up to stand
                elif self.stage == 1:
                    rospy.loginfo(f"stage: {self.stage}")
                    self.move_targets_pose(self.targets_pose2)
                    rospy.sleep(3)
                    self.stage += 1

                # pose 2 to 3: stand to sit
                elif self.stage == 2:
                    rospy.loginfo(f"stage: {self.stage}")
                    self.move_targets_pose(self.targets_pose3)
                    rospy.sleep(3)
                    self.stage += 1

                # pose 3 to 0: prepare to lift up
                elif self.stage == 3:
                    rospy.loginfo(f"stage: {self.stage}")
                    self.move_targets_pose(self.targets_pose0)
                    rospy.sleep(3)
                    self.stage = 0

            # control loop rate
            rate.sleep()



if __name__ == "__main__":
    robot = STSRobot()
    robot.run()