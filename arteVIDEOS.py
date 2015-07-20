#!/usr/bin/python
# -*- coding: utf-8 -*-

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
# The order is significant: the first player available is used
PLAYERS = (
        'vlc',
		'C:/Program Files (x86)/VideoLAN/VLC/vlc.exe',
		'C:/Program Files/VideoLAN/VLC/vlc.exe'
        )

DEFAULT_LANG = 'fr'
DEFAULT_QUALITY = 'hd'
########################################################################
# DO NOT MODIFY below this line unless you know what you are doing     #
########################################################################

import sys
try:
    from bs4 import BeautifulSoup
except ImportError:
    print >> sys.stderr, 'Error: you need the BeautifulSoup(v4) python module'
    sys.exit(1)
import urllib2
from urllib import unquote, urlretrieve
import urlparse
import os
import platform
import subprocess
from optparse import OptionParser
from cmd import Cmd
import json


reload(sys)
sys.setdefaultencoding("utf-8")

VERSION = '0.5'
QUALITY = ('sd', 'md', 'ld', 'hd')
LANG = ('fr', 'de')
DEFAULT_DLDIR = os.getcwd()
PARAMS = {'hd':'SQ', 'sd':'MQ', 'ld':'LQ', 'md':'EQ', 'fr':'1', 'de':'2'}
METHOD = {'HTTP':'HTTP_MP4', 'RTMP':'RTMP'}

VIDEO_PER_PAGE = 900
DOMAIN = 'http://www.arte.tv'
DIRECT_URL = {'fr': DOMAIN + '/guide/fr/direct', 'de':DOMAIN+'/guide/de/live'}
GUIDE_URL = DOMAIN + '/guide/%s/plus7'
PLUS_URL = DOMAIN + '/guide/%s/plus7?regions=ALL%%2Cdefault%%2CDE_FR%%2CSAT%%2CEUR_DE_FR'
SEARCH_URL = DOMAIN + '/guide/%s/%s?keyword=%s'
SEARCH_KEYWORD = {'fr':'resultats-de-recherche', 'de':'suchergebnisse'}

HIST_CMD = ('plus7', 'programs', 'search')

BOLD   = '\033[1m'
if platform.system()=='Windows':
	BOLD   = '['
	
NC     = '\033[0m'    # no color
if platform.system()=='Windows':
	NC     = ']'
	
class Video(object):
    '''Store info about a given video'''
    def __init__(self, page_url, title, teaser, options, info=None, video_url=None):
        self.title = title
        self.page_url = page_url
        self.teaser = teaser
        self.options = options
        self._info = info
        self._video_url = video_url
        self._mp4 = None

    def get_data(self):
        print ':: Retrieving video info',
        sys.stdout.flush()
        self._video_url, self._info = get_url(self.page_url, quality=self.options.quality, lang=self.options.lang)
        soup = BeautifulSoup(urllib2.urlopen(self.page_url).read(),"lxml")
        self.teaser = soup.find('div', {'class':'description_short'}).find('p').encode("utf-8")
        self.title = soup.find('title').text.encode("utf-8")
        sys.stdout.write('\r')
        sys.stdout.flush()

    # automatic retrieval of video info if a property is not defined
    @property
    def info(self):
        if self._info is None:
            self.get_data()
        return self._info

    @property
    def video_url(self):
        if self._video_url is None:
            self.get_data()
        return self._video_url

    @property
    def mp4(self):
        '''create output file name'''
        if self._mp4 is None:
            self._mp4 = urlparse.urlparse(self.video_url).path.split('/')[-1]
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

    def extend(self, p):
        self.__value.extend(p)

    def print_page(self, verbose=True):
        '''print list of video: title in bold with a number followed by teaser'''
        for i in range(min(self.video_per_page, len(self.__value)-self.page*self.video_per_page)):
            nb = i+self.video_per_page*self.page
            print '%s(%d) %s'% (BOLD, nb+1, self.__value[nb].title.encode("utf-8") + NC)
            if verbose:
                print '    '+ self.__value[nb].teaser.encode("utf-8")

class Navigator(object):
    '''Main object storing all info requested from server and help navigation'''
    def __init__(self, options):
        self.options = options
        self.programs = None
        self.more = True
        self.last_cmd = ''
        self.npage = 1
        self.video_per_page = options.video_per_page
        self.stop = False
        # holds last search result from any command (list, program, search)
        self.results = Results(self.video_per_page)

    def clear_info(self):
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
            err('You need to run either a plus7, search or program command first')

    def parse_search(self, url):
        if not self.more:
            self.npage = 1
            self.stop = False
            self.results = Results(self.video_per_page)

        soup = BeautifulSoup(urllib2.urlopen(url).read(),"lxml")
        vid = soup.find_all('section', {'class':'result'})
        videos = []
        for v in vid:
            teaser = v.find('p', {'class':'description'}).text.replace('<br>',' ').replace('<b>...</b>', ' ')
            title = v.find('h3')['title']
            page_url = v.find('a')['href']
            videos.append(Video(page_url, title, teaser, self.options))
        self.stop = True
        if videos == []:
            print ':: No results found'
        else:
            self.results.extend(videos)

    def retrieve(self, url):
        if not self.more:
            self.npage = 1
            self.stop = False
            self.results = Results(self.video_per_page)

        soup = BeautifulSoup(urllib2.urlopen(url).read(),"lxml")
        ul = soup.find('ul', {'class':'clearfix list-inline list-unstyled'})
        if ul == None:
            print ':: No results found'
            return
        vid = ul.find_all('li', {'class':'video'})
        videos = []
        for v in vid:
            teaser = v.find('div', {'class':'video-block ARTE_PLUS_SEVEN has-play'})['data-description']
            title = v.find('h3')['title']
            url_json = v.find('div', {'class':'video-container'})['arte_vp_url']
            url, info = extract_json(url_json)
            videos.append(Video(url_json, title, teaser, self.options, info=info, video_url=url))
        self.stop = True
        self.results.extend(videos)

    def request(self, url):
        if not self.more:
            self.npage = 1
            self.stop = False
            self.results = Results(self.video_per_page)
        try:
            data_json = json.loads(urllib2.urlopen(url).read())
            videos = extract_videos(data_json, self.options)
            self.stop = True
            self.results.extend(videos)
        except urllib2.URLError:
            die("Can't complete request")

    def program(self, arg):
        '''get a list of videos for given program'''
        pr = int(arg) - 1
        url = self.programs[pr][1]
        print ':: Retrieving requested program list'
        self.retrieve(url)

    def search(self, s):
        '''search videos matching string s'''
        url = SEARCH_URL % (self.options.lang, SEARCH_KEYWORD[self.options.lang], s.replace(' ', '+'))
        print ':: Waiting for search request'
        self.parse_search(url)

    def plus7(self):
        '''get the list of videos from url'''
        url = PLUS_URL % self.options.lang
        print ':: Retrieving plus7 videos list'
        self.request(url)

    def get_programs(self):
        '''get programs'''
        if self.programs is not None:
            return
        try:
            print ':: Retrieving programs name'
            url = GUIDE_URL % self.options.lang
            soup = BeautifulSoup(urllib2.urlopen(url).read(),"lxml")
            # get the programs
            sec = soup.find('section', {'class':'nav-clusters'})
            lis = sec.find_all('div', {'class': 'col-xs-12 col-sm-2 cluster'})
            programs, urls = [], []
            for l in lis:
                programs.append(l.find('span', {'class': 'ellipsis title'}).text.strip())
                urls.append(l.find('a')['href'])
            if programs != []:
                self.programs = zip(programs, urls)
            else:
                self.programs = None
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
                err('Error: argument should be a number')

    def do_live(self, arg):
        '''Play arte live'''
        soup = BeautifulSoup(urllib2.urlopen(DIRECT_URL[self.nav.options.lang]).read(),"lxml")
        url = soup.find('div', {'class':'video-container'})['arte_vp_live-url']
        data_json = json.loads(urllib2.urlopen(url).read())
        v = Video('', '', '', '', video_url=data_json['videoJsonPlayer']['VSR']['M3U8_HQ']['url'])
        print ':: Playing Live'
        play(v)

    def do_previous(self, arg):
        if self.nav.last_cmd.startswith(HIST_CMD) and self.nav.results.page >= 0 and self.nav.results.page > 0:
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
            print video.video_url
        except ValueError:
            err('Error: wrong argument (must be an integer)')
        except IndexError:
            err('Error: no video with this number')
            self.nav.extra_help()

    def do_info(self, arg):
        '''info NUMBER
        display details about chosen video'''
        try:
            video = self.nav[arg]
            print '%s== %s ==%s'% (BOLD, video.title.encode("utf-8"), NC)
            print video.info
        except ValueError:
            err('Error: wrong argument (must be an integer)')
        except IndexError:
            err('Error: no video with this number')
            self.nav.extra_help()

    def do_play(self, arg):
        '''play NUMBER [NUMBER] ...
    play the chosen videos'''
        playlist = []
        for i in arg.split():
            try:
                playlist.append(self.nav[i])
            except ValueError:
                err('"%s": wrong argument, must be an integer' % i)
                return
            except IndexError:
                err('Error: no video with this number: %s' % i)
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
                err('"%s": wrong argument, must be an integer' % i)
                return
            except IndexError:
                err('Error: no video with this number: %s' % i)
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

    def do_lang(self, arg):
        '''lang [fr|de|en]
    display or switch to a different language'''
        if arg == '':
            print self.nav.options.lang
        elif arg in LANG:
            self.nav.options.lang = arg
            self.nav.clear_info()
        else:
            err('Error: lang could be %s' % ','.join(LANG))

    def complete_quality(self, text, line, begidx, endidx):
        if text == '':
            return QUALITY
        elif text.startswith('s'):
            return ('sd',)
        elif text.startswith('h'):
            return('hd',)
        elif text.startswith('m'):
            return('md',)
        elif text.startswith('l'):
            return('ld',)

    def do_quality(self, arg):
        '''quality [hd|md|sd|ld] display or switch to a different quality'''
        if arg == '':
            print self.nav.options.quality
        elif arg in QUALITY:
            self.nav.options.quality = arg
            self.nav.clear_info()
            print ':: All lists/results have been cleared'
        else:
            err('Error: quality could be %s' % ','.join(QUALITY))

    def do_plus7(self, arg):
        '''list [more]
    list 25 videos from the home page'''
        self.nav.plus7()
        self.nav.results.print_page()

    def do_programs(self, arg):
        '''programs [NUMBER] ...
    display available programs or search video for given program(s)'''
        # try to get them from home page
        self.nav.get_programs()
        if arg == '':
            print '\n'.join('(%d) %s' % (i+1, self.nav.programs[i][0].encode("utf-8")) for i in range(len(self.nav.programs)))
        else:
            try:
                self.nav.program(arg)
                self.nav.results.print_page()
            except IndexError:
                err('Error: unknown program')
            except ValueError:
                err('Error: wrong argument; must be an integer')

    def do_dldir(self,arg):
        '''dldir [PATH] ...
    display or change download directory'''
        if arg == '':
            print self.nav.options.dldir
            return
        arg = expand_path(arg) # resolve environment variables and '~'s
        if not os.path.exists(arg):
            err('Error: wrong argument; must be a valid path')
        else:
            self.nav.options.dldir = arg

    def do_help(self, arg):
        '''print the help'''
        if arg == '':
            print '''COMMANDS:
    plus7            list videos from arte+7
    programs         list videos from programs tab
    live             play arte live
    search STRING    search for a video

    next             list videos of the next page
    previous         list videos of previous page

    url NUMBER       show url of video
    play NUMBERS     play chosen videos
    record NUMBERS   download and save videos to a local file
    info NUMBER      display details about given video

    dldir [PATH]     display or change download directory
    lang [fr|de]  display or switch to a different language
    quality [hd|md|sd|ld]  display or switch to a different video quality
    video_per_page [NUMBER]
                     display or change number of video shown per page

    help             show this help
    quit             quit the cli
    exit             exit the cli'''
        else:
            try:
                print getattr(self, 'do_'+arg).__doc__
            except AttributeError:
                err('Error: no help for command %s' % arg)

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
        err('Error: don\'t know how to %s' % arg)

    def emptyline(self):
        pass

def err(msg):
    print >> sys.stderr, msg

def die(msg):
    print >> sys.stderr, 'Error: %s. See %s --help' % (msg, sys.argv[0])
    sys.exit(1)

def extract_json(url_json, quality='hd', lang='fr', method='HTTP'):
    try:
        data_json = json.loads(urllib2.urlopen(url_json).read())
        #print json.dumps(data_json, sort_keys=True, indent=2)
        player = data_json['videoJsonPlayer']['VSR']['%s_%s_%s'% (METHOD[method], PARAMS[quality], PARAMS[lang])]
        if method == 'HTTP':
            video_url = player['url']
        else:
            video_url = player['streamer'] + player['url']
        info = data_json['videoJsonPlayer']['VDE']+'\n\n' + data_json['videoJsonPlayer']['VRA']
        return (video_url, info)
    except urllib2.URLError:
        die('Invalid URL')

def get_url(url_page, quality='hd', lang='fr', method='HTTP'):
    '''get the url of the video and info about video'''
    try:
        # get the web page
        soup = BeautifulSoup(urllib2.urlopen(url_page).read(),"lxml")
        object_tag = soup.find('div', {'class':'video-container'})
        try:
            url_json = object_tag['arte_vp_url']
        except KeyError:
            die('Video url not found')
        if not url_json.endswith('ALL.json'):
            # go one step further to really get all the data for the video
            data_json = json.loads(urllib2.urlopen(url_json).read())
            url_json = data_json['videoJsonPlayer']['videoPlayerUrl']
        (video_url, info) = extract_json(url_json, quality, lang, method)
        return (video_url, info)
    except urllib2.URLError:
        die('Invalid URL')

def extract_videos(data_json, options):
    '''extract list of videos title, url, and teaser from data_json'''
    videos = []
    for v in data_json['videos']:
        title = v['title']
        teaser = v['desc'].strip()
        url = v['url']
        videos.append(Video(url, title, teaser, options))
    return videos

def play(video):
    player_cmd = find_player(PLAYERS)

    if player_cmd is not None:
        print ':: Streaming URL: %s' % video.video_url
        if video.video_url.endswith(('.mp4', '.m3u8')):
            subprocess.call(player_cmd.split(' ') + [video.video_url])
    else:
        err('Error: no player has been found.')

def record(video, dldir):
    print ':: Recording %s' % video.video_url
    cwd = os.getcwd()
    os.chdir(dldir)

    if video.video_url.endswith('.mp4'):
        import re
        filename = re.sub('[^A-Za-z0-9.]+', '',video.title).strip()+'.mp4'
        urlretrieve(video.video_url, filename)
    else:
        err('Error: Did not retrieved %s' % video.video_url)

    os.chdir(cwd)

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
        cmd = p.strip()
        if (cmd.startswith('/') or cmd[1] ==':') and os.path.isfile(cmd):
            print ':: using this player : '+ cmd
            return cmd
        else:
            if find_in_path(os.environ['PATH'], cmd):
                print ':: using this player : '+ cmd
                return cmd
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
       %prog live
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
            a simple command line interpreter
    live    play arte live'''

    parser = OptionParser(usage=usage)
    parser.add_option('-d', '--downloaddir', dest='dldir', type='string',
            default=DEFAULT_DLDIR, action='store', help='directory for downloads')
    parser.add_option('-l', '--lang', dest='lang', type='string', default=DEFAULT_LANG,
            action='store', help=('language of the video fr, de (default: %s)' % DEFAULT_LANG))
    parser.add_option('-q', '--quality', dest='quality', type='string', default=DEFAULT_QUALITY,
            action='store', help='quality of the video hd or md or sd or ld (default: hd)')

    options, args = parser.parse_args()

    term_size = get_term_size()
    if term_size:
        setattr(options, 'video_per_page', (term_size[0]-5)/2)
    else:
        setattr(options, 'video_per_page', 25)

    if not os.path.exists(options.dldir):
        die('Invalid download directory path')
    if options.lang not in ('fr', 'de'):
        die('Invalid lang option')
    if options.quality not in ('sd', 'hd', 'md', 'ld'):
        die('Invalid quality option')
    if len(args) < 1:
        MyCmd(options).cmdloop()
        sys.exit(0)
    if args[0] not in ('url', 'play', 'record', 'search', 'live'):
        die('Invalid command')

    if args[0] == 'url':
        print get_url(args[1], quality=options.quality, lang=options.lang)[0]

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

    elif args[0] == 'live':
        soup = BeautifulSoup(urllib2.urlopen(DIRECT_URL[options.lang]).read(),"lxml")
        url = soup.find('div', {'class':'video-container'})['arte_vp_live-url']
        data_json = json.loads(urllib2.urlopen(url).read())
        v = Video('', '', '', '', video_url=data_json['videoJsonPlayer']['VSR']['M3U8_HQ']['url'])
        print ':: Playing Live'
        play(v)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print '\nAborted'
