#!/usr/bin/python
# -*- coding: utf8 -*-
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
from urllib2 import urlopen, URLError
from urllib import unquote
from urlparse import urlparse
from subprocess import call as subprocess_call
from os.path import exists as os_path_exists
from os import environ as os_environ
from sys import exit, argv, stderr
from optparse import OptionParser
from cmd import Cmd

VERSION = '0.2'
DEFAULT_LANG = 'fr'
DEFAULT_QUALITY = 'hd'
CLSID = 'clsid:d27cdb6e-ae6d-11cf-96b8-444553540000'
SEARCH_URL = 'http://videos.arte.tv/%s/do_search/videos/%s?q='
SEARCH_LANG = {'fr': 'recherche', 'de':'suche', 'en': 'search'}
FILTER_URL = 'http://videos.arte.tv/%s/do_delegate/videos/arte7/index-3211552,view,asThumbnail.html?hash=%s/thumb///1/50/'
CHANNELS = (
        3188640, # Arts & Culture (0)
        3188644, # Discovery (1)
        3188646, # Documentary (2)
        3188642, # Drama & Cinema (3)
        3188650, # Environment & Science (4)
        3188648, # Europe (5)
        3188654, # Geopolitics & History (6)
        3188656, # Kids & Family (7)
        3188636, # News (8)
        3188638, # Pop Culture & Music (9)
        3188652, # Society (10)
        )
CHANNELS_LANG = {'fr': (
            ('Actualités'               , 8),
            ('Art & Culture'            , 0),
            ('Cinéma & Fiction'         , 3),
            ('Culture Pop & Alternative', 9),
            ('Découverte'               , 1),
            ('Documentaire'             , 2),
            ('Environnement & Sciences' , 4),
            ('Europe'                   , 5),
            ('Géopolitique & Histoire'  , 6),
            ('Junior'                   , 7),
            ('Société'                  , 10)
            ), 'de': (
            ('Aktuelles'               , 8),
            ('Dokumentationen'         , 2),
            ('Entdeckung'              , 1),
            ('Europa'                  , 5),
            ('Geopolitik & Geschichte' , 6),
            ('Gesellschaft'            , 10),
            ('Junior'                  , 7),
            ('Kino & Serien'           , 3),
            ('Kunst & Kultur'          , 0),
            ('Popkultur & Musik'       , 9),
            ('Umwelt & Wissenschaft'   , 4)
            ), 'en':(
            ('Arts & Culture'         , 0),
            ('Discovery'              , 1),
            ('Documentary'            , 2),
            ('Drama & Cinema'         , 3),
            ('Environment & Science'  , 4),
            ('Europe'                 , 5),
            ('Geopolitics & History'  , 6),
            ('Kids & Family'          , 7),
            ('News'                   , 8),
            ('Pop Culture & Music'    , 9),
            ('Society'                , 10)
            )
        }

PROGRAMS = (
        3188704,    # 360° - GEO Report (0)
        3188708,    # ARTE Journal (1)
        3219086,    # ARTE Lounge (2)
        3188710,    # ARTE Reportage (3)
        3188720,    # Arts & artists (4)
        3199714,    # Cut up (5)
        3199710,    # Giordano meets .. (6)
        3188722,    # History on Wednesday (7)
        3224652,    # Karambolage (8)
        3188724,    # Metropolis (9)
        3188728,    # Philosophy (10)
        3188712,    # Short Circuit (11)
        3193602,    # The blogger (12)
        3188716,    # The Night / La Nuit (13)
        3188628,    # Tracks (14)
        3188730,    # X:enius (15)
        3188732)    # Yourope (16)

PROGRAMS_LANG = {
            'fr': (
            ('360° - GEO'                  , 0),
            ('ARTE Journal'                , 1),
            ('ARTE Lounge'                 , 2),
            ('ARTE Reportage'              , 3),
            ('Court-Circuit'               , 11),
            ('Cut up'                      , 5),
            ('Die Nacht/La nuit'           , 13),
            ('Giordano hebdo'              , 6),
            ('Karambolage'                 , 8),
            ('L\'Art et la Manière'        , 4),
            ('Le Blogueur'                 , 12),
            ('Les mercredis de l\'histoire', 7),
            ('Metropolis'                  , 9),
            ('Philosophie'                 , 10),
            ('Tracks'                      , 14),
            ('X:enius'                     , 15),
            ('Yourope'                     , 16),
            ),
            'de': (
            ('360° - GEO-Reportage'  , 0),
            ('ARTE Journal'          , 1),
            ('ARTE Lounge'           , 2),
            ('ARTE Reportage'        , 3),
            ('Cut up'                , 5),
            ('Der Blogger'           , 12),
            ('Geschichte am Mittwoch', 7),
            ('Giordano trifft ... '  , 6),
            ('Karambolage'           , 8),
            ('Künstler hautnah'      , 4),
            ('Kurzschluss'           , 11),
            ('La nuit/Die Nacht'     , 13),
            ('Metropolis'            , 9),
            ('Philosophie'           , 10),
            ('Tracks'                , 14),
            ('X:enius'               , 15),
            ('Yourope'               , 16),
            ),
            'en': (
            ('360° - GEO Report'   , 0),
            ('ARTE Journal'        , 1),
            ('ARTE Lounge'         , 2),
            ('ARTE Reportage'      , 3),
            ('Arts & artists'      , 4),
            ('Cut up'              , 5),
            ('Giordano meets ..'   , 6),
            ('History on Wednesday', 7),
            ('Karambolage'         , 8),
            ('Metropolis'          , 9),
            ('Philosophy'          , 10),
            ('Short Circuit'       , 11),
            ('The blogger'         , 12),
            ('The Night / La Nuit' , 13),
            ('Tracks'              , 14),
            ('X:enius'             , 15),
            ('Yourope'             , 16),
            )
            }

BOLD   = '[1m'
NC     = '[0m'    # no color

class ArgError(Exception):
    pass

class MyCmd(Cmd):
    def __init__(self, videos, options):
        Cmd.__init__(self)
        self.prompt = 'arte+7> '
        self.intro = '\nType "help" to see available commands.'

        self.videos = videos
        self.options = options

    def process_num(self, arg):
        num = int(arg)-1
        if num < 0 or num >= len(self.videos):
            raise ArgError

        return 'http://videos.arte.tv'+self.videos[num].find('h2').a['href']

    def do_url(self, arg):
        '''url NUMBER
    show the url of the chosen video'''
        try:
            url_page = self.process_num(arg)
            print get_rtmp_url(url_page)[0]
        except ValueError:
            print 'Error: wrong argument (must be an integer)'
        except ArgError:
            print 'Error: no video with this number'

    def do_play(self, arg):
        '''play NUMBER
    play the chosen video'''
        try:
            url_page = self.process_num(arg)
            #video_url = get_rtmp_url(url_page)[0]
            video_url = None
            play(video_url)
        except ValueError:
            print 'Error: wrong argument (must be an integer)'
        except ArgError:
            print 'Error: no video with this number'

    def do_record(self, arg):
        '''record NUMBER
    record the chosen video to a local file'''
        try:
            url_page = self.process_num(arg)
            record(url_page, self.options)
        except ValueError:
            print 'Error: wrong argument (must be an integer)'
        except ArgError:
            print 'Error: no video with this number'

    def do_search(self, arg):
        '''search STRING
    search for a given STRING on arte+7 web site'''
        results = search(arg, self.options.lang)
        if results is not None:
            print_results(results)
            self.videos = results

    def do_lang(self, arg):
        '''lang [fr|de|en]
    display or switch to a different language'''
        if arg == '':
            print self.options.lang
        elif arg in ('fr' ,'de', 'en'):
            self.options.lang = arg

    def do_quality(self, arg):
        '''quality [sd|hd]
    display or switch to a different quality'''
        if arg == '':
            print self.options.quality
        elif arg in ('sd', 'hd'):
            self.options.quality = arg

    def do_channels(self, arg):
        '''channels [NUMBER] ...
    display available channels or search video for given channel(s)'''
        if arg == '':
            for c,n in CHANNELS_LANG[self.options.lang]:
                print '(%d) %s' % (n+1, c)
        else:
            try:
                ch = [int(i)-1 for i in arg.split(' ')]
                for i in ch:
                    if i<0 or i>=len(CHANNELS):
                        print >> stderr, 'Error: argument out of range.'
                        return
                videos = channels(ch, self.options.lang)
                print_results(videos)
                self.videos = videos
            except ValueError:
                print >> stderr, 'Error: wrong argument; must be an integer'

    def do_programs(self, arg):
        '''programs [NUMBER] ...
    display available programs or search video for given program(s)'''
        if arg == '':
            for c,n in PROGRAMS_LANG[self.options.lang]:
                print '(%d) %s' % (n+1, c)
        else:
            try:
                pr = [int(i)-1 for i in arg.split(' ')]
                for i in pr:
                    if i<0 or i>=len(PROGRAMS):
                        print >> stderr, 'Error: argument out of range.'
                        return
                videos = programs(pr, self.options.lang)
                print_results(videos)
                self.videos = videos
            except ValueError:
                print >> stderr, 'Error: wrong argument; must be an integer'

    def do_help(self, arg):
        '''print the help'''
        if arg == '':
            print '''COMMANDS:
    url NUMBER      show real url of video
    play NUMBER     play chosen video (NOT IMPLEMENTED YET)
    record NUMBER   download and save video to a local file
    search STRING   search for a video
    lang [fr|de|en] display or switch to a different language
    quality [sd|hd] display or switch to a different video quality
    channels [NUMBER] display available channels or search video for given channel(s)
    programs [NUMBER] display available programs or search video for given program(s)
    help            show this help
    quit            quit the cli
    exit            exit the cli'''
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

    def default(self, arg):
        print 'Error: don\'t know how to %s' % arg

def die(msg):
    print >> stderr, 'Error: %s. See %s --help' % (msg, argv[0])
    exit(1)

def get_rtmp_url(url_page, quality='hd', lang='fr'):
    '''get the real url of the video'''
    # inspired by the get_rtmp_url from arte7recorder project

    # get the web page
    try:
        soup = BeautifulSoup(urlopen(url_page).read())
        object_tag = soup.find('object', classid=CLSID)
        # get the player_url straight from it
        player_url = unquote(object_tag.find('embed')['src'])

        # now we need a few jumps to get to the correct url
        movie_url = object_tag.find('param', {'name':'movie'})
        # first xml file
        xml_url = unquote(movie_url['value'].split('videorefFileUrl=')[-1])
        soup = BeautifulStoneSoup(urlopen(xml_url).read())
        # second xml file
        videos_list = soup.findAll('video')
        videos = {}
        for v in videos_list:
            videos[v['lang']] = v['ref']
        if lang not in videos:
            print >> stderr, 'The video in not available in the language %s.  using the default one' % lang
            if DEFAULT_LANG in videos:
                xml_url = videos[DEFAULT_LANG]
            else:
                xml_url = videos[0]
        else:
            xml_url = videos[lang]

        soup = BeautifulStoneSoup(urlopen(xml_url).read())
        # at last the video url
        video_url = soup.urls.find('url', {'quality': quality}).string

        return (video_url, player_url)
    except URLError:
        die('Invalid URL')

def find_in_path(path, filename):
    for i in path.split(':'):
        if os_path_exists('/'.join([i, filename])):
            return True
    return False

def channels(ch, lang):
    try:
        url = (FILTER_URL % (lang, lang)) + 'channel-'+','.join('%d' % CHANNELS[i] for i in ch)  + '-program-'
        soup = BeautifulSoup(urlopen(url).read(), convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        videos = soup.findAll('div', {'class': 'video'})
        return videos
    except URLError:
        die("Can't complete the requested search")
    return None

def programs(pr, lang):
    try:
        url = (FILTER_URL % (lang, lang)) + 'channel-' + '-program-'+','.join('%d' % PROGRAMS[i] for i in pr) 
        soup = BeautifulSoup(urlopen(url).read(), convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        videos = soup.findAll('div', {'class': 'video'})
        return videos
    except URLError:
        die("Can't complete the requested search")
    return None

def search(s, lang):
    try:
        url = (SEARCH_URL % (lang, SEARCH_LANG[lang])) + s.replace(' ', '+')
        soup = BeautifulSoup(urlopen(url).read(), convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        videos = soup.findAll('div', {'class': 'video'})
        return videos
    except URLError:
        die("Can't complete the requested search")
    return None

def print_results(results, verbose=True):
    count = 0
    for r in results:
        count += 1
        print BOLD + '(%d) '% count + r.find('h2').a.string + NC
        if verbose:
            print '    '+r.find('p', {'class': 'teaserText'}).string

def play(video_url):
    print >> stderr, 'Error: <play> is not implemented yet. Use record and then your favorite player'

def record(url_page, options):
    video_url, player_url = get_rtmp_url(url_page, quality=options.quality, lang=options.lang)
    output_file = urlparse(url_page).path.split('/')[-1].replace('.html','.flv')
    if not find_in_path(os_environ['PATH'], 'rtmpdump'):
        print >> stderr, 'Error: rtmpdump has not been found'
        exit(1)
    cmd_args = '-r %s --swfVfy %s --flv %s' % (video_url, player_url, output_file)
    if options.quiet:
        cmd_args += ' --quiet'
    if os_path_exists(output_file):
        # try to resume a download
        cmd_args += ' --resume'
        print ':: Resuming download of %s' % output_file
    else:
        print ':: Downloading and saving to %s' % output_file

    subprocess_call(['rtmpdump'] + cmd_args.split(' '))

def main():
    usage = '''Usage: %prog url|play|record [OPTIONS] URL
       %prog search [OPTIONS] STRING...

Play or record arte+7 videos without a mandatory browser.

You need to get the url of the page presenting the video on arte+7 site
(so you might need a browser after all) ;-)
or use the search command to get a list of videos

COMMANDS
    url     show the real url of the video
    play    play the video directly (NOT IMPLEMENTED YET)
    record  save the video into a local file
    search  search for a video on arte+7
            It will display a numbered list of results and enter
            a simple command line interpreter that has the same 4 commands:
                url NUMBER
                play NUMBER (NOT IMPLEMENTED YET)
                record NUMBER
                search STRING'''

    parser = OptionParser(usage=usage)
    parser.add_option('-l', '--lang', dest='lang', type='string', default=DEFAULT_LANG,
            action='store', help='language of the video fr, de, en (default: fr)')
    parser.add_option('-q', '--quality', dest='quality', type='string', default=DEFAULT_QUALITY,
            action='store', help='quality of the video sd or hd (default: hd)')
    parser.add_option('--quiet', dest='quiet', default=False,
            action='store_true', help='do not show output of rtmpdump')

    options, args = parser.parse_args()

    if options.lang not in ('fr', 'de', 'en'):
        die('Invalid option')
    if options.quality not in ('sd', 'hd'): # what is EQ ?
        die('Invalid option')
    if len(args) < 2:
        MyCmd([], options).cmdloop()
        exit(0)
    if args[0] not in ('url', 'play', 'record', 'search'):
        die('Invalid command')

    if args[0] == 'play':
        # video_url = get_rtmp_url(args[1], quality=options.quality, lang=options.lang)[0]
        video_url = None
        play(video_url)
        exit(1)

    elif args[0] == 'url':
        print get_rtmp_url(args[1], quality=options.quality, lang=options.lang)[0]

    elif args[0] == 'record':
        record(args[1], options)

    elif args[0] == 'search':
        results = search(' '.join(args[1:]), options.lang)
        if results is not None:
            print_results(results)
            MyCmd(results, options).cmdloop()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print 'Aborted'
