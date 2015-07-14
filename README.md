A script to watch/record videos from the catch-up TV site http://www.arte.tv

- No flash-plugin required: just use your favorite player
- Internet lag? just record the video and play it later.

# WARNING:
These videos are **copyrighted by ARTE**. I guess that you are **NOT** free to *share*, *sell* or *modify* those videos !
You will not be able to view videos if you are outside these countries: France, Germany, Belgium, Austria and Switzerland.
Some videos that are restricted to a mature audience (+18) are only visible between 23:00 and 05:00.

# REQUIREMENTS

* python 2.7 (but not python 3)
* beautifulsoup 4.x
* a video player like *mplayer*, *vlc*, *xine* or *totem* to use the play command.
Or add your own player in the script. Help is provided

# FLATTR
You can show your support for this little software:
- You can flattr at http://flattr.com/thing/176287/arteVIDEOS
- You can even make a donation via *Flattr* !

# USAGE

    Usage: arteVIDEOS.py url|play|record [OPTIONS] URL
           arteVIDEOS.py search [OPTIONS] STRING...
           arteVIDEOS.py live
           arteVIDEOS.py

    Play or record videos from arte VIDEOS website without a mandatory browser.

    In the first form, you need the url of the video page
    In the second form, just enter your search term
    In the last form (without any argument), you enter an interactive interpreter
    (type help to get a list of them, once in the interpreter)

    COMMANDS
        url     show the url of the video
        play    play the video directly (NOT IMPLEMENTED YET)
        record  save the video into a local file
        live    play arte live
        search  search for a video on arte+7
                It will display a numbered list of results and enter
                a simple command line interpreter

    Options:
      -h, --help            show this help message and exit
      -d DLDIR, --downloaddir=DLDIR
                            directory where to save the downloads
      -l LANG, --lang=LANG  preferred language of the video fr, de (default: fr)
      -q QUALITY, --quality=QUALITY
                            quality of the video hd or md or sd or ld (default: hd)

# QUALITY:
Each quality is a resolution height x width @ bitrate
* hd: 1280x720@2200
* md: 720x406@1500
* sd: 720x406@800
* ld: 384x216@300

If you run it without any argument, you enter a simple command line interpreter.
Here is an example of a session. [...] is used to shorten the output:

    arteVIDEOS> plus7
    :: Retrieving plus7 videos list
    (1) La reine du silence
        Denisa, une jeune Rom sourde, s’invente une nouvelle vie en dansant sur des films de Bollywood...
    [...]
    (17) Profession négociateur (4/6)
        Alors que King négocie la libération d'un couple de Britanniques, la police indienne ouvre le feu...
    arteVIDEOS> play 17
    :: Playing video(s): #17
    :: Playing http://arte.gl-systemhaus.de/am/tvguide/default/054720-004-A_SQ_2_VF-STF_01823860_MP4-2200_AMM-Tvguide.mp4
    arteVIDEOS> next
    (18) Tout est vrai (ou presque)
        Toute la vérité (ou presque) sur Bob Dylan.
    [...]
    (34) La cuisine anti-gaspi
        Au Pays-Bas, tout est là: fast-foods responsables, chefs innovants et adeptes de la cuisine à base d'insectes!
    arteVIDEOS> info 26
    == X:enius ==
    Tout le monde en parle, mais peu de gens les utilisent. Les voitures électriques ne sont-elles qu'une mode passagère
    ou sont-elles en passe de révolutionner la circulation routière ? En Europe, l'Allemagne, numéro 1 de l'industrie automobile,
    est pourtant considérée comme la lanterne rouge de l'électromobilité...

    21/05/2015 08:29:40 +0200
    arteVIDEOS> record 26
    :: Recording video(s): #26
    :: Recording http://arte.gl-systemhaus.de/am/tvguide/ALL/055916-011-A_SQ_2_VF-STF_01823061_MP4-2200_AMM-Tvguide.mp4

    arteVIDEOS> exit
