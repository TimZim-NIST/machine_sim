# Machine Simulator

The Python script simulates MODBUS TCP server operations implemented by machine tools a typical manufacturing environment. The script was written to be deployed on a Beaglebone Black. The machine operations are simulated with a simple state machine. MODBUS TCP registers are updated at the rate defined in SIMULATION_FREQ_HZ. The script does not operate in real-time, nor does the script attempt to compensate for any delays, so jitter will likely be present.

Modified from https://pymodbus.readthedocs.io/en/latest/examples/updating-server.html

Author: Timothy Zimmerman (timothy.zimmerman@nist.gov)<br />
Organization: National Institute of Standards and Technology,
U.S. Department of Commerce<br />
License: Public Domain<br />

### Dependencies
pymodbus - https://pypi.python.org/pypi/pymodbus<br />
Twisted - https://pypi.python.org/pypi/Twisted<br />
Adafruit BBIO - https://github.com/adafruit/adafruit-beaglebone-io-python

### MBTCP BITS AND REGISTERS
##### Coils (RW):
[0] ESTOP_IN - Machine will go into ESTOP if TRUE<br />
[1] RESET - Resets counters<br />
[2] ROBOT_PROXIMITY - Informs if the robot is in proximity<br />

##### Holding Registers (RW):
[0] MACHINING_TIME - Amount of time machining process takes<br />
[1] MODE - Stop/Run<br />

##### Discrete Inputs (RO):
[0] ESTOP_OUT - Status of the ESTOP<br />
[1] DOOR_STATE - Status of the door (True=CLOSED)<br />
[2] CHUCK_STATE - Status of the chuck (True=CLOSED)<br />
[3] STOCK_PRESENT - Stock is in the chuck<br />

##### Input Registers (RO):
[0] STATE - Numerical state of the state machine<br />
[1] MODE - Run/Stop/Estop<br />
[2] PROGRESS - 0-100% integer of machining progress<br />
[3] PART_COUNT - Number of completed parts<br />
[4] HEARTBEAT_COUNTER - Monitor to verify sim is running<br />
[5] MACHINE_ID - ID value for the machine (station number)<br />

### Upgrade the BBB
The most recent revision of this project uses the following image:
```
Linux beaglebone 4.4.54-ti-r93 #1 SMP Fri Mar 17 13:08:22 UTC 2017 armv7l GNU/Linux
```
Upgrade the BBB with this image, available from https://beagleboard.org/latest-images.

### Internet Connection Sharing
If connection sharing is required, follow this guide: https://elementztechblog.wordpress.com/2014/12/22/sharing-internet-using-network-over-usb-in-beaglebone-black/

### Setup the BBB
1. Follow the 'Getting Started' guide from http://beagleboard.org/getting-started
2. Connect to the BBB as root: ```ssh root@192.168.7.2```
3. Perform the following:
```
# cd /etc/init.d/
# chmod -x avahi-daemon
# chmod -x console-setup
# chmod -x keyboard-setup
# chmod -x kmod
# chmod -x screen-cleanup
# chmod -x wicd
# chmod -x x11-common
# sudo apt purge lightdm
# sudo apt purge lxqt*
```
4. Perform the following to disable cloud9: (http://kacangbawang.com/beagleboneblack-revc-debloat-part-1/):
```
# systemctl stop cloud9.service            #stop working copy
# systemctl stop cloud9.socket             #stop working copy
# systemctl disable cloud9.service         #disable autorun
# systemctl disable cloud9.socket          #disable autorun
# systemctl daemon-reload                  #restart/reload systemctl daemon
```
5. Perform the following to disable bonescript (http://kacangbawang.com/beagleboneblack-revc-debloat-part-1/):
```
# systemctl stop bonescript-autorun.service        #stop currently running copy
# systemctl stop bonescript.service
# systemctl stop bonescript.socket
# systemctl disable bonescript-autorun.service     #purge autorun scripts
# systemctl disable bonescript.service
# systemctl disable bonescript.socket
# systemctl daemon-reload                          #restart/reload systemctl deamon
```
6. Edit ```/etc/apache2/ports.conf``` to listen on port 80:
```
Listen 80
```
7. Reboot the BBB: ```shutdown -r now```
8. Edit the ```/etc/network/interfaces``` file. The eth0 interface should be configured with a 192.168.1.10x IP address, where x = the station number, in order to operate properly in the NIST testbed. To make ssh connections easier, each usb0 interface should be configured with a 192.168.7.y IP address, where y = the board's serial number, located on the top of the Ethernet RJ-45 connector (DO NOT FORGET TO UPDATE THE NETMASK TO 255.255.255.0):
```
  # The primary network interface
  # This is the information regarding the ethernet static IP
  # Addresses are asigned as 192.168.[0 for Control Sys 1 for Field Comm].xyz
  auto eth0
  iface eth0 inet static
  address 192.168.1.10x
  netmask 255.255.255.0
  gateway 192.168.1.2

  # Ethernet/RNDIS gadget (g_ether)
  # Used by: /opt/scripts/boot/autoconfigure_usb0.sh
  # This is the information used for the static USB IP address
  iface usb0 inet static
      address 192.168.7.y
      netmask 255.255.255.0
      network 192.168.7.0
      gateway 192.168.7.1
```
10. Add a new user called 'machine' to the environment: ```adduser machine```. Add this user to the sudo group: ```usermod -aG sudo machine```. Exit the SSH session and reconnect as 'machine'. Disable the 'debian' user: ```chage -E 0 debian```.
11. Add the following alias in ```~/.bashrc```:
```
  alias ll='ls -al'
```
12. Install the following packages:
```
  apt install python-pymodbus python-twisted
```
13. Add the bash shell script as a cron job that executes every minute to check if the machine is running. Execute: ```crontab -e```. NOTE: It may be smart to comment this line out in the cron table until you're ready to have the machine run automatically:
```
  * * * * * /home/machine/Projects/machine_sim/machine_check.sh
```
14. Install the 'ntp' package: ```apt install ntp```. Edit the NTP configuration: ```nano ntp.conf```. Comment out all default NTP pool servers, and add the following:
```
  server 192.168.1.2
  minpoll 4
  maxpoll 6
```
