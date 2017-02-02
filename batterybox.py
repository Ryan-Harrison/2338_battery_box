#!/usr/bin/env python
import tkinter as tk
import serial
from functools import partial
import RPi.GPIO as GPIO
import threading
import queue
from enum import Enum

GPIO.setmode(GPIO.BCM)
GPIO.setup(24,GPIO.IN)	#Bank 0, charging
GPIO.setup(25,GPIO.IN)	#Bank 0, done
GPIO.setup(27,GPIO.IN)	#Bank 1, charging
GPIO.setup(22,GPIO.IN)	#Bank 1, done
GPIO.setup(18,GPIO.IN)	#Bank 2, charging
GPIO.setup(23,GPIO.IN)	#Bank 2, done

left_button = 0			#Corresponds between the position of the button on the GUI and the battery in the bank
left_complete = False	#True if the left bank has charged all batteries so far
middle_button = 4
middle_complete = False	#True if the middle bank has charged all batteries so far
right_button = 8
right_complete = False	#True if the right bank has charged all batteries so far

q = queue.Queue()		#Used to interrupt timer in case the GUI is interacted with during the run_timer

class Bank_State(Enum):	#States of checking banks
	NONE = 0
	LEFT = 1
	MIDDLE = 2
	RIGHT = 3
	
class Battery_State(Enum):	#States of battery charging
	NONE = 0
	CHARGING = 1
	CHARGED = 2

def run_timer():
	global left_button, left_complete, middle_button, middle_complete, right_button, right_complete
	state = Bank_State.LEFT	#Start at the left bank
	left_bat = Battery_State.NONE	#Assume no batteries exist until you've seen them
	middle_bat = Battery_State.NONE
	right_bat= Battery_State.NONE
	cycle = True			#Tells if the timer completed at each state
	
	while(True):
		while(not (left_complete and middle_complete and right_complete)):	#Before the bottom of the banks is reached
			cycle = True
			
			for i in range(15):	#Wait for 15 seconds
				try:
					q.get(timeout=1)	#Countdown one second at a time, executes rest of code if something is added to queue
					cycle = False		#If interrupted, change behavior
					break				#Stop timer
				except queue.Empty:
					pass	#Do nothing
					
			if cycle:	#If the timer completed
				if state == Bank_State.LEFT:	#Left bank
					if GPIO.input(24) and not left_bat == Battery_State.CHARGING:	#If found charging, but wasn't already
						gpio_callback(24)
						left_bat = Battery_State.CHARGING
						
					elif GPIO.input(25) and not left_complete:	#If fully charged, but isn't the final battery in the bank
						gpio_callback(25)
						left_bat = Battery_State.CHARGED
						
					elif not (GPIO.input(24) or GPIO.input(25)):#If neither LED turns on, battery isn't there
						gui.button_missing(left_button)
						left_bat = Battery_State.NONE
						
					state = Bank_State.MIDDLE	#Move to next bank
					
				elif state == Bank_State.MIDDLE:
					if GPIO.input(27) and not middle_bat == Battery_State.CHARGING:
						gpio_callback(27)
						middle_bat = Battery_State.CHARGING
						
					elif GPIO.input(22) and not middle_complete:
						gpio_callback(22)
						middle_bat = Battery_State.CHARGED
						
					elif not (GPIO.input(27) or GPIO.input(22))
						gui.button_missing(middle_button)
						middle_bat = Battery_State.NONE
						
					state = Bank_State.RIGHT
					
				elif state == Bank_State.RIGHT:
					if GPIO.input(18) and not right_bat == Battery_State.CHARGING:
						gpio_callback(18)
						right_bat = Battery_State.CHARGING
						
					elif GPIO.input(23) and not right_complete:
						gpio_callback(23)
						right_bat = Battery_State.CHARGED
						
					elif not (GPIO.input(18) or GPIO.input(23)):
						gui.button_missing(right_button)
						right_bat = Battery_State.NONE
						
					state = Bank_State.LEFT
					
			else:		#If timer was interrupted, reset
				state = Bank_State.LEFT
				left_bat = Battery_State.NONE
				middle_bat = Battery_State.NONE
				right_bat = Battery_State.NONE
				
		while(left_complete and middle_complete and right_complete):	#When the bottom of the banks is reached
			cycle = True
			
			for i in range(600):	#Wait for 10 minutes
				try:
					q.get(timeout=1)
					cycle = False
					break
				except queue.Empty:
					pass	#Do nothing
					
			state = Bank_State.LEFT	#Reset
			left_complete = False
			middle_complete = False
			right_complete = False
			if cycle:	#If no button was pushed, start again at the top
				left_button = 0
				middle_button = 4
				right_button = 8

class USB:	#Handles sending signals through usb to the charger switch
	ser = serial.Serial("/dev/ttyUSB0",9600,8,"N",1,timeout=5)	#usb location,baud rate, data bits, no parity, stop bit
	
	def read(self):
		return this.ser.readline()

	def switch_on(self,button):
		output = ""
		relay = button+1	#USB relay starts at 1 instead of 0
		
		if relay < 10:
			output = "0" + str(relay) + "+//"	#single digit relays require a 0 in front
			
		else:
			output = str(relay) + "+//"
			
		self.ser.write(output.encode('utf-8'))
		self.ser.flush()
		
	def switch_off(self,button):
		output = ""
		relay = button+1
		
		if relay < 10:
			output = "0" + str(relay) + "-//"
			
		else:
			output = str(relay) + "-//"
			
		self.ser.write(output.encode('utf-8'))
		self.ser.flush()
		
usb = USB()	#Handles sending signals through usb to the charger switch
'''
def button_click(button):	#Turn button purple and switch to charging that bank
	global left_button, left_complete, middle_button, middle_complete, right_button, right_complete
	gui.button_list[button]["bg"] = "purple"
	if button < 4:	#Left buttons
		usb.switch_off(left_button)
		left_button = button
		left_complete = False
	elif button > 3 and button < 8:	#Middle buttons
		usb.switch_off(middle_button)
		middle_button = button
		middle_complete = False
	else:	#Right buttons
		usb.switch_off(right_button)
		right_button = button
		right_complete = False
	usb.switch_on(button)
	q.put(None)
'''	
class GUI(tk.Frame):
	def __init__(self,master=None):
		super().__init__(master)
		self.grid()				#Makes widget visible
		self.button_list = []	#Stores all 12 buttons for easy reference
		self.create_widgets()
		
	def create_widgets(self):
		self.header = tk.Label(self,text="2338 Battery Charger")
		self.header.grid(column=1)
		
		self.left = tk.Frame(self)		#Left battery bank
		self.left.header = tk.Frame(self.left)
		self.left.header.charging = tk.Label(self.left.header,text="C0 Charging")
		self.left.header.charged = tk.Label(self.left.header,text="C0 Charged")
		self.left.b0 = tk.Button(self.left,text="C00",command=partial(self.button_click,0))	#Battery Left 1
		self.button_list.append(self.left.b0)
		self.left.b1 = tk.Button(self.left,text="C01",command=partial(self.button_click,1))	#Battery Left 2
		self.button_list.append(self.left.b1)
		self.left.b2 = tk.Button(self.left,text="C02",command=partial(self.button_click,2))	#Battery Left 3
		self.button_list.append(self.left.b2)
		self.left.b3 = tk.Button(self.left,text="C03",command=partial(self.button_click,3))	#Battery Left 4
		self.button_list.append(self.left.b3)
		self.left.grid()
		self.left.header.grid()
		self.left.header.charging.grid()
		self.left.header.charged.grid(column=1, row=0)
		self.left.b0.grid()
		self.left.b1.grid()
		self.left.b2.grid()
		self.left.b3.grid()
		
		self.middle = tk.Frame(self)	#Middle battery bank
		self.middle.header = tk.Frame(self.middle)
		self.middle.header.charging = tk.Label(self.middle.header,text="C1 Charging")
		self.middle.header.charged = tk.Label(self.middle.header,text="C1 Charged")
		self.middle.b0 = tk.Button(self.middle,text="C10",command=partial(self.button_click,4))	#Battery Middle 1
		self.button_list.append(self.middle.b0)
		self.middle.b1 = tk.Button(self.middle,text="C11",command=partial(self.button_click,5))	#Battery Middle 2
		self.button_list.append(self.middle.b1)
		self.middle.b2 = tk.Button(self.middle,text="C12",command=partial(self.button_click,6))	#Battery Middle 3
		self.button_list.append(self.middle.b2)
		self.middle.b3 = tk.Button(self.middle,text="C13",command=partial(self.button_click,7))	#Battery Middle 4
		self.button_list.append(self.middle.b3)
		self.middle.grid(column=1, row=1)
		self.middle.header.grid()
		self.middle.header.charging.grid()
		self.middle.header.charged.grid(column=1, row=0)
		self.middle.b0.grid()
		self.middle.b1.grid()
		self.middle.b2.grid()
		self.middle.b3.grid()
		
		self.right = tk.Frame(self)		#Right battery bank
		self.right.header = tk.Frame(self.right)
		self.right.header.charging = tk.Label(self.right.header,text="C2 Charging")
		self.right.header.charged = tk.Label(self.right.header,text="C2 Charged")
		self.right.b0 = tk.Button(self.right,text="C20",command=partial(self.button_click,8))	#Battery Right 1
		self.button_list.append(self.right.b0)
		self.right.b1 = tk.Button(self.right,text="C21",command=partial(self.button_click,9))	#Battery Right 2
		self.button_list.append(self.right.b1)
		self.right.b2 = tk.Button(self.right,text="C22",command=partial(self.button_click,10))	#Battery Right 3
		self.button_list.append(self.right.b2)
		self.right.b3 = tk.Button(self.right,text="C23",command=partial(self.button_click,11))	#Battery Right 4
		self.button_list.append(self.right.b3)
		self.right.grid(column=2, row=1)
		self.right.header.grid()
		self.right.header.charging.grid()
		self.right.header.charged.grid(column=1, row=0)
		self.right.b0.grid()
		self.right.b1.grid()
		self.right.b2.grid()
		self.right.b3.grid()
		
	def button_click(self,button):	#Turn button purple and switch to charging that bank
		global left_button, left_complete, middle_button, middle_complete, right_button, right_complete
		self.button_list[button]["bg"] = "purple"
		
		if button < 4:	#Left buttons
			usb.switch_off(left_button)
			left_button = button
			left_complete = False
			
		elif button > 3 and button < 8:	#Middle buttons
			usb.switch_off(middle_button)
			middle_button = button
			middle_complete = False
			
		else:	#Right buttons
			usb.switch_off(right_button)
			right_button = button
			right_complete = False
			
		usb.switch_on(button)
		q.put(None)
		
	def button_charging(self,button=0):
		self.button_list[button]["bg"] = "yellow"
		
	def button_switch(self,button=0):
		usb.switch_off(button)
		
		if button < 3:
			usb.switch_on(button+1)
			
		elif (button > 3 and button < 7):
			usb.switch_on(button+1)
			
		elif (button > 7 and button < 11):
			usb.switch_on(button+1)
		
	def button_done(self,button=0):
		self.button_list[button]["bg"] = "green"
		self.button_switch(button)
			
	def button_missing(self,button=0):
		self.button_list[button]["bg"] = "gray"
		self.button_switch(button)
			
root = tk.Tk()
gui = GUI(master=root)
gui.master.title('2338 Battery Charger')
	
def gpio_callback(channel):	#Called whenever an LED lights up, parses which LED lit and responds accordingly
	global left_button, left_complete, middle_button, middle_complete, right_button, right_complete
	
	if channel == 24:	#Bank 0 (left bank), charging
		gui.button_charging(button=left_button)
		
	elif channel == 25:	#Bank 0 (left bank), done
		gui.button_done(button=left_button)
		
		if left_button < 3:
			left_button += 1	#Increment button/battery position
			
		else:
			left_complete = True
			
	elif channel == 27:	#Bank 1 (middle bank), charging
		gui.button_charging(button=middle_button)
		
	elif channel == 22:	#Bank 1 (middle bank), done
		gui.button_done(button=middle_button)
		
		if middle_button < 7:
			middle_button += 1
			
		else:
			middle_complete = True
			
	elif channel == 18:	#Bank 2 (right bank), charging
		gui.button_charging(button=right_button)
		
	elif channel == 23:	#Bank 2 (right bank), done
		gui.button_done(button=right_button)
		
		if right_button < 11:
			right_button += 1
			
		else:
			right_complete = True
			
def run():	
	usb.switch_off(0)	#Turn off all banks for hard reset
	usb.switch_off(1)
	usb.switch_off(2)
	usb.switch_off(3)
	usb.switch_off(4)
	usb.switch_off(5)
	usb.switch_off(6)
	usb.switch_off(7)
	usb.switch_off(8)
	usb.switch_off(9)
	usb.switch_off(10)
	usb.switch_off(11)
	
	usb.switch_on(left_button)	#Start from the top
	usb.switch_on(middle_button)
	usb.switch_on(right_button)
	
	th = threading.Thread(target=run_timer)
	th.start()
	
	gui.mainloop()

run()
