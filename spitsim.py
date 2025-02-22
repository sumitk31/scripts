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
from datetime import timezone
import json
def prRed(prt): print(datetime.now().strftime("%d-%m-%Y %H:%M:%S")+"\033[91m {}\033[00m" .format(prt))
def prGreen(prt): print(datetime.now().strftime("%d-%m-%Y %H:%M:%S")+"\033[92m {}\033[00m" .format(prt))
def prYellow(prt): print("\033[93m {}\033[00m" .format(prt))
def prLightPurple(prt): print("\033[94m {}\033[00m" .format(prt))
def prPurple(prt): print(datetime.now().strftime("%d-%m-%Y %H:%M:%S")+"\033[95m {}\033[00m" .format(prt))
def prCyan(prt): print("\033[96m {}\033[00m" .format(prt))
def prLightGray(prt): print(datetime.now().strftime("%d-%m-%Y %H:%M:%S")+"\033[97m {}\033[00m" .format(prt))
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
new_sim_path=""
yaml = ""
httpport=""
platform=""
password=""
boot_golden=""
build_golden=""
spirent_topo=""
ws_upd_notified="N"
start_time=int(datetime.now().strftime('%s'))
auto_upd = ""
branch = ""
disable_selinux = ""
selinux_disable_patch = "/auto/appmgr/selinux_disable_on_8k.diff"
def generateGiso():
    child = pexpect.spawn("rm -rf ./hc_sb")
    time.sleep(1)
    child = pexpect.spawn("mkdir ./hc_sb")
    time.sleep(1)
    os.system("cp img-8000/optional-rpms/healthcheck/*.rpm ./hc_sb/")
    os.system("cp img-8000/optional-rpms/sandbox/*.rpm ./hc_sb/")
    time.sleep(1)
    child = pexpect.spawn("/auto/ioxprojects13/lindt-giso/isotools.sh --clean --iso img-8000/8000-x64.iso --label healthcheck --repo ./hc_sb/ --pkglist xr-healthcheck xr-sandbox")
    out = child.expect(['Checksums OK','The specified output dir is not empty'],timeout=1000)
    if out == 1:
      prRed("Deleting existing GISO")
      child = pexpect.spawn("rm -rf output_gisobuild/")
      time.sleep(1)
      prGreen("Generating Golden ISO")
      child = pexpect.spawn("/auto/ioxprojects13/lindt-giso/isotools.sh --iso img-8000/8000-x64.iso --label healthcheck --repo ./hc_sb/ --pkglist xr-healthcheck xr-sandbox")
      out = child.expect(['Checksums OK','The specified output dir is not empty'],timeout=1000)
      time.sleep(15)

def wait_for_file(file_path, timeout):
    start_time = time.time()

    while True:
        if os.path.exists(file_path):
            prPurple(f"File {file_path} created.")
            return True
        
        if time.time() - start_time > timeout:
            prPurple(f"Timeout exceeded while waiting for file {file_path}.")
            return False
        
        time.sleep(300) 
def bootGiso():
      global yaml
      golden_img = glob.glob( "output_gisobuild/giso/8000-golden*.iso")
      if(len(golden_img) == 0):
        prRed("Golden ISO missing.. Continuing with normal iso")
      else:
        prRed("Updating "+yaml+" to use "+golden_img[0].strip())
        i = pexpect.spawn("sed -i \'s|img-8000\/8000-x64\.iso|"+golden_img[0].strip()+"|g\' infra\/appmgr\/test\/etc\/"+yaml)
        time.sleep(3)
        
def rebuild_with_selinux_disable_patch():
    global selinux_disable_patch
    command = "git apply "+ selinux_disable_patch
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    process.wait()
    prLightGray( process.returncode)
    buildcmd = "tools/misc/xr_bld -plat 8000"
    prGreen("Starting XR-build with Patch")
    process = subprocess.Popen(buildcmd, shell=True, stdout=subprocess.PIPE)
    process.wait()
    prLightGray( process.returncode)
    prGreen(" XR-build completed")
    command = "git restore platforms/spitfire/thinxr/boot/src/grub_rp.yaml"
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    process.wait()
    prLightGray( process.returncode)
    
def pullWorkSpaceAndBuild(platform,branch):
    command="git clone git@gh-xr.scm.engit.cisco.com:xr/iosxr.git"
    #command="git clone https://github.com/sumitk31/scripts.git"
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    process.wait()
    os.chdir("iosxr")
    command="git checkout "+branch
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    if platform in ["1","2"]:
      plat = "8000"
    elif platform == "3":
      plat = "xrv9k"
    else :
      prLightGray("Invalid Platform")
      sys.exit(0)
    buildcmd = "tools/misc/xr_bld -plat "+ plat
    prGreen("Starting XR-build")
    process = subprocess.Popen(buildcmd, shell=True, stdout=subprocess.PIPE)
    process.wait()
    prLightGray( process.returncode)
    if build_golden == "Y":
      generateGiso()

def getUserInputs():
    global yaml
    global httpport 
    global platform
    global password
    global auto_upd
    global boot_golden
    global build_golden
    global spirent_topo
    global branch
    global disable_selinux
    
    pullws = input("Do you want to pull a WS Y/N ?")
    if(pullws =='Y'):
        branch = input("Branch name?")
        auto_upd = input("Do you want to Auto Upgrade WS every week  Y/N ?")

    platform= input("Choose 1)SFF 2)SFD 3) XRV9k 4) ASR9k 5)Glandon")
    if platform == "1":
        yaml = "spitfire-f.yaml"
    elif platform == "2":
        yaml = "spitfire-d.yaml"
    elif platform == "3":
        yaml = "xrv9k.yaml"
    elif platform == "4":
        yaml = "asr9k.yaml"
    elif platform == "5":
        yaml = "spitfire-glandon-f.yaml"
    else :
        prRed("Wrong Input")
        sys.exit(0)


    revert_yaml = input("Revert back the sim config.yaml Y/N? Choose N if you have modifed the yaml")
    if revert_yaml == 'Y':
      #revert back the config file before each run
      i = pexpect.spawn("git checkout infra/appmgr/test/etc/"+yaml)
    password=getpass.getpass("CEC Password")
    
    i = pexpect.spawn("sed -i \'s|R1|router0|g\' infra\/appmgr\/test\/etc\/"+yaml)
    time.sleep(3)
    if platform != "3":
        disable_selinux = input("Disable SELinux via patch and rebuild Y/N?")
        
   
    boot_golden = input("Boot Golden iso Y/N?")
    if boot_golden.upper() == 'Y':
      build_golden = input("Generate the Golden ISO Y/N?")
    spirent_topo = input("Spirent topo required Y/N?")
    if pullws.upper() == "Y":
      pullWorkSpaceAndBuild(platform,branch)
    routerport = "router0.HundredGigE0/0/0/0"
    if spirent_topo.upper() == 'Y':
        cmd = """ echo "  tgn:
        platform: spirent
        spirent_images:
           windows: /auto/vxr/images/spirent/WindowsWithTestCenter_5_38
           api: /auto/vxr/images/spirent/Spirent_TestCenter_LabServer-5.38.img
           port: /auto/vxr/images/spirent/sptvm-5_38.img " >>infra/appmgr/test/etc/"""+yaml
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        process.wait()
        if platform == "1":
            i = pexpect.spawn("sed -i \'/hubs:/r nosi_tgen.txt' infra\/appmgr\/test\/etc\/"+yaml)
            time.sleep(3)
        '''
          cmd = """ echo "
        TGEN-1-router0:
        - tgn.1/1
        - router0.FourHundredGigE0/0/0/0

        TGEN-1-R2:
        - tgn.1/2
        - router0.FourHundredGigE0/0/0/1"  >> infra/appmgr/test/etc/"""+yaml

        if platform == "2":
          cmd = """ echo "
connections:
    hubs:
        TGEN-1-router0:
        - tgn.1/1
        - router0.HundredGigE0/0/0/0

        TGEN-1-R2:
        - tgn.1/2
        - router0.HundredGigE0/0/0/1"  >> infra/appmgr/test/etc/"""+yaml
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        process.wait()
        '''
        '''
        cmd = "sed -i '6i\        vxr_sim_config:' infra/appmgr/test/etc/"+yaml
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        process.wait()
        cmd = "sed -i '7i\          shelf:' infra/appmgr/test/etc/"+yaml
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        process.wait()
        cmd = "sed -i '8i\            ConfigEnableNgdp: \"True\" ' infra/appmgr/test/etc/"+yaml
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        process.wait()
        '''
    if disable_selinux.upper() == 'Y':
        rebuild_with_selinux_disable_patch()
    if build_golden.upper() == 'Y':
        generateGiso()
    if boot_golden.upper() == 'Y':
        bootGiso()



    # Arguments passed
logfile = sys.argv[1]
def mount_nb_sf(child):
     while True:
       global password
       child.sendline("dhclient -i eth-mgmt")
       child.sendline("sshfs "+user+"@"+MYADS+":/nobackup/"+user+" /nb -o reconnect,ServerAliveInterval=15,ServerAliveCountMax=3 ")
       break
       '''
       try:
         ret = child.expect(['Are you sure','password'],timeout=60)
         if ret == 0:
           child.sendline('yes')
           child.expect(['password'],timeout=60)
       except:
         prRed("sshfs to ADS failed check connectivity to ADS")
         return
       child.sendline(password)
       ret = child.expect(['CPU0:','password','Enter a passcode'],timeout=10)
       if ret==1:
         prRed("Mount nobackup failed, probably the CEC password was wrong")
         password=getpass.getpass("CEC Password")
         child.sendline(password)
         break
       elif ret == 2:
         prRed("Check Duo Notification on phone")
         child.sendline('1\r\n')
         break
       '''

def mount_nb_xrv9k(child):
     while True:
       global password
       child.sendline("exit")
       ret = child.expect(['CPU0:'],timeout=60)
       child.sendline("admin")
       ret = child.expect(['sysadmin'],timeout=100)
       child.sendline("run ssh 10.0.2.16")
       ret = child.expect(['host'],timeout=100)
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
  global spirent_topo
  dictionary = {'httpport':httpport,'yaml':yaml,'platform':platform,'start_time':start_time,'spirent_topo':spirent_topo}
  with open("sim_user_input.json", "w") as outfile:
    json.dump(dictionary, outfile)

def loadUserInput(read_ts):
  global httpport
  global platform
  global yaml
  global start_time
  global spirent_topo
  with open("sim_user_input.json", "r") as infile:
    dictionary = json.load(infile)
    httpport = dictionary['httpport']
    platform = dictionary['platform']
    yaml = dictionary['yaml']
    spirent_topo = dictionary['spirent_topo']
    if read_ts == True:
      start_time = int(dictionary['start_time'])
def BootSpitfireSim():# new_sim_path added to allow more than on sim being launched from same ws
  fail=0
  global httpport
  global platform
  global yaml
  global start_time
  global new_sim_path
  prPurple("starting Sim")
  storeUserInput()
  #i = pexpect.spawn("it_helper_config --http_server_port "+httpport)
  if(os.path.exists("vxr.out/slurm.jobid") and new_sim_path == ""):
     prPurple("Prev Running instance detected")
     prPurple("Cleaning previous instances....")
     command = "/auto/vxr/pyvxr/latest/vxr.py clean"
     child = pexpect.spawn(command,timeout=None)
     child.expect(['Releasing'],timeout=1000)
     time.sleep(60)
     child = pexpect.spawn("rm -rf vxr.out", timeout=None)
     prPurple("Starting fresh instances....")
     
  try:
     if platform in ["1","2"]:
         file_path = "img-8000/8000-x64.iso"
     if platform == "3":
         file_path = "img-xrv9k/xrv9k-full-x.iso"
     if platform == "4":
         file_path = "img-asr9k/asr9k-mini-x64.iso"
     if platform == "5":
         file_path = "img-8000-aarch64/8000-aarch64.iso"
         
     timeout = 5000  # Timeout in seconds (5 minutes)
     prPurple(f"Waiting for iso {file_path} to be created...")
     if wait_for_file(file_path, timeout):
        prPurple("iso available. Proceeding with further actions.")
     else:
        prPurple("iso not found within the specified timeout. Exiting.")
        sys.exit(0)
     if new_sim_path == "":
         command = "/auto/vxr/pyvxr/latest/vxr.py start ./infra/appmgr/test/etc/"+yaml
     else:
         os.makedirs(new_sim_path,exist_ok=True)
         command = "/auto/vxr/pyvxr/latest/vxr.py start --output-dir "+new_sim_path+" ./infra/appmgr/test/etc/"+yaml
     child = pexpect.spawn(command,timeout=None)
     child.logfile = open(logfile, "wb")
  except:
       prPurple("Exception")
  time.sleep(5)                             
  i = child.expect(['Sim up'],timeout=3000)
  start_time=int(datetime.now().strftime('%s'))
  if (i == 0):
     prPurple('Sim UP')
     prPurple('SITH Cleanup ongoing...')
     command = "sith cleanup"
     prGreen('SITH Configure ongoing...')
     child = pexpect.spawn(command,timeout=None)
     command = "sith configure --vxr"
     child = pexpect.spawn(command,timeout=None)
     flushedStuff=""
     if new_sim_path == "":
        child = pexpect.spawn('/bin/sh -c "/auto/vxr/pyvxr/latest/vxr.py ports > ports.json"')
        time.sleep(10)
        fo = open('ports.json')
     else:
        os.chdir(new_sim_path)
        child = pexpect.spawn('/bin/sh -c "/auto/vxr/pyvxr/latest/vxr.py ports > ports.json"')
        time.sleep(10)
        fo = open('ports.json')
        os.chdir("..")

     data = json.load(fo)
     host = data['router0']['HostAgent']
     serial0 = data['router0']['serial0']
     xr_mgmt_ip = data['router0']['xr_mgmt_ip']
     
     if spirent_topo.upper() == 'Y':
       spi_gui_ip = data['tgn_gui']['SimLocalIp']
       spi_gui_port = data['tgn_gui']['redir3389']
     prPurple("Connecting to " +str(host)+":"+str(serial0))

     command_console = "telnet -l cisco "+str(host)+" "+str(serial0)

     command = "sshpass -p cisco123  ssh -x -J "+str(host)+" cisco@"+str(xr_mgmt_ip)
     
     child = pexpect.spawn(command,timeout=None,ignore_sighup=True)
     time.sleep(1)
     child.sendline("\r\n");
     child.expect(['CPU0:["-z]*#'],timeout=300)
     prPurple("Setting up routes")
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
"""
     if platform == "1":
       intf_config="""
interface FourHundredGigE0/0/0/0
 ipv4 address 10.0.0.1 255.255.255.0
 no shut
!
interface FourHundredGigE0/0/0/1
 ipv4 address 20.0.0.1 255.255.255.0
 no shut
!
"""
     if platform == "2":
       intf_config="""
interface HundredGigE0/0/0/0
 ipv4 address 10.0.0.1 255.255.255.0
 no shut
!
interface HundredGigE0/0/0/1
 ipv4 address 20.0.0.1 255.255.255.0
 no shut
!
"""

     if platform == "5":
       intf_config="""
interface HundredGigE0/0/0/0
 ipv4 address 10.0.0.1 255.255.255.0
 no shut
!
interface HundredGigE0/0/0/1
 ipv4 address 20.0.0.1 255.255.255.0
 no shut
!
"""
     cmd = cmd + intf_config
     child.sendline(cmd)
     time.sleep(3)
     child.sendline('commit')
     child.sendline('end')
     #child.sendline("run ip netns exec xrnns bash")
     child.sendline("run")
     #child.sendline("dhclient eth-mgmt")
     time.sleep(1)
     child.sendline("route add -host "+MYADS+" gw 192.168.122.1 eth-mgmt")
     #pdb.set_trace()
     #child.sendline("setenforce 0")
     prPurple("Setting up nobackup mount")
     
     if platform == "3":
         mount_nb_xrv9k(child)
     else:
         child.sendline("mkdir /nb")
         mount_nb_sf(child)
     time.sleep(3)
     child.sendline('\r\n')
     child.sendline('\r\n')
     child.sendline('\r\n')

     try:
      while not child.expect(r'.+', timeout=1):
       flushedStuff += str(child.match.group(0))
     except:
       pass

     child.sendline('exit')
     time.sleep(2)
     child.sendline('show run interface MgmtEth 0/RP0/CPU0/0')
     child.sendline('exit')
     child.sendline('\r\n')
     prGreen("Sim Is UP , login using below command")
     prGreen("Console "+command_console)
     prGreen("MGMT "+command)
     prGreen("To Disable Selinux please use below command and reboot")
     prGreen("run grub-editenv /boot/efi/EFI/BOOT/grubenv set slx_dev=1")
     prRed("If nobackup doesn't mount please use below command")
     prGreen("sshfs "+user+"@"+MYADS+":/nobackup/"+user+" /nb -o reconnect,ServerAliveInterval=15,ServerAliveCountMax=3")
     if spirent_topo.upper() == 'Y':
       prGreen("Spirent RD Details "+spi_gui_ip+":"+str(spi_gui_port))
       prGreen("Spirent user-id vxr-ixia-pc\\vxr-ixia Password <blank> ")
       prGreen("Connections 1/1<-------------> HUndredGigE 0/0/0/0 , 1/2 <--------------> HUndredGigE 0/0/0/1")
     child.sendline('^]')
     child.sendline('q')
     child.sendline('\r\n')
     child.sendline('\r\n')
     child.close()
     start_time = int(datetime.now().strftime('%s'))
sim_status_fail = ["unknown","not running","aborted","ended"]
sim_status_run = ["running"]
def checkSim(takeUserInput):
     command = "/auto/vxr/pyvxr/latest/vxr.py status"
     out =""
     try:
       child1 = pexpect.spawn(command,timeout=None)
       out = child1.expect(['\nDidn\'t find a valid','vxr-','rch-'],timeout=300)
     except KeyboardInterrupt:
         prLightGray("\nInterrupted")
         sys.exit(0)
     except:
          prLightGray("\nSim not found.Starting again")
          if(takeUserInput == True):
              getUserInputs()
          BootSpitfireSim()
     else:
       if out == 1 or out == 2:
        status = child1.read()
        if out == 1:
            curr_status = (b'{"vxr-'+status)
        if out == 2:
            curr_status = (b'{"rch-'+status)
        decoded_string = curr_status.decode("utf-8")
        status = list(json.loads(decoded_string).values())

        #if status in status.decode("utf-8") or 'unknown' in status.decode("utf-8") or 'not running' in status.decode("utf-8"):
        if status[0] in sim_status_fail:
          prLightGray("\nSim ended.Starting again")
          if(takeUserInput == True):
              getUserInputs()
          BootSpitfireSim()
        elif status[0] in sim_status_run:
          loadUserInput(takeUserInput)
          curr_time = int(datetime.now().strftime('%s'))
          duration = curr_time - start_time
          hours = divmod(duration,3600)[0]
          mins = int(divmod(duration,3600)[1]/60)
          print("Sim running in current ws for "+str(hours)+" hours "+str(mins)+" mins.",end ='\r')
          if (takeUserInput == True):
            relaunch = input("Kill Current Simulation and launch new Y/N?   ")
            new_relaunch = input("Relaunch in new path Y/N?   ")
            if (relaunch == "Y"):
              getUserInputs()
              BootSpitfireSim()
            if (new_relaunch == "Y"):
                global new_sim_path
                new_sim_path = input("Please provide new sim path   ")
                getUserInputs()
                BootSpitfireSim()
            else :
              #child = pexpect.spawn('/bin/sh -c "/auto/vxr/pyvxr/latest/vxr.py ports > ports.json"')
              #time.sleep(10)
              command="/auto/vxr/pyvxr/latest/vxr.py ports > ports.json"
              process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
              process.wait()
              fo = open('ports.json')
              data = json.load(fo)
              host = data['router0']['HostAgent']
              serial0 = data['router0']['serial0']
              xr_mgmt_ip = data['router0']['xr_mgmt_ip']
              command = "sshpass -p cisco123  ssh -J "+str(host)+" cisco@"+str(xr_mgmt_ip)
              prPurple("Connect to existing Sim using console telnet " +str(host)+" "+str(serial0))
              prPurple("Connect to existing Sim using mgmt  "+command)
              prGreen("To Disable Selinux please use below command and reboot")
              prGreen("run grub-editenv /boot/efi/EFI/BOOT/grubenv set slx_dev=1")
              #sys.exit(0)


       if out == 0:
          prLightGray("VXR Sim not found.Starting again")
          if(takeUserInput == True):
              getUserInputs()
          BootSpitfireSim()

def CheckAndUpgradeWS():
    global ws_upd_notified
    global branch
    global auto_upd
    d1 = os.popen("git log -1 --format=%cd")
    d1str=d1.read()
    d1 = datetime.strptime(d1str,"%a %b %d %H:%M:%S %Y %z\n")
    d2 = datetime.now(timezone.utc)
    if(auto_upd == 'Y' and (d2-d1).days >= 6 and ws_upd_notified=="N"):
     ws_upd_notified="Y"
     process = subprocess.Popen("echo "'WS will auto upgrade in 1 day ' " | mail -s 'Upgrade Scheduled' "+user+"@cisco.com",shell=True)
     process.wait()
    if(auto_upd == 'Y' and (d2-d1).days >= 7):
        prRed("Current WS EFR is " +str((d2-d1).days)+" days old upgrading")
        loadUserInput(False)
        prGreen("Collecting diff and storing to TFTP\n");
        command="git diff > $TFTP/"+(d2.strftime("%m_%d_%Y")+".diff")
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        process.wait()
        command="/auto/vxr/pyvxr/latest/vxr.py stop"
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        process.wait()
        process = subprocess.Popen("lcleanup --killprocs; lcleanup --unmount; lcleanup --mqueues; lcleanup --deletews", shell=True, stdout=subprocess.PIPE, executable='/bin/bash')
        process.wait()
        os.chdir("..")
        pullWorkSpaceAndBuild(platform,branch)
        #sys.exit(0)




def main():
     prLightGray("Checking for running instance....")
     # CheckAndUpgradeWS()
     checkSim(True)
     while True:
         time.sleep(60)
         CheckAndUpgradeWS()
         checkSim(False)

if __name__ == '__main__':
    main()
