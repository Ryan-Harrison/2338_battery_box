#!/usr/bin/env python
import tkinter as tk
import serial
from functools import partial
import RPi.GPIO as GPIO
import threading
import queue
#import time


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

qw = queue.Queue()		#Used to interrupt timer in case the GUI is interacted with during reset_wait
ql = queue.Queue()		#Used to interrupt timer in case the GUI is interacted with during 
qm = queue.Queue()		#Used to interrupt timer in case the GUI is interacted with during 
qr = queue.Queue()		#Used to interrupt timer in case the GUI is interacted with during 

def reset_wait():		#Runs in another thread after all banks are finished, resets after timeout
	global left_button, left_complete, middle_button, middle_complete, right_button, right_complete
	reset = True		#If timeout does not get interrupted, start from the beginning
	for i in range(600):#Wait for 10 minutes
		try:
			qw.get(timeout=1)
			reset = False
			break
		except queue.Empty:
			pass	#Do nothing
	if reset:
		left_button = 0	#Reset and start over	
		left_complete = False	
		middle_button = 4		
		middle_complete = False	
		right_button = 8
		right_complete = False
		
def left_wait():		#Runs in another thread after transitioning to the next battery, skips to another battery if no battery is found, left bank
	skip = True			#If timout does not get interrupted, skip to next battery
	for i in range(15):	#Wait for 15 seconds
		try:
			ql.get(timeout=1)
			skip = False
			break
		except queue.Empty:
			pass	#Do nothing
	if skip:
		gui.button_missing(left_button)
		
def middle_wait():		#Runs in another thread after transitioning to the next battery, skips to another battery if no battery is found, middle bank
	skip = True			#If timout does not get interrupted, skip to next battery
	for i in range(15):	#Wait for 15 seconds
		try:
			qm.get(timeout=1)
			skip = False
			break
		except queue.Empty:
			pass	#Do nothing
	if skip:
		gui.button_missing(middle_button)
		
def right_wait():		#Runs in another thread after transitioning to the next battery, skips to another battery if no battery is found, right bank
	skip = True			#If timout does not get interrupted, skip to next battery
	for i in range(15):	#Wait for 15 seconds
		try:
			qr.get(timeout=1)
			skip = False
			break
		except queue.Empty:
			pass	#Do nothing
	if skip:
		gui.button_missing(right_button)

class USB:	#Handles sending signals through usb to the charger switch
	#ser = serial.serial_for_url("/dev/ttyUSB0")
	ser = serial.Serial("/dev/ttyUSB0",9600,8,"N",1,timeout=5)	#usb location,baud rate, data bits, no parity, stop bit
	'''
	def switch_board(self,arg):
		switcher = {
			1: "01",
			2: "02",
			3: "03",
			4: "04",
			5: "05",
			6: "06",
			7: "07",
			8: "08",
			9: "09",
			10: "10",
			11: "11",
			12: "12"
		}
		return switcher.get(arg, "nothing")
	'''
	
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

def button_click(button):	#Turn button purple and switch to charging that bank
	global left_button, left_complete, middle_button, middle_complete, right_button, right_complete
	if left_complete and middle_complete and right_complete:
		qw.put(None)	#Prematurely stops countdown after all batteries are charged
	gui.button_list[button]["bg"] = "purple"
	if button < 4:	#Left buttons
		#gui.button_list[left_button]["bg"] = "yellow"
		usb.switch_off(left_button)
		left_button = button
		usb.switch_on(button)
		left_complete = False
	elif button > 3 and button < 8:	#Middle buttons
		#gui.button_list[middle_button]["bg"] = "yellow"
		usb.switch_off(middle_button)
		middle_button = button
		usb.switch_on(button)
		middle_complete = False
	else:	#Right buttons
		#gui.button_list[right_button]["bg"] = "yellow"
		usb.switch_off(right_button)
		right_button = button
		usb.switch_on(button)
		right_complete = False
	
class GUI(tk.Frame):
	def __init__(self,master=None):
		super().__init__(master)
		self.grid()				#Makes widget visible
		self.button_list = []	#Stores all 12 buttons for easy reference
		'''
		self.left_pos = 12		#Indicates current charging bank in each column
		self.middle_pos = 12	#Starts at 12 to indicate that no bank is selected yet
		self.right_pos = 12
		'''
		self.create_widgets()
		
	def create_widgets(self):
		self.header = tk.Label(self,text="2338 Battery Charger")
		self.header.grid(column=1)
		
		self.left = tk.Frame(self)		#Left battery bank
		self.left.header = tk.Frame(self.left)
		self.left.header.charging = tk.Label(self.left.header,text="C0 Charging")
		self.left.header.charged = tk.Label(self.left.header,text="C0 Charged")
		self.left.b0 = tk.Button(self.left,text="C00",command=partial(button_click,0))	#Battery Left 1
		self.button_list.append(self.left.b0)
		self.left.b1 = tk.Button(self.left,text="C01",command=partial(button_click,1))	#Battery Left 2
		self.button_list.append(self.left.b1)
		self.left.b2 = tk.Button(self.left,text="C02",command=partial(button_click,2))	#Battery Left 3
		self.button_list.append(self.left.b2)
		self.left.b3 = tk.Button(self.left,text="C03",command=partial(button_click,3))	#Battery Left 4
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
		self.middle.b0 = tk.Button(self.middle,text="C10",command=partial(button_click,4))	#Battery Middle 1
		self.button_list.append(self.middle.b0)
		self.middle.b1 = tk.Button(self.middle,text="C11",command=partial(button_click,5))	#Battery Middle 2
		self.button_list.append(self.middle.b1)
		self.middle.b2 = tk.Button(self.middle,text="C12",command=partial(button_click,6))	#Battery Middle 3
		self.button_list.append(self.middle.b2)
		self.middle.b3 = tk.Button(self.middle,text="C13",command=partial(button_click,7))	#Battery Middle 4
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
		self.right.b0 = tk.Button(self.right,text="C20",command=partial(button_click,8))	#Battery Right 1
		self.button_list.append(self.right.b0)
		self.right.b1 = tk.Button(self.right,text="C21",command=partial(button_click,9))	#Battery Right 2
		self.button_list.append(self.right.b1)
		self.right.b2 = tk.Button(self.right,text="C22",command=partial(button_click,10))	#Battery Right 3
		self.button_list.append(self.right.b2)
		self.right.b3 = tk.Button(self.right,text="C23",command=partial(button_click,11))	#Battery Right 4
		self.button_list.append(self.right.b3)
		self.right.grid(column=2, row=1)
		self.right.header.grid()
		self.right.header.charging.grid()
		self.right.header.charged.grid(column=1, row=0)
		self.right.b0.grid()
		self.right.b1.grid()
		self.right.b2.grid()
		self.right.b3.grid()
		
		'''
		self.hi_there["text"] = "Hello World\n(click me)"
		self.hi_there["command"] = self.say_hi
		self.hi_there.grid(padx=100, pady=50)
		'''
	
	#def button_click(self,button):	#Turn button purple and switch to charging that bank
		
	def button_charging(self,button=0):
		self.button_list[button]["bg"] = "yellow"
		
	def button_switch(self,button=0):
		usb.switch_off(button)
		if button < 3:
			usb.switch_on(button+1)
			th = threading.Thread(target=left_wait)
			th.start()
		elif (button > 3 and button < 7):
			usb.switch_on(button+1)
			th = threading.Thread(target=middle_wait)
			th.start()
		elif (button > 7 and button < 11):
			usb.switch_on(button+1)
			th = threading.Thread(target=right_wait)
			th.start()
			
		if left_complete and middle_complete and right_complete:
			th = threading.Thread(target=reset_wait)
			th.start()
		
	def button_done(self,button=0):
		self.button_list[button]["bg"] = "green"
		self.button_switch(button)
			
	def button_missing(self,button=0):
		self.button_list[button["bg"] = "gray"
		self.button_switch(button)
			
root = tk.Tk()
gui = GUI(master=root)
gui.master.title('2338 Battery Charger')
	
def gpio_callback(channel):	#Called whenever an LED lights up, parses which LED lit and responds accordingly
	global left_button, left_complete, middle_button, middle_complete, right_button, right_complete
	if channel == 24:	#Bank 0 (left bank), charging
		gui.button_charging(button=left_button)
		ql.put(None)	#Interrupts waiting for left battery, shows that there is indeed a battery present
	elif channel == 25:	#Bank 0 (left bank), done
		gui.button_done(button=left_button)
		if left_button < 3:
			left_button += 1	#Increment button/battery position
		else:
			left_complete = True
	elif channel == 27:	#Bank 1 (middle bank), charging
		gui.button_charging(button=middle_button)
		qm.put(None)	#Interrupts waiting for middle battery, shows that there is indeed a battery present
	elif channel == 22:	#Bank 1 (middle bank), done
		gui.button_done(button=middle_button)
		if middle_button < 7:
			middle_button += 1
		else:
			middle_complete = True
	elif channel == 18:	#Bank 2 (right bank), charging
		gui.button_charging(button=right_button)
		qr.put(None)	#Interrupts waiting for right battery, shows that there is indeed a battery present
	elif channel == 23:	#Bank 2 (right bank), done
		gui.button_done(button=right_button)
		if right_button < 11:
			right_button += 1
		else:
			right_complete = True
			
def run():
	GPIO.add_event_detect(24, GPIO.RISING) #Bank 0, charging
	GPIO.add_event_callback(24, partial(gpio_callback,24))
	GPIO.add_event_detect(25, GPIO.RISING) #Bank 0, done
	GPIO.add_event_callback(25, partial(gpio_callback,25))
	GPIO.add_event_detect(27, GPIO.RISING) #Bank 1, charging
	GPIO.add_event_callback(27, partial(gpio_callback,27))
	GPIO.add_event_detect(22, GPIO.RISING) #Bank 1, done
	GPIO.add_event_callback(22, partial(gpio_callback,22))
	GPIO.add_event_detect(18, GPIO.RISING) #Bank 2, charging
	GPIO.add_event_callback(18, partial(gpio_callback,18))
	GPIO.add_event_detect(23, GPIO.RISING) #Bank 2, done
	GPIO.add_event_callback(23, partial(gpio_callback,23))
	
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
	
	gui.mainloop()

run()
