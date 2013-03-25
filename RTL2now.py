from imports import *
from Components.config import config
from PlayRtmpMovie import PlayRtmpMovie

def rtl2AuswahlListEntry(entry):
	return [entry,
		(eListboxPythonMultiContent.TYPE_TEXT, 20, 0, 900, 25, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, entry[0])
		]

def rtl2SerieListEntry(entry):
	return [entry,
		(eListboxPythonMultiContent.TYPE_TEXT, 20, 0, 900, 25, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, entry[0])
		]

class RTL2nowGenreScreen(Screen):
	
	def __init__(self, session):
		self.session = session
		path = "/usr/lib/enigma2/python/Plugins/Extensions/mediaportal/skins/%s/RTLnowGenreScreen.xml" % config.mediaportal.skin.value
		if not fileExists(path):
			path = "/usr/lib/enigma2/python/Plugins/Extensions/mediaportal/skins/original/RTLnowGenreScreen.xml"
		with open(path, "r") as f:
			self.skin = f.read()
			f.close()
			
		Screen.__init__(self, session)
		
		self["actions"]  = ActionMap(["OkCancelActions", "ShortcutActions", "WizardActions", "ColorActions", "SetupActions", "NumberActions", "MenuActions"], {
			"ok"    : self.keyOK,
			"cancel": self.keyCancel,
			"up" : self.keyUp,
			"down" : self.keyDown,
			"right" : self.keyRight,
			"left" : self.keyLeft
		}, -1)
		
		self['title'] = Label("RTL2NOW.de")
		self['name'] = Label("Genre Auswahl")
		self['handlung'] = Label("")
		self['Pic'] = Pixmap()

		self.genreliste = []
		self.keyLocked = True
		self.chooseMenuList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.chooseMenuList.l.setFont(0, gFont('mediaportal', 23))
		self.chooseMenuList.l.setItemHeight(25)
		self['List'] = self.chooseMenuList
		
		self.onLayoutFinish.append(self.loadPage)
		
	def loadPage(self):
		self.keyLocked = True
		url = "http://rtl2now.rtl2.de"
		getPage(url, agent=std_headers, headers={'Content-Type':'application/x-www-form-urlencoded'}).addCallback(self.loadPageData).addErrback(self.dataError)
		
	def loadPageData(self, data):
		rtl2FreeVideos = re.findall('<div class="seriennavi_free" style=""><a href="(.*?)".*?>FREE.*?</div>.*?<div style="" class="seriennavi_link">.*?">(.*?)</a>.*?</div>', data, re.S)
		if rtl2FreeVideos:
			self.genreliste = []
			for url, title in rtl2FreeVideos:
				url = "http://rtl2now.rtl2.de" + url
				self.genreliste.append((title, url))
			self.chooseMenuList.setList(map(rtl2AuswahlListEntry, self.genreliste))
			self.keyLocked = False
		
	def dataError(self, error):
		print error
		
	def keyOK(self):
		if self.keyLocked:
			return
		streamGenreLink = self['List'].getCurrent()[0][1]
		self.session.open(RTL2nowFilmeListeScreen, streamGenreLink)
		
	def keyLeft(self):
		if self.keyLocked:
			return
		self['List'].pageUp()
		
	def keyRight(self):
		if self.keyLocked:
			return
		self['List'].pageDown()
		
	def keyUp(self):
		if self.keyLocked:
			return
		self['List'].up()

	def keyDown(self):
		if self.keyLocked:
			return
		self['List'].down()

	def keyCancel(self):
		self.close()

class RTL2nowFilmeListeScreen(Screen):
	
	def __init__(self, session, streamGenreLink):
		self.session = session
		self.streamGenreLink = streamGenreLink
		path = "/usr/lib/enigma2/python/Plugins/Extensions/mediaportal/skins/%s/RTLnowFilmeScreen.xml" % config.mediaportal.skin.value
		if not fileExists(path):
			path = "/usr/lib/enigma2/python/Plugins/Extensions/mediaportal/skins/original/RTLnowFilmeScreen.xml"
		print path
		with open(path, "r") as f:
			self.skin = f.read()
			f.close()
			
		Screen.__init__(self, session)
		
		self["actions"]  = ActionMap(["OkCancelActions", "ShortcutActions", "WizardActions", "ColorActions", "SetupActions", "NumberActions", "MenuActions", "EPGSelectActions"], {
			"ok"    : self.keyOK,
			"cancel": self.keyCancel
		}, -1)

		self['title'] = Label("RTL2NOW.de")
		self['name'] = Label("Film Auswahl")

		self.keyLocked = True
		self.filmliste = []
		self.keckse = {}
		self.chooseMenuList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.chooseMenuList.l.setFont(0, gFont('mediaportal', 23))
		self.chooseMenuList.l.setItemHeight(25)
		self['List'] = self.chooseMenuList

		self.onLayoutFinish.append(self.loadPage)
		
	def loadPage(self):
		getPage(self.streamGenreLink, agent=std_headers, headers={'Content-Type':'application/x-www-form-urlencoded'}).addCallback(self.loadPageData).addErrback(self.dataError)
		
	def dataError(self, error):
		print error
		
	def loadPageData(self, data):
		allData = ""
		ajax_posts = []
		self.filmliste = []
		selects = re.compile('<select\s*?onchange.*?xajax_show_top_and_movies.*?\'(.*?)\'.*?\'(.*?)\'.*?\'(.*?)\'.*?\'(.*?)\'.*?\'(.*?)\'.*?>(.*?)</select>',re.DOTALL).search(data)
		if selects:
			tabSelects = "&xajaxargs[]="+selects.group(1)+"&xajaxargs[]="+selects.group(2)+"&xajaxargs[]="+selects.group(3)+"&xajaxargs[]="+selects.group(4)+"&xajaxargs[]="+selects.group(5)+"&xajax=show_top_and_movies&xajaxr="+str(time()).replace('.','')
			tabs = re.compile('<option.*?value=\'(\d)\'.*?>',re.DOTALL).findall(selects.group(6))
			for tab in tabs:
				ajax_posts.append(("xajaxargs[]="+tab+tabSelects)) 
				
		if len(ajax_posts) != 0:
			self.count = len(ajax_posts)
			print "pages:", self.count
			ds = defer.DeferredSemaphore(tokens=1)
			downloads = [ds.run(self.download,item).addCallback(self.get_series_more_pages).addErrback(self.dataError) for item in ajax_posts]
			finished = defer.DeferredList(downloads).addErrback(self.dataError)
		else:
			self.get_series_more_pages(data)

	def download(self, item):
		print item
		return getPage('http://rtl2now.rtl2.de/xajaxuri.php', method='POST', postdata=item, headers={'Content-Type':'application/x-www-form-urlencoded'})

	def get_series_more_pages(self, data):					
		folgen = re.findall('id="title_basic_.*?[0-9]"><a\shref="(.*?)"\stitle="(.*?)">.*?(kostenlos|Nur\s22\s-\s6h|Nur\s23\s-\s6h)</a>', data)
		if folgen:
			for (url,title, sperre) in folgen:
				print title
				url = "http://rtl2now.rtl2.de" + url.replace('amp;','')
				title = decodeHtml(title)
				lock = "free"
				if sperre == "Nur 22 - 6h":
					title = "gesperrt bis 22 Uhr: " + title
					lock = "22"
				if sperre == "Nur 23 - 6h":
					title = "gesperrt bis 23 Uhr: " + title
					lock = "23"
				self.filmliste.append((title, url, lock))
			self.chooseMenuList.setList(map(rtl2SerieListEntry, self.filmliste))
			self.keyLocked = False			

	def keyOK(self):
		if self.keyLocked:
			return
		self.streamName = self['List'].getCurrent()[0][0]
		self.pageurl = self['List'].getCurrent()[0][1]
		sperre = self['List'].getCurrent()[0][2]
		if sperre == "22":
			message = self.session.open(MessageBox, _("Dieses Video ist aus Jugendschutzgruenden momentan gesperrt und ist erst ab ca. 22 Uhr verfuegbar."), MessageBox.TYPE_INFO, timeout=5)
			return
		if sperre == "23":
			message = self.session.open(MessageBox, _("Dieses Video ist aus Jugendschutzgruenden momentan gesperrt und ist erst ab ca. 23 Uhr verfuegbar."), MessageBox.TYPE_INFO, timeout=5)
			return
		print self.pageurl
		getPage(self.pageurl, agent=std_headers, cookies=self.keckse, headers={'Content-Type':'application/x-www-form-urlencoded'}).addCallback(self.get_xml).addErrback(self.dataError)

	def get_xml(self, data):
		print "xml data"
		self.stream = re.findall("'playerdata': '(.*?)'", data, re.S)
		if self.stream:
			print self.stream[0].replace('amp;',''), self.keckse
			getPage(self.stream[0].replace('amp;',''), agent=std_headers, headers={'Content-Type':'application/x-www-form-urlencoded'}).addCallback(self.get_stream).addErrback(self.dataError)
		else:
			print "nix"
			
	def get_stream(self, data):
		print "stream data"
		rtmpe_data = re.findall('<filename.*?><!\[CDATA\[(rtmpe://.*?rtl2now/)(.*?)\]\]></filename>', data, re.S|re.I)
		if rtmpe_data:
			print rtmpe_data, self.pageurl
			(host, playpath) = rtmpe_data[0]
			print host, playpath
			if config.mediaportal.useRtmpDump.value:
				final = "%s' --swfVfy=1 --playpath=mp4:%s --app=rtl2now/_definst_ --pageUrl=http://rtl2now.rtl2.de/ --tcUrl=rtmpe://fms-fra30.rtl.de/rtl2now/ --swfUrl=http://rtl2now.rtl2.de/includes/vodplayer.swf'" % (host, playpath)
				print final
				movieinfo = [final,self.streamName+'.f4v']
				self.session.open(PlayRtmpMovie, movieinfo, self.streamName)
			else:
				final = "%s swfUrl=http://rtl2now.rtl2.de/includes/vodplayer.swf pageurl=%s playpath=mp4:%s swfVfy=1" % (host, self.pageurl, playpath)
				print final
				sref = eServiceReference(0x1001, 0, final)
				sref.setName(self.streamName)
				self.session.open(MoviePlayer, sref)
	
	def keyTMDbInfo(self):
		if TMDbPresent:
			title = self['List'].getCurrent()[0][0]
			self.session.open(TMDbMain, title)
			
	def keyCancel(self):
		self.close()