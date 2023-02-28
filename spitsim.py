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
from datetime import datetime
import json
def prRed(prt): print("\033[91m {}\033[00m" .format(prt))
def prGreen(prt): print("\033[92m {}\033[00m" .format(prt))
def prYellow(prt): print("\033[93m {}\033[00m" .format(prt))
def prLightPurple(prt): print("\033[94m {}\033[00m" .format(prt))
def prPurple(prt): print(datetime.now().strftime("%H:%M:%S")+"\033[95m {}\033[00m" .format(prt))
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
yaml = ""
httpport=""
platform=""
password=""
start_time=int(datetime.now().strftime('%s'))
def getUserInputs():
    global yaml
    global httpport 
    global platform
    global password
    platform= input("Choose 1)SFF 2)SFD 3) XRV9k")
    if platform == "1":
        yaml = "spitfire-f.yaml"
    if platform == "2":
        yaml = "spitfire-d.yaml"
    if platform == "3":
        yaml = "xrv9k.yaml"

    revert_yaml = input("Revert back the sim config.yaml Y/N? Choose N if you have modifed the yaml")
    if revert_yaml == 'Y':
      #revert back the config file before each run
      i = pexpect.spawn("git checkout infra/appmgr/test/etc/"+yaml)
    boot_golden = input("Boot Golden iso Y/N")
    if boot_golden=='Y':
      build_golden = input("Generate the Golden ISO Y/N")
      if build_golden == 'Y':
        child = pexpect.spawn("rm -rf /nobackup/"+user+"/ihc_sb")
        time.sleep(1)
        child = pexpect.spawn("mkdir /nobackup/"+user+"/hc_sb")
        time.sleep(1)
        os.system("cp img-8000/optional-rpms/healthcheck/*.rpm /nobackup/"+user+"/hc_sb/")
        os.system("cp img-8000/optional-rpms/sandbox/*.rpm /nobackup/"+user+"/hc_sb/")
        time.sleep(1)
        child = pexpect.spawn("/auto/ioxprojects13/lindt-giso/isotools.sh --clean --iso img-8000/8000-x64.iso --label healthcheck --repo /nobackup/"+user+"/hc_sb/ --pkglist xr-healthcheck xr-sandbox")
        out = child.expect(['Checksums OK','The specified output dir is not empty'],timeout=1000)
        if out == 1:
          prRed("Deleting existing GISO")
          child = pexpect.spawn("rm -rf output_gisobuild/")
          time.sleep(1)
          child = pexpect.spawn("/auto/ioxprojects13/lindt-giso/isotools.sh --iso img-8000/8000-x64.iso --label healthcheck --repo /nobackup/"+user+"/hc_sb/ --pkglist xr-healthcheck xr-sandbox")
          out = child.expect(['Checksums OK','The specified output dir is not empty'],timeout=1000)
          time.sleep(15)
    golden_img = glob.glob( "output_gisobuild/giso/8000-golden*.iso")
    if boot_golden=='Y':
      if(len(golden_img) == 0):
        prRed("Golden ISO missing.. Continuing with normal iso")
      else:
        i = pexpect.spawn("sed -i \'s|img-8000\/8000-x64\.iso|"+golden_img[0].strip()+"|g\' infra\/appmgr\/test\/etc\/"+yaml)
    password=getpass.getpass("CEC Password")
    httpport = input("Enter http port for remote repo ")

    # Arguments passed
logfile = sys.argv[1]
def mount_nb_sf(child):
     while True:
       global password
       child.sendline("sshfs "+user+"@"+MYADS+":/nobackup/"+user+" /nb -o reconnect,ServerAliveInterval=15,ServerAliveCountMax=3 ")
       try:
         child.expect(['Are you sure'],timeout=60)
         child.sendline('yes')
         child.expect(['password'],timeout=600)
       except:
         prRed("sshfs to ADS failed check connectivity to ADS")
         return
       child.sendline(password)
       ret = child.expect(['CPU0:','password'],timeout=10)
       if ret==1:
         prRed("Mount nobackup failed, probably the CEC password was wrong")
         password=getpass.getpass("CEC Password")
         child.sendline(password)
         break
       else:
         break

def mount_nb_xrv9k(child):
     while True:
       global password
       child.sendline("exit")
       ret = child.expect(['CPU0:'],timeout=10)
       child.sendline("admin")
       ret = child.expect(['sysadmin'],timeout=10)
       child.sendline("run ssh 10.0.2.16")
       ret = child.expect(['host'],timeout=10)
       child.sendline("passwd")
       ret = child.expect(['Enter new UNIX password:'],timeout=10)
       child.sendline("cisco123")
       ret = child.expect(['Retype new UNIX password:'],timeout=10)
       child.sendline("cisco123")
       ret = child.expect(['host'],timeout=10)
       child.sendline("mkdir /nb")
       child.sendline("sshfs "+user+"@"+MYADS+":/nobackup/"+user+ " /nb")
       child.expect(['password'],timeout=10)
       child.sendline(password)
       child.expect(['host'],timeout=10)
       child.sendline("exit")
       ret = child.expect(['sysadmin'],timeout=10)
       child.sendline("exit")
       child.expect(['CPU0:'],timeout=100)
       child.sendline("run")
       child.sendline("sshfs 10.0.2.16:/nb /nb")
       child.expect(['password'],timeout=300)
       child.sendline("cisco123")
       child.expect(['CPU0:'],timeout=100)
       break

def storeUserInput():
  global httpport
  global platform
  global yaml
  global start_time
  dictionary = {'httpport':httpport,'yaml':yaml,'platform':platform,'start_time':start_time}
  with open("sim_user_input.json", "w") as outfile:
    json.dump(dictionary, outfile)

def loadUserInput(read_ts):
  global httpport
  global platform
  global yaml
  global start_time
  with open("sim_user_input.json", "r") as infile:
    dictionary = json.load(infile)
    httpport = dictionary['httpport']
    platform = dictionary['platform']
    yaml = dictionary['yaml']
    if read_ts == True:
      start_time = int(dictionary['start_time'])
def BootSpitfireSim():
  fail=0
  global httpport
  global platform
  global yaml
  global start_time
  prPurple("starting Sim")
  i = pexpect.spawn("it_helper_config --http_server_port "+httpport)
  if(os.path.exists("vxr.out/slurm.jobid")):
     prPurple("Prev Running instance detected")
     prPurple("Cleaning previous instances....")
     command = "/auto/vxr/pyvxr/latest/vxr.py clean"
     child = pexpect.spawn(command,timeout=None)
     child.expect(['Releasing'],timeout=1000)
     time.sleep(60)
     prPurple("Starting fresh instances....")
  try:
     command = "/auto/vxr/pyvxr/latest/vxr.py start ./infra/appmgr/test/etc/"+yaml
     child = pexpect.spawn(command,timeout=None)
     child.logfile = open(logfile, "wb")
  except:
       prPurple("Exception")
  time.sleep(5)                             
  i = child.expect(['Sim up'],timeout=1800)
  start_time=int(datetime.now().strftime('%s'))
  if (i == 0):
     prPurple('Sim UP')
     flushedStuff=""
     child = pexpect.spawn('/bin/sh -c "/auto/vxr/pyvxr/latest/vxr.py ports > ports.json"')
     time.sleep(10)
     fo = open('ports.json')
     data = json.load(fo)
     host = data['R1']['HostAgent']
     serial0 = data['R1']['serial0']
     prPurple("Connecting to " +str(host)+":"+str(serial0))

     command = "telnet -l cisco "+str(host)+" "+str(serial0)
     child = pexpect.spawn(command,timeout=None,ignore_sighup=True)
     time.sleep(1)
     child.sendline("\r\n");
     child.expect(['CPU0:["-z]*#'],timeout=300)
     prPurple("Setting up routes")
     #child.sendline("run ip netns exec xrnns bash")
     child.sendline("run")
     time.sleep(1)
     #child.sendline("dhclient eth-mgmt")
     time.sleep(1)
     child.sendline("route add -host "+MYADS+" gw 192.168.122.1 eth-mgmt")
     #child.sendline("setenforce 0")
     child.sendline("mkdir /nb")
     prPurple("Setting up nobackup mount")
     time.sleep(3)
     if platform == "3":
         mount_nb_xrv9k(child)
     else:
         mount_nb_sf(child)
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
     child.sendline('\r\n')
     prGreen("Sim Is UP , login using below command")
     prGreen(command)
     prRed("If nobackup doesn't mount please use below command")
     prGreen("sshfs "+user+"@"+MYADS+":/nobackup/"+user+" /nb -o reconnect,ServerAliveInterval=15,ServerAliveCountMax=3")
     child.sendline('^]')
     child.sendline('q')
     child.sendline('\r\n')
     child.sendline('\r\n')
     child.close()
     start_time = int(datetime.now().strftime('%s'))
     storeUserInput()

def checkSim(takeUserInput):
     command = "/auto/vxr/pyvxr/latest/vxr.py status"
     out =""
     try:
       child1 = pexpect.spawn(command,timeout=None)
       out = child1.expect(['\nDidn\'t find a valid','vxr-'],timeout=300)
     except KeyboardInterrupt:
         print("\nInterrupted")
         sys.exit(0)
     except:
          print("\nSim not found.Starting again")
          if(takeUserInput == True):
              getUserInputs()
          BootSpitfireSim()
     else:
       if out == 1:
        status = child1.read()
        if 'ended' in status.decode("utf-8") or 'unknown' in status.decode("utf-8") or 'not running' in status.decode("utf-8"):
          print("\nSim ended.Starting again")
          if(takeUserInput == True):
              getUserInputs()
          BootSpitfireSim()
        elif 'running' in status.decode("utf-8"):
          loadUserInput(takeUserInput)
          curr_time = int(datetime.now().strftime('%s'))
          duration = curr_time - start_time
          hours = divmod(duration,3600)[0]
          mins = int(divmod(duration,3600)[1]/60)
          print("Sim running in current ws for "+str(hours)+" hours "+str(mins)+" mins.",end ='\r')

     if out == 0:
          print("VXR Sim not found.Starting again")
          if(takeUserInput == True):
              getUserInputs()
          BootSpitfireSim()


def main():
     print("Checking for running instance....")
     checkSim(True)
     while True:
         time.sleep(100)
         checkSim(False)

if __name__ == '__main__':
    main()
