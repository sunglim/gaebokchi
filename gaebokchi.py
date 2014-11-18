#!/usr/bin/env python

import json
import os, sys, stat
import shutil
from subprocess import PIPE, Popen
import sys
import time
import optparse
import getpass

# where tar.gz exist
SERVER_IP = '156.147.61.24'
ACCOUNT_WHOAMI = 'sungguk.lim'

CURRENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
STARFISH_TOP_DIR = os.path.join(CURRENT_DIR, 'ccc_magic')
HYBRIDTV_DIR = os.path.join(STARFISH_TOP_DIR, 'meta-lg-webos', 'meta-starfish', 'recipes-binaries', 'hybridtv')

PATCH_LIST = ['hybridtv-atsc_m14tv.bb', 'hybridtv-atsc_h15.bb', 'hybridtv-atsc_lm15u.bb',
              'hybridtv-dvb_m14tv.bb', 'hybridtv-dvb_h15.bb', 'hybridtv-dvb_lm15u.bb',
              'hybridtv-arib_m14tv.bb', 'hybridtv-arib_h15.bb', 'hybridtv-arib_lm15u.bb']

def RemoveStarfishDir():
  if os.path.exists(STARFISH_TOP_DIR):
    print '# Remove Old directory %s,' % STARFISH_TOP_DIR
    shutil.rmtree(STARFISH_TOP_DIR)

def CloneStarfish(branch_name):
  """
  Get lastest starfish, and checkout inserted branch, and run MCF command.
  """
  print "## Clone Starfish"
  os.chdir(CURRENT_DIR)
  print "run clone"
  Popen(['git', 'clone', 'ssh://polar.lge.com:29438/starfish/build-starfish.git', 'ccc_magic'], stdout = PIPE).communicate()
  os.chdir(STARFISH_TOP_DIR)
  print "run checkout"
  Popen(['git', 'checkout', branch_name], stdout = PIPE).communicate()
  Popen(['./mcf', '-b', '16', '-p', '16', 'm14tv', '--premirror=file:///starfish/downloads'], stdout = PIPE).communicate()

def GetSubmisison():
  os.chdir(HYBRIDTV_DIR)
  file = open('hybridtv_git_log.txt', 'rw')
  content = file.readline()
  submission = content[content.index('/') + 1:content.index(')')]
  if submission.isdigit():
    return submission
  print "WRONG SUBMISSION---------"
  sys.exit(0)

def DownloadCheckSum(serverip):
  os.chdir(HYBRIDTV_DIR)
  Popen(['wget', 'ftp://%s/lg1311/%s/hybridtv_git_log.txt' % (serverip, ACCOUNT_WHOAMI)], stdout = PIPE).communicate()
  submission = GetSubmisison()
  Popen(['wget', 'ftp://%s/lg1311/%s/hybridtv*%s-checksum.txt' % (serverip, ACCOUNT_WHOAMI, submission)], stdout = PIPE).communicate()
  Popen(['wget', 'ftp://%s/lg1210/%s/hybridtv*%s-checksum.txt' % (serverip, ACCOUNT_WHOAMI, submission)], stdout = PIPE).communicate()
  Popen(['wget', 'ftp://%s/lm15u/%s/hybridtv*%s-checksum.txt' % (serverip, ACCOUNT_WHOAMI, submission)], stdout = PIPE).communicate()

def ReplaceKey(bb_file, checksum_file):
  os.chdir(HYBRIDTV_DIR)
  MD5SUM_START = 'SRC_URI[md5sum] = "'
  SHA256SUM_START = 'SRC_URI[sha256sum] = "'
  file = open(bb_file, 'rw')
  content = file.read()
  file.close()
  start = content.find(MD5SUM_START) + len(MD5SUM_START)
  end = content.find('\n', start) - 1
  old_md5sum = content[start:end]

  start = content.find(SHA256SUM_START) + len(SHA256SUM_START)
  end = content.find('\n', start) - 1
  old_sha256sum = content[start:end]
  
  checksum = open(checksum_file, 'r')
  checksum_content = checksum.read()
  CHECKSUM_MD5SUM_START = "[md5sum]\n"
  CHECKSUM_SHA256SUM_START = "[sha256sum]\n"
  checksum_start = checksum_content.find(CHECKSUM_MD5SUM_START) + len(CHECKSUM_MD5SUM_START)
  checksum_end = checksum_content.find(' ', checksum_start)
  new_md5sum = checksum_content[checksum_start:checksum_end]

  checksum_start = checksum_content.find(CHECKSUM_SHA256SUM_START) + len(CHECKSUM_SHA256SUM_START)
  checksum_end = checksum_content.find(' ', checksum_start)
  new_sha256sum = checksum_content[checksum_start:checksum_end]

  print "          " + bb_file + " : " + checksum_file
  print "OLD KEY : " + old_md5sum + " : " + old_sha256sum
  print "NEW KEY : " + new_md5sum + " : " + new_sha256sum

  file = open(bb_file, 'rw+')
  content = content.replace(old_md5sum, new_md5sum)
  content = content.replace(old_sha256sum, new_sha256sum)
  file.write(content)
  file.close()

def IncreaseInc():
  os.chdir(HYBRIDTV_DIR)
  INC_START = 'WEBOS_VERSION = "1.0.0-'
  INC_END = '"'
  file = open('hybridtv.inc', 'r')
  content = file.read()
  file.close()
  start = content.find(INC_START) + len(INC_START)
  end = content.find(INC_END, start)
  oldsumission = content[start:end]
  content = content.replace(oldsumission, GetSubmisison())
  file = open('hybridtv.inc', 'rw+')
  file.write(content)
  file.close()
  print "Increase submission to " + GetSubmisison()

def GetCheckSumfileFromBbFile(bbfile):
  foo = bbfile.replace('_', '-')
  foo = foo.replace('.bb', '')
  foo = foo + '-1.0.0-' + GetSubmisison() + '-checksum.txt'
  return foo

def Patch():
  for bb_file in PATCH_LIST:
    ReplaceKey(bb_file, GetCheckSumfileFromBbFile(bb_file))
  IncreaseInc()

def DrawLogo():
  print "-----------------------------------------------"
  print " Gae Bok Chi, with a focusing on automation.\n"
  print "                         v0.0.1   < ')+++<"
  print "-----------------------------------------------"

def ReceiveSettings():
  print "--"

def TearDown():
  os.chdir(HYBRIDTV_DIR)
  for bb_file in PATCH_LIST:
    os.remove(GetCheckSumfileFromBbFile(bb_file))

def main(argv):
  DrawLogo()
  RemoveStarfishDir()
  CloneStarfish('@beehive4tv')
  DownloadCheckSum(SERVER_IP)
  Patch()
  TearDown()

if __name__ == '__main__':
  sys.exit(main(sys.argv))
