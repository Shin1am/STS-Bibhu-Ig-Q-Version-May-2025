#!/usr/bin/env python
# license removed for brevity
import rospy
from std_msgs.msg import String
from sensor_msgs.msg import Joy
import subprocess
import yaml
global lf
global lr
global rr
global rf
lf='00372080'
lr='00372251'
rr='00372242'
rf='00372247'
lin='00343198'

def jrk2cmd(*args):
    return subprocess.check_output(['jrk2cmd'] + list(args))

def initial():
	status1 = yaml.safe_load(jrk2cmd('-d',lf,'-s', '--full'))
	status2 = yaml.safe_load(jrk2cmd('-d',lr,'-s', '--full'))
	status3 = yaml.safe_load(jrk2cmd('-d',rf,'-s', '--full'))
	status4 = yaml.safe_load(jrk2cmd('-d',rr,'-s', '--full'))
	status5 = yaml.safe_load(jrk2cmd('-d',lin,'-s', '--full'))
	rospy.sleep(2)
	jrk2cmd('-d',lf,'--target', '500')
	jrk2cmd('-d',rf,'--target', '500')
	jrk2cmd('-d',lr,'--target', '500')
	jrk2cmd('-d',rr,'--target', '500')
	jrk2cmd('-d',lin,'--target', '4000')

def callback1(data):
    global is_left
    if data.buttons[1]==1:
    	is_left=1
    else:
    	is_left=0

def callback2(data):
    global is_right
    if data.buttons[0]==1:
    	is_right=1
    else:
    	is_right=0

def talker():
    global is_left
    global is_right
    global is_both
    global count
    initial()
    is_left=0
    is_right=0
    is_both=0
    count=0
    rospy.init_node('listed', anonymous=True)
    rospy.Subscriber('/j0', Joy, callback1)
    rospy.Subscriber('/j1', Joy, callback2)
    rate = rospy.Rate(100) # 10hz
    while not rospy.is_shutdown():
    	if is_left==1 and is_right==1:
    		count=count+1
    		if count==1:
    			jrk2cmd('-d',lf,'--target', '2500')
    			jrk2cmd('-d',rf,'--target', '2500')
    			jrk2cmd('-d',lr,'--target', '3900')
    			jrk2cmd('-d',rr,'--target', '3900')
    			rospy.sleep(3)
    		elif count==2:
    			jrk2cmd('-d',lf,'--target', '300')
    			jrk2cmd('-d',rf,'--target', '300')
    			jrk2cmd('-d',lr,'--target', '3800')
    			jrk2cmd('-d',rr,'--target', '3800')
    			rospy.sleep(3)
    		elif count==3:
    			jrk2cmd('-d',lf,'--target', '300')
    			jrk2cmd('-d',rf,'--target', '300')
    			jrk2cmd('-d',lr,'--target', '2000')
    			jrk2cmd('-d',rr,'--target', '2000')
    		elif count==4:
    			count=1
    	elif is_left==1 and is_right==0:
    		jrk2cmd('-d',lin,'--target', '4000')
    	elif is_left==0 and is_right==1:
    		jrk2cmd('-d',lin,'--target', '200')
    	elif is_left==0 and is_right==0:
    		jrk2cmd('-d',lin,'--stop')
    	rate.sleep()

if __name__ == '__main__':
    try:
        talker()
    except rospy.ROSInterruptException:
        pass
