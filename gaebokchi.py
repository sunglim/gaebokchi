#!/usr/bin/env python

import json
import os, sys, stat
import shutil
from subprocess import PIPE, Popen
import sys
import time
import optparse
import getpass
import urllib2

# where tar.gz exist
SERVER_IP = '156.147.61.35'
ACCOUNT_WHOAMI = getpass.getuser()

CURRENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
STARFISH_TOP_DIR = os.path.join(CURRENT_DIR, 'ccc_magic')
HYBRIDTV_DIR = os.path.join(STARFISH_TOP_DIR, 'meta-lg-webos', 'meta-starfish', 'recipes-binaries', 'hybridtv')

PATCH_LIST = ['hybridtv-atsc_m14tv.bb', 'hybridtv-atsc_h15.bb', 'hybridtv-atsc_lm15u.bb',
              'hybridtv-dvb_m14tv.bb', 'hybridtv-dvb_h15.bb', 'hybridtv-dvb_lm15u.bb',
              'hybridtv-arib_m14tv.bb', 'hybridtv-arib_h15.bb', 'hybridtv-arib_lm15u.bb']

COMMIT_MSG = """hybridtv={submission}

:Release Notes:
Hybridtv includes HbbTV,MHP,MHEG,GINGA,OHTV,BML,HybridCast
// TODO: Add release note

:Detailed Notes:
submissions/{pre-submission}..submissions/{submission}
{detail_notes}

:Testing Performed:
MiniBAT: see // TODO

:Issues Addressed:
[BHV-17627] CCC: hybridtv=34
// TODO: Add issue links
"""

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
  html = urllib2.urlopen("http://webos.lge.com/binary/starfish-beehive/lm15u/official/hybridtv-dvb/").read()
  START_TAG = '<a href="hybridtv-dvb-lm15u-tc1-1.0.0-'
  start = html.rfind('<a href="hybridtv-dvb-lm15u-tc1-1.0.0-') + len(START_TAG)
  end = html.find('.tar.bz2', start)
  GetSubmisison.get = html[start:end]

GetSubmisison.get = ''

def DownloadCheckSum(serverip):
  os.chdir(HYBRIDTV_DIR)
  submission = GetSubmisison.get
  Popen(['wget', 'ftp://%s/lg1311/%s/hybridtv*%s-checksum.txt' % (serverip, ACCOUNT_WHOAMI, submission)], stdout = PIPE).communicate()
  Popen(['wget', 'ftp://%s/lg1210/%s/hybridtv*%s-checksum.txt' % (serverip, ACCOUNT_WHOAMI, submission)], stdout = PIPE).communicate()
  Popen(['wget', 'ftp://%s/lm15u/%s/hybridtv*%s-checksum.txt' % (serverip, ACCOUNT_WHOAMI, submission)], stdout = PIPE).communicate()

def getTvbinUrlFromBb(bb_file, submission):
  url = 'http://tvbin.lge.com:8080/p/hybridtv-{type}/starfish-beehive/{chip}/1.0.0-{submission}/tc1/detail/'
  # unhappy this code. find better way
  if 'atsc' in bb_file:
    url = url.replace('{type}', 'atsc')
  elif 'dvb' in bb_file:
    url = url.replace('{type}', 'dvb')
  elif 'arib' in bb_file:
    url = url.replace('{type}', 'arib')

  if 'm14tv' in bb_file:
    url = url.replace('{chip}', 'm14tv')
  elif 'lm15u' in bb_file:
    url = url.replace('{chip}', 'lm15u')
  elif 'h15' in bb_file:
    url = url.replace('{chip}', 'h15')
  url = url.replace('{submission}', submission)
  return url

def ReplaceKeyFromWeb(bb_file, submission):
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
  
  checksum_content = urllib2.urlopen(getTvbinUrlFromBb(bb_file, submission)).read()
  START_MD5_TAG = 'Md5sum: '
  START_SHA256_TAG = 'Sha256sum: '
  END_TAG = '</li>'

  checksum_start = checksum_content.find(START_MD5_TAG) + len(START_MD5_TAG)
  checksum_end = checksum_content.find(END_TAG, checksum_start)
  new_md5sum = checksum_content[checksum_start:checksum_end]

  checksum_start = checksum_content.find(START_SHA256_TAG) + len(START_SHA256_TAG)
  checksum_end = checksum_content.find(END_TAG, checksum_start)
  new_sha256sum = checksum_content[checksum_start:checksum_end]

  print "\n        " + bb_file + " : " + getTvbinUrlFromBb(bb_file, submission) 
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
  content = content.replace(oldsumission, GetSubmisison.get)
  file = open('hybridtv.inc', 'rw+')
  file.write(content)
  file.close()
  print "Increase submission to " + GetSubmisison.get

def Patch():
  for bb_file in PATCH_LIST:
    ReplaceKeyFromWeb(bb_file, GetSubmisison.get)
  IncreaseInc()

def DrawLogo():
  """ Draw Logo and set env """
  print "-----------------------------------------------"
  print " Gae Bok Chi, with a focusing on automation.\n"
  print "                         v0.0.1   < ')+++<"
  print "-----------------------------------------------"
  GetSubmisison()

def Commit():
  os.chdir(HYBRIDTV_DIR)
  msg = COMMIT_MSG.replace('{submission}', GetSubmisison.get)
  msg = msg.replace('{detail_notes}', GetSubmisison.get)
  file = open('COMMIT_MSG', 'w+')
  file.write(msg)
  file.close()

def main(argv):
  DrawLogo()
  RemoveStarfishDir()
  CloneStarfish('@beehive4tv')
  Patch()
  Commit()

  print '\n>> cd ccc_magic/meta-lg-webos/meta-starfish/recipes-binaries/hybridtv/'
  print '>> git commit -a'
  print '>> git push origin HEAD:refs/for/@beehive4tv'

if __name__ == '__main__':
  sys.exit(main(sys.argv))
