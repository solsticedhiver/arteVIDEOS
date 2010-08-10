#!/usr/bin/python
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
    switch to a different language'''
        if arg == '':
            print self.options.lang
        elif arg in ('fr' ,'de', 'en'):
            self.options.lang = arg

    def do_help(self, arg):
        '''print the help'''
        if arg == '':
            print '''COMMANDS:
    url NUMBER      show real url of video
    play NUMBER     play chosen video (NOT IMPLEMENTED YET)
    record NUMBER   download and save video to a local file
    search STRING   search for a video
    lang [fr|de|en] switch to a different language
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
