# XBMCnfoMoviesImporter
# XBMCnfoMoviesImporter
# spec'd from: http://wiki.xbmc.org/index.php?title=Import_-_Export_Library#Video_nfo_Files
#
# Original code author: Harley Hooligan
# Modified by Guillaume Boudreau
# Eden and Frodo compatibility added by Jorge Amigo
# Cleanup and some extensions by SlrG
# Multipart filter idea by diamondsw
# Logo by CrazyRabbit
# Krypton Rating fix by F4RHaD
#
import os, re, time, datetime, platform, traceback, re, htmlentitydefs
from dateutil.parser import parse

COUNTRY_CODES = {
  'Australia': 'Australia,AU',
  'Canada': 'Canada,CA',
  'France': 'France,FR',
  'Germany': 'Germany,DE',
  'Netherlands': 'Netherlands,NL',
  'United Kingdom': 'UK,GB',
  'United States': 'USA,',
}

PERCENT_RATINGS = {
  'rottentomatoes','rotten tomatoes','rt','flixster'
}

class xbmcnfo(Agent.Movies):
	name = 'XBMCnfoMoviesImporter'
	ver = '1.1-54-g2094a1b-160'
	primary_provider = True
	languages = [Locale.Language.NoLanguage]
	accepts_from = ['com.plexapp.agents.localmedia','com.plexapp.agents.opensubtitles','com.plexapp.agents.podnapisi','com.plexapp.agents.subzero']

##### helper functions #####
	def DLog (self, LogMessage):
		if Prefs['debug']:
			Log (LogMessage)

	def getRelatedFile(self, videoFile, fileExtension):
		videoFileExtension = videoFile.split(".")[-1]
		videoFileBase = videoFile.replace('.' + videoFileExtension, '')
		videoFileBase = re.sub(r'(?is)\s*\-\s*(cd|dvd|disc|disk|part|pt|d)\s*[0-9]$', '', videoFileBase)
		videoFileBase = re.sub(r'(?is)\s*\-\s*(cd|dvd|disc|disk|part|pt|d)\s*[a-d]$', '', videoFileBase)
		return (videoFileBase + fileExtension)

	def getMovieNameFromFolder(self, folderpath, withYear):
		foldersplit = folderpath.split (os.sep)
		if withYear == True:
			if foldersplit[-1] == 'VIDEO_TS':
				moviename = os.sep.join(foldersplit[1:len(foldersplit)-1:]) + os.sep + foldersplit[-2]
			else:
				moviename = os.sep.join(foldersplit) + os.sep + foldersplit[-1]
			self.DLog("Moviename from folder (withYear): " + moviename)
		else:
			if foldersplit[-1] == 'VIDEO_TS':
				moviename = os.sep.join(foldersplit[1:len(foldersplit)-1:]) + os.sep + re.sub (r' \(.*\)',r'',foldersplit[-2])
			else:
				moviename = os.sep.join(foldersplit) + os.sep + re.sub (r' \(.*\)',r'',foldersplit[-1])
			self.DLog("Moviename from folder: " + moviename)
		return moviename

	def checkFilePaths(self, pathfns, ftype):
		for pathfn in pathfns:
			self.DLog("Trying " + pathfn)
			if not os.path.exists(pathfn):
				continue
			else:
				Log("Found " + ftype + " file " + pathfn)
				return pathfn
		else:
			Log("No " + ftype + " file found! Aborting!")

	def RemoveEmptyTags(self, xmltags):
		for xmltag in xmltags.iter("*"):
			if len(xmltag):
				continue
			if not (xmltag.text and xmltag.text.strip()):
				#self.DLog("Removing empty XMLTag: " + xmltag.tag)
				xmltag.getparent().remove(xmltag)
		return xmltags

	##
	# Removes HTML or XML character references and entities from a text string.
	# Copyright: http://effbot.org/zone/re-sub.htm October 28, 2006 | Fredrik Lundh
	# @param text The HTML (or XML) source text.
	# @return The plain text, as a Unicode string, if necessary.

	def unescape(self, text):
		def fixup(m):
			text = m.group(0)
			if text[:2] == "&#":
				# character reference
				try:
					if text[:3] == "&#x":
						return unichr(int(text[3:-1], 16))
					else:
						return unichr(int(text[2:-1]))
				except ValueError:
					pass
			else:
				# named entity
				try:
					text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
				except KeyError:
					pass
			return text # leave as is
		return re.sub("&#?\w+;", fixup, text)

##### search function #####
	def search(self, results, media, lang):
		self.DLog("++++++++++++++++++++++++")
		self.DLog("Entering search function")
		self.DLog("++++++++++++++++++++++++")
		Log ("" + self.name + " Version: " + self.ver)

		path1 = media.items[0].parts[0].file
		self.DLog('media file: ' + path1)
		folderpath = os.path.dirname(path1)
		self.DLog('folderpath: ' + folderpath)

		# Moviename with year from folder
		movienamewithyear = self.getMovieNameFromFolder (folderpath, True)
		# Moviename from folder
		moviename = self.getMovieNameFromFolder (folderpath, False)

		nfoNames = []
		# Eden / Frodo
		nfoNames.append (self.getRelatedFile(path1, '.nfo'))
		nfoNames.append (movienamewithyear + '.nfo')
		nfoNames.append (moviename + '.nfo')
		# VIDEO_TS
		nfoNames.append (os.path.join(folderpath, 'video_ts.nfo'))
		# movie.nfo (e.g. FilmInfo!Organizer users)
		nfoNames.append (os.path.join(folderpath, 'movie.nfo'))
		# last resort - use first found .nfo
		nfoFiles = [f for f in os.listdir(folderpath) if f.endswith('.nfo')]
		if nfoFiles: nfoNames.append (os.path.join(folderpath, nfoFiles[0]))

		# check possible .nfo file locations
		nfoFile = self.checkFilePaths (nfoNames, '.nfo')

		if nfoFile:
			nfoText = Core.storage.load(nfoFile)
			# work around failing XML parses for things with &'s in
			# them. This may need to go farther than just &'s....
			nfoText = re.sub(r'&(?![A-Za-z]+[0-9]*;|#[0-9]+;|#x[0-9a-fA-F]+;)', r'&amp;', nfoText)
			# remove empty xml tags from nfo
			self.DLog('Removing empty XML tags from movies nfo...')
			nfoText = re.sub(r'^\s*<.*/>[\r\n]+', '', nfoText, flags = re.MULTILINE)

			nfoTextLower = nfoText.lower()
			if nfoTextLower.count('<movie') > 0 and nfoTextLower.count('</movie>') > 0:
				# Remove URLs (or other stuff) at the end of the XML file
				nfoText = '%s</movie>' % nfoText.rsplit('</movie>', 1)[0]

				# likely an xbmc nfo file
				try: nfoXML = XML.ElementFromString(nfoText).xpath('//movie')[0]
				except:
					self.DLog('ERROR: Cant parse XML in ' + nfoFile + '. Aborting!')
					return

				# Title
				try: media.name = nfoXML.xpath('title')[0].text
				except:
					self.DLog("ERROR: No <title> tag in " + nfoFile + ". Aborting!")
					return
				# Sort Title
				try: media.title_sort = nfoXML.xpath('sorttitle')[0].text
				except:
					self.DLog("No <sorttitle> tag in " + nfoFile + ".")
					pass
				# Year
				try:
					media.year = int(nfoXML.xpath('year')[0].text.strip())
					self.DLog ("Reading year tag: " + str(media.year))
				except: pass
				# ID
				try:
					id = nfoXML.xpath('id')[0].text.strip()
				except:
					id=""
					pass
				if len(id) > 2:
						media.id = id
						self.DLog("ID from nfo: " + media.id)
				else:
					# if movie id doesn't exist, create
					# one based on hash of title and year
					ord3 = lambda x : '%.3d' % ord(x)
					id = int(''.join(map(ord3, media.name+str(media.year))))
					id = str(abs(hash(int(id))))
					media.id = id
					self.DLog("ID generated: " + media.id)

				results.Append(MetadataSearchResult(id=media.id, name=media.name, year=media.year, lang=lang, score=100))
				try: Log('Found movie information in NFO file: title = ' + media.name + ', year = ' + str(media.year) + ', id = ' + media.id)
				except: pass
			else:
				Log("ERROR: No <movie> tag in " + nfoFile + ". Aborting!")

##### update Function #####
	def update(self, metadata, media, lang):
		self.DLog("++++++++++++++++++++++++")
		self.DLog("Entering update function")
		self.DLog("++++++++++++++++++++++++")
		Log ("" + self.name + " Version: " + self.ver)

		path1 = media.items[0].parts[0].file
		self.DLog('media file: ' + path1)
		folderpath = os.path.dirname(path1)
		self.DLog('folderpath: ' + folderpath)
		isDVD = os.path.basename(folderpath).upper() == 'VIDEO_TS'
		if isDVD: folderpathDVD = os.path.dirname(folderpath)

		# Moviename with year from folder
		movienamewithyear = self.getMovieNameFromFolder (folderpath, True)
		# Moviename from folder
		moviename = self.getMovieNameFromFolder (folderpath, False)

		if not Prefs['localmediaagent']:
			posterData = None
			posterFilename = ""
			posterNames = []
			# Frodo
			posterNames.append (self.getRelatedFile(path1, '-poster.jpg'))
			posterNames.append (movienamewithyear + '-poster.jpg')
			posterNames.append (moviename + '-poster.jpg')
			posterNames.append (os.path.join(folderpath, 'poster.jpg'))
			if isDVD: posterNames.append (os.path.join(folderpathDVD, 'poster.jpg'))
			# Eden
			posterNames.append (self.getRelatedFile(path1, '.tbn'))
			posterNames.append (folderpath + "/folder.jpg")
			if isDVD: posterNames.append (os.path.join(folderpathDVD, 'folder.jpg'))
			# DLNA
			posterNames.append (self.getRelatedFile(path1, '.jpg'))
			# Others
			posterNames.append (folderpath + "/cover.jpg")
			if isDVD: posterNames.append (os.path.join(folderpathDVD, 'cover.jpg'))
			posterNames.append (folderpath + "/default.jpg")
			if isDVD: posterNames.append (os.path.join(folderpathDVD, 'default.jpg'))
			posterNames.append (folderpath + "/movie.jpg")
			if isDVD: posterNames.append (os.path.join(folderpathDVD, 'movie.jpg'))

			# check possible poster file locations
			posterFilename = self.checkFilePaths (posterNames, 'poster')

			if posterFilename:
				posterData = Core.storage.load(posterFilename)
				for key in metadata.posters.keys():
					del metadata.posters[key]

			fanartData = None
			fanartFilename = ""
			fanartNames = []
			# Eden / Frodo
			fanartNames.append (self.getRelatedFile(path1, '-fanart.jpg'))
			fanartNames.append (movienamewithyear + '-fanart.jpg')
			fanartNames.append (moviename + '-fanart.jpg')
			fanartNames.append (os.path.join(folderpath, 'fanart.jpg'))
			if isDVD: fanartNames.append (os.path.join(folderpathDVD, 'fanart.jpg'))
			# Others
			fanartNames.append (os.path.join(folderpath, 'art.jpg'))
			if isDVD: fanartNames.append (os.path.join(folderpathDVD, 'art.jpg'))
			fanartNames.append (os.path.join(folderpath, 'backdrop.jpg'))
			if isDVD: fanartNames.append (os.path.join(folderpathDVD, 'backdrop.jpg'))
			fanartNames.append (os.path.join(folderpath, 'background.jpg'))
			if isDVD: fanartNames.append (os.path.join(folderpathDVD, 'background.jpg'))

			# check possible fanart file locations
			fanartFilename = self.checkFilePaths (fanartNames, 'fanart')

			if fanartFilename:
				fanartData = Core.storage.load(fanartFilename)
				for key in metadata.art.keys():
					del metadata.art[key]

		nfoNames = []
		# Eden / Frodo
		nfoNames.append (self.getRelatedFile(path1, '.nfo'))
		nfoNames.append (movienamewithyear + '.nfo')
		nfoNames.append (moviename + '.nfo')
		# VIDEO_TS
		nfoNames.append (os.path.join(folderpath, 'video_ts.nfo'))
		# movie.nfo (e.g. FilmInfo!Organizer users)
		nfoNames.append (os.path.join(folderpath, 'movie.nfo'))
		# last resort - use first found .nfo
		nfoFiles = [f for f in os.listdir(folderpath) if f.endswith('.nfo')]
		if nfoFiles: nfoNames.append (os.path.join(folderpath, nfoFiles[0]))

		# check possible .nfo file locations
		nfoFile = self.checkFilePaths (nfoNames, '.nfo')

		if nfoFile:
			nfoText = Core.storage.load(nfoFile)
			# work around failing XML parses for things with &'s in
			# them. This may need to go farther than just &'s....
			nfoText = re.sub(r'&(?![A-Za-z]+[0-9]*;|#[0-9]+;|#x[0-9a-fA-F]+;)', r'&amp;', nfoText)
			# remove empty xml tags from nfo
			self.DLog('Removing empty XML tags from movies nfo...')
			nfoText = re.sub(r'^\s*<.*/>[\r\n]+', '', nfoText, flags = re.MULTILINE)

			nfoTextLower = nfoText.lower()
			if nfoTextLower.count('<movie') > 0 and nfoTextLower.count('</movie>') > 0:
				# Remove URLs (or other stuff) at the end of the XML file
				nfoText = '%s</movie>' % nfoText.rsplit('</movie>', 1)[0]

				# likely an xbmc nfo file
				try: nfoXML = XML.ElementFromString(nfoText).xpath('//movie')[0]
				except:
					self.DLog('ERROR: Cant parse XML in ' + nfoFile + '. Aborting!')
					return

				#remove empty xml tags
				self.DLog('Removing empty XML tags from movies nfo...')
				nfoXML = self.RemoveEmptyTags(nfoXML)

				# Title
				try: metadata.title = nfoXML.xpath('title')[0].text.strip()
				except:
					self.DLog("ERROR: No <title> tag in " + nfoFile + ". Aborting!")
					return
				# Sort Title
				try: metadata.title_sort = nfoXML.xpath('sorttitle')[0].text.strip()
				except:
					self.DLog("No <sorttitle> tag in " + nfoFile + ".")
					pass
				# Year
				try:
					metadata.year = int(nfoXML.xpath('year')[0].text.strip())
					self.DLog ("Set year tag: " + str(metadata.year))
				except: pass
				# Original Title
				try: metadata.original_title = nfoXML.xpath('originaltitle')[0].text.strip()
				except: pass
				# Content Rating
				metadata.content_rating = ''
				content_rating = {}
				mpaa_rating = ''
				try:
					mpaatext = nfoXML.xpath('./mpaa')[0].text.strip()
					match = re.match(r'(?:Rated\s)?(?P<mpaa>[A-z0-9-+/.]+(?:\s[0-9]+[A-z]?)?)?', mpaatext)
					if match.group('mpaa'):
						mpaa_rating = match.group('mpaa')
						self.DLog('MPAA Rating: ' + mpaa_rating)
				except: pass
				try:
					for cert in nfoXML.xpath('certification')[0].text.split(" / "):
						country = cert.strip()
						country = country.split(':')
						if not country[0] in content_rating:
							if country[0] == "Australia":
								if country[1] == "MA": country[1] = "MA15"
								if country[1] == "R": country[1] = "R18"
								if country[1] == "X": country[1] = "X18"
							if country[0] == "DE":
								country[0] = "Germany"
							content_rating[country[0]]=country[1].strip('+').replace('FSK','').replace('ab ','').strip()
					self.DLog('Content Rating(s): ' + str(content_rating))
				except: pass
				if Prefs['country'] != '':
					cc = COUNTRY_CODES[Prefs['country']].split(',')
					self.DLog('Country code from settings: ' + Prefs['country'] + ':' + str(cc))
					if cc[0] in content_rating:
						if cc[1] == "":
							metadata.content_rating = content_rating.get(cc[0])
						else:
							metadata.content_rating = '%s/%s' % (cc[1].lower(), content_rating.get(cc[0]))
				if metadata.content_rating == '' and mpaa_rating != '':
					metadata.content_rating = mpaa_rating
				if metadata.content_rating == '' and 'USA' in content_rating:
					metadata.content_rating = content_rating.get('USA')
				if metadata.content_rating == '' or metadata.content_rating == 'Not Rated':
					metadata.content_rating = 'NR'
				if '(' in metadata.content_rating:
					metadata.content_rating = re.sub(r'\s*\(.*?\)', '', metadata.content_rating)

				# Studio
				try: metadata.studio = nfoXML.xpath("studio")[0].text.strip()
				except: pass
				# Premiere
				try:
					release_string = None
					release_date = None
					try:
						self.DLog("Reading releasedate tag...")
						release_string = nfoXML.xpath("releasedate")[0].text.strip()
						self.DLog("Releasedate tag is: " + release_string)
					except:
						self.DLog("No releasedate tag found...")
						pass
					if not release_string:
						try:
							self.DLog("Reading premiered tag...")
							release_string = nfoXML.xpath("premiered")[0].text.strip()
							self.DLog("Premiered tag is: " + release_string)
						except:
							self.DLog("No premiered tag found...")
							pass
					if not release_string:
						try:
							self.DLog("Reading dateadded tag...")
							release_string = nfoXML.xpath("dateadded")[0].text.strip()
							self.DLog("Dateadded tag is: " + release_string)
						except:
							self.DLog("No dateadded tag found...")
							pass
					if release_string:
						try:
							if Prefs['dayfirst']:
								dt = parse(release_string, dayfirst=True)
							else:
								dt = parse(release_string)
							release_date = dt
							self.DLog("Set premiere to: " + dt.strftime('%Y-%m-%d'))
							if not metadata.year:
								metadata.year = int(dt.strftime('%Y'))
								self.DLog ("Set year tag from premiere: " + str(metadata.year))
						except:
							self.DLog("Couldn't parse premiere: " + air_string)
							pass
				except:
					self.DLog("Exception parsing releasedate: " + traceback.format_exc())
					pass
				try:
					if not release_date:
						self.DLog("Fallback to year tag instead...")
						release_date = time.strptime(str(metadata.year) + "-01-01", "%Y-%m-%d")
						metadata.originally_available_at = datetime.datetime.fromtimestamp(time.mktime(release_date)).date()
					else:
						self.DLog("Setting releasedate...")
						metadata.originally_available_at = release_date
				except: pass

				# Tagline
				try: metadata.tagline = nfoXML.xpath("tagline")[0].text.strip()
				except: pass
				# Summary (Outline/Plot)
				try:
					if Prefs['plot']:
						self.DLog("User setting forces plot before outline...")
						stype1 = 'plot'
						stype2 = 'outline'
					else:
						self.DLog("Default setting forces outline before plot...")
						stype1 ='outline'
						stype2 = 'plot'
					try:
						summary = nfoXML.xpath(stype1)[0].text.strip('| \t\r\n')
						if not summary:
							self.DLog("No or empty " + stype1 + " tag. Fallback to " + stype2 +"...")
							raise
					except:
						summary = nfoXML.xpath(stype2)[0].text.strip('| \t\r\n')
					metadata.summary = summary
				except:
					self.DLog("Exception on reading summary!")
					metadata.summary = ""
					pass
				# Ratings
				try:
					nforating = None
					nforating = round(float(nfoXML.xpath("rating")[0].text.replace(',', '.')),1)
					self.DLog("Series Rating found: " + str(nforating))
				except:
					pass
				if not nforating:
					self.DLog("Reading old rating style failed. Trying new Krypton style.")
					for ratings in nfoXML.xpath('ratings'):
						try:
							rating=ratings.xpath("rating")[0]
							nforating = round(float(rating.xpath("value")[0].text.replace(',', '.')),1)
							self.DLog("Krypton style series rating found: " + str(nforating))
						except:
							self.DLog("Can't read rating from tvshow.nfo.")
							nforating = 0.0
							pass
				if Prefs['altratings']:
					self.DLog("Searching for additional Ratings...")
					allowedratings = Prefs['ratings']
					if not allowedratings: allowedratings = ""
					addratingsstring = ""
					try:
						addratings = nfoXML.xpath('ratings')
						self.DLog("Trying to read additional ratings from .nfo.")
					except:
						self.DLog("Can't read additional ratings from .nfo.")
						pass
					if addratings:
						for addratingXML in addratings:
							for addrating in addratingXML:
								try:
									ratingprovider = str(addrating.attrib['moviedb'])
								except:
									pass
									self.DLog("Skipping additional rating without moviedb attribute!")
									continue
								ratingvalue = str(addrating.text.replace (',','.'))
								if ratingprovider.lower() in PERCENT_RATINGS:
									ratingvalue = ratingvalue + "%"
								if ratingprovider in allowedratings or allowedratings == "":
									self.DLog("adding rating: " + ratingprovider + ": " + ratingvalue)
									addratingsstring = addratingsstring + " | " + ratingprovider + ": " + ratingvalue
							if addratingsstring != "":
								self.DLog("Putting additional ratings at the " + Prefs['ratingspos'] + " of the summary!")
								if Prefs['ratingspos'] == "front":
									if Prefs['preserverating']:
										metadata.summary = addratingsstring[3:] + self.unescape(" &#9733;\n\n") + metadata.summary
									else:
										metadata.summary = self.unescape("&#9733; ") + addratingsstring[3:] + self.unescape(" &#9733;\n\n") + metadata.summary
								else:
									metadata.summary = metadata.summary + self.unescape("\n\n&#9733; ") + addratingsstring[3:] + self.unescape(" &#9733;")
							else:
								self.DLog("Additional ratings empty or malformed!")
				if Prefs['preserverating']:
					self.DLog("Putting .nfo rating in front of summary!")
					if not nforating:
						nforating = 0.0
					metadata.summary = self.unescape(str(Prefs['beforerating'])) + "{:.1f}".format(nforating) + self.unescape(str(Prefs['afterrating'])) + metadata.summary
					metadata.rating = nforating
				else:
					metadata.rating = nforating
				# Writers (Credits)
				try:
					credits = nfoXML.xpath('credits')
					metadata.writers.clear()
					for creditXML in credits:
						for c in creditXML.text.split("/"):
							metadata.writers.new().name = c.strip()
				except: pass
				# Directors
				try:
					directors = nfoXML.xpath('director')
					metadata.directors.clear()
					for directorXML in directors:
						for d in directorXML.text.split("/"):
							metadata.directors.new().name = d.strip()
				except: pass
				# Genres
				try:
					genres = nfoXML.xpath('genre')
					metadata.genres.clear()
					[metadata.genres.add(g.strip()) for genreXML in genres for g in genreXML.text.split("/")]
					metadata.genres.discard('')
				except: pass
				# Countries
				try:
					countries = nfoXML.xpath('country')
					metadata.countries.clear()
					[metadata.countries.add(c.strip()) for countryXML in countries for c in countryXML.text.split("/")]
					metadata.countries.discard('')
				except: pass
				# Collections (Set)
				try:
					sets = nfoXML.xpath('set')
					metadata.collections.clear()
					for setXML in sets:
						for s in setXML.text.split("/"):
							collection = s.strip()
							metadata.collections.add(collection)
							self.DLog ("Adding Set/Collection tag: " + collection)
				except:
					self.DLog ("Exception adding Set/Collection tag:" + traceback.format_exc())
					pass
				# Duration
				try:
					self.DLog ("Trying to read <durationinseconds> tag from .nfo file...")
					fileinfoXML = XML.ElementFromString(nfoText).xpath('fileinfo')[0]
					streamdetailsXML = fileinfoXML.xpath('streamdetails')[0]
					videoXML = streamdetailsXML.xpath('video')[0]
					runtime = videoXML.xpath("durationinseconds")[0].text.strip()
					metadata.duration = int(re.compile('^([0-9]+)').findall(runtime)[0]) * 1000 # s
				except:
					try:
						self.DLog ("Fallback to <runtime> tag from .nfo file...")
						runtime = nfoXML.xpath("runtime")[0].text.strip()
						metadata.duration = int(re.compile('^([0-9]+)').findall(runtime)[0]) * 60 * 1000 # ms
					except:
						self.DLog("No Duration in .nfo file.")
						pass
				# Actors
				metadata.roles.clear()
				for actor in nfoXML.xpath('actor'):
					role = metadata.roles.new()
					try: role.name = actor.xpath("name")[0].text
					except:
						role.name = "unknown"
					try: role.role = actor.xpath("role")[0].text
					except:
						role.role = "unknown"
					try: role.photo = actor.xpath("thumb")[0].text
					except:
						pass

				if not Prefs['localmediaagent']:
					# Remote posters and fanarts are disabled for now; having them seems to stop the local artworks from being used.
					#(remote) posters
					#(local) poster
					if posterData:
						metadata.posters[posterFilename] = Proxy.Media(posterData)
					#(remote) fanart
					#(local) fanart
					if fanartData:
						metadata.art[fanartFilename] = Proxy.Media(fanartData)

					# Trailer Support
					# Eden / Frodo
					if Prefs['trailer']:
						for f in os.listdir(folderpath):
							(fn, ext) = os.path.splitext(f)
							try:
								title = ""
								if fn.endswith('-trailer'):
										title = ' '.join(fn.split('-')[:-1])
								if fn == "trailer" or f.startswith ('movie-trailer'):
										title = metadata.title
								if title != "":
									metadata.extras.add(TrailerObject(title=title, file=os.path.join(folderpath, f)))
									self.DLog("Found trailer file " + os.path.join(folderpath, f))
									self.DLog("Trailer title:" + title)
							except:
								self.DLog("Exception adding trailer file!")


				Log("---------------------")
				Log("Movie nfo Information")
				Log("---------------------")
				try: Log("ID: " + str(metadata.guid))
				except: Log("ID: -")
				try: Log("Title: " + str(metadata.title))
				except: Log("Title: -")
				try: Log("Sort Title: " + str(metadata.title_sort))
				except: Log("Sort Title: -")
				try: Log("Year: " + str(metadata.year))
				except: Log("Year: -")
				try: Log("Original: " + str(metadata.original_title))
				except: Log("Original: -")
				try: Log("Rating: " + str(metadata.rating))
				except: Log("Rating: -")
				try: Log("Content: " + str(metadata.content_rating))
				except: Log("Content: -")
				try: Log("Studio: " + str(metadata.studio))
				except: Log("Studio: -")
				try: Log("Premiere: " + str(metadata.originally_available_at))
				except: Log("Premiere: -")
				try: Log("Tagline: " + str(metadata.tagline))
				except: Log("Tagline: -")
				try: Log("Summary: " + str(metadata.summary))
				except: Log("Summary: -")
				Log("Writers:")
				try: [Log("\t" + writer.name) for writer in metadata.writers]
				except: Log("\t-")
				Log("Directors:")
				try: [Log("\t" + director.name) for director in metadata.directors]
				except: Log("\t-")
				Log("Genres:")
				try: [Log("\t" + genre) for genre in metadata.genres]
				except: Log("\t-")
				Log("Countries:")
				try: [Log("\t" + country) for country in metadata.countries]
				except: Log("\t-")
				Log("Collections:")
				try: [Log("\t" + collection) for collection in metadata.collections]
				except: Log("\t-")
				try: Log("Duration: " + str(metadata.duration // 60000) + ' min')
				except: Log("Duration: -")
				Log("Actors:")
				try: [Log("\t" + actor.name + " > " + actor.role) for actor in metadata.roles]
				except: [Log("\t" + actor.name) for actor in metadata.roles]
				except: Log("\t-")
				Log("---------------------")
			else:
				Log("ERROR: No <movie> tag in " + nfoFile + ". Aborting!")
			return metadata
