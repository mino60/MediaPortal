﻿#	-*-	coding:	utf-8	-*-

from imports import *

class MTVdeLink:

	def __init__(self, session):
		print "MTVdeLink:"
		self.session = session
		self._callback = None
		self.title = ''
		self.imgurl = ''

	def getLink(self, cb_play, cb_err, title, token, imgurl):
		self._callback = cb_play
		self.title = title
		self.imgurl = imgurl

		self.artist = ''
		p = title.find(' - ')
		if p > 0:
			self.artist = title[:p].strip()
			self.title = title[p+3:].strip()

		data = ''
		url = "http://api.mtvnn.com/v2/mrss?uri=mgid:sensei:video:mtvnn.com:music_video-%s-DE" % token
		try:
			data = urlopen2(url).read()
		except (URLError, HTTPException, socket.error), err:
			printl(err,self,"E")

		rtmpurl = re.search("<media:content.*?url='(.*?)'>", data)
		if rtmpurl:
			try:
				data = urlopen2(rtmpurl.group(1)).read()
			except (URLError, HTTPException, socket.error), err:
				printl(err,self,"E")

		rtmplink = re.findall('<src>(rtmp.*?)</src>', data)
		if rtmplink:
			videourl = rtmplink[-1] + ' swfUrl=http://player.mtvnn.com/g2/g2player_2.1.4.swf swfVfy=1'
		else:
			videourl = None

		self._callback(self.title, videourl, imgurl=self.imgurl, artist=self.artist)