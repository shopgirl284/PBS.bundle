PBS 		= SharedCodeService.CoveAPI.connect
SortThumbs	= SharedCodeService.SortThumbs.SortThumbs
API_ID		= SharedCodeService.PBS_API.API_ID
API_SECRET	= SharedCodeService.PBS_API.API_SECRET

PBS_PREFIX      = "/video/pbs"
CACHE_INTERVAL  = 3600 * 3
PBS_URL         = 'http://video.pbs.org/'
PBS_VIDEO_URL   = 'http://video.pbs.org/video/%s'
PAGE_SIZE  		= 12

COVEAPI_HOST 	= 'http://api.pbs.org'
ALL_PROGRAMS 	= '/cove/v1/programs/?fields=associated_images'
ALL_EPISODES	= '/cove/v1/videos/?fields=associated_images&filter_availability_status=Available&filter_program=%s&filter_type=Episode&order_by=-airdate'

NAMESPACES = {'a':'http://www.w3.org/2001/SMIL20/Language'}

####################################################################################################
def Start():
  Plugin.AddPrefixHandler(PBS_PREFIX, VideoMenu, 'PBS', 'icon-default.png', 'art-default.jpg')
  ObjectContainer.title1 = 'PBS'
  ObjectContainer.art = R('art-default.jpg')
  DirectoryObject.thumb = R("icon-default.png")
  HTTP.CacheTime = CACHE_INTERVAL

####################################################################################################
@route('/video/pbs/videomenu')
def VideoMenu():
  oc = ObjectContainer(no_cache=True)
  oc.add(DirectoryObject(key=Callback(GetPrograms), title=L('All Programs')))
  oc.add(DirectoryObject(key=Callback(GetMostWatched), title=L('Most Watched')))
  oc.add(SearchDirectoryObject(identifier="com.plexapp.plugins.pbs", title=L("Search..."), prompt=L("Search for Videos"), thumb=R('search.png')))
  return oc

####################################################################################################
@route('/video/pbs/programs')
def GetPrograms():
  oc = ObjectContainer(title2=L('All Programs'))
  programs = PBS(String.Decode(API_ID), String.Decode(API_SECRET)).programs.get(ALL_PROGRAMS)
  for program in programs['results']:
    thumbs = SortThumbs(program['associated_images'])
    title = program['title']
    tagline = program['short_description']
    summary = program['long_description']
    uri = program['resource_uri']
    oc.add(DirectoryObject(key=Callback(GetEpisodes, uri=uri, title=title), title=title, tagline=tagline, summary=summary, thumb=Resource.ContentsOfURLWithFallback(url=thumbs, fallback='icon-default.png')))
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
@route('/video/pbs/mostwatched')
def GetMostWatched():
  oc = ObjectContainer(title2=L("Most Watched"))
  for show in HTML.ElementFromURL(PBS_URL).xpath('//div[@id="most-watched-videos"]//li'):
    title = show.xpath('.//span[@class="title clear clearfix"]/a')[0].text
    summary = show.xpath('.//span[@class="description"]')[0].text.strip()
    thumb = show.xpath('.//img')[0].get('src')
    href = show.xpath('.//div/a')[0].get('href')
    oc.add(VideoClipObject(url=href, title=title, summary=summary, thumb=Resource.ContentsOfURLWithFallback(url=thumb, fallback='icon-default.png')))
  
  return oc
  
####################################################################################################