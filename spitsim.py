#!/usr/bin/python                                                               
#Sumit Kala, Feb 2022                                               
from __future__ import print_function
import sys                                                                      
import socket
import glob                                                                     
import os                                                                       
import pdb                                                                       
import re                                                                       
import subprocess
import _thread
import time 
import getpass
from os.path import exists, join
from time import gmtime, strftime
import threading
import json
def prRed(prt): print("\033[91m {}\033[00m" .format(prt))
def prGreen(prt): print("\033[92m {}\033[00m" .format(prt))
def prYellow(prt): print("\033[93m {}\033[00m" .format(prt))
def prLightPurple(prt): print("\033[94m {}\033[00m" .format(prt))
def prPurple(prt): print("\033[95m {}\033[00m" .format(prt))
def prCyan(prt): print("\033[96m {}\033[00m" .format(prt))
def prLightGray(prt): print("\033[97m {}\033[00m" .format(prt))
def prBlack(prt): print("\033[98m {}\033[00m" .format(prt))
# total arguments
n = len(sys.argv)
if (n<2):
  prRed("Usage:")
  prGreen("python3 spitsim.py logfile")
  prGreen("E.g. python3 spitsim.py /tmp/spitsimbringup.log")
  sys.exit(0)

try :
    import pexpect
except:
    prRed("pexpect is not available install it using the script pythonsetup")
    sys.exit(0);
MYADS=socket.gethostbyname(socket.gethostname())
user=os.getlogin()
#revert back the config file before each run
i = pexpect.spawn("git checkout infra/appmgr/test/etc/spitfire-f.yaml")
boot_golden = input("Boot Golden iso Y/N")
golden_img = glob.glob( "output_isotools/8000-golden*.iso")
if boot_golden=='Y':
  i = pexpect.spawn("sed -i \'s|img-8000\/8000-x64\.iso|"+golden_img[0].strip()+"|g\' infra\/appmgr\/test\/etc\/spitfire-f\.yaml")
password=getpass.getpass("CEC Password")
httpport = input("Enter http port for remote repo ")

# Arguments passed
logfile = sys.argv[1]
def BootSpitfireSim():
  fail=0
  print("starting Sim")
  i = pexpect.spawn("it_helper_config --http_server_port "+httpport)
  while True:
   if (fail >0):
     prRed("Auto Cleaning failed, Please try manual clean \'/auto/vxr/pyvxr/latest/vxr.py clean\'")
     sys.exit(0)
   try:
     command = "/auto/vxr/pyvxr/latest/vxr.py start ./infra/appmgr/test/etc/spitfire-f.yaml"
     child = pexpect.spawn(command,timeout=None)
     child.logfile = open(logfile, "wb")
     i = child.expect(['pexpect.exceptions.EOF'],timeout=10000)
   except:
     print("Prev Running instance detected")
     print("Cleaning previous instances....")
     command = "/auto/vxr/pyvxr/latest/vxr.py clean"
     child = pexpect.spawn(command,timeout=None)
     child.expect(['Releasing'],timeout=1000)
     time.sleep(60)
     print("Starting fresh instances....")
     command = "/auto/vxr/pyvxr/latest/vxr.py start ./infra/appmgr/test/etc/spitfire-f.yaml"
     child = pexpect.spawn(command,timeout=None)
     child.logfile = open(logfile, "wb")
     fail = fail+1
   time.sleep(5)                             
   i = child.expect(['Sim up'],timeout=5000)
   if (i == 0):
     print('Sim UP')
     flushedStuff=""
     child = pexpect.spawn('/bin/sh -c "/auto/vxr/pyvxr/latest/vxr.py ports > ports.json"')
     time.sleep(10)
     fo = open('ports.json')
     data = json.load(fo)
     host = data['R1']['HostAgent']
     serial0 = data['R1']['serial0']
     print("Connecting to " +str(host)+":"+str(serial0))

     command = "telnet -l cisco "+str(host)+" "+str(serial0)
     child = pexpect.spawn(command,timeout=None,ignore_sighup=True)
     time.sleep(1)
     child.sendline("\r\n");
     child.expect(['CPU0:["-z]*#'],timeout=300)
     print("Setting up routes")
     #child.sendline("run ip netns exec xrnns bash")
     child.sendline("run")
     time.sleep(1)
     #child.sendline("dhclient eth-mgmt")
     time.sleep(1)
     child.sendline("route add -host "+MYADS+" gw 192.168.122.1 eth-mgmt")
     child.sendline("setenforce 0")
     child.sendline("mkdir /nb")
     print("Setting up nobackup mount")
     time.sleep(3)
     while True:
       global password
       child.sendline("sshfs "+user+"@"+MYADS+":/nobackup/"+user+" /nb -o reconnect,ServerAliveInterval=15,ServerAliveCountMax=3 ")
       child.expect(['Are you sure'],timeout=300)
       child.sendline('yes')
       child.expect(['password'],timeout=300)
       child.sendline(password)
       ret = child.expect(['CPU0:','password'],timeout=10)
       if ret==1:
         prRed("Mount nobackup failed, probably the CEC password was wrong")
         password=getpass.getpass("CEC Password")
         child.sendline(password)
         break
       else:
         break
     time.sleep(3)
     child.sendline('\r\n')
     child.sendline('\r\n')
     child.sendline('\r\n')

     time.sleep(3)
     try:
      while not child.expect(r'.+', timeout=1):
       flushedStuff += str(child.match.group(0))
     except:
       pass
     print("Flushed"+flushedStuff)

     time.sleep(3)
     child.sendline('exit')

     time.sleep(3)

     child.sendline('conf t')
     time.sleep(3)
     child.sendline('root')
     time.sleep(2)
     #Insert your it_helper_config here
     cmd="""router static
  vrf management
    address-family ipv4 unicast
      """+MYADS+"""/32 192.168.122.1
    !
  !
!

install
  repository remote_dev_rpm
     url http://"""+MYADS+""":"""+httpport+""";management/
  !
!
"""
     child.sendline(cmd)
     time.sleep(3)
     child.sendline('commit')
     child.sendline('end')
     time.sleep(2)
     child.sendline('show run interface MgmtEth 0/RP0/CPU0/0')
     child.sendline('exit')
     prGreen("Sim Is UP , login using below command")
     print(command)
     prRed("If nobackup doesn't mount please use below command")
     prGreen("sshfs "+user+"@"+MYADS+":/nobackup/"+user+" /nb -o reconnect,ServerAliveInterval=15,ServerAliveCountMax=3")
     break

def main():
  BootSpitfireSim()

if __name__ == '__main__':
    main()
