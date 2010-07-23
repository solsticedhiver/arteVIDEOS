#!/usr/bin/python
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
from urllib2 import urlopen
from urllib import unquote
from urlparse import urlparse
from subprocess import call
from os.path import exists
from os import environ as os_environ
from sys import exit, argv, stderr

#lang = 'fr' # 'fr 'de'
#quality = 'hd' # 'sd' 'EQ' 'hd'

def usage(progname):
    print '''Usage: %s url|play|record URL
Play arte+7 videos without a mandatory browser or even record them. 
You will need however to pass the url of the webpage presenting the video.
They all begin with http://videos.arte.tv/fr/videos/{...}
    url     just show the real url of the video
    play    play the video directly
    record  record the video to a file 
''' % progname

def get_url(url_page, quality='hd', lang='fr'):
    '''get the real url of the video'''
    # inspired by the get_rtmp_url from arte7recorder project

    # get the web page
    soup = BeautifulSoup(urlopen(url_page).read())
    object_tag = soup.find('object', classid='clsid:d27cdb6e-ae6d-11cf-96b8-444553540000')
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
        raise 'There is no video for the language %s' % lang
    soup = BeautifulStoneSoup(urlopen(xml_url).read())
    # at last the video url
    video_url = soup.urls.find('url', {'quality': quality}).string

    return (video_url, player_url)

def find_in_path(path, filename):
    for i in path.split(':'):
        if exists('/'.join([i, filename])):
            return True
    return False

if __name__ == '__main__':
    if len(argv) < 3 or argv[1] not in ('url', 'play', 'record'):
        usage(argv[0])
        exit(1)
    if argv[1] in ('-h', '--help', 'help'):
        usage(argv[0])
        exit(0)

    url_page = argv[2]
    video_url, player_url = get_url(url_page)
    output_file = urlparse(url_page).path.split('/')[-1].replace('.html','.flv')

    if argv[1] == 'url':
        print video_url
        exit(0)
    elif argv[1] == 'record':
        if not find_in_path(os_environ['PATH'], 'rtmpdump'):
            print >>stderr, 'Error: rtmpdump has not been found'
            exit(1)
        cmd_args = '-r %s --swfVfy %s --flv %s' % (video_url, player_url, output_file)
        if exists(output_file):
            # try to resume a download
            cmd_args += ' --resume'

        print ':: Downloading and saving to %s' % output_file
        call(['rtmpdump'] + cmd_args.split(' '))

