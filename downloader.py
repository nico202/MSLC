#This script will download all the lyrics from the given site(s) and get info (BPM, genre, etc) about them
#Output lyrics as .txt files on ./lyrics
#We need to define a way to attach info in that file
#And which site are we going to use
from lxml import html
import requests
import datetime
import sqlite3
import os.path
import sys

try:
    script, task, item = sys.argv
except:
    script = sys.argv[0]
    print "Usage: %s [download|update|analyse] [hits|lyrics]" % (script)
    exit()

is_new_session = not os.path.isfile('lyricsdb.sqlite')

db = sqlite3.connect('lyricsdb.sqlite')
c = db.cursor()

if is_new_session:
    c.execute('''CREATE TABLE hits
                 (year int, artist text, name text, number int, month int)
            ''')
    c.execute('''CREATE TABLE lyrics
                 (lyric text, charsNumber int, versesNumber int, linesNumber int, linesPerVerse int)
            ''')
    c.execute('''CREATE TABLE assoc
                 (word text, times int, verseNumber int, nextWord int, precWord int)
            ''')

if task == "download":
    if item == "hits":
        ##import pprint #debug
        #Get the current year
        now = datetime.datetime.now().year

        #Download last 5 years' top songs
        page = {}
        for year in range(now-5,now):
            
            #Don't download songs we already have
            c.execute('SELECT 1 FROM hits WHERE `year` = ?', (year,))
            if c.fetchone():
                print "We already have hits for year %s" % (year)
                continue
            else:
                try:
                    print "Downloading top10songs from year: %s" % year
                    url = "http://top10songs.com/months-of-%s.html" % year
                    #page.append(year)
                    page[year] = requests.get(url).text
                    #print r.content
                    tree = html.fromstring(page[year])
                    months = tree.xpath('//tr[@class="first_row"]/td/b/text()')
                #    songs = tree.xpath('//a[@class="song_link"]/text()')
                #    artists = tree.xpath('//a[@class="artist_link"]/text()')
                    list = tree.xpath('//td[@class="left"]//text()')
                    artists = []
                    songs = []
                    num = 0
                    for element in list:
                        if ( num == 0 ):
                            songs.append(element)
                            num = 1
                        else:
                            artists.append(element)
                            num = 0

                    num = 0
                    for artist in artists:
                        ##print "Artista, canzone, anno: %s, %s, %s" % (artist, songs[num], year)
                        number = num + 1
                        
                        month_counter = 12
                        
                        while number > 10:
                            number -= 10
                            month_counter -= 1
                            
                        to_add = [year,artist,songs[num],number,month_counter]
                        db.execute('INSERT INTO hits VALUES ( ?,?,?,?,? )', to_add)

                        num += 1
                except:
                    print "Network error, try again"
    else:
        #Download lyrics
        print "Scarica testi"            

# Save (commit) the changes
db.commit()

# We can also close the connection if we are done with it.
# Just be sure any changes have been committed or they will be lost.
db.close()
