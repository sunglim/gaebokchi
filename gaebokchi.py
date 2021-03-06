#!/usr/bin/env python

import os, sys
import shutil
from subprocess import PIPE, Popen
import sys
import getpass
import urllib2

ACCOUNT_WHOAMI = getpass.getuser()

CURRENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
STARFISH_TOP_DIR = os.path.join(CURRENT_DIR, 'ccc_magic')
HOOK_DIR = os.path.join(STARFISH_TOP_DIR, 'meta-lg-webos', '.git', 'hooks')
HYBRIDTV_DIR = os.path.join(STARFISH_TOP_DIR, 'meta-lg-webos', 'meta-starfish',
                            'recipes-binaries', 'hybridtv')

PATCH_LIST = ['hybridtv-atsc_m14tv.bb', 'hybridtv-atsc_h15.bb',
              'hybridtv-atsc_lm15u.bb', 'hybridtv-dvb_m14tv.bb',
              'hybridtv-dvb_h15.bb', 'hybridtv-dvb_lm15u.bb',
              'hybridtv-arib_m14tv.bb', 'hybridtv-arib_h15.bb',
              'hybridtv-arib_lm15u.bb']

HOOK_SCRIPT = '''
#!/bin/sh
unset GREP_OPTIONS

CHANGE_ID_AFTER="Bug|Issue"
MSG="$1"

# Check for, and add if missing, a unique Change-Id
#
add_ChangeId() {
	clean_message=`sed -e '
		/^diff --git .*/{
			s///
			q
		}
		/^Signed-off-by:/d
		/^#/d
	' "$MSG" | git stripspace`
	if test -z "$clean_message"
	then
		return
	fi

	if test "false" = "`git config --bool --get gerrit.createChangeId`"
	then
		return
	fi

	# Does Change-Id: already exist? if so, exit (no change).
	if grep -i '^Change-Id:' "$MSG" >/dev/null
	then
		return
	fi

	id=`_gen_ChangeId`
	T="$MSG.tmp.$$"
	AWK=awk
	if [ -x /usr/xpg4/bin/awk ]; then
		# Solaris AWK is just too broken
		AWK=/usr/xpg4/bin/awk
	fi
	$AWK '
	BEGIN {
		# while we start with the assumption that textLine+
		# is a footer, the first block is not.
		isFooter = 0
		footerComment = 0
		blankLines = 0
	}

	# Skip lines starting with "#" without any spaces before it.
	/^#/ { next }

	/^diff --git / {
		blankLines = 0
		while (getline) { }
		next
	}

	# Count blank lines outside footer comments
	/^$/ && (footerComment == 0) {
		blankLines++
		next
	}

	# Catch footer comment
	/^\[[a-zA-Z0-9-]+:/ && (isFooter == 1) {
		footerComment = 1
	}

	/]$/ && (footerComment == 1) {
		footerComment = 2
	}

	# We have a non-blank line after blank lines. Handle this.
	(blankLines > 0) {
		print lines
		for (i = 0; i < blankLines; i++) {
			print ""
		}

		lines = ""
		blankLines = 0
		isFooter = 1
		footerComment = 0
	}

	# Detect that the current block is not the footer
	(footerComment == 0) && (!/^\[?[a-zA-Z0-9-]+:/ || /^[a-zA-Z0-9-]+:\/\//) {
		isFooter = 0
	}

	{
		# We need this information about the current last comment line
		if (footerComment == 2) {
			footerComment = 0
		}
		if (lines != "") {
			lines = lines "\\n";
		}
		lines = lines $0
	}

	END {
		unprinted = 1
		if (isFooter == 0) {
			print lines "\\n"
			lines = ""
		}
		changeIdAfter = "^(" tolower("'"$CHANGE_ID_AFTER"'") "):"
		numlines = split(lines, footer, "\\n")
		for (line = 1; line <= numlines; line++) {
			if (unprinted && match(tolower(footer[line]), changeIdAfter) != 1) {
				unprinted = 0
				print "Change-Id: I'"$id"'"
			}
			print footer[line]
		}
		if (unprinted) {
			print "Change-Id: I'"$id"'"
		}
	}' "$MSG" > "$T" && mv "$T" "$MSG" || rm -f "$T"
}
_gen_ChangeIdInput() {
	echo "tree `git write-tree`"
	if parent=`git rev-parse "HEAD^0" 2>/dev/null`
	then
		echo "parent $parent"
	fi
	echo "author `git var GIT_AUTHOR_IDENT`"
	echo "committer `git var GIT_COMMITTER_IDENT`"
	echo
	printf '%s' "$clean_message"
}
_gen_ChangeId() {
	_gen_ChangeIdInput |
	git hash-object -t commit --stdin
}


add_ChangeId
'''

COMMIT_MSG = """hybridtv={submission}

:Release Notes:
Hybridtv includes HbbTV,MHP,MHEG,GINGA,OHTV,BML,HybridCast
// TODO: Add release note

:Detailed Notes:
submissions/{pre-submission}..submissions/{submission}
{detail_notes}

:Testing Performed:
MiniBAT: see // TODO

:QA Notes:

:Issues Addressed:
[BHV-????] CCC: hybridtv=
// TODO: Add issue links

{signed-off-by}
"""

def RemoveStarfishDir():
  if os.path.exists(STARFISH_TOP_DIR):
    print '# Remove Old directory %s,' % STARFISH_TOP_DIR
    shutil.rmtree(STARFISH_TOP_DIR)

def CloneStarfish(branch_name):
  """
  Git clone starfish. and checkout |branch_name|, and run MCF command.
  """
  print "## Clone Starfish"
  os.chdir(CURRENT_DIR)
  print "run clone"
  Popen(['git', 'clone', 'ssh://polar.lge.com:29438/starfish/build-starfish.git', 'ccc_magic'], stdout = PIPE).communicate()
  os.chdir(STARFISH_TOP_DIR)
  print "run checkout"
  Popen(['git', 'checkout', branch_name], stdout = PIPE).communicate()
  Popen(['./mcf', '-b', '16', '-p', '16', 'm14tv', '--premirror=_fd:///starfish/downloads'], stdout = PIPE).communicate()

def GetSubmisison():
  html = urllib2.urlopen("http://webos.lge.com/binary/starfish-beehive/m14tv/official/hybridtv-dvb/?C=M;O=A").read()
  START_TAG = '<a href="hybridtv-dvb-m14tv-tc1-1.0.0-'
  start = html.rfind('<a href="hybridtv-dvb-m14tv-tc1-1.0.0-') + len(START_TAG)
  end = html.find('.tar.bz2', start)
  GetSubmisison.get = html[start:end]

GetSubmisison.get = ''

def getTvbinUrlFromBb(bb__fd, submission):
  url = 'http://tvbin.lge.com:8080/p/hybridtv-{type}/starfish-beehive/{chip}/1.0.0-{submission}/tc1/detail/'
  # unhappy this code. find better way
  if 'atsc' in bb__fd:
    url = url.replace('{type}', 'atsc')
  elif 'dvb' in bb__fd:
    url = url.replace('{type}', 'dvb')
  elif 'arib' in bb__fd:
    url = url.replace('{type}', 'arib')

  if 'm14tv' in bb__fd:
    url = url.replace('{chip}', 'm14tv')
  elif 'lm15u' in bb__fd:
    url = url.replace('{chip}', 'lm15u')
  elif 'h15' in bb__fd:
    url = url.replace('{chip}', 'h15')
  url = url.replace('{submission}', submission)
  return url

def ReplaceKeyFromWeb(bb__fd, submission):
  """ Get hash key from tvbin site and patch """
  os.chdir(HYBRIDTV_DIR)
  MD5SUM_START = 'SRC_URI[md5sum] = "'
  SHA256SUM_START = 'SRC_URI[sha256sum] = "'
  _fd = open(bb__fd, 'rw')
  content = _fd.read()
  _fd.close()
  start = content.find(MD5SUM_START) + len(MD5SUM_START)
  end = content.find('\n', start) - 1
  old_md5sum = content[start:end]

  start = content.find(SHA256SUM_START) + len(SHA256SUM_START)
  end = content.find('\n', start) - 1
  old_sha256sum = content[start:end]
  
  tvbin_content = urllib2.urlopen(getTvbinUrlFromBb(bb__fd, submission)).read()
  START_MD5_TAG = 'Md5sum: '
  START_SHA256_TAG = 'Sha256sum: '
  END_TAG = '</li>'

  start = tvbin_content.find(START_MD5_TAG) + len(START_MD5_TAG)
  end = tvbin_content.find(END_TAG, start)
  new_md5sum = tvbin_content[start:end]

  start = tvbin_content.find(START_SHA256_TAG) + len(START_SHA256_TAG)
  end = tvbin_content.find(END_TAG, start)
  new_sha256sum = tvbin_content[start:end]

  print "\n        " + bb__fd + " : " + getTvbinUrlFromBb(bb__fd, submission)
  print "OLD KEY : " + old_md5sum + " : " + old_sha256sum
  print "NEW KEY : " + new_md5sum + " : " + new_sha256sum

  _fd = open(bb__fd, 'rw+')
  content = content.replace(old_md5sum, new_md5sum)
  content = content.replace(old_sha256sum, new_sha256sum)
  _fd.write(content)
  _fd.close()

def IncreaseInc():
  os.chdir(HYBRIDTV_DIR)
  INC_START = 'WEBOS_VERSION = "1.0.0-'
  INC_END = '"'
  _fd = open('hybridtv.inc', 'r')
  content = _fd.read()
  _fd.close()
  start = content.find(INC_START) + len(INC_START)
  end = content.find(INC_END, start)
  oldsumission = content[start:end]
  content = content.replace(oldsumission, GetSubmisison.get)
  _fd = open('hybridtv.inc', 'rw+')
  _fd.write(content)
  _fd.close()
  print "Increase submission to " + GetSubmisison.get

def Patch():
  for bb__fd in PATCH_LIST:
    ReplaceKeyFromWeb(bb__fd, GetSubmisison.get)
  IncreaseInc()

def DrawLogo():
  """ Draw Logo and load env """
  print "-----------------------------------------------"
  print " Gae Bok Chi, with a focusing on automation.\n"
  print "                         v0.0.2   < ')+++<"
  print "-----------------------------------------------"
  GetSubmisison()
  print "Submission : " + GetSubmisison.get

def Commit():
  """ Git commit and push to Gerrit """

  # commit-msg _fd is necessary to automatically insert Change-Id.
  os.chdir(HOOK_DIR)
  msg_fd = open('commit-msg', 'wt')
  os.chmod('commit-msg', 0755)
  msg_fd.write(HOOK_SCRIPT)
  msg_fd.close()

  os.chdir(HYBRIDTV_DIR)
  msg = COMMIT_MSG.replace('{submission}', GetSubmisison.get)

  # Signed-off-by: _fdd is necessary. to automatically make Change-Id.
  msg = msg.replace('{signed-off-by}', 'Signed-off-by: ' + ACCOUNT_WHOAMI + ' <' + ACCOUNT_WHOAMI + '@lge.com>')
  _fd = open('COMMIT_MSG', 'w+')
  _fd.write(msg)
  _fd.close()
  Popen(['git', 'commit', '-aF', 'COMMIT_MSG'], stdout = PIPE).communicate()
  Popen(['git', 'push', 'origin', 'HEAD:refs/for/@badlands'], stdout = PIPE).communicate()

def main():
  DrawLogo()
  RemoveStarfishDir()
  CloneStarfish('@badlands')
  Patch()
  Commit()

if __name__ == '__main__':
  sys.exit(main())
