#!/usr/bin/python
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
from urllib2 import urlopen, URLError, Request
from urllib import unquote
import urlparse
import os
from subprocess import Popen, PIPE
from optparse import OptionParser
from cmd import Cmd

VERSION = '0.2.3.3'
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
# with 50 per page but only get 25 because the rest is done with ajax (?)
HOME_URL = 'http://videos.arte.tv/%s/videos#/tv/thumb///1/25/'
SEARCH_URL = 'http://videos.arte.tv/%s/do_search/videos/%s?q='
SEARCH_LANG = {'fr': 'recherche', 'de':'suche', 'en': 'search'}
LANG = SEARCH_LANG.keys()
# same remark as above
FILTER_URL = 'http://videos.arte.tv/%s/do_delegate/videos/index-3188698,view,asThumbnail.html?hash=tv/thumb///%s/50/'

BOLD   = '[1m'
NC     = '[0m'    # no color

class ArgError(Exception):
    pass

class MyCmd(Cmd):
    def __init__(self, results, options):
        Cmd.__init__(self)
        self.prompt = 'arte+7> '
        self.intro = '\nType "help" to see available commands.'

        # holds last search result from any command (list, channel, program, search)
        self.results = results
        self.options = options
        # holds the videos from list command
        self.videos = None
        self.channels = None
        self.programs = None

    def extra_help(self):
        if len(self.results) == 0:
            print >> stderr, 'You need to run either a list, search, channel or program command first'

    def process_num(self, arg):
        num = int(arg)-1
        if num < 0 or num >= len(self.results):
            raise ArgError
        return num

    def do_url(self, arg):
        '''url NUMBER
    show the url of the chosen video'''
        try:
            video = self.results[self.process_num(arg)]
            if 'rtmp_url' not in video:
                get_video_player_info(video, self.options)
            print video['rtmp_url']
        except ValueError:
            print >> stderr, 'Error: wrong argument (must be an integer)'
        except ArgError:
            print >> stderr, 'Error: no video with this number'
            self.extra_help()

    def do_player_url(self, arg):
        '''player_url NUMBER
    show the Flash player url of the chosen video'''
        try:
            video = self.results[self.process_num(arg)]
            if 'player_url' not in video:
                get_video_player_info(video, self.options)
            print video['player_url']
        except ValueError:
            print >> stderr, 'Error: wrong argument (must be an integer)'
        except ArgError:
            print >> stderr, 'Error: no video with this number'
            self.extra_help()

    def do_info(self, arg):
        '''info NUMBER
        display details about chosen video'''
        try:
            video = self.results[self.process_num(arg)]
            if 'info' not in video:
                get_video_player_info(video, self.options)
            print video['info']
        except ValueError:
            print >> stderr, 'Error: wrong argument (must be an integer)'
        except ArgError:
            print >> stderr, 'Error: no video with this number'
            self.extra_help()

    def do_play(self, arg):
        '''play NUMBER [NUMBER] ...
    play the chosen videos'''
        playlist = []
        for i in arg.split():
            try:
                playlist.append(self.results[self.process_num(i)])
            except ValueError:
                print >> stderr, '"%s": wrong argument, must be an integer' % i
                return
            except ArgError:
                print >> stderr, 'Error: no video with this number: %s' % i
                self.extra_help()
                return
        print ':: Playing video(s): ' + ', '.join('#%s' % i for i in arg.split())
        for v in playlist:
            play(v, self.options)

    def do_record(self, arg):
        '''record NUMBER [NUMBER] ...
    record the chosen videos to a local file'''
        playlist = []
        for i in arg.split():
            try:
                playlist.append(self.results[self.process_num(i)])
            except ValueError:
                print >> stderr, '"%s": wrong argument, must be an integer' % i
                return
            except ArgError:
                print >> stderr, 'Error: no video with this number: %d' % i
                self.extra_help()
                return
        print ':: Recording video(s): ' + ', '.join('#%s' % i for i in arg.split())
        # TODO: do that in parallel ?
        for v in playlist:
            record(v, self.options)

    def do_search(self, arg):
        '''search STRING
    search for a given STRING on arte+7 web site'''
        results = search(arg, self.options.lang)
        if results is not None:
            print_results(results)
            self.results = results

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
            print self.options.lang
        elif arg in LANG:
            self.options.lang = arg
            if self.videos is not None:
                for v in self.videos:
                    try:
                        del v['rtmp_url']
                    except KeyError:
                        pass
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
            self.options.quality = arg
            if self.videos is not None:
                for v in self.videos:
                    try:
                        del v['rtmp_url']
                    except KeyError:
                        pass
        else:
            print >> stderr, 'Error: quality could be %s' % ','.join(QUALITY)

    def do_list(self, arg):
        '''list [more]
    list 25 videos from the home page (55 ones with more)'''
        if arg == 'more':
            page = 1
            self.videos = get_list(page, self.options.lang)
        elif self.videos is None:
            c,p,v = get_channels_programs(self.options.lang)
            if c is not None:
                self.channels = c
                self.programs = p
                self.videos = v

        print_results(self.videos)
        self.results = self.videos

    def do_channel(self, arg):
        '''channel [NUMBER] ...
    display available channels or search video for given channel(s)'''
        if self.channels is None:
            # try to get them from home page
            c,p,v = get_channels_programs(self.options.lang)
            if c is not None:
                self.channels = c
                self.programs = p
                if self.videos is None:
                    self.videos = v
            else:
                print >> stderr, 'Error: Can\'t retrieve channels'
                return
        if arg == '':
            print '\n'.join('(%d) %s' % (i+1, self.channels[i][0]) for i in range(len(self.channels)))
        else:
            try:
                ch = [int(i)-1 for i in arg.split(' ')]
                for i in ch:
                    if i<0 or i>=len(self.channels):
                        print >> stderr, 'Error: unknown channel #%d.' % (i+1)
                        return
                videos = channel(ch, self.options.lang, self.channels)
                print_results(videos)
                self.results = videos
            except ValueError:
                print >> stderr, 'Error: wrong argument; must be an integer'

    def do_program(self, arg):
        '''program [NUMBER] ...
    display available programs or search video for given program(s)'''
        if self.programs is None:
            # try to get them from home page
            c,p,v = get_channels_programs(self.options.lang)
            if p is not None:
                self.programs = p
                self.channels = c
                if self.videos is None:
                    self.videos = v
            else:
                print >> stderr, 'Error: Can\'t retrieve programs'
                return
        if arg == '':
            print '\n'.join('(%d) %s' % (i+1, self.programs[i][0]) for i in range(len(self.programs)))
        else:
            try:
                pr = [int(i)-1 for i in arg.split(' ')]
                for i in pr:
                    if i<0 or i>=len(self.programs):
                        print >> stderr, 'Error: unknown program #%d.' % (i+1)
                        return
                videos = program(pr, self.options.lang, self.programs)
                print_results(videos)
                self.results = videos
            except ValueError:
                print >> stderr, 'Error: wrong argument; must be an integer'

    def do_dldir(self,arg):
        '''dldir [PATH] ...
    display or change download directory'''
        if arg == '':
            print self.options.dldir
            return
        arg = expand_path(arg) # resolve environment variables and '~'s
        if not os.path.exists(arg): #we could also check for write access if you want
            print >> stderr, 'Error: wrong argument; must be a valid path'
        else:
            self.options.dldir = arg

    def do_help(self, arg):
        '''print the help'''
        if arg == '':
            print '''COMMANDS:
    url NUMBER       show url of video
    play NUMBERS     play chosen videos
    record NUMBERS   download and save videos to a local file
    dldir [PATH]     display or change download directory
    info NUMBER      display details about given video
    search STRING    search for a video
    lang [fr|de|en]  display or switch to a different language
    quality [sd|hd]  display or switch to a different video quality
    channel [NUMBER] display available channels or search video for given channel(s)
    program [NUMBER] display available programs or search video for given program(s)
    list [more]      list 25 videos from the home page (list 55 ones with more)
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
        first_soup = soup = BeautifulSoup(urlopen(url_page).read())
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
            soup = BeautifulStoneSoup(urlopen(flashvars['videorefFileUrl'][0]).read())
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
            soup = BeautifulStoneSoup(urlopen(xml_url).read())
            # at last the video url
            rtmp_url = soup.urls.find('url', {'quality': quality}).string

        return (rtmp_url, player_url, info, first_soup)
    except URLError:
        die('Invalid URL')

def find_in_path(path, filename):
    '''is filename in $PATH ?'''
    for i in path.split(':'):
        if os.path.exists('/'.join([i, filename])):
            return True
    return False

def get_list(page, lang):
    '''get the list of videos from home page'''
    try:
        url = FILTER_URL % (lang, page)
        soup = BeautifulSoup(urlopen(url).read(), convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        videos = extract_videos(soup)
        return videos
    except URLError:
        die("Can't get the home page of arte+7")
    return None

def get_video_player_info(video, options):
    '''get various info from page of video: *modify* video variable'''
    print ':: Retrieving video data'
    r, p, i, s = get_rtmp_url(video['url'], quality=options.quality, lang=options.lang)
    video['rtmp_url'] = r
    video['player_url'] = p
    video['info'] = i

def get_channels_programs(lang):
    '''get channels and programs from home page'''
    try:
        print ':: Retrieving channels and programs'
        url = HOME_URL % (lang, )
        soup = BeautifulSoup(urlopen(url).read(), convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        #get the channels
        uls = soup.findAll('ul', {'class': 'channelList'})
        channels, codes = [], []
        for u in uls:
            channels.extend(i.string for i in u.findAll('a'))
            codes.extend(int(i['value']) for i in u.findAll('input'))
        if channels != []:
            channels = zip(channels, codes)
        else:
            channels = None

        # get the programs
        uls = soup.findAll('ul', {'class': 'programList'})
        programs, codes = [], []
        for u in uls:
            programs.extend(i.string for i in u.findAll('a'))
            codes.extend(int(i['value']) for i in u.findAll('input'))
        if programs != []:
            programs = zip(programs, codes)
        else:
            programs = None

        # get the videos
        videos = extract_videos(soup)

        return (channels, programs, videos)
    except URLError:
        die("Can't get the home page of arte+7")
    return None

def channel(ch, lang, channels):
    '''get a list of videos for channel ch'''
    try:
        url = (FILTER_URL % (lang, 1)) + 'channel-'+','.join('%d' % channels[i][1] for i in ch)  + '-program-'
        soup = BeautifulSoup(urlopen(url).read(), convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        videos = extract_videos(soup)
        return videos
    except URLError:
        die("Can't complete the requested search")
    return None

def program(pr, lang, programs):
    '''get a list of videos for program pr'''
    try:
        url = (FILTER_URL % (lang, 1)) + 'channel-' + '-program-'+','.join('%d' % programs[i][1] for i in pr)
        soup = BeautifulSoup(urlopen(url).read(), convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        videos = extract_videos(soup)
        return videos
    except URLError:
        die("Can't complete the requested search")
    return None

def search(s, lang):
    '''search videos matching string s'''
    try:
        url = (SEARCH_URL % (lang, SEARCH_LANG[lang])) + s.replace(' ', '+')
        soup = BeautifulSoup(urlopen(url).read(), convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        videos = extract_videos(soup)
        return videos
    except URLError:
        die("Can't complete the requested search")
    return None

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
        videos.append({'title':a.string, 'url':'http://videos.arte.tv'+a['href'], 'teaser':teaser})
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

def print_results(results, verbose=True):
    '''print list of video:
    title in bold with a number followed by teaser'''
    for i in range(len(results)):
        print '%s(%d) %s'% (BOLD, i+1, results[i]['title'] + NC)
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

def find_player(d):
    for e, c in d:
        if find_in_path(os.environ['PATH'], e):
            return c
    return None

def main():
    usage = '''Usage: %prog url|play|record [OPTIONS] URL
       %prog search [OPTIONS] STRING...
       %prog

Play or record arte+7 videos without a mandatory browser.

You need to get the url of the page presenting the video on arte+7 site
(so you might need a browser after all) ;-)
or use the search command to get a list of videos

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
        MyCmd([], options).cmdloop()
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
        results = search(term, options.lang)
        if results is not None:
            print_results(results)
            MyCmd(results, options).cmdloop()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print '\nAborted'
