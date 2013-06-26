# -*- coding:utf-8 -*-

from imports import *
from Components.config import config
from urllib2 import Request, urlopen
from enigma import eTimer, eConsoleAppContainer, eBackgroundFileEraser
from Components.Slider import Slider
from os import path as os_path, readlink as os_readlink, system as os_system
from Tools import ASCIItranslit
from Plugins.Extensions.MediaPortal.resources.simpleplayer import SimplePlayer

class PlayRtmpMovie(Screen):
	skin = """
		<screen position="center,center" size="450,240" title="Caching..." >
			<widget source="label_filename" transparent="1" render="Label" zPosition="2" position="10,10" size="430,21" font="Regular;19" />
			<widget source="label_speed" transparent="1" render="Label" zPosition="2" position="10,60" size="430,21" font="Regular;19" />
			<widget source="label_timeleft" transparent="1" render="Label" zPosition="2" position="10,85" size="430,21" font="Regular;19" />
			<widget source="label_progress" transparent="1" render="Label" zPosition="2" position="10,110" size="430,21" font="Regular;19" />
			<widget name="activityslider" position="10,150" size="430,30" zPosition="3" transparent="0" />
			<widget name="key_red" position="10,200" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="key_green" position="155,200" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="key_blue" position="300,200" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/red.png" position="10,200" size="140,40" alphatest="on" />
			<ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/green.png" position="155,200" size="140,40" alphatest="on" />
			<ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/blue.png" position="300,200" size="140,40" alphatest="on" />
		</screen>"""

	def __init__(self, session, movieinfo, movietitle):
		self.skin = PlayRtmpMovie.skin
		Screen.__init__(self, session)

		self.url = movieinfo[0]
		self.filename = movieinfo[1]
		self.movietitle = movietitle
		self.movieinfo = movieinfo
		self.destination = config.mediaportal.storagepath.value
		#self.moviepath = self.destination + ASCIItranslit.legacyEncode(self.filename)
		self.moviepath = self.destination + ".rtmp_movie"
		
		self.streamactive = False
		self.isVisible = True

		self.container=eConsoleAppContainer()
		self.container.appClosed.append(self.copyfinished)
		self.container.stdoutAvail.append(self.progressUpdate)
		self.container.stderrAvail.append(self.progressUpdate)
		self.container.setCWD(self.destination)

		self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()

		self.BgFileEraser = eBackgroundFileEraser.getInstance()

		filesize = 0
		self.filesize = float(filesize) # in bytes

		self.dummyfilesize = False
		self.lastcmddata = None
		self.lastlocalsize = 0
		self.localsize = 0
		self.isplaying = False
		self.autoplaythreshold = config.mediaportal.autoplayThreshold.value

		self["key_green"] = Button(_("Play"))
		self["key_red"] = Button(_("Cancel"))
		self["key_blue"] = Button(_("Show/Hide"))

		self["label_filename"] = StaticText("File: %s" % (self.filename))
		self["label_progress"] = StaticText("Progress: N/A")
		self["label_speed"] = StaticText("Speed: N/A")
		self["label_timeleft"] = StaticText("Time left: N/A")

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"cancel": self.exit,
			"ok": self.okbuttonClick,
			"red": self.exit,
			"green": self.playfile,
			"blue": self.visibility
		}, -1)

		self.StatusTimer = eTimer()
		self.StatusTimer.callback.append(self.UpdateStatus)

		self.activityslider = Slider(0, 100)
		self["activityslider"] = self.activityslider

		self.onFirstExecBegin.append(self.firstExecBegin)

	def firstExecBegin(self):
		self.progressperc = 0
		if not fileExists("/usr/bin/rtmpdump"):
			message = self.session.open(MessageBox, _("RTMPDump is required for playback of this stream, please install it first."), MessageBox.TYPE_INFO, timeout=10)
			self.exit()
			
		if not self.checkStoragePath():
			self.exit()
			
		self.copyfile()

	def okbuttonClick(self):
		if self.isVisible == False:
			self.visibility()

	def checkStoragePath(self):
		tmppath = config.mediaportal.storagepath.value
		if tmppath != "/tmp" and tmppath != "/media/ba":
			if os_path.islink(tmppath):
				tmppath = os_readlink(tmppath)
			loopcount = 0
			while not os_path.ismount(tmppath):
				loopcount += 1
				tmppath = os_path.dirname(tmppath)
				if tmppath == "/" or tmppath == "" or loopcount > 50:
					self.session.open(MessageBox, _("Error: Can not create cache-folders inside flash memory. Check your Cache-Folder Settings!"), type=MessageBox.TYPE_INFO, timeout=20)
					return False

		os_system("mkdir -p "+config.mediaportal.storagepath.value)
		if not os_path.exists(config.mediaportal.storagepath.value):
			self.session.open(MessageBox, _("Error: No write permission to create cache-folders. Check your Cache-Folder Settings!"), type=MessageBox.TYPE_INFO, timeout=20)
			return False
		else:
			return True
		
	def UpdateStatus(self):
		#print "UpdateStatus:"
		if fileExists(self.moviepath, 'r'):
			#print "file exists"
			self.localsize = os_path.getsize(self.moviepath)
		else:
			self.localsize = 0

		if self.filesize > 0 and not self.dummyfilesize:
			self.progressperc = int(float(self.localsize) / self.filesize * 100.0 + 0.5)
			#print "psz: ",self.progressperc

		if int(self.progressperc) > 0:
			self["activityslider"].setValue(self.progressperc)

		if self.lastlocalsize != 0:
			transferspeed = int(float(self.localsize - self.lastlocalsize) / 1024.0 / 5 + 0.5)
			kbytesleft = int(float(self.filesize - self.localsize) / 1024.0 + 0.5)
			if kbytesleft < 0:
				kbytesleft = 0
			if transferspeed > 0:
				timeleft = round(float(kbytesleft) / transferspeed / 60.0, 1)
			else:
				timeleft = 0
		else:
			transferspeed = 0
			kbytesleft = 0
			timeleft = 0

		self.lastlocalsize = self.localsize

		self["label_speed"].setText("Speed: " + str(transferspeed) + " KBit/s")
		self["label_progress"].setText("Progress: " + str(int(float(self.localsize) / 1024.0 / 1024.0 + 0.5)) + "MB of " + str(int(float(self.filesize) / 1024.0 / 1024.0 + 0.5)) + "MB (" + str(self.progressperc) + "%)")
		self["label_timeleft"].setText("Time left: " + str(timeleft) + " Minutes")
		#print "sz: ",self.localsize," lsz: ", self.lastlocalsize, " dsz: ", self.dummyfilesize, " fsz: ",self.filesize
		self.StatusTimer.start(5000, True)
		if self.progressperc >= self.autoplaythreshold and not self.isplaying:
			self.playfile()

	def copyfile(self):
		#print "copyfile:"
		if self.url[0:4] == "rtmp":
			cmd = "rtmpdump -r '%s' -o '%s'" % (self.url, self.moviepath)
		else:
			self.session.openWithCallback(self.exit, MessageBox, _("This stream can not get saved on HDD\nProtocol %s not supported :(") % self.url[0:5], MessageBox.TYPE_ERROR)
			return

		if fileExists(self.moviepath, 'r'):
			self.localsize = os_path.getsize(self.moviepath)
			if self.localsize > 0 and self.localsize >= self.filesize:
				cmd = "echo File already downloaded! Skipping download ..."
			elif self.localsize == 0:
				self.BgFileEraser.erase(self.moviepath)

		self.StatusTimer.start(1000, True)
		self.streamactive = True

		print "[PlayRtmp] execute command: " + cmd
		self.container.execute(cmd)

	def progressUpdate(self, data):
		self.lastcmddata = data
		if data.endswith('%)'):
			startpos = data.rfind("sec (")+5
			if startpos and startpos != -1:
				self.progressperc = int(float(data[startpos:-4])+0.5)

				if self.lastlocalsize > 0 and self.progressperc > 0:
					self.filesize = int(float(self.lastlocalsize/self.progressperc)*100+0.5)
					self.dummyfilesize = True

	def copyfinished(self,retval):
		#print "copyfinished:"
		self.container.kill()
		self.streamactive = False
		self.filesize = self.localsize
		self.progressperc = 100
		self.UpdateStatus()
		#self["label_progress"].setText("Progress: 100%")
		#self["activityslider"].setValue(100)
		if not self.isplaying:
			self.playfile()

	def playfile(self):
		if self.lastlocalsize > 0:
			self.isplaying = True
			self.StatusTimer.stop()
			"""
			sref = eServiceReference(0x1001, 0, self.moviepath)
			sref.setName(self.movietitle)
			self.session.openWithCallback(self.MoviePlayerCallback, MoviePlayer, sref)
			"""
			self.session.openWithCallback(self.MoviePlayerCallback, PlayRtmpPlayer, [self.movietitle, self.moviepath])
		else:
			self.session.openWithCallback(self.exit, MessageBox, _("Error downloading file:\n%s") % self.lastcmddata, MessageBox.TYPE_ERROR)

	def MoviePlayerCallback(self, response=None):
		#print "movieplayercallback:"
		if self.isVisible == False:
			self.visibility()
		self.filesize = self.localsize
		self.UpdateStatus()

	def visibility(self):
		if self.isVisible == True:
			self.isVisible = False
			self.hide()
		else:
			self.isVisible = True
			self.show()

	def exit(self, retval=None):
		if self.isVisible == False:
			self.visibility()
			return

		self.container.kill()
		self.BgFileEraser.erase(self.moviepath)

		self.StatusTimer.stop()
		self.session.nav.playService(self.oldService)
		self.close()
		
class PlayRtmpPlayer(SimplePlayer):

	def __init__(self, session, playList):
		print "PlayRtmpPlayer:"

		SimplePlayer.__init__(self, session, playList)

	def getVideo(self):
		title = self.playList[self.playIdx][0]
		url = self.playList[self.playIdx][1]
		self.playStream(title, url)

	def openPlaylist(self):
		pass

	def playPrevStream(self):
		pass

	def playNextStream(self):
		pass
