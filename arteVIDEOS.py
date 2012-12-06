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

########################################################################
#                           PLAYERS                                    #
########################################################################
# You can add your favorite player at the beginning of the PLAYERS tuple
# The command must read data from stdin
# The order is significant: the first player available is used
PLAYERS = (
        'mplayer -really-quiet -',
        'vlc -',
        'xine stdin:/',
        '/usr/bin/totem --enqueue fd://0', # you could use absolute path for the command too
        )

DEFAULT_LANG = 'fr'
DEFAULT_QUALITY = 'hd'
########################################################################
# DO NOT MODIFY below this line unless you know what you are doing     #
########################################################################

import sys
try:
    from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
except ImportError:
    print >> sys.stderr, 'Error: you need the BeautifulSoup(v3) python module'
    sys.exit(1)
import urllib2
from urllib import unquote
import urlparse
import os
import subprocess
from optparse import OptionParser
from cmd import Cmd

VERSION = '0.3.2'
QUALITY = ('sd', 'hd')
DEFAULT_DLDIR = os.getcwd()

CLSID = 'clsid:d27cdb6e-ae6d-11cf-96b8-444553540000'
VIDEO_PER_PAGE = 50
DOMAIN = 'http://videos.arte.tv'
GENERIC_URL = DOMAIN + '/%s/videos/%s'
HOME_URL = DOMAIN + '/%%s/videos#/tv/thumb///1/%d/' % VIDEO_PER_PAGE
SEARCH_URL = DOMAIN + '/%%s/do_search/videos/%%s/index--3188352,view,searchResult.html?itemsPerPage=%d&pageNr=%%s&q=' % VIDEO_PER_PAGE
FILTER_URL = DOMAIN + '/%s/do_delegate/videos/index--3188698,view,asThumbnail.html'

QUERY_STRING = '?hash=tv/thumb///%%s/%d/' % VIDEO_PER_PAGE
EVENTS_PAGE = 'events/index--3188672.html'

SEARCH = {'fr': 'recherche', 'de':'suche', 'en': 'search'}
LANG = SEARCH.keys()
ALL_VIDEOS = {'fr':'toutesLesVideos', 'de':'alleVideos', 'en':'allVideos'}
PROGRAMS = {'fr':'programmes', 'de':'sendungen', 'en':'programs'}
HIST_CMD = ('plus7', 'programs', 'events', 'allvideos', 'search')

BOLD   = '[1m'
NC     = '[0m'    # no color

class Video(object):
    '''Store info about a given cideo'''
    def __init__(self, url, title, teaser, options):
        self.title = title
        self.url = url
        self.teaser = teaser
        self.options = options
        self._info = None
        self._player_url = None
        self._rtmp_url = None
        self._flv = None
        self._mp4 = None

    def get_data(self):
        print ':: Retrieving video info',
        sys.stdout.flush()
        self._rtmp_url, self._player_url, self._info = get_rtmp_url(self.url, quality=self.options.quality, lang=self.options.lang)
        sys.stdout.write('\r')
        sys.stdout.flush()

    # automatic retrieval of video info if a property is not defined
    @property
    def info(self):
        if self._info is None:
            self.get_data()
        return self._info

    @property
    def player_url(self):
        if self._player_url is None:
            self.get_data()
        return self._player_url

    @property
    def rtmp_url(self):
        if self._rtmp_url is None:
            self.get_data()
        return self._rtmp_url

    @property
    def flv(self):
        '''create output file name'''
        if self._flv is None:
            flv = urlparse.urlparse(self.url).path.split('/')[-1]
            self._flv = flv.replace('.html', '_%s_%s.flv' % (self.options.quality, self.options.lang))
        return self._flv

    @property
    def mp4(self):
        if self._mp4 is None:
            self._mp4 = self.flv.replace('.flv', '.mp4')
        return self._mp4

class Results(object):
    '''Holds a list of results from a request to server'''
    def __init__(self, video_per_page):
        ''' a wrapper around list instead of inhereting from it'''
        self.__value = []
        self.page = 0
        self.video_per_page = video_per_page

    def __getitem__(self, k):
        return self.__value[k]

    def __setitem__(self, k, v):
        self.__value[k] = v

    def __len__(self):
        return len(self.__value)

    def extend(self, L):
        self.__value.extend(L)

    def print_page(self, verbose=True):
        '''print list of video:
        title in bold with a number followed by teaser'''
        for i in range(min(self.video_per_page, len(self.__value)-self.page*self.video_per_page)):
            nb = i+self.video_per_page*self.page
            print '%s(%d) %s'% (BOLD, nb+1, self.__value[nb].title + NC)
            if verbose:
                print '    '+ self.__value[nb].teaser

class Navigator(object):
    '''Main object storing all info requested from server and help navigation'''
    def __init__(self, options):
        self.options = options
        self.events = None
        self.allvideos = None
        self.programs = None
        self.more = False
        self.last_cmd = ''
        self.npage = 1
        self.video_per_page = options.video_per_page
        self.stop = False
        # holds last search result from any command (list, program, search)
        self.results = Results(self.video_per_page)

    def clear_info(self):
        self.events = None
        self.allvideos = None
        self.programs = None
        self.last_cmd = ''
        self.npage = 1
        self.stop = False
        self.results = Results(self.video_per_page)

    def __getitem__(self, key):
        indx = int(key)-1
        return self.results[indx]

    def extra_help(self):
        if len(self.results) == 0:
            print >> sys.stderr, 'You need to run either a plus7, search or program command first'

    def request(self, url, indirect=False):
        if not self.more:
            self.npage = 1
            self.stop = False
            self.results = Results(self.video_per_page)
        try:
            soup = BeautifulSoup(urllib2.urlopen(url).read(), convertEntities=BeautifulSoup.ALL_ENTITIES)
            if indirect:
                try:
                    soup = unicode(soup)
                    start = soup.index('thumbnailViewUrl: "')+19
                    url = DOMAIN + soup[start:soup.index('"', start)] + QUERY_STRING % (self.npage,)
                    soup = BeautifulSoup(urllib2.urlopen(url).read(), convertEntities=BeautifulSoup.ALL_ENTITIES)
                except ValueError:
                    print >> sys.stderr, 'Error: when parsing the page'
                    return
            videos = extract_videos(soup, self.options)
            if len(videos) < VIDEO_PER_PAGE:
                self.stop = True
            self.results.extend(videos)
        except urllib2.URLError:
            die("Can't complete request")

    def event(self, arg):
        '''get a list of videos for given event'''
        ev = int(arg) - 1
        url = DOMAIN + self.events[ev][1]
        print ':: Retrieving events list'
        self.request(url, indirect=True)

    def program(self, arg):
        '''get a list of videos for given program'''
        pr = int(arg) - 1
        url = DOMAIN + self.programs[pr][1]
        print ':: Retrieving requested program list'
        self.request(url, indirect=True)

    def search(self, s):
        '''search videos matching string s'''
        url = SEARCH_URL % (self.options.lang, SEARCH[self.options.lang], self.npage) + s.replace(' ', '+')
        print ':: Waiting for search request'
        self.request(url)

    def allvideo(self, arg):
        '''get a list of all videos'''
        v = int(arg) - 1
        url = DOMAIN + self.allvideos[v][1]
        print ':: Retrieving requested video list'
        self.request(url)

    def plus7(self):
        '''get the list of videos from url'''
        url = FILTER_URL % self.options.lang + QUERY_STRING % (self.npage,)
        print ':: Retrieving plus7 videos list'
        self.request(url)

    def get_events(self):
        '''get events'''
        if self.events is not None:
            return
        try:
            print ':: Retrieving events name'
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

    def get_programs(self):
        '''get programs'''
        if self.programs is not None:
            return
        try:
            print ':: Retrieving programs name'
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

    def get_allvideos(self):
        '''get allvideos'''
        if self.allvideos is not None:
            return
        try:
            print ':: Retrieving all videos categories'
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

class MyCmd(Cmd):
    '''cli interpreter object'''
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

    def do_video_per_page(self, arg):
        '''show or specify the number of video to be displayed per screen'''
        if arg == '':
            print self.nav.results.video_per_page
        else:
            try:
                self.nav.results.video_per_page = int(arg)
                self.nav.results.page = 0
                print ':: Current page is now #1'
                if self.nav.results is not None:
                    self.nav.results.print_page()
            except VelueError:
                print >> sys.stderr, 'Error: argument should be a number'

    def do_previous(self, arg):
        if self.nav.last_cmd.startswith(HIST_CMD) and self.nav.results.page >= 0:
            self.nav.results.page -= 1
            self.nav.results.print_page()
        return False

    def do_next(self, arg):
        if self.nav.last_cmd.startswith(HIST_CMD):
            if self.nav.results.page == len(self.nav.results)/self.nav.results.video_per_page and self.nav.stop:
                print ':: No more results found'
            else:
                self.nav.results.page += 1
                if (self.nav.results.page+1)*self.nav.results.video_per_page <= len(self.nav.results) or self.nav.stop:
                    self.nav.results.print_page()
                else:
                    self.nav.more = True
                    self.nav.npage += 1
                    self.onecmd(self.nav.last_cmd)
                    self.nav.more = False
        return False

    def do_url(self, arg):
        '''url NUMBER
    show the url of the chosen video'''
        try:
            video = self.nav[arg]
            print video.rtmp_url
        except ValueError:
            print >> sys.stderr, 'Error: wrong argument (must be an integer)'
        except IndexError:
            print >> sys.stderr, 'Error: no video with this number'
            self.nav.extra_help()

    def do_player_url(self, arg):
        '''player_url NUMBER
    show the Flash player url of the chosen video'''
        try:
            video = self.nav[arg]
            print video.player_url
        except ValueError:
            print >> sys.stderr, 'Error: wrong argument (must be an integer)'
        except IndexError:
            print >> sys.stderr, 'Error: no video with this number'
            self.nav.extra_help()

    def do_info(self, arg):
        '''info NUMBER
        display details about chosen video'''
        try:
            video = self.nav[arg]
            print '%s== %s ==%s'% (BOLD, video.title, NC)
            print video.info
        except ValueError:
            print >> sys.stderr, 'Error: wrong argument (must be an integer)'
        except IndexError:
            print >> sys.stderr, 'Error: no video with this number'
            self.nav.extra_help()

    def do_play(self, arg):
        '''play NUMBER [NUMBER] ...
    play the chosen videos'''
        playlist = []
        for i in arg.split():
            try:
                playlist.append(self.nav[i])
            except ValueError:
                print >> sys.stderr, '"%s": wrong argument, must be an integer' % i
                return
            except IndexError:
                print >> sys.stderr, 'Error: no video with this number: %s' % i
                self.nav.extra_help()
                return
        print ':: Playing video(s): ' + ', '.join('#%s' % i for i in arg.split())
        for v in playlist:
            play(v)

    def do_record(self, arg):
        '''record NUMBER [NUMBER] ...
    record the chosen videos to a local file'''
        playlist = []
        for i in arg.split():
            try:
                playlist.append(self.nav[i])
            except ValueError:
                print >> sys.stderr, '"%s": wrong argument, must be an integer' % i
                return
            except IndexError:
                print >> sys.stderr, 'Error: no video with this number: %s' % i
                self.nav.extra_help()
                return
        print ':: Recording video(s): ' + ', '.join('#%s' % i for i in arg.split())
        # TODO: do that in parallel ?
        for v in playlist:
            record(v, self.nav.options.dldir)

    def do_search(self, arg):
        '''search STRING
    search for a given STRING on arte+7 web site'''
        self.nav.search(arg)
        self.nav.results.print_page()

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
            print >> sys.stderr, 'Error: lang could be %s' % ','.join(LANG)

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
            print self.nav.options.quality
        elif arg in QUALITY:
            self.nav.options.quality = arg
            self.nav.clear_info()
            print ':: All lists/results have been cleared'
        else:
            print >> sys.stderr, 'Error: quality could be %s' % ','.join(QUALITY)

    def do_plus7(self, arg):
        '''list [more]
    list 25 videos from the home page'''
        self.nav.plus7()
        self.nav.results.print_page()

    def do_allvideos(self, arg):
        '''allvideos [NUMBER] ...
    display available videos or search for given videos(s)'''
        self.nav.get_allvideos()
        if arg == '':
            print '\n'.join('(%d) %s' % (i+1, self.nav.allvideos[i][0]) for i in range(len(self.nav.allvideos)))
        else:
            try:
                self.nav.allvideo(arg)
                self.nav.results.print_page()
            except IndexError:
                print >> sys.stderr, 'Error: unknown channel'
            except ValueError:
                print >> sys.stderr, 'Error: wrong argument; must be an integer'

    def do_events(self, arg):
        '''events [NUMBER] ...
    display available events or search video for given event(s)'''
        self.nav.get_events()
        if arg == '':
            print '\n'.join('(%d) %s' % (i+1, self.nav.events[i][0]) for i in range(len(self.nav.events)))
        else:
            try:
                self.nav.event(arg)
                self.nav.results.print_page()
            except IndexError:
                print >> sys.stderr, 'Error: unknown events'
            except ValueError:
                print >> sys.stderr, 'Error: wrong argument; must be an integer'

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
                self.nav.results.print_page()
            except IndexError:
                print >> sys.stderr, 'Error: unknown program'
            except ValueError:
                print >> sys.stderr, 'Error: wrong argument; must be an integer'

    def do_dldir(self,arg):
        '''dldir [PATH] ...
    display or change download directory'''
        if arg == '':
            print self.nav.options.dldir
            return
        arg = expand_path(arg) # resolve environment variables and '~'s
        if not os.path.exists(arg):
            print >> sys.stderr, 'Error: wrong argument; must be a valid path'
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
    video_per_page [NUMBER]
                     display or change number of video shown per page

    help             show this help
    quit             quit the cli
    exit             exit the cli'''
        else:
            try:
                print getattr(self, 'do_'+arg).__doc__
            except AttributeError:
                print >> sys.stderr, 'Error: no help for command %s' % arg

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
        print >> sys.stderr, 'Error: don\'t know how to %s' % arg

    def emptyline(self):
        pass

def die(msg):
    print >> sys.stderr, 'Error: %s. See %s --help' % (msg, sys.argv[0])
    sys.exit(1)

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
                print >> sys.stderr, 'The video in not available in the language %s. Using the default one' % lang
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
                url = soup.urls.find('url')
                print >> sys.stderr, "Warning: Can't find the desired quality. Using the first one found"
            rtmp_url = url.string

        return (rtmp_url, player_url, info)
    except urllib2.URLError:
        die('Invalid URL')

def extract_videos(soup, options):
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
            title = a.contents[0]
        except IndexError:
            # empty title ??
            title = '== NO TITLE =='
        videos.append(Video(DOMAIN+a['href'], title, teaser, options))
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

def play(video):
    cmd_args = make_cmd_args(video, streaming=True)
    if 'nogeo/carton_23h' in video.rtmp_url:
        print >> sys.stderr, 'Error: This video is only available between 23:00 and 05:00'
        return
    player_cmd = find_player(PLAYERS)

    if player_cmd is not None:
        p1 = subprocess.Popen(['rtmpdump'] + cmd_args.split(' '), stdout=subprocess.PIPE)
        p2 = subprocess.Popen(player_cmd.split(' '), stdin=p1.stdout, stderr=subprocess.PIPE)
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
        print >> sys.stderr, 'Error: no player has been found.'

def record(video, dldir):
    cwd = os.getcwd()
    os.chdir(dldir)
    resume = os.path.exists(video.flv)
    cmd_args = make_cmd_args(video, resume=resume)
    if 'nogeo/carton_23h' in video.rtmp_url:
        print >> sys.stderr, 'Error: this video is only available between 23:00 and 05:00'
        return
    p = subprocess.Popen(['rtmpdump'] + cmd_args.split(' '))
    rt = p.wait()

    if rt != 0:
        if rt == 2:
            print >> sys.stderr, 'Error: incomplete transfer; please rerun previous command to finish download'
        elif rt == 1:
            print >> sys.stderr, 'Error: rtmpdump unrecoverable error'
    else:
        # Convert to mp4
        cmd = 'ffmpeg -v -10 -i %s -acodec copy -vcodec copy %s' % (video.flv, video.mp4)
        print ':: Converting to mp4 format'
        is_file_present = os.path.isfile(video.mp4)
        try:
            subprocess.check_call(cmd.split(' '))
            os.unlink(video.flv)
        except OSError as e:
            print >> sys.stderr, 'Error: ffmpeg command not found. Conversion aborted.'
        except subprocess.CalledProcessError as e:
            print >> sys.stderr, e
            print >> sys.stderr, 'Error: conversion failed.'
            # delete file if it was not there before conversion process started
            if os.path.isfile(video.mp4) and not is_file_present:
                os.unlink(video.mp4)

    os.chdir(cwd)

def make_cmd_args(video, resume=False, streaming=False):
    if not find_in_path(os.environ['PATH'], 'rtmpdump'):
        print >> sys.stderr, 'Error: rtmpdump has not been found'
        sys.exit(1)

    cmd_args = '--rtmp %s --swfVfy %s --quiet' % (video.rtmp_url, video.player_url)

    if not streaming:
        cmd_args += ' --flv %s' % video.flv
        if resume:
            # try to resume a download
            cmd_args += ' --resume'
            print ':: Resuming download of %s' % video.flv
        else:
            print ':: Downloading to %s' % video.flv
    else:
        print ':: Streaming from %s' % video.rtmp_url

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

def find_player(players):
    for p in players:
        cmd = p.split(' ')[0]
        if cmd.startswith('/') and os.path.isfile(cmd):
            return p
        else:
            if find_in_path(os.environ['PATH'], cmd):
                return p
    return None

def get_term_size():
    import re
    try:
        output = subprocess.check_output(['stty', '-a'])
        m = re.search('rows\D+(?P<rows>\d+); columns\D+(?P<columns>\d+);', output)
        if m:
            try:
                return int(m.group('rows')), int(m.group('columns'))
            except ValueError:
                return None
        else:
            return None
    except OSError:
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
            action='store', help=('language of the video fr, de, en (default: %s)' % DEFAULT_LANG))
    parser.add_option('-q', '--quality', dest='quality', type='string', default=DEFAULT_QUALITY,
            action='store', help='quality of the video sd or hd (default: hd)')

    options, args = parser.parse_args()

    term_size = get_term_size()
    if term_size:
        setattr(options, 'video_per_page', (term_size[0]-5)/2)
    else:
        setattr(options, 'video_per_page', 25)

    if not os.path.exists(options.dldir):
        die('Invalid Path')
    if options.lang not in ('fr', 'de', 'en'):
        die('Invalid option')
    if options.quality not in ('sd', 'hd'):
        die('Invalid option')
    if len(args) < 2:
        MyCmd(options).cmdloop()
        sys.exit(0)
    if args[0] not in ('url', 'play', 'record', 'search'):
        die('Invalid command')

    if args[0] == 'url':
        print get_rtmp_url(args[1], quality=options.quality, lang=options.lang)[0]

    elif args[0] == 'play':
        play(Video(args[1], '', '', options))
        sys.exit(1)

    elif args[0] == 'record':
        record(Video(args[1], '', '', options), options.dldir)

    elif args[0] == 'search':
        term = ' '.join(args[1:])
        print ':: Searching for "%s"' % term
        nav = Navigator(options)
        nav.search(term)
        nav.last_cmd = 'search %s' % term
        if nav.results is not None:
            nav.results.print_page()
            MyCmd(options, nav=nav).cmdloop()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print '\nAborted'
