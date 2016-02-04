PBS 		= SharedCodeService.CoveAPI.connect
SortThumbs  = SharedCodeService.SortThumbs.SortThumbs
API_ID		= SharedCodeService.PBS_API.API_ID
API_SECRET	= SharedCodeService.PBS_API.API_SECRET

CACHE_INTERVAL  = 3600 * 3
PBS_URL         = 'http://video.pbs.org'
PBS_VIDEO_URL   = 'http://video.pbs.org/video/%s'
PAGE_SIZE  		= 12

COVEAPI_HOST 	= 'http://api.pbs.org'
PROGRAMS 	    = '/cove/v1/programs/?fields=associated_images&%s'
EPISODES	    = '/cove/v1/videos/?fields=associated_images,program&filter_availability_status=Available&%s&filter_type=Episode&order_by=-airdate'
#The following URLs are used to pull json to build popular and searched show lists
SEARCH_URL	    = 'http://www.pbs.org/search-videos/?q=%s&callsign=&page=1'
SHOWS_JSON	    = 'http://www.pbs.org/shows-page/0/?genre=&title=&callsign=&alphabetically=false'

####################################################################################################
def Start():
  ObjectContainer.title1 = 'PBS'
  HTTP.CacheTime = CACHE_INTERVAL

####################################################################################################
@handler('/video/pbs', 'PBS')
def VideoMenu():
  oc = ObjectContainer(no_cache=True)
  oc.add(DirectoryObject(key=Callback(ProducePrograms, url=SHOWS_JSON, title='Popular Shows', filter='filter_title='), title='Popular Shows'))
  oc.add(DirectoryObject(key=Callback(ProducePrograms, url=PBS_URL, title='All PBS Programs', filter='filter_producer__name=', xpath='PBS'), title='All PBS Programs'))
  oc.add(InputDirectoryObject(key=Callback(ProducePrograms, url=SEARCH_URL, title='Search PBS Shows', filter='filter_title='), title='Search for PBS Shows', summary="Click here to search for shows", prompt="Search for the shows you would like to find"))
  oc.add(DirectoryObject(key=Callback(GetEpisodes, title='Videos Expiring Soon', filter='filter_expire_datetime__lt=', uri=''), title='Videos Expiring Soon'))
  oc.add(DirectoryObject(key=Callback(GetEpisodes, title='Latest Videos', filter='filter_available_datetime__gt=', uri=''), title='Latest Videos'))
  if Prefs['local']:
    oc.add(DirectoryObject(key=Callback(ProducePrograms, url=PBS_URL, title='Local Channel Shows', filter='filter_producer__name=', xpath=''), title='Local Channel Shows'))
  oc.add(SearchDirectoryObject(identifier="com.plexapp.plugins.pbs", title=L("Search PBS Videos"), prompt=L("Search for Videos")))
  oc.add(PrefsObject(title = L('Preferences')))

  return oc

####################################################################################################
# This function allows us to pull up shows using the API with different filters. That way we can always get the proper
# uri number needed to produce episodes in the EpisodeFind Function. We either use the title filter or producer filter
@route('/video/pbs/produceprograms')
def ProducePrograms(title, url, filter, xpath='', query=''):
  oc = ObjectContainer(title2=title)
  # This is for title filters. The titles are pulled from json by either a search or program json page
  # We construct the url for the show search and send them to functions to produce a list of titles
  if 'title' in filter:
    if query:
      url = url %String.Quote(query, usePlus = True)
      show_list = ProgramSearchJSON(url)
    else:
      show_list = ProgramListJSON(url)
  # This is for producer filters. We separate it by putting 'PBS' in the xpath field
  # so it either uses that xpath field or pulls the local producer filter from the Preferences
  else:
    if xpath:
      producer = xpath
    else:
      # Check the local PBS Call letters to make sure they are the right parameters
      producer = Prefs['local']
      if len(producer)!= 4 or not producer.isalpha():
        return ObjectContainer(header='Error', message='The Local PBS Station entered in Preferences is incorrect. Please enter a four letter code for your local station')
    # We then create a showlist of one, so the function will loop properly
    show_list = [producer]
  for show in show_list:
    show_filter = filter + show
    local_url = PROGRAMS %show_filter
    # there are over 400 listed shows in the main listing and we get them in chunks of 200. This loop makes sure we get that full list
    if show == "PBS":
      loop = ['','&limit_start=200','&limit_start=400'] 
    else:
      loop = ['']
    for i in loop:
      programs = PBS(String.Decode(API_ID), String.Decode(API_SECRET)).programs.get(local_url+i)
      for program in programs['results']:
        thumbs = SortThumbs(program['associated_images'])
        title = program['title']
        tagline = program['short_description']
        summary = program['long_description']
        uri = program['resource_uri']
        oc.add(DirectoryObject(key=Callback(GetEpisodes, uri=uri, title=title, filter='filter_program='), title=title, tagline=tagline, summary=summary, thumb=Resource.ContentsOfURLWithFallback(url=thumbs)))

  # these need proper sorting, the API doesn't give them to us in alphabetical order
  oc.objects.sort(key = lambda obj: obj.title)

  return oc

####################################################################################################
# This function allows us to pull up videos using the API with different filters. 
# We either use the program (uri) filter or date filter with one week lead time
# with the 'filter_available_datetime__gt' filters for latest and filter_expire_datetime__lt for expiring
@route('/video/pbs/episodes')
def GetEpisodes(uri, filter, title='Episodes'):
  oc = ObjectContainer(title2=title)
  if 'program' in filter:
    show_id = uri.split('/')[-2]
    show_filter = filter + show_id
 # else this is a datetime filter
  else:
    # set the date in YYYY-MM-DD format for one week from today or one week prior to today
    if 'expire' in filter:
      week_date = str(Datetime.Now().date() + Datetime.Delta(days=7))
    else:
      week_date = str(Datetime.Now().date() - Datetime.Delta(days=7))
    show_filter = filter + week_date
  local_url = EPISODES % show_filter
  # There is an issue with converting commas correctly, so do it manually here to prevent 401 errors
  local_url = local_url.replace(',', '%2C')
  videos = PBS(String.Decode(API_ID), String.Decode(API_SECRET)).programs.get(local_url)
  for video in videos['results']:
    thumbs = SortThumbs(video['associated_images'])
    show_title = video['program']['title']
    airdate = video['airdate']
    # Found an empty date so this prevent errors
    try: airdate = Datetime.ParseDate(airdate).date()
    except: airdate = None
    summary = video['long_description']
    title = video['title']
    uri = video['resource_uri']
    tp_id = video['tp_media_object_id']
    oc.add(VideoClipObject(
      url=PBS_VIDEO_URL % tp_id,
      title=title,
      source_title=show_title,
      summary=summary,
      originally_available_at=airdate,
      thumb=Resource.ContentsOfURLWithFallback(url=thumbs)
      ))
  
  if len(oc) == 0:
    return ObjectContainer(header='PBS', message='No Episodes found')
  else:
    return oc

####################################################################################################
@route('/video/pbs/programlistjson')
def ProgramListJSON(url):
  title_list = []
  json = JSON.ObjectFromURL(url)
  for show in json['results']['content']:
    relevance = show['popularity']
    if relevance < 30:
      title = show['title']
      api_title = String.Quote(title, usePlus = True)
      title_list.append(api_title)
  
  #Log('the len of title_list is %s' %len(title_list))
  return title_list  
####################################################################################################
@route('/video/pbs/programsearchjson')
def ProgramSearchJSON(url):
  title_list = []
  json = JSON.ObjectFromURL(url)
  for show in json['results']['shows']:
    title = show['title']
    api_title = String.Quote(title, usePlus = True)
    title_list.append(api_title)
  
  return title_list  
