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

CLSID = 'clsid:d27cdb6e-ae6d-11cf-96b8-444553540000'

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
        xml_url = soup.find('video', {'lang': lang})['ref']
        if xml_url is None:
            raise 'The language %s is not available for this video' % lang
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

def main():
    usage = '''Usage: %prog url|play|record [OPTIONS] URL
Play arte+7 videos without a mandatory browser or even record them. 
You will need however to pass the url of the webpage presenting the video.
They all begin with http://videos.arte.tv/fr/videos/{...}
    url     just show the real url of the video
    play    play the video directly (NOT IMPLEMENTED)
    record  record the video to a file'''

    parser = OptionParser(usage=usage)
    parser.add_option('-l', '--lang', dest='lang', type='string', default='fr',
            action='store', help='language of the video fr or de (default: fr)')
    parser.add_option('-q', '--quality', dest='quality', type='string', default='hd',
            action='store', help='quality of the video sd or hd (default: hd)')
    parser.add_option('--quiet', dest='quiet', default=False,
            action='store_true', help='do not show output of rtmpdump')

    options, args = parser.parse_args()

    if options.lang not in ('fr', 'de'):
        die('Invalid option')
    if options.quality not in ('sd', 'hd'): # what is EQ ?
        die('Invalid option')
    if len(args) != 2 or args[0] not in ('url', 'play', 'record'):
        die('Invalid command')

    if args[0] == 'play':
        print >> stderr, 'Error: <play> is not implemented yet. Use record and then your favorite player'
        exit(1)

    url_page = args[1]
    video_url, player_url = get_rtmp_url(url_page, quality=options.quality, lang=options.lang)
    output_file = urlparse(url_page).path.split('/')[-1].replace('.html','.flv')

    if args[0] == 'url':
        print video_url
        exit(0)
    elif args[0] == 'record':
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

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print 'Aborted'
