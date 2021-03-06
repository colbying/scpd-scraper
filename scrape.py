#!/usr/bin/env python
import re
import os
import sys
from getpass import *
from mechanize import Browser
from bs4 import BeautifulSoup

"""

See README for general documentation:

Dependencies:
1. BeautifulSoup for parsing: [sudo easy_install beautifulsoup4] or [http://www.crummy.com/software/BeautifulSoup/](http://www.crummy.com/software/BeautifulSoup/)
2. Mechanize for emulating a browser: [sudo easy_install mechanize] or [http://wwwsearch.sourceforge.net/mechanize/](http://wwwsearch.sourceforge.net/mechanize/)
3. mimms for downloading video streams [sudo apt-get install mimms] or using MacPorts for Mac [http://www.macports.org/](http://www.macports.org/)
4. (optional- To convert to mp4) Handbrake CLI, for converting to mp4: [http://handbrake.fr/downloads2.php](http://handbrake.fr/downloads2.php)
5. (optional- prevents scraper from crashing when notes are being used) html5lib parser for BeautifulSoup http://www.crummy.com/software/BeautifulSoup/bs4/doc/#installing-a-parser

Usage:
    python scrape.py [yourUserName] [optional flags] "Interactive Computer Graphics" "Programming Abstractions" ...

"""


#Flags
ALL_FLAG = "--all"
ORGANIZE_FLAG = "--org"
MP4_FLAG = "--mp4"
HELP_FLAG = "--help"
NEW_FIRST_FLAG = "--priority=new"

def convertToMp4(wmv, mp4):
    print "Converting ", mp4
    os.system('HandBrakeCLI -i %s -o %s' % (wmv, mp4))
    os.system('rm -f %s' % wmv)
    print "Finished mp4 conversion for " + courseName

def download(work, courseName, downloadSettings):
    # work[0] is url, work[1] is wmv, work[2] is mp4
    if os.path.exists(work[1]) or os.path.exists(courseName + "/" + work[1]) or os.path.exists(courseName + "/" + work[2]) or os.path.exists("watched/"+work[1]) or os.path.exists(work[2]) or os.path.exists("watched/"+work[2]):
        print "Already downloaded", work[1]
        return

    print "Starting", work[1]

    wmvpath = work[1]
    mp4path = work[2]
    if (downloadSettings["shouldOrganize"]):
        coursePath = courseName.replace(" ", "\ ") # spaces break command line navigation
        assertDirectoryExists("./"+courseName)
        wmvpath = "./" + coursePath + "/" + wmvpath
        mp4path = "./" + coursePath + "/" + mp4path

    os.system("mimms -c %s %s" % (work[0], wmvpath))
    if (downloadSettings["shouldConvertToMP4"]):
        try:
            convertToMp4(wmvpath, mp4path)
        except:
            print "MP4 Error: unable to convert " + courseName + " to mp4, you may not have installed HandBrakeCLI"
    print "Finished", work[1]

def assertLoginSuccessful(forms):
    for form in forms:
        if (form.name == "login"):
            print "Login Error: username or password likely incorrect"
            sys.exit(0)

def assertDirectoryExists(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)

def downloadAllLectures(username, courseName, password, downloadSettings):
    br = Browser()
    br.addheaders = [('User-agent', 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6; en-us) AppleWebKit/531.9 (KHTML, like Gecko) Version/4.0.3 Safari/531.9')]
    br.set_handle_robots(False)
    br.open("https://myvideosu.stanford.edu/oce/currentquarter.aspx")
    assert br.viewing_html()
    br.select_form(name="login")
    br["username"] = username
    br["password"] = password

    # Open the course page for the title you're looking for
    print "Logging in to myvideosu.stanford.edu..."
    response = br.submit()

    # Assert that the login was successful
    assertLoginSuccessful(br.forms())
    br.select_form(name="multifactor_send")
    br.submit()
    br.select_form(name="login")

    # Assumes you have two-factor authentication with SMS texting
    otp = raw_input('Enter your code: ')

    br["otp"] = otp
    response = br.submit()

    # Assert Course Exists
    try:
        response = br.follow_link(text=courseName)
    except:
        print 'Course Read Error: "'+ courseName + '"" not found'
        return

    print "Logged in, going to course link."

    # Build up a list of lectures
    print '\n=== Starting "' + courseName + '" ==='
    print "Loading video links."
    links = []
    for link in br.links(text="WMP"):
        course = link.url.split('%22,%22')[1]
        courseID = link.url.split('%22,%22')[0].split('openSL(%22')[1]
        lastPart = str(link).split('","","WA","&wmp=true");'')])')[0].split(course + '","')[1]
        coID = lastPart.split('","')[0]
        lectureID = lastPart.split('","')[1]
        linkurl = "http://myvideosu.stanford.edu/player/slplayer.aspx?coll=" + courseID + "&course=" + course + "&co=" + coID + "&lecture=" + lectureID + "&authtype=WA&wmp=true"
        links.append(linkurl)
    link_file = open('links.txt', 'w')

    if not downloadSettings["newestFirst"]:
        links.reverse() # download the oldest ones first.

    print "Found %d links, getting video streams."%(len(links))
    videos = []
    for link in links:
        try:
            response = br.open(link)
            soup = BeautifulSoup(response.read())
        except:
            print '\n'
            print "Error reading "+ link
            print 'If this error is unexpected, try installing the html5lib parser for BeautifulSoup. Pages with Notes stored on them have been known to crash when using an outdated parser'
            print 'you can find instructions on installing the html5lib at "http://www.crummy.com/software/BeautifulSoup/bs4/doc/#installing-a-parser"'
            print '\n'
            continue
        video = soup.find('object', id='WMPlayer')['data']
        video = re.sub("http","mms",video)
        video = video.replace(' ', '%20') # remove spaces, they break urls
        output_name = re.search(r"[a-z]+[0-9]+[a-z]?/[0-9]+",video).group(0).replace("/","_") #+ ".wmv"

        #specify video name and path for .wmv file type
        output_wmv = output_name + ".wmv"
        link_file.write(video + '\n')

        #specify video name and path for .mp4 file type
        output_mp4 = output_name + ".mp4"
        videos.append((video, output_wmv, output_mp4))

        print video
    link_file.close()

    print "Downloading %d video streams."%(len(videos))
    for video in videos:
        download(video, courseName, downloadSettings)
    print "Done!"

def downloadAllCourses(username, courseNames, downloadSettings):
    password = getpass()
    for courseName in courseNames:
        downloadAllLectures(username, courseName, password, downloadSettings)


def printHelpDocumentation():
    print "\n"
    print "=== SCPD Scrape Help==="
    print "https://github.com/cschubiner/scpd-scraper"
    print "Usage:"
    print "  python scrape.py 'username' '--flag1' ... '--flagN' 'courseName1' 'courseName2' ... 'courseNameN'"
    print "Flags:"
    print "  " +    ALL_FLAG   + ": downloads all new videos based on names of subdirectories in addition to courses listed"
    print "  " + ORGANIZE_FLAG + ": auto-organize downloads into subdirectories titled with the course name"
    print "  " +    MP4_FLAG   + ": converts video to mp4"
    print "  " +NEW_FIRST_FLAG + ": downloads the newest (most recent) videos first"
    print "Dependencies:"
    print "  1. BeautifulSoup for parsing: [sudo easy_install beautifulsoup4] or [http://www.crummy.com/software/BeautifulSoup/](http://www.crummy.com/software/BeautifulSoup/)"
    print "  2. Mechanize for emulating a browser: [sudo easy_install mechanize] or [http://wwwsearch.sourceforge.net/mechanize/](http://wwwsearch.sourceforge.net/mechanize/)"
    print "  3. mimms for downloading video streams [sudo apt-get install mimms] or using MacPorts for Mac [http://www.macports.org/](http://www.macports.org/)"
    print "  4. (optional- To convert to mp4) Handbrake CLI, for converting to mp4: [http://handbrake.fr/downloads2.php](http://handbrake.fr/downloads2.php)"
    print "  5. (optional- prevents scraper from crashing when notes are being used) html5lib parser for BeautifulSoup http://www.crummy.com/software/BeautifulSoup/bs4/doc/#installing-a-parser"
    print "\n"


if __name__ == '__main__':
    if (len(sys.argv) < 2):
        print "Incorrect usage: please enter 'python scrape.py " + HELP_FLAG + "' for help"
    else:
        username = sys.argv[1]
        flags = [param for param in sys.argv[1:len(sys.argv)] if param.startswith('--')]
        courseNames = [param for param in sys.argv[2:len(sys.argv)] if not param.startswith('--')]
        downloadSettings = {"shouldOrganize": False, "shouldConvertToMP4": False, "newestFirst": False}

        # parse flags
        if (len(flags) != 0):
            if HELP_FLAG in flags:
                printHelpDocumentation()
                sys.exit(0)
            if ALL_FLAG in flags:
                # Append names of subdirectories (excluding hidden folders and 'watched') to courseNames list
                courseNames += [dirName for dirName in os.listdir(".") if os.path.isdir(dirName) and not (dirName.startswith('.') or dirName is "watched")]
                flags.remove(ALL_FLAG)
            if ORGANIZE_FLAG in flags:
                downloadSettings["shouldOrganize"] = True
                flags.remove(ORGANIZE_FLAG)
            if MP4_FLAG in flags:
                downloadSettings["shouldConvertToMP4"] = True
                flags.remove(MP4_FLAG)
            if NEW_FIRST_FLAG in flags:
                downloadSettings["newestFirst"] = True
                flags.remove(NEW_FIRST_FLAG)

            if not len(flags) is 0:
                print "following flags undefined and will be ignored: "
                print flags


        downloadAllCourses(username, courseNames, downloadSettings)
