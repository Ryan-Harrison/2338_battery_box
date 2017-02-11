import tkinter as tk
import serial
from functools import partial
import RPi.GPIO as GPIO
import threading
import queue
from enum import Enum
import time

class Bank(Enum):						#States of checking banks
	NONE = 0
	LEFT = 1
	MIDDLE = 2
	RIGHT = 3
	
class Battery_State(Enum):				#States of battery charging
	NONE = 0
	CHARGING = 1
	CHARGED = 2
	
class USB_Command(on_in,button_in):		#on: boolean, determins if the relay is turning on or off; button: int, location of relay
	on = on_in
	button = button_in

class Main:
	left_charging = 24					#GPIO address, change where necessary
	left_charged = 25
	middle_charging = 27
	middle_charged = 22
	right_charging = 18
	right_charged = 23
	
	left_beginning = 0					#Corresponds between the position of the button on the GUI and the battery in the bank
	middle_beginning = 4
	right_beginning = 8

	left_button = left_beginning		#Start at the beginning
	middle_button = middle_beginning
	right_button = right_beginning
	
	left_complete = False				#True if the left bank has charged all batteries so far
	middle_complete = False
	right_complete = False

	GPIO.setmode(GPIO.BCM)
	GPIO.setup(left_charging,GPIO.IN)	#Bank 0, charging
	GPIO.setup(left_charged,GPIO.IN)	#Bank 0, done
	GPIO.setup(middle_charging,GPIO.IN)	#Bank 1, charging
	GPIO.setup(middle_charged,GPIO.IN)	#Bank 1, done
	GPIO.setup(right_charging,GPIO.IN)	#Bank 2, charging
	GPIO.setup(right_charged,GPIO.IN)	#Bank 2, done

	q = queue.Queue()					#Used to interrupt timer in case the GUI is interacted with during the run_timer
	usbq = queue.Queue()				#Add USB add commands for staggered execution
	
	stop = False						#Stops loops
	
	def run_timer(self):
		state = Bank.LEFT				#Start at the left bank
		left_bat = Battery_State.NONE	#Assume no batteries exist until you've seen them
		middle_bat = Battery_State.NONE
		right_bat= Battery_State.NONE
		cycle = True					#Tells if the timer completed at each state
		
		while(not self.stop):
			while(not ((self.left_complete and self.middle_complete and self.right_complete) or self.stop)):	#Before the bottom of the banks is reached
				cycle = True
				for i in range(10):		#Wait for 10 seconds
					if not self.stop:
						try:
							self.q.get(timeout=1)	#Countdown one second at a time, executes rest of code if something is added to queue
							cycle = False	#If interrupted, change behavior
							break		#Stop timer
						except queue.Empty:
							pass		#Do nothing
					
					else:
						break
						
				if cycle and not self.stop:	#If the timer completed
					if state == Bank.LEFT:	#Left bank
						if GPIO.input(self.left_charging) and not left_bat == Battery_State.CHARGING:	#If found charging, but wasn't already
							self.gpio_callback(self.left_charging)
							left_bat = Battery_State.CHARGING
							
						elif GPIO.input(self.left_charged) and not self.left_complete:	#If fully charged, but isn't the final battery in the bank
							self.gpio_callback(self.left_charged)
							left_bat = Battery_State.CHARGED
							
						elif not (GPIO.input(self.left_charging) or GPIO.input(self.left_charged)):#If neither LED turns on, battery isn't there
							gui.button_missing(self.left_button)
							left_bat = Battery_State.NONE
							gui.bank_nothing(state)
							self.increment_button(Bank.LEFT)
							
						state = Bank.MIDDLE	#Move to next bank
						
					elif state == Bank.MIDDLE:
						if GPIO.input(self.middle_charging) and not middle_bat == Battery_State.CHARGING:
							self.gpio_callback(self.middle_charging)
							middle_bat = Battery_State.CHARGING
							
						elif GPIO.input(self.middle_charged) and not self.middle_complete:
							self.gpio_callback(self.middle_charged)
							middle_bat = Battery_State.CHARGED
							
						elif not (GPIO.input(self.middle_charging) or GPIO.input(self.middle_charged)):
							gui.button_missing(self.middle_button)
							middle_bat = Battery_State.NONE
							gui.bank_nothing(state)
							self.increment_button(Bank.MIDDLE)
							
						state = Bank.RIGHT
						
					elif state == Bank.RIGHT:
						if GPIO.input(self.right_charging) and not right_bat == Battery_State.CHARGING:
							self.gpio_callback(self.right_charging)
							right_bat = Battery_State.CHARGING
							
						elif GPIO.input(self.right_charged) and not self.right_complete:
							self.gpio_callback(self.right_charged)
							right_bat = Battery_State.CHARGED
							
						elif not (GPIO.input(self.right_charging) or GPIO.input(self.right_charged)):
							gui.button_missing(self.right_button)
							right_bat = Battery_State.NONE
							gui.bank_nothing(state)
							self.increment_button(Bank.RIGHT)
							
						state = Bank.LEFT
						
				elif not (cycle or self.stop):	#If timer was interrupted, reset
					state = Bank.LEFT
					left_bat = Battery_State.NONE
					middle_bat = Battery_State.NONE
					right_bat = Battery_State.NONE
					
			while(self.left_complete and self.middle_complete and self.right_complete and not self.stop):#When the bottom of the banks is reached
				cycle = True
				
				#for i in range(600):	#Wait for 10 minutes
				for i in range(15):		#Only for testing
					if not self.stop:
						try:
							self.q.get(timeout=1)
							cycle = False
							break
						except queue.Empty:
							pass		#Do nothing
							
					else:
						break
				if not self.stop:	
					state = Bank.LEFT	#Reset
					self.reset_complete()
					if cycle:			#If no button was pushed, start again at the top
						self.reset_buttons()
					usb.reset()

	def usb_timer(self):				#Staggers and calls commands to the usb relay so as not to overload it
		next_item = None				#Holds relay position and command to turn on or off
		while(not self.stop):
			try:
				next_item = self.usbq.get(timeout=1)
				if next_item.on:
					usb.switch_on(next_item.button)
				else:
					usb.switch_off(next_item.button)
				time.sleep(1)			#Only do one command at a time
			except queue.Empty:
				pass					#Do nothing
				
	def usbq_add(self,on,button):
		command = USB_Command(on,button)
		usbq.add(command)

	def gpio_callback(self,channel):	#Called whenever an LED lights up, parses which LED lit and responds accordingly		
		if channel == self.left_charging:		#Bank 0 (left bank), charging
			gui.button_charging(button=self.left_button)
			gui.bank_charging(Bank.LEFT)
			
		elif channel == self.left_charged:		#Bank 0 (left bank), done
			gui.button_done(button=self.left_button)
			gui.bank_charged(Bank.LEFT)
			self.increment_button(Bank.LEFT)	#Increment button/battery position
				
		elif channel == self.middle_charging:	#Bank 1 (middle bank), charging
			gui.button_charging(button=self.middle_button)
			gui.bank_charging(Bank.MIDDLE)
			
		elif channel == self.middle_charged:	#Bank 1 (middle bank), done
			gui.button_done(button=self.middle_button)
			gui.bank_charged(Bank.MIDDLE)
			self.increment_button(Bank.MIDDLE)
				
		elif channel == self.right_charging:	#Bank 2 (right bank), charging
			gui.button_charging(button=self.right_button)
			gui.bank_charging(Bank.RIGHT)
			
		elif channel == self.right_charged:		#Bank 2 (right bank), done
			gui.button_done(button=self.right_button)
			gui.bank_charged(Bank.RIGHT)
			self.increment_button(Bank.RIGHT)
	
	def reset_complete(self):
		self.left_complete = False
		self.middle_complete = False
		self.right_complete = False
		
	def reset_buttons(self):
		self.left_button = self.left_beginning
		self.middle_button = self.middle_beginning
		self.right_button = self.right_beginning	
	
	def increment_button(self,bank):
		if bank == Bank.LEFT:
			if self.left_button < 3:
				self.usbq_add(False,self.left_button)
				self.left_button += 1
				self.usbq_add(True,self.left_button)
			
			else:
				self.left_complete = True
			
		elif bank == Bank.MIDDLE:
			if self.middle_button < 7:
				self.usbq_add(False,self.middle_button)
				self.middle_button += 1
				self.usbq_add(True,self.middle_button)
				
			else:
				self.middle_complete = True
			
		elif bank == Bank.RIGHT:
			if self.right_button < 11:
				self.usbq_add(False,self.right_button)
				self.right_button += 1
				self.usbq_add(True,self.right_button)
				
			else:
				self.right_complete = True
	
	def set_button(self,bank,button):
		if bank == Bank.LEFT:
			self.usbq_add(False,self.left_button)
			self.left_button = button
			self.left_complete = False
			
		elif bank == Bank.MIDDLE:
			self.usbq_add(False,self.middle_button)
			self.middle_button = button
			self.middle_complete = False
			
		elif bank == Bank.RIGHT:
			self.usbq_add(False,self.right_button)
			self.right_button = button
			self.right_complete = False
		
		self.usbq_add(True,button)
		self.q.put(None)
		
	def on_closing(self):
		self.stop = True
	
	def run(self):
		usb.reset()
		
		th1 = threading.Thread(target=self.run_timer)
		th2 = threading.Thread(target=self.usb_timer)
		th1.start()
		th2.start()
		
		gui.mainloop()

class USB:								#Handles sending signals through usb to the charger switch
	ser = serial.Serial('/dev/ttyUSB0',9600,8,'N',1,timeout=5)	#usb location,baud rate, data bits, no parity, stop bit
	
	def read(self):
		return this.ser.readline()

	def switch_on(self,button):
		output = ''
		relay = button+1				#USB relay starts at 1 instead of 0
		if relay < 10:
			output = '0' + str(relay) + '+//'	#single digit relays require a 0 in front
			
		else:
			output = str(relay) + '+//'
			
		self.ser.write(output.encode('utf-8'))
		self.ser.flush()
		
	def switch_off(self,button):
		output = ''
		relay = button+1
		if relay < 10:
			output = '0' + str(relay) + '-//'
			
		else:
			output = str(relay) + '-//'
			
		self.ser.write(output.encode('utf-8'))
		self.ser.flush()
		
	def switch_all_off(self):
		output = 'off//'
		self.ser.write(output.encode('utf-8'))
		self.ser.flush()
		
	def reset(self):
		self.switch_all_off()			#Turn off all batteries
		main.usbq_add(True,main.left_button)
		main.usbq_add(True,main.middle_button)
		main.usbq_add(True,main.right_button)

class GUI(tk.Frame):
	def __init__(self,master=None):
		super().__init__(master)
		self.grid()						#Makes widget visible
		self.button_list = []			#Stores all 12 buttons for easy reference
		self.create_widgets()
		
	def create_widgets(self):
		self.header = tk.Label(self,text='2338 Battery Charger')
		self.header.grid(column=1)
		
		self.left = tk.Frame(self)		#Left battery bank
		self.left.header = tk.Frame(self.left)
		self.left.header.charging = tk.Label(self.left.header,text='C0 Charging')
		self.left.header.charged = tk.Label(self.left.header,text='C0 Charged')
		self.left.b0 = tk.Button(self.left,text='C00',command=partial(self.button_click,0))	#Battery Left 1
		self.button_list.append(self.left.b0)
		self.left.b1 = tk.Button(self.left,text='C01',command=partial(self.button_click,1))	#Battery Left 2
		self.button_list.append(self.left.b1)
		self.left.b2 = tk.Button(self.left,text='C02',command=partial(self.button_click,2))	#Battery Left 3
		self.button_list.append(self.left.b2)
		self.left.b3 = tk.Button(self.left,text='C03',command=partial(self.button_click,3))	#Battery Left 4
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
		self.middle.header.charging = tk.Label(self.middle.header,text='C1 Charging')
		self.middle.header.charged = tk.Label(self.middle.header,text='C1 Charged')
		self.middle.b0 = tk.Button(self.middle,text='C10',command=partial(self.button_click,4))	#Battery Middle 1
		self.button_list.append(self.middle.b0)
		self.middle.b1 = tk.Button(self.middle,text='C11',command=partial(self.button_click,5))	#Battery Middle 2
		self.button_list.append(self.middle.b1)
		self.middle.b2 = tk.Button(self.middle,text='C12',command=partial(self.button_click,6))	#Battery Middle 3
		self.button_list.append(self.middle.b2)
		self.middle.b3 = tk.Button(self.middle,text='C13',command=partial(self.button_click,7))	#Battery Middle 4
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
		self.right.header.charging = tk.Label(self.right.header,text='C2 Charging')
		self.right.header.charged = tk.Label(self.right.header,text='C2 Charged')
		self.right.b0 = tk.Button(self.right,text='C20',command=partial(self.button_click,8))	#Battery Right 1
		self.button_list.append(self.right.b0)
		self.right.b1 = tk.Button(self.right,text='C21',command=partial(self.button_click,9))	#Battery Right 2
		self.button_list.append(self.right.b1)
		self.right.b2 = tk.Button(self.right,text='C22',command=partial(self.button_click,10))	#Battery Right 3
		self.button_list.append(self.right.b2)
		self.right.b3 = tk.Button(self.right,text='C23',command=partial(self.button_click,11))	#Battery Right 4
		self.button_list.append(self.right.b3)
		self.right.grid(column=2, row=1)
		self.right.header.grid()
		self.right.header.charging.grid()
		self.right.header.charged.grid(column=1, row=0)
		self.right.b0.grid()
		self.right.b1.grid()
		self.right.b2.grid()
		self.right.b3.grid()
		
	def button_click(self,button):		#Turn button purple and switch to charging that bank
		self.button_list[button]['bg'] = 'purple'
		if button < 4:	#Left buttons
			main.set_button(Bank.LEFT,button)
			
		elif button > 3 and button < 8:	#Middle buttons
			main.set_button(Bank.MIDDLE,button)
			
		else:	#Right buttons
			main.set_button(Bank.RIGHT,button)
	
	def bank_charging(self,bank):		#Change header to charging
		if bank == Bank.LEFT:
			self.left.header.charged['bg'] = 'gray'
			self.left.header.charging['bg'] = 'red'
			
		elif bank == Bank.MIDDLE:
			self.middle.header.charged['bg'] = 'gray'
			self.middle.header.charging['bg'] = 'red'
			
		elif bank == Bank.RIGHT:
			self.right.header.charged['bg'] = 'gray'
			self.right.header.charging['bg'] = 'red'
			
	def bank_charged(self,bank):		#Change header to charged
		if bank == Bank.LEFT:
			self.left.header.charged['bg'] = 'green'
			self.left.header.charging['bg'] = 'gray'
			
		elif bank == Bank.MIDDLE:
			self.middle.header.charged['bg'] = 'green'
			self.middle.header.charging['bg'] = 'gray'
			
		elif bank == Bank.RIGHT:
			self.right.header.charged['bg'] = 'green'
			self.right.header.charging['bg'] = 'gray'
			
	def bank_nothing(self,bank):		#Change header to neither
		if bank == Bank.LEFT:
			self.left.header.charged['bg'] = 'gray'
			self.left.header.charging['bg'] = 'gray'
			
		elif bank == Bank.MIDDLE:
			self.middle.header.charged['bg'] = 'gray'
			self.middle.header.charging['bg'] = 'gray'
			
		elif bank == Bank.RIGHT:
			self.right.header.charged['bg'] = 'gray'
			self.right.header.charging['bg'] = 'gray'
		
	def button_charging(self,button=0):
		self.button_list[button]['bg'] = 'yellow'	
		
	def button_done(self,button=0):
		self.button_list[button]['bg'] = 'green'
			
	def button_missing(self,button=0):
		self.button_list[button]['bg'] = 'gray'

usb = USB()								#Handles sending signals through usb to the charger switch		
main = Main()		

root = tk.Tk()
root.protocol('WM_DELETE_WINDOW', main.on_closing)
gui = GUI(master=root)
gui.master.title('2338 Battery Charger')

main.run()
