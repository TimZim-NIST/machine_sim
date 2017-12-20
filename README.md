TODO: Add instructions for changing the hostname, disabling dnsmasq 172.1.8.1 forward, NTP, etc.

# Machine Simulator

The Python script simulates MODBUS TCP server operations implemented by machine tools a typical manufacturing environment. The script was written to be deployed on a Beaglebone Black. The machine operations are simulated with a simple state machine. MODBUS TCP registers are updated at the rate defined in SIMULATION_FREQ_HZ. The script does not operate in real-time, nor does the script attempt to compensate for any delays, so jitter will likely be present.

Modified from https://pymodbus.readthedocs.io/en/latest/examples/updating-server.html

Author: Timothy Zimmerman (timothy.zimmerman@nist.gov)<br />
Modified by: Christian Burns (christian.burns@nist.gov)<br />
Organization: National Institute of Standards and Technology,
U.S. Department of Commerce<br />
License: Public Domain<br />

### Dependencies
pymodbus - https://pypi.python.org/pypi/pymodbus<br />
Twisted - https://pypi.python.org/pypi/Twisted<br />
Adafruit BBIO - https://github.com/adafruit/adafruit-beaglebone-io-python<br />

### MBTCP BITS AND REGISTERS
##### Coils (RW):
[0] ESTOP_IN - Machine will go into ESTOP if TRUE<br />
[1] RESET - Resets counters<br />
[2] ROBOT_PROXIMITY - Informs if the robot is in proximity<br />
[3] EXIT - Kill the python process<br />
[4] INVALIDSTATE - Anomaly: Machine reports an invalid state (>0x05)<br />
[5] TROUBLECALL - Anomaly: Machine reports trouble calls before each part<br />
[6] SHUTDOWN - Anomaly: Machine enters the 'STOPPED' state during workcell operations<br />

##### Holding Registers (RW):
[0] MACHINING_TIME - Amount of time machining process takes<br />
[1] MODE - Stop/Run<br />

##### Discrete Inputs (RO):
[0] ESTOP_OUT - Status of the ESTOP<br />
[1] DOOR_STATE - Status of the door (True=CLOSED)<br />
[2] CHUCK_STATE - Status of the chuck (True=CLOSED)<br />
[3] STOCK_PRESENT - Stock is in the chuck<br />
[4] INSPECTION_PASS - Current part PASSED inspection<br />
[5] INSPECTION_FAIL - Current part FAILED inspection<br />

##### Input Registers (RO):
[0] STATE - Numerical state of the state machine<br />
[1] MODE - Run/Stop/Estop<br />
[2] PROGRESS - 0-100% integer of machining progress<br />
[3] PART_COUNT - Number of completed parts<br />
[4] HEARTBEAT_COUNTER - Monitor to verify sim is running<br />
[5] MACHINE_ID - ID value for the machine (station number)<br />
[6] SW_VERSION - Software version number<br />
[7] INSPECTION_PASS - Counter for parts that passed inspection<br />
[8] INSPECTION_FAIL - Counter for parts that failed inspection<br />

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
# sudo apt-get purge lightdm
# sudo apt-get purge lxqt*
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
7. Edit ```/etc/apache2/sites-enabled/000-default.conf``` to listen on port 80:
```
<VirtualHost *:80>
```
and add the following to alias the simulator web pages:
```
  Alias /status "/dev/shm/status"
  <Directory "/dev/shm/status">
    AuthType Basic
    AuthName "Restricted Content"
    AuthUserFile /etc/apache2/.htpasswd
    Require valid-user
  </Directory>

```
8. Generate the .htpasswd file with the credentials (admin:1234):
```
$ sudo htpasswd -c /etc/apache2/.htpasswd admin
```
9. Reboot the BBB: ```shutdown -r now```
10. Configure USB networking. The USB interface should be configured with 192.168.7.<beaglebone number> To make ssh connections easier, each usb0 interface should be configured with a 192.168.7.y IP address, where y = the board's serial number, located on the top of the Ethernet RJ-45 connector (DO NOT FORGET TO UPDATE THE NETMASK TO 255.255.255.0):
```
cd /etc/networking
sudo nano interfaces
add the following:
# Ethernet/RNDIS gadget (g_ether)
# Used by: /opt/scripts/boot/autoconfigure_usb0.sh
# This is the information used for the static USB IP address
iface usb0 inet static
    address 192.168.7.X
    netmask 255.255.255.0
    network 192.168.7.0
    gateway 192.168.7.1
```
11. Configure Ethernet networking using connmanctl. The eth0 interface should be configured with a 192.168.1.10x IP address, where x = the station number, in order to operate properly in the NIST testbed.
```
sudo -s
connmanctl
>services
> config <service> --ipv4 manual <192.168.1.10x> 255.255.255.0 192.168.1.2
> Exit
systemctl restart networking
```
12. Add a new user called 'machine' to the environment: ```adduser machine```. Add this user to the sudo group: ```usermod -aG sudo machine```. Exit the SSH session and reconnect as 'machine'.
13. Disable the 'debian' user: ```chage -E 0 debian```.
14. Add the following alias in ```~/.bashrc```:
```
  alias ll='ls -al'
```
15. Install the following packages:
```
  apt install python-pymodbus python-twisted
```
16. Configure GPIO pin UART1 for the LCD by going to ```cd /boot/uEnv.txt```. Change the following:
```
##Example v4.1.x,
# cape_disable=bone_capemgr.disable_partno=
cape_enable=bone_capemgr.enable_partno=BB-UART1
```
17. Add the bash shell script as a cron job that executes every minute to check if the machine is running. Execute: ```crontab -e```. NOTE: It may be smart to comment this line out in the cron table until you're ready to have the machine run automatically:
```
  * * * * * /home/machine/Projects/machine_sim/machine_check.sh
```
18. Install the 'ntp' package: ```apt install ntp```. Open NTP Configuration: ```cd /etc``` and Edit the NTP configuration: ```nano ntp.conf```. Comment out all default NTP pool servers, and add the following:
```
  server 192.168.1.2
  minpoll 4
  maxpoll 6
```
19. Upload the simulator code to the BBB with the upload.sh script:
```
$ ./upload.sh
```
