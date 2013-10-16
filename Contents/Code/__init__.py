PBS 		= SharedCodeService.CoveAPI.connect
SortThumbs	= SharedCodeService.SortThumbs.SortThumbs
API_ID		= SharedCodeService.PBS_API.API_ID
API_SECRET	= SharedCodeService.PBS_API.API_SECRET

CACHE_INTERVAL  = 3600 * 3
PBS_URL         = 'http://video.pbs.org'
PBS_VIDEO_URL   = 'http://video.pbs.org/video/%s'
PAGE_SIZE  		= 12

COVEAPI_HOST 	= 'http://api.pbs.org'
ALL_PROGRAMS 	= '/cove/v1/programs/?fields=associated_images&filter_producer__name=PBS'
PROGRAMS 	    = '/cove/v1/programs/?fields=associated_images&%s'
ALL_EPISODES	= '/cove/v1/videos/?fields=associated_images&filter_availability_status=Available&filter_program=%s&filter_type=Episode&order_by=-airdate'
SEARCH_URL	    = 'http://video.pbs.org/search/?q=%s'

####################################################################################################
def Start():
  ObjectContainer.title1 = 'PBS'
  ObjectContainer.art = R('art-default.jpg')
  DirectoryObject.thumb = R('icon-default.png')
  HTTP.CacheTime = CACHE_INTERVAL

####################################################################################################
@handler('/video/pbs', 'PBS', thumb='icon-default.png', art='art-default.jpg')
def VideoMenu():
  oc = ObjectContainer(no_cache=True)
  oc.add(DirectoryObject(key=Callback(ProducePrograms, url=PBS_URL + '/programs/', title='Featured Programs', filter='filter_title=', xpath='carouselProgramList'), title='Featured Programs'))
  oc.add(DirectoryObject(key=Callback(AllPrograms, title='All PBS Programs'), title='All PBS Programs'))
  oc.add(DirectoryObject(key=Callback(SectionVideos, title='Most Popular Videos', type='popular/', url=PBS_URL), title='Most Popular Videos'))
  oc.add(DirectoryObject(key=Callback(SectionVideos, title='Videos Expiring Soon', type='expiring/', url=PBS_URL), title='Videos Expiring Soon'))
  oc.add(DirectoryObject(key=Callback(ProducePrograms, url=PBS_URL, title='Local Channel Shows', filter='filter_producer__name=', xpath=''), title='Local Channel Shows'))
  oc.add(InputDirectoryObject(key=Callback(SectionVideos, title='Search PBS Videos', url=SEARCH_URL, type=''), title='Search PBS Videos', summary="Click here to search videos", prompt="Search for the videos you would like to find"))
  oc.add(PrefsObject(title = L('Preferences')))

  return oc

####################################################################################################
@route('/video/pbs/produceprograms')
def ProducePrograms(title, url, filter, xpath):
  oc = ObjectContainer(title2=title)
  if 'title' in filter:
    show_list = ProgramList(url, xpath)
  else:
    producer = Prefs['local']
    show_list = [producer]
  for show in show_list:
    show_filter = filter + show
    local_url = PROGRAMS %show_filter
    programs = PBS(String.Decode(API_ID), String.Decode(API_SECRET)).programs.get(local_url)
    for program in programs['results']:
      thumbs = SortThumbs(program['associated_images'])
      title = program['title']
      tagline = program['short_description']
      summary = program['long_description']
      uri = program['resource_uri']
      oc.add(DirectoryObject(key=Callback(GetEpisodes, uri=uri, title=title), title=title, tagline=tagline, summary=summary, thumb=Resource.ContentsOfURLWithFallback(url=thumbs, fallback='icon-default.png')))

  # these need proper sorting, the API doesn't give them to us in alphabetical order
  oc.objects.sort(key = lambda obj: obj.title)

  return oc

####################################################################################################
@route('/video/pbs/allprograms')
def AllPrograms(title):
  oc = ObjectContainer(title2=title)
  loop = ['','&limit_start=200','&limit_start=400'] # there are over 400 listed shows in the main listing and we get them in chunks of 200
  for i in loop:
	  programs = PBS(String.Decode(API_ID), String.Decode(API_SECRET)).programs.get(ALL_PROGRAMS+i)
	  for program in programs['results']:
	    thumbs = SortThumbs(program['associated_images'])
	    title = program['title']
	    tagline = program['short_description']
	    summary = program['long_description']
	    uri = program['resource_uri']
	    oc.add(DirectoryObject(key=Callback(GetEpisodes, uri=uri, title=title), title=title, tagline=tagline, summary=summary, thumb=Resource.ContentsOfURLWithFallback(url=thumbs, fallback='icon-default.png')))

  # these need proper sorting, the API doesn't give them to us in alphabetical order
  oc.objects.sort(key = lambda obj: obj.title)

  return oc

####################################################################################################
@route('/video/pbs/episodes')
def GetEpisodes(uri, title='Episodes', page=1):
  oc = ObjectContainer(title2=title)
  show_id = uri.split('/')[-2]
  videos = PBS(String.Decode(API_ID), String.Decode(API_SECRET)).programs.get(ALL_EPISODES % show_id)
  for video in videos['results']:
    thumbs = SortThumbs(video['associated_images'])
    airdate = video['airdate']
    summary = video['long_description']
    title = video['title']
    uri = video['resource_uri']
    tp_id = video['tp_media_object_id']
    oc.add(VideoClipObject(url=PBS_VIDEO_URL % tp_id, title=title, summary=summary, originally_available_at=Datetime.ParseDate(airdate).date(),
      thumb=Resource.ContentsOfURLWithFallback(url=thumbs, fallback='icon-default.png')))
  
  if len(oc) == 0:
    return ObjectContainer(header='PBS', message='No Episodes found')
  else:
    return oc

####################################################################################################
@route('/video/pbs/sectionvideos')
def SectionVideos(title, type, url, query=''):
  oc = ObjectContainer(title2=title)
  if query:
    local_url = url %String.Quote(query, usePlus = True)
  else:
    if type:
      local_url = url + '/' + type
    else:
      local_url = url
  data = HTML.ElementFromURL(local_url)
  for show in data.xpath('//li[@class="videoItem"]'):
    try:
      href = PBS_URL + show.xpath('./a//@href')[0]
    except:
      continue
    show_title = show.xpath('./div/h4/a//text()')[0]
    title = show.xpath('./div/h3/a//text()')[0]
    summary = show.xpath('./p[@class="description"]//text()')[0].strip()
    thumb_data = show.xpath('./a/span//@data-r0')[0]
    thumb = HTML.ElementFromString(thumb_data).xpath('//img//@src')[0].split('.fit')[0]
    duration = show.xpath('./p[@class="duration"]//text()')[0].split('|')[0]
    duration = duration.strip()
    try:
      duration = Datetime.MillisecondsFromString(duration)
    except:
      duration = None
    oc.add(VideoClipObject(url=href, title=title, source_title=show_title, summary=summary, duration=duration, thumb=Resource.ContentsOfURLWithFallback(url=thumb, fallback='icon-default.png')))
  
  # This goes through all the pages of a search
  # After first page, the Prev and Next have the same page_url, so have to check for
  try:
    page_type = data.xpath('//ul[@class="pagination"]/li/a//text()')
    x = len(page_type)-1
    if 'Next' in page_type[x]:
      page_url = data.xpath('//ul[@class="pagination"]/li/a//@href')[x]
      oc.add(NextPageObject(
        key = Callback(SectionVideos, title=title, type=type, url=PBS_URL + page_url), 
        title = L("Next Page ...")))
    else:
      pass
  except:
    pass
    
  if len(oc) == 0:
    return ObjectContainer(header='PBS', message='No Episodes found')
  else:
    return oc
  
####################################################################################################
@route('/video/pbs/programlist')
def ProgramList(url, xpath):
  title_list = []
  data = HTML.ElementFromURL(url)
  for show in data.xpath('//ul[@id="%s"]/li[@class="videoItem"]' %xpath):
    title = show.xpath('./h3/a//text()')[0]
    api_title = String.Quote(title, usePlus = True)
    title_list.append(api_title)
  
  return title_list  
