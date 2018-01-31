NAME = 'PBS'
ART = 'art-default.jpg'
ICON = 'icon-default.jpg'
PREFIX = '/video/pbs'

BASE_URL   = 'http://www.pbs.org'

VIDEO_URL   = 'http://www.pbs.org/video/%s'
SHOW_URL   = 'http://www.pbs.org/shows/?genre=%s&title=&station=%s&alphabetically=%s'
# values are genre, station (true/false), sort/alphabetically (true/false)

SHOWS_JSON	    = 'http://www.pbs.org/shows-page/%s/?genre=%s&title=&callsign=%s&alphabetically=%s'
# we would need a page, genre, callsign, alphabetically (true/false) values

SEARCH_JSON	    = 'http://www.pbs.org/search-videos/?callsign=%s&filter_item_type=video&filter_video_availability=public&q=%s'
# requires callsign, query and page value, and a page number on the end
# Provides filters and sort orders (-premiere_date or premiere_date for dated order and expire_date by expiring soonest
# WILL NOT PRODUCE RESULTS WITHOUT CALLSIGN AND QUERY VALUE
#SEASON_JSON = '/season/%s/%s/1/'
# Add to show url and need a season code as well as a type (episode, extra, special)

RE_SXX_EXX = Regex('S (\d+).+Ep (\d+)')

####################################################################################################
def Start():

	ObjectContainer.title1 = NAME
	DirectoryObject.thumb = R(ICON)
	HTTP.CacheTime = CACHE_1HOUR
	HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36'

####################################################################################################
@handler(PREFIX, NAME, art=ART, thumb=ICON)
def MainMenu():

	oc = ObjectContainer()
	oc.add(DirectoryObject(key=Callback(ShowMenu, title="Shows"), title="Shows"))
	oc.add(DirectoryObject(key=Callback(GetVideos, title="Popular Videos", url=BASE_URL+'/collections/most-popular-videos/'), title="Popular Videos"))
	oc.add(DirectoryObject(key=Callback(GetVideos, title="Latest Videos", url=BASE_URL+'/collections/new-videos'), title="Latest Videos"))
	oc.add(InputDirectoryObject(key=Callback(SearchMenu, title="Search PBS"), title="Search PBS"))
	oc.add(PrefsObject(title = L('Preferences')))
	return oc

####################################################################################################
@route(PREFIX + '/showmenu')
def ShowMenu(title):

    oc = ObjectContainer(title2=title)
    oc.add(DirectoryObject(key=Callback(ProgramListJSON, title="Popular Shows"), title="Popular Shows"))
    oc.add(DirectoryObject(key=Callback(Genre, title="Shows by Genre"), title="Shows by Genre"))
    oc.add(DirectoryObject(key=Callback(ProgramListJSON, title="Local Station Shows", station='true'), title="Local Station Shows"))
    oc.add(DirectoryObject(key=Callback(ProgramListJSON, title="All Shows A to Z", sort='true'), title="All Shows A to Z"))
    return oc

####################################################################################################
@route(PREFIX + '/genre')
def Genre(title):

	oc = ObjectContainer(title2=title)
	json = JSON.ObjectFromURL(SHOWS_JSON %(0, '', '', 'false'), headers={"X-Requested-With": "XMLHttpRequest"})
	for genre_type in json['genres']:
		title = genre_type['title']
		genre = genre_type['id']
		if genre=='All':
			continue
		oc.add(DirectoryObject(key=Callback(ProgramListJSON, title=title, genre=genre), title=title))
	return oc

####################################################################################################
@route(PREFIX + '/programlistjson', page=int)
def ProgramListJSON(title, page=0, genre='', sort='false', station='false'):

	oc = ObjectContainer(title2=title)
	if station=='true':
		callsign = Prefs['local']
	else:
		callsign = ''
	json_url = SHOWS_JSON %(str(page), genre, callsign, sort)
	json = JSON.ObjectFromURL(json_url, headers={"X-Requested-With": "XMLHttpRequest"})
	for show in json['results']['content']:
		#Log('the value of popularity is %s' %show['popularity'])
		# Skip lower scores (50-60) for Popular results
		if "Popular" in title and show['popularity'] < 85:
			continue
		show_title = show['title']
		show_url = show['url']
		if not show_url.startswith('http:'):
			show_url = BASE_URL + show_url
		slug = show['slug']
		summary = show['description']
		thumb = show['image']
		oc.add(DirectoryObject(key=Callback(ShowJSON, title=show_title, thumb=thumb, slug=slug), 
			title=show_title,
			summary=summary, 
			thumb=Resource.ContentsOfURLWithFallback(url=thumb)
		))

	if "Popular" not in title and page+1 < json['results']['totalPages']:
		page = page+1
		oc.add(NextPageObject(key=Callback(ProgramListJSON, title=title, page=page, genre=genre, sort=sort), 
			title = 'Next Page ...'
		))

	if len(oc) < 1:
		return ObjectContainer(header="Empty", message="There are no results to list.")
	else:
		return oc

####################################################################################################
# Uses the slug value of a show to build a search URL of its videos and separate them by video type
@route(PREFIX + '/showjson')
def ShowJSON(title, slug, thumb):

	oc = ObjectContainer(title2=title)
	callsign=Prefs['local']
	json_url = SEARCH_JSON %(callsign, String.Quote(slug, usePlus = True)) + '&filter_show=' + String.Quote(title, usePlus = False)
	json = JSON.ObjectFromURL(json_url+ '&page=1', headers={"X-Requested-With": "XMLHttpRequest"})
	for section in json['filters']['filter_item_type']['options'][0]['options']:
		section_title = section['label']
		section_url = '%s&filter_video_type=%s&rank=%s' %(json_url, section['value'], Prefs['sort'])
		#Log('the value of section_url is %s' %section_url)
		oc.add(DirectoryObject(key=Callback(SearchJSON, title=section_title, url=section_url, search_type='articles'), 
			title=section_title, 
			thumb=Resource.ContentsOfURLWithFallback(url=thumb)
		))
		
	return oc

####################################################################################################
# Pulls the videos from an html video page
@route(PREFIX + '/getvideos')
def GetVideos(title, url, section=''):

	oc = ObjectContainer(title2=title)
	page = HTML.ElementFromURL(url)
	if section:
		video_list = page.xpath('//section//h2[contains(text(),"%s")]/following-sibling::div/div[@class="video-grid__item"]' %section)
	else:
		video_list = page.xpath('//div[@class="video-catalog__item"]')
	for video in video_list:
		url = video.xpath('./div/a/@href')[0].strip()
		if not url.startswith('http:'):
			url = BASE_URL + url
		thumbs = video.xpath('.//img/@data-srcset')[0].split(',')[0]
		vid_title = video.xpath('.//p[@class="popover__title"]//text()')[0].strip()
		summary = video.xpath('.//p[@class="description"]/text()')[0].strip()
		other_data = video.xpath('.//p[@class="popover__meta-data"]/text()')[0].strip().split(' | ')
		try: (season, episode) = RE_SXX_EXX.search(other_data[0]).groups()
		except: (season, episode) = (None, None)
		duration = other_data[1].replace("h ", ':').replace("m ", ':').replace("s", '')
		#duration = Datetime.MillisecondsFromString(duration)
		oc.add(EpisodeObject(
			url=url,
			title=vid_title,
			show=title,
			season=int(season) if season else None,
			index=int(episode) if episode else None,
			summary=summary,
			#duration=duration,
			thumb=Resource.ContentsOfURLWithFallback(url=thumbs)
		))

	if len(oc) < 1:
		return ObjectContainer(header="Empty", message="There are no results to list.")
	else:
		return oc

####################################################################################################
# WE COULD SPLIT THE VIDEOS UP BY CLIPS PREVIEWS AND FULL LENGTH
@route(PREFIX + '/searchmenu')
def SearchMenu(title, query):

	oc = ObjectContainer(title2=title)
	callsign=Prefs['local']
	json_url = SEARCH_JSON %(callsign, String.Quote(query, usePlus = True)) + "&rank=" + Prefs['sort']
	oc.add(DirectoryObject(key=Callback(SearchJSON, title="Search Videos", url=json_url, search_type='articles'), title="Search Videos"))
	oc.add(DirectoryObject(key=Callback(SearchJSON, title="Search Shows", url=json_url, search_type='shows'), title="Search Shows"))
	return oc

####################################################################################################
@route(PREFIX + '/searchjson', page=int)
def SearchJSON(title, url, search_type, page=1):

	oc = ObjectContainer(title2=title)
	local_url = url + '&page=' + str(page)
	json = JSON.ObjectFromURL(local_url, headers={"X-Requested-With": "XMLHttpRequest"})
	for video in json['results'][search_type]:
		thumb = video['image']
		title = video['title']
		item_url = BASE_URL + video['url']
		summary = video['description_long']
		if search_type=='shows':
			oc.add(DirectoryObject(key=Callback(ShowSections, title=title, url=item_url, thumb=thumb), 
				title=title,
				summary=summary,
				thumb=Resource.ContentsOfURLWithFallback(url=thumb)
			))
		else:
			show_title = video['show']['title']
			index = video['show']['episode']
			if not isinstance(index, int):
				index=None
			Log('the value of index is %s' %index)
			season = video['show']['season']
			airdate = video['air_date']
			airdate = Datetime.ParseDate(airdate).date()
			duration = video['duration'].strip()
			Log('the value of duration is %s' %duration)
			#duration_list = duration.split()
			#duration = duration_list[len(duration_list)-1]
			duration = duration.replace("h ", ':').replace("m ", ':').replace("s", '')
			Log('the value of duration is %s' %duration)
			#duration = Datetime.MillisecondsFromString(duration)
			oc.add(EpisodeObject(
				url=item_url,
				title=title,
				show=show_title,
				season=season,
				index=index,
				summary=summary,
				#duration=duration,
				originally_available_at=airdate,
				thumb=Resource.ContentsOfURLWithFallback(url=thumb)
			))

	if search_type!='shows' and page < json['results']['totalPages']:
		page = page+1
		oc.add(NextPageObject(key=Callback(SearchJSON, title=title, url=url, search_type=search_type, page=page), 
			title = 'Next Page ...'
		))

	if len(oc) < 1:
		return ObjectContainer(header="Empty", message="There are no results to list.")
	else:
		return oc
