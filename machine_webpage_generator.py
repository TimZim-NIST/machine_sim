#!/usr/bin/env python

import os
from time import localtime, strftime

class Generator:

	WWW_DIR         = "/var/www/html"
	WORKING_DIR     = "/dev/shm/status"
	HTML_HOMEPAGE   = "<html><body><h1>Machine 999</h1><p><a href='./status'>Machine Status</a></p><p><a href='./logs'>View Logs</a></p></body></html>"
	HTML_STATUS     = "<html><head><meta http-equiv='refresh' content='1'></head><body><h1>Machine 999 Status</h1><table cellpadding='5' border='1'>TABLE</table></body></html>"
	HTML_STATUS_ROW = "<tr><td>TITLE</td><td bgcolor='COLOR'>DATA</td></tr>"
	mb_data         = None
	status_page     = None
	MACHINE_STATES  = [ "UNLOADED","LOADED","ACTIVE","FINISHED","STOPPED","TROUBLE" ]

	def __init__(self,station_num,mb_data):
		self.mb_data = mb_data

		# Fix the strings since we now know the station number
		self.HTML_HOMEPAGE = self.HTML_HOMEPAGE.replace("999",str(station_num))
		self.HTML_STATUS = self.HTML_STATUS.replace("999",str(station_num))

		if os.path.isdir(self.WWW_DIR) == False:
			os.makedirs(self.WWW_DIR)

		# ALWAYS WRITE THIS -- In case things change
		#if os.path.isfile(self.WWW_DIR + "/index.html") == False:
		homepage = open(self.WWW_DIR + "/index.html","w")
		homepage.write(self.HTML_HOMEPAGE)
		homepage.close()

		# Check for the required directories (stored in shared mem so the beaglebone keeps it in RAM).
		# If it does not exist, create it.
		if os.path.isdir(self.WORKING_DIR) == False:
			os.makedirs(self.WORKING_DIR)

	def format(self,title,data):
		c = "white"
		if title in ("Robot Proximity","Stock Present"):
			if data == 0:
				d = "FALSE"
			else:
				d = "TRUE"
		elif title == "Job State":
			d = self.MACHINE_STATES[data]
		elif title in ("Workcell Mode", "Machine State"):
			if data == 0:
				d = "STOP"
				c = "gold"
			else:
				d = "RUN"
				c = "green"
		elif title in ("Door State","Chuck State"):
			if data == 0:
				d = "OPEN"
			else:
				d = "CLOSED"
		elif title == "Safety State":
			if data == True:
				d = "SAFE"
				c = "green"
			else:
				d = "FAULT"
				c = "red"
		elif title == "Progress":
			d = str(data) + "%"
		else:
			d = str(data)

		return self.HTML_STATUS_ROW.replace("TITLE",title).replace("DATA",d).replace("COLOR",c)

	def update(self):
		mb_co = self.mb_data[0].getValues(1,0x00,count=4)
		mb_di = self.mb_data[0].getValues(2,0x00,count=5)
		mb_hr = self.mb_data[0].getValues(3,0x00,count=2)
		mb_ir = self.mb_data[0].getValues(4,0x00,count=8)

		# Build the web page
		table = "<tr><th colspan='2' bgcolor='silver'>Machine Status</th></tr>"
		table += self.format("Safety State", mb_di[0])
		table += self.format("Machine State", mb_ir[1])
		table += self.format("Door State", mb_di[1])
		table += self.format("Chuck State", mb_di[2])

		table += "<tr><th colspan='2' bgcolor='silver'>Job Status</th></tr>"
		table += self.format("Job State", mb_ir[0])
		table += self.format("Stock Present", mb_di[3])
		table += self.format("Progress", mb_ir[2])
		table += self.format("Part Counter", mb_ir[3])

		table += "<tr><th colspan='2' bgcolor='silver'>External I/O</th></tr>"
		table += self.format("Robot Proximity", mb_co[2])
		table += self.format("Workcell Mode", mb_hr[1])

		table += "<tr><th colspan='2' bgcolor='silver'>System Info</th></tr>"
		table += self.format("Firmware Version", mb_ir[6])
		table += self.format("Time", strftime("%d %b %Y %H:%M:%S", localtime()))

		# Write to file
		with open(self.WORKING_DIR + "/index.html", "w") as status_page:
			status_page.write(self.HTML_STATUS.replace("TABLE",table))
			status_page.close()