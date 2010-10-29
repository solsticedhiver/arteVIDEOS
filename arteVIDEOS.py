#!/usr/bin/python2
# -*- coding: utf8 -*-

#             DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
#                     Version 2, December 2004
#
#  Copyright (C) 2010 solsTiCe d'Hiver <solstice.dhiver@gmail.com>
#
#  Everyone is permitted to copy and distribute verbatim or modified
#  copies of this license document, and changing it is allowed as long
#  as the name is changed.
#
#             DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
#    TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION
#
#   0. You just DO WHAT THE FUCK YOU WANT TO.

from sys import exit, argv, stderr
try:
    from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
except ImportError:
    print >> stderr, 'Error: you need BeautifulSoup python module'
    exit(1)
import urllib2
from urllib import unquote
import urlparse
import os
from subprocess import Popen, PIPE
from optparse import OptionParser
from cmd import Cmd

VERSION = '0.3'
DEFAULT_LANG = 'fr'
QUALITY = ('sd', 'hd')
DEFAULT_QUALITY = 'hd'
DEFAULT_DLDIR = os.getcwd()
# You could add your favorite player at the beginning of the PLAYERS tuple
# It must follow the template:
# ('executable to look for', 'command to read from stdin')
# the order is significant i.e. the players are looked for in this order
PLAYERS = (
        ('mplayer', 'mplayer -really-quiet -'),
        ('vlc', 'vlc -'),
        ('xine', 'xine stdin:/'),
        ('totem', 'totem fd://0'),
        )

CLSID = 'clsid:d27cdb6e-ae6d-11cf-96b8-444553540000'
DOMAIN = 'http://videos.arte.tv'
VIDEO_PER_PAGE = 25
HOME_URL = DOMAIN + '/%%s/videos#/tv/thumb///1/%d/' % VIDEO_PER_PAGE
SEARCH_URL = DOMAIN + '/%%s/do_search/videos/%%s/index-3188352,view,searchResult.html?itemsPerPage=%d&pageNr=%%s&q=' % VIDEO_PER_PAGE
FILTER_URL = DOMAIN + '/%s/do_delegate/videos/index-3188698,view,asThumbnail.html'

QUERY_STRING = '?hash=tv/thumb///%%s/%d/' % VIDEO_PER_PAGE
SEARCH = {'fr': 'recherche', 'de':'suche', 'en': 'search'}
LANG = SEARCH.keys()
ALL_VIDEOS = {'fr':'toutesLesVideos', 'de':'alleVideos', 'en':'allVideos'}
PROGRAMS = {'fr':'programmes', 'de':'sendungen', 'en':'programs'}
GENERIC_URL = 'http://videos.arte.tv/%s/videos/%s'
EVENTS_PAGE = 'events/index-3188672.html'
HIST_CMD = ('plus7', 'programs', 'events', 'allvideos', 'search')

BOLD   = '[1m'
NC     = '[0m'    # no color

class Navigator(object):
    def __init__(self, options):
        self.options = options
        self.events = None
        self.allvideos = None
        self.programs = None
        self.more = False
        self.last_cmd = ''
        self.page = 0

        # holds last search result from any command (list, program, search)
        self.results = []

    def __getitem__(self, key):
        indx = int(key)-1
        return self.results[indx/VIDEO_PER_PAGE][indx % VIDEO_PER_PAGE]

    def extra_help(self):
        if len(self.results) == 0:
            print >> stderr, 'You need to run either a list, search or program command first'

    def get_events(self):
        '''get events'''
        if self.events is not None:
            return
        try:
            print ':: Retrieving events list'
            url = GENERIC_URL % (self.options.lang, EVENTS_PAGE)
            soup = BeautifulSoup(urllib2.urlopen(url).read(), convertEntities=BeautifulSoup.ALL_ENTITIES)
            # get the events
            lis = soup.find('div', {'id': 'listChannel'}).findAll('li')
            events, urls = [], []
            for l in lis:
                a = l.find('a')
                events.append(a.contents[0])
                urls.append(a['href'])
            if events != []:
                self.events = zip(events, urls)
            else:
                self.events = None
        except urllib2.URLError:
            die("Can't get the home page of arte+7")
        return None

    def event(self, arg):
        '''get a list of videos for given event'''
        ev = int(arg) - 1
        if not self.more:
            self.page = 0
            self.results = []
        try:
            url = DOMAIN + self.events[ev][1]
            soup = unicode(BeautifulSoup(urllib2.urlopen(url).read(), convertEntities=BeautifulSoup.ALL_ENTITIES))
            try:
                start = soup.index('thumbnailViewUrl: "')+19
            except ValueError:
                print >> stderr, 'Error: when parsing the page'
                self.results[self.page] = []
                return
            url = DOMAIN + soup[start:soup.index('"', start)] + QUERY_STRING % (self.page+1,)
            soup = BeautifulSoup(urllib2.urlopen(url).read(), convertEntities=BeautifulSoup.ALL_ENTITIES)
            self.results.append(extract_videos(soup))
        except urllib2.URLError:
            die("Can't complete the requested search")

    def get_allvideos(self):
        '''get allvideos'''
        if self.allvideos is not None:
            return
        try:
            print ':: Retrieving all videos list'
            url = GENERIC_URL % (self.options.lang, ALL_VIDEOS[self.options.lang])
            soup = BeautifulSoup(urllib2.urlopen(url).read(), convertEntities=BeautifulSoup.ALL_ENTITIES)
            # get the channels
            lis = soup.find('div', {'id': 'listChannel'}).findAll('li')
            allvideos, urls = [], []
            for l in lis:
                a = l.find('a')
                allvideos.append(a.contents[0])
                urls.append(a['href'])
            if allvideos != []:
                self.allvideos = zip(allvideos, urls)
            else:
                self.allvideos = None
        except urllib2.URLError:
            die("Can't get the home page of arte+7")
        return None

    def allvideo(self, arg):
        '''get a list of videos for given event'''
        v = int(arg) - 1
        if not self.more:
            self.page = 0
            self.results = []
        try:
            url = DOMAIN + self.allvideos[v][1]
            soup = unicode(BeautifulSoup(urllib2.urlopen(url).read(), convertEntities=BeautifulSoup.ALL_ENTITIES))
            try:
                start = soup.index('thumbnailViewUrl: "')+19
            except ValueError:
                print >> stderr, 'Error: when parsing the page'
                self.results[self.page-1] = []
                return
            url = DOMAIN + soup[start:soup.index('"', start)] + QUERY_STRING % (self.page+1,)
            soup = BeautifulSoup(urllib2.urlopen(url).read(), convertEntities=BeautifulSoup.ALL_ENTITIES)
            self.results.append(extract_videos(soup))
        except urllib2.URLError:
            die("Can't complete the requested search")

    def get_programs(self):
        '''get programs'''
        if self.programs is not None:
            return
        try:
            print ':: Retrieving programs list'
            url = GENERIC_URL % (self.options.lang, PROGRAMS[self.options.lang])
            soup = BeautifulSoup(urllib2.urlopen(url).read(), convertEntities=BeautifulSoup.ALL_ENTITIES)
            # get the programs
            lis = soup.find('div', {'id': 'listChannel'}).findAll('li')
            programs, urls = [], []
            for l in lis:
                a = l.find('a')
                programs.append(a.contents[0])
                urls.append(a['href'])
            if programs != []:
                self.programs = zip(programs, urls)
            else:
                self.programs = None
        except urllib2.URLError:
            die("Can't get the home page of arte+7")
        return None

    def program(self, arg):
        '''get a list of videos for given program'''
        pr = int(arg) - 1
        if not self.more:
            self.page = 0
            self.results = []
        try:
            url = DOMAIN + self.programs[pr][1]
            soup = unicode(BeautifulSoup(urllib2.urlopen(url).read(), convertEntities=BeautifulSoup.ALL_ENTITIES))
            start = soup.index('thumbnailViewUrl: "')+19
            url = DOMAIN + soup[start:soup.index('"', start)] + QUERY_STRING % (self.page+1,)
            soup = BeautifulSoup(urllib2.urlopen(url).read(), convertEntities=BeautifulSoup.ALL_ENTITIES)
            self.results.append(extract_videos(soup))
        except urllib2.URLError:
            die("Can't complete the requested search")

    def search(self, s):
        '''search videos matching string s'''
        if not self.more:
            self.page = 0
            self.results = []
        try:
            url = SEARCH_URL % (self.options.lang, SEARCH[self.options.lang], self.page+1) + s.replace(' ', '+')
            soup = BeautifulSoup(urllib2.urlopen(url).read(), convertEntities=BeautifulSoup.ALL_ENTITIES)
            self.results.append(extract_videos(soup))
        except urllib2.URLError:
            die("Can't complete the requested search")

    def get_plus7(self):
        '''get the list of videos from url'''
        if not self.more:
            self.page = 0
            self.results = []
        try:
            url = FILTER_URL % self.options.lang + QUERY_STRING % (self.page+1,)
            soup = BeautifulSoup(urllib2.urlopen(url).read(), convertEntities=BeautifulSoup.ALL_ENTITIES)
            self.results.append(extract_videos(soup))
        except urllib2.URLError:
            die("Can't get the home page of arte+7")

    def clear_info(self):
        self.events = None
        self.allvideos = None
        self.programs = None
        self.last_cmd = ''
        self.page = 0
        self.results = []

class MyCmd(Cmd):
    def __init__(self, options, nav=None):
        Cmd.__init__(self)
        self.prompt = 'arteVIDEOS> '
        self.intro = '\nType "help" to see available commands.'
        if nav is None:
            self.nav = Navigator(options)
        else:
            self.nav = nav

    def postcmd(self, stop, line):
        if line.startswith(HIST_CMD):
            self.nav.last_cmd = line
        return stop

    def do_previous(self, arg):
        if self.nav.last_cmd.startswith(HIST_CMD) and self.nav.page > 0:
            self.nav.page -= 1
            print_results(self.nav.results[self.nav.page], page=self.nav.page)
        return False

    def do_next(self, arg):
        if self.nav.last_cmd.startswith(HIST_CMD):
            self.nav.page += 1
            if self.nav.page > len(self.nav.results)-1:
                self.nav.more = True
                self.onecmd(self.nav.last_cmd)
                self.nav.more = False
            else:
                print_results(self.nav.results[self.nav.page], page=self.nav.page)
        return False

    def do_url(self, arg):
        '''url NUMBER
    show the url of the chosen video'''
        try:
            video = self.nav[arg]
            if 'rtmp_url' not in video:
                get_video_player_info(video, self.nav.options)
            print video['rtmp_url']
        except ValueError:
            print >> stderr, 'Error: wrong argument (must be an integer)'
        except IndexError:
            print >> stderr, 'Error: no video with this number'
            self.nav.extra_help()

    def do_player_url(self, arg):
        '''player_url NUMBER
    show the Flash player url of the chosen video'''
        try:
            video = self.nav[arg]
            if 'player_url' not in video:
                get_video_player_info(video, self.nav.options)
            print video['player_url']
        except ValueError:
            print >> stderr, 'Error: wrong argument (must be an integer)'
        except IndexError:
            print >> stderr, 'Error: no video with this number'
            self.nav.extra_help()

    def do_info(self, arg):
        '''info NUMBER
        display details about chosen video'''
        try:
            video = self.nav[arg]
            if 'info' not in video:
                get_video_player_info(video, self.nav.options)
            print '%s== %s ==%s'% (BOLD, video['title'], NC)
            print video['info']
        except ValueError:
            print >> stderr, 'Error: wrong argument (must be an integer)'
        except IndexError:
            print >> stderr, 'Error: no video with this number'
            self.nav.extra_help()

    def do_play(self, arg):
        '''play NUMBER [NUMBER] ...
    play the chosen videos'''
        playlist = []
        for i in arg.split():
            try:
                playlist.append(self.nav[i])
            except ValueError:
                print >> stderr, '"%s": wrong argument, must be an integer' % i
                return
            except IndexError:
                print >> stderr, 'Error: no video with this number: %s' % i
                self.nav.extra_help()
                return
        print ':: Playing video(s): ' + ', '.join('#%s' % i for i in arg.split())
        for v in playlist:
            play(v, self.nav.options)

    def do_record(self, arg):
        '''record NUMBER [NUMBER] ...
    record the chosen videos to a local file'''
        playlist = []
        for i in arg.split():
            try:
                playlist.append(self.nav[i])
            except ValueError:
                print >> stderr, '"%s": wrong argument, must be an integer' % i
                return
            except IndexError:
                print >> stderr, 'Error: no video with this number: %d' % i
                self.extra_help()
                return
        print ':: Recording video(s): ' + ', '.join('#%s' % i for i in arg.split())
        # TODO: do that in parallel ?
        for v in playlist:
            record(v, self.nav.options)

    def do_search(self, arg):
        '''search STRING
    search for a given STRING on arte+7 web site'''
        self.nav.search(arg)
        print_results(self.nav.results[self.nav.page], page=self.nav.page)

    def complete_lang(self, text, line, begidx, endidx):
        if text == '':
            return LANG
        elif text.startswith('d'):
            return ('de',)
        elif text.startswith('f'):
            return('fr',)
        elif text.startswith('e'):
            return('en',)

    def do_lang(self, arg):
        '''lang [fr|de|en]
    display or switch to a different language'''
        if arg == '':
            print self.nav.options.lang
        elif arg in LANG:
            self.nav.options.lang = arg
            self.nav.clear_info()
        else:
            print >> stderr, 'Error: lang could be %s' % ','.join(LANG)

    def complete_quality(self, text, line, begidx, endidx):
        if text == '':
            return QUALITY
        elif text.startswith('s'):
            return ('sd',)
        elif text.startswith('h'):
            return('hd',)

    def do_quality(self, arg):
        '''quality [sd|hd]
    display or switch to a different quality'''
        if arg == '':
            print self.options.quality
        elif arg in QUALITY:
            self.nav.options.quality = arg
            self.nav.clear_info()
        else:
            print >> stderr, 'Error: quality could be %s' % ','.join(QUALITY)

    def do_plus7(self, arg):
        '''list [more]
    list 25 videos from the home page'''
        print ':: Retrieving plus7 videos list'
        self.nav.get_plus7()
        print_results(self.nav.results[self.nav.page], page=self.nav.page)

    def do_allvideos(self, arg):
        '''allvideos [NUMBER] ...
    display available videos or search for given videos(s)'''
        self.nav.get_allvideos()
        if arg == '':
            print '\n'.join('(%d) %s' % (i+1, self.nav.allvideos[i][0]) for i in range(len(self.nav.allvideos)))
        else:
            try:
                self.nav.allvideo(arg)
                print_results(self.nav.results[self.nav.page], page=self.nav.page)
            except IndexError:
                print >> stderr, 'Error: unknown channel'
            except ValueError:
                print >> stderr, 'Error: wrong argument; must be an integer'

    def do_events(self, arg):
        '''events [NUMBER] ...
    display available events or search video for given event(s)'''
        self.nav.get_events()
        if arg == '':
            print '\n'.join('(%d) %s' % (i+1, self.nav.events[i][0]) for i in range(len(self.nav.events)))
        else:
            try:
                self.nav.event(arg)
                print_results(self.nav.results[self.nav.page], page=self.nav.page)
            except IndexError:
                print >> stderr, 'Error: unknown events'
            except ValueError:
                print >> stderr, 'Error: wrong argument; must be an integer'

    def do_programs(self, arg):
        '''programs [NUMBER] ...
    display available programs or search video for given program(s)'''
        # try to get them from home page
        self.nav.get_programs()
        if arg == '':
            print '\n'.join('(%d) %s' % (i+1, self.nav.programs[i][0]) for i in range(len(self.nav.programs)))
        else:
            try:
                self.nav.program(arg)
                print_results(self.nav.results[self.nav.page], page=self.nav.page)
            except IndexError:
                print >> stderr, 'Error: unknown program'
            except ValueError:
                print >> stderr, 'Error: wrong argument; must be an integer'

    def do_dldir(self,arg):
        '''dldir [PATH] ...
    display or change download directory'''
        if arg == '':
            print self.nav.options.dldir
            return
        arg = expand_path(arg) # resolve environment variables and '~'s
        if not os.path.exists(arg):
            print >> stderr, 'Error: wrong argument; must be a valid path'
        else:
            self.nav.options.dldir = arg

    def do_help(self, arg):
        '''print the help'''
        if arg == '':
            print '''COMMANDS:
    plus7            list videos from arte+7
    allvideos        list videos from allvideos tab
    events           list videos from events tab
    programs         list videos from programs tab
    search STRING    search for a video

    next             list videos of the next page
    previous         list videos of previous page

    url NUMBER       show url of video
    play NUMBERS     play chosen videos
    record NUMBERS   download and save videos to a local file
    info NUMBER      display details about given video

    dldir [PATH]     display or change download directory
    lang [fr|de|en]  display or switch to a different language
    quality [sd|hd]  display or switch to a different video quality

    help             show this help
    quit             quit the cli
    exit             exit the cli'''
        else:
            try:
                print getattr(self, 'do_'+arg).__doc__
            except AttributeError:
                print >> stderr, 'Error: no help for command %s' % arg

    def do_quit(self, arg):
        '''quit the command line interpreter'''
        return True

    def do_exit(self, arg):
        '''exit the command line interpreter'''
        return True

    def do_EOF(self, arg):
        '''exit the command line interpreter'''
        print
        return True

    def default(self, arg):
        print >> stderr, 'Error: don\'t know how to %s' % arg

    def emptyline(self):
        pass

def die(msg):
    print >> stderr, 'Error: %s. See %s --help' % (msg, argv[0])
    exit(1)

def get_rtmp_url(url_page, quality='hd', lang='fr'):
    '''get the rtmp url of the video and player url and info about video and soup'''
    # inspired by the get_rtmp_url from arte7recorder project

    # get the web page
    try:
        first_soup = soup = BeautifulSoup(urllib2.urlopen(url_page).read())
        info = extract_info(soup)
        object_tag = soup.find('object', classid=CLSID)
        # get the player_url straight from it
        player_url = unquote(object_tag.find('embed')['src'])

        try:
            # if they decide to use jwPlayer
            flashvars = urlparse.parse_qs(object_tag.find('param', {'name':'flashvars'})['value'])
            rtmp_url = flashvars['streamer'][0]+flashvars['file'][0]
        except TypeError:
            # the OLD way - we need a few jumps to get to the correct url
            flashvars = urlparse.parse_qs(object_tag.find('param', {'name':'movie'})['value'])
            # first xml file
            soup = BeautifulStoneSoup(urllib2.urlopen(flashvars['videorefFileUrl'][0]).read())
            videos_list = soup.findAll('video')
            videos = {}
            for v in videos_list:
                videos[v['lang']] = v['ref']
            if lang not in videos:
                print >> stderr, 'The video in not available in the language %s. Using the default one' % lang
                if DEFAULT_LANG in videos:
                    xml_url = videos[DEFAULT_LANG]
                else:
                    xml_url = videos.popitem()[1]
            else:
                xml_url = videos[lang]
            # second xml file
            soup = BeautifulStoneSoup(urllib2.urlopen(xml_url).read())
            # at last the video url
            url = soup.urls.find('url', {'quality': quality})
            if url is None:
                url = soup.urls.find('url')[0]
                print >> stderr, "Can't find the desired quality. Using the first one found"
            rtmp_url = url.string

        return (rtmp_url, player_url, info)
    except urllib2.URLError:
        die('Invalid URL')

def get_video_player_info(video, options):
    '''get various info from page of video: *modify* video variable'''
    print ':: Retrieving video data'
    r, p, i = get_rtmp_url(video['url'], quality=options.quality, lang=options.lang)
    video['rtmp_url'] = r
    video['player_url'] = p
    video['info'] = i

def extract_videos(soup):
    '''extract list of videos title, url, and teaser from video_soup'''
    videos = []
    video_soup = soup.findAll('div', {'class': 'video'})
    for v in video_soup:
        teaserNode = v.find('p', {'class': 'teaserText'})
        teaser = teaserNode.string if teaserNode is not None else ''
        try:
            a = v.find('h2').a
        except AttributeError:
            # ignore bottom videos
            continue
        try:
            videos.append({'title':a.contents[0], 'url':DOMAIN+a['href'], 'teaser':teaser})
        except IndexError:
            # empty title ??
            videos.append({'title':'== NO TITLE ==', 'url':DOMAIN+a['href'], 'teaser':teaser})
    return videos

def extract_info(soup):
    '''extract info about video from soup'''
    rtc = soup.find('div', {'class':'recentTracksCont'})
    s = ''
    for i in rtc.div.findAll('p'):
        s += '\n'.join(j.string for j in i if j.string is not None)
    s += '\n\n'
    more = rtc.find('div', {'id':'more'}).findAll('p')
    for i in more:
        s += ' '.join(j.string for j in i if j.string is not None).replace('\n ', '\n')
    s = s.strip('\n').replace('\n\n\n', '\n\n')
    return s

def print_results(results, verbose=True, page=1):
    '''print list of video:
    title in bold with a number followed by teaser'''
    for i in range(len(results)):
        print '%s(%d) %s'% (BOLD, i+1+VIDEO_PER_PAGE*page, results[i]['title'] + NC)
        if verbose:
            print '    '+ results[i]['teaser']
    if len(results) == 0:
        print ':: the search returned nothing'

def play(video, options):
    cmd_args = make_cmd_args(video, options, streaming=True)
    player_cmd = find_player(PLAYERS)

    if player_cmd is not None:
        p1 = Popen(['rtmpdump'] + cmd_args.split(' '), stdout=PIPE)
        p2 = Popen(player_cmd.split(' '), stdin=p1.stdout, stderr=PIPE)
        p2.wait()
        # kill the zombie rtmpdump
        try:
            p1.kill()
            p1.wait()
        except AttributeError:
            # if we use python 2.5
            from signal import SIGKILL
            from os import kill, waitpid
            kill(p1.pid, SIGKILL)
            waitpid(p1.pid, 0)
    else:
        print >> stderr, 'Error: no player has been found.'

def record(video, options):
    cwd = os.getcwd()
    os.chdir(options.dldir)
    cmd_args = make_cmd_args(video, options)
    p = Popen(['rtmpdump'] + cmd_args.split(' '))
    os.chdir(cwd)
    p.wait()

def make_cmd_args(video, options, streaming=False):
    if not find_in_path(os.environ['PATH'], 'rtmpdump'):
        print >> stderr, 'Error: rtmpdump has not been found'
        exit(1)

    if 'rtmp_url' not in video:
        get_video_player_info(video, options)
    output_file = None
    if not streaming:
        output_file = urlparse.urlparse(video['url']).path.split('/')[-1]
        output_file = output_file.replace('.html', '_%s_%s.flv' % (options.quality, options.lang))
        cmd_args = '--rtmp %s --flv %s --swfVfy %s' % (video['rtmp_url'], output_file, video['player_url'])
    else:
        cmd_args = '--rtmp %s --swfVfy %s' % (video['rtmp_url'], video['player_url'])
    if not options.verbose:
        cmd_args += ' --quiet'

    if not streaming:
        if os.path.exists(output_file):
            # try to resume a download
            cmd_args += ' --resume'
            print ':: Resuming download of %s' % output_file
        else:
            print ':: Downloading to %s' % output_file
    else:
        print ':: Streaming from %s' % video['rtmp_url']

    return cmd_args

def expand_path(path):
    if '~' in path:
        path = os.path.expanduser(path)
    if ('$' in path) or ('%' in path):
        path = os.path.expandvars(path)
    return path

def find_in_path(path, filename):
    '''is filename in $PATH ?'''
    for i in path.split(':'):
        if os.path.exists('/'.join([i, filename])):
            return True
    return False

def find_player(d):
    for e, c in d:
        if find_in_path(os.environ['PATH'], e):
            return c
    return None

def main():
    usage = '''Usage: %prog url|play|record [OPTIONS] URL
       %prog search [OPTIONS] STRING...
       %prog

Play or record videos from arte VIDEOS website without a mandatory browser.

In the first form, you need the url of the video page
In the second form, just enter your search term
In the last form (without any argument), you enter an interactive interpreter
(type help to get a list of available commands, once in the interpreter)

COMMANDS
    url     show the url of the video
    play    play the video directly
    record  save the video into a local file
    search  search for a video on arte+7
            It will display a numbered list of results and enter
            a simple command line interpreter'''

    parser = OptionParser(usage=usage)
    parser.add_option('-d', '--downloaddir', dest='dldir', type='string',
            default=DEFAULT_DLDIR, action='store', help='directory for downloads')
    parser.add_option('-l', '--lang', dest='lang', type='string', default=DEFAULT_LANG,
            action='store', help='language of the video fr, de, en (default: fr)')
    parser.add_option('-q', '--quality', dest='quality', type='string', default=DEFAULT_QUALITY,
            action='store', help='quality of the video sd or hd (default: hd)')
    parser.add_option('--verbose', dest='verbose', default=False,
            action='store_true', help='show output of rtmpdump')

    options, args = parser.parse_args()

    if not os.path.exists(options.dldir):
        die('Invalid Path')
    if options.lang not in ('fr', 'de', 'en'):
        die('Invalid option')
    if options.quality not in ('sd', 'hd'):
        die('Invalid option')
    if len(args) < 2:
        MyCmd(options).cmdloop()
        exit(0)
    if args[0] not in ('url', 'play', 'record', 'search'):
        die('Invalid command')

    if args[0] == 'url':
        print get_rtmp_url(args[1], quality=options.quality, lang=options.lang)[0]

    elif args[0] == 'play':
        play({'url':args[1]}, options)
        exit(1)

    elif args[0] == 'record':
        record({'url':args[1]}, options)

    elif args[0] == 'search':
        term = ' '.join(args[1:])
        print ':: Searching for "%s"' % term
        nav = Navigator(options)
        nav.search(term)
        if nav.results is not None:
            print_results(nav.results)
            MyCmd(options, nav=nav).cmdloop()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print '\nAborted'
