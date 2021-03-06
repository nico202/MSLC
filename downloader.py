#This script will download all the lyrics from the given site(s) and get info (BPM, genre, etc) about them
#Save all to a db


from lxml import html
import urllib
import requests
import datetime
import sqlite3
import os.path
import sys
import ast
from random import randint

network_error_message = "Network error, try again"

def is_number(num):
    try:
        return int(num)
    except:
        return False

def count_letters(word):
    BAD_LETTERS = " "
    return len([letter for letter in word if letter not in BAD_LETTERS])

def clear_word(word):
    TO_REMOVE = '''()?![]{}=,;:".-+*/\\|'''
    return "".join([letter for letter in word if letter not in TO_REMOVE])

try:
    script, task, item = sys.argv
except:
    script = sys.argv[0]
    print "Usage: %s [download|update|analyse] [hits|lyrics]" % (script)
    print "Usage generate: %s generate starting_word" % (script)
    exit()

is_new_session = not os.path.isfile('lyricsdb.sqlite')

db = sqlite3.connect('lyricsdb.sqlite')

c = db.cursor()
d = db.cursor()
if is_new_session:
    c.execute('''CREATE TABLE hits
                 (year int, artist text, title text, number int, month int)
            ''')
    c.execute('''CREATE TABLE lyrics
                 (artist text, title text, lyric text, charsNumber int, versesNumber int, linesNumber int, linesPerVerse int, wordNumbers int)
            ''')
    c.execute('''CREATE TABLE assoc
                 (artist text, title text, word text, times int, verseNumber int, nextWord text, precWord text)
            ''')

if task == 'download':
    if item == "hits":
        ##import pprint #debug
        #Get the current year
        now = datetime.datetime.now().year

        #Download last 5 years' top songs
        page = {}
        for year in range(now-10,now):
            
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
                    print network_error_message
    else:
        print "Lyrics Download"
        c.execute('SELECT artist,title FROM hits')
        songs = c.fetchall()
        
        for song in songs:
            query = song[0] + ' ' + song[1]
            query = query.encode('utf-8')
            artist = urllib.quote_plus(song[0].encode('utf-8'))
            song_title = urllib.quote_plus(song[1].encode('utf-8'))
            c.execute('SELECT 1 FROM lyrics WHERE `artist` = ? AND `title` = ?', (artist,song_title,))
            if c.fetchone():
                print "Lyrics %s from %s already present, skipping" % (song[1], song[0])
                continue
            else:
              #  try:
                #Download lyrics
                print "Looking for %s ..." % query,
                # TODO: if not found, try to replace & with and etc
                # Or removing "featuring" etc
                url = "http://lyrics.wikia.com/api.php?artist=%s&song=%s" % (artist,song_title)
                page = requests.get(url).text
                tree = html.fromstring(page)
                in_page_search = tree.xpath('//body/h3/a')
                song_url = in_page_search[0].attrib['href']
                print "... downloading it"
                page = requests.get(song_url).text
                tree = html.fromstring(page)
                song_text = tree.xpath('//div[@class="lyricbox"]/text()')
                new_lines = tree.xpath('//div[@class="lyricbox"]//br')
                
                total_lines = 0
                for br in new_lines:
                    total_lines += 1
                
                song_text = [value for value in song_text if value != '\n']
                
                charlenght = 0
                words_number = 0
                for verse in song_text:
                    verse.encode('utf-8')
                    charlenght += count_letters(verse)
                    words_number += len(verse) - count_letters(verse) + 1 #Count words as spaces +1
                
                #TODO: I lose a new line somewhere... but this way works
                br_number = total_lines - len(song_text) + 1 + 1
                
                verse_lenght = str(song_text)
                # (artist, title, lyric, charsNumber, versesNumber, linesNumber, linesPerVerse, wordNumbers)
                to_add = [artist, song_title, str(song_text), charlenght, br_number, len(song_text),"", words_number]
                db.execute('INSERT INTO lyrics VALUES ( ?,?,?,?,?,?,?, ? )', to_add)
                db.commit()

#                except:
     #          print network_error_message

elif task == 'analyse':
    ##Add BPM, genre, mood
    c.execute('SELECT artist,title,lyric FROM lyrics')
    songs = c.fetchall()
    
    for song in songs:
        artist = song[0]
        title = song[1]
        lyric = ast.literal_eval(song[2])  
        d.execute('SELECT 1 FROM assoc WHERE artist = ? AND title = ?', (artist, title,))
        if d.fetchone():
            print "Lyrics %s from %s already present, skipping" % (title, artist)
            continue
        else:
            print "Analysing %s from %s ..." % (title, artist),
            for line in lyric:
                
                a = ""
                b = ""
                c = ""
                ##Works but is ugly. FIX
                for word in line.split():
                    a = b
                    b = c
                    c = clear_word(word)
                    #(artist text, title text, word text, times int, verseNumber int, nextWord text, precWord text)
                    to_add = [artist, title, b, "", "", c, a]
                    if b:
                        db.execute('INSERT INTO assoc VALUES ( ?,?,?,?,?,?,? )', to_add)
                a = b
                b = c
                c = ""
                to_add = [artist, title, b, "", "", c, a]
                db.execute('INSERT INTO assoc VALUES ( ?,?,?,?,?,?,? )', to_add)
                
            db.commit()
            print "... done!"

elif task == 'generate':
    #Get mean line word lenght
    c.execute('SELECT AVG(`wordNumbers`), AVG(`linesNumber`), AVG(`versesNumber`) FROM lyrics')
    stats = c.fetchone()
    if not stats:
        print "Error with the db"
        exit()
    
    meanWords = stats[0]
    meanLines = stats[1]
    meanVerse = stats[2]
    meanLineLen = meanWords / meanLines
    meanVerseLen = meanLines / meanVerse
    print "Info: generating lines of lenght: %s words, %s verse lines, %s verses\n" % (meanLineLen, meanVerseLen, meanVerse)
    
    
    for gen_verse in range (0, int(meanVerse)+randint(-3,3)): # 15 versi
        #print "NEW VERSE (%s)" % (gen_verse)
        for gen_line in range(0,int(meanVerseLen)+randint(-2,2)): # 3 linee
            #print "NEW LINE (%s)" % (gen_line)
            #Decide the word to start with: NOT NULL, WITHOUT A PRECEDING WORD; WITH A FOLLOWING WORD
            c.execute('SELECT `word` FROM assoc WHERE `precWord` == "" AND `word` != "" AND `nextWord` != "" ORDER BY RANDOM () LIMIT 1')
            next_word = c.fetchone()[0]
            current_word = ""
            
            for gen_word in range(0,(int(meanLineLen)+randint(-3,3))): #6 parole
                prec_word = current_word
                current_word = next_word
                #prevent same-word-loop.
                if (current_word == prec_word):
                    QUERY = 'SELECT `nextWord` FROM assoc WHERE `precWord` LIKE ? AND `word` != ? AND `nextWord` != "" ORDER BY RANDOM () LIMIT 1'
                    QUERY_LIMIT = 'SELECT `nextWord` FROM assoc WHERE `precWord` LIKE ? AND `word` != ? ORDER BY RANDOM () LIMIT 1'
                else:
                    #prec_word = '%prec_word%'
                    QUERY = 'SELECT `nextWord` FROM assoc WHERE `precWord` LIKE ? AND `word` = ? AND `nextWord` != "" ORDER BY RANDOM () LIMIT 1'
                    QUERY_LIMIT = 'SELECT `nextWord` FROM assoc WHERE `precWord` LIKE ? AND `word` = ? ORDER BY RANDOM () LIMIT 1'
                #Use that word to gen N words
                # We could use len(x) to get the exact number of letters
                # With LIKE % & LIKE _ we can search for "rhyming" words (difficult in english)
                if (gen_word <= int (meanLineLen) - 4): # far from desired lenght. Let nextWord exist
                    c.execute(QUERY, (prec_word,current_word,))
                elif (gen_word <= int (meanLineLen) + 4): #approching to meanLineLen. nextWord can be unexistent
                    c.execute(QUERY_LIMIT, (prec_word,current_word,))
                else: #last needed word. Force it not to exist
                    c.execute('SELECT `nextWord` FROM assoc WHERE `precWord` = ? AND `word` = ? AND `nextWord` == "" ORDER BY RANDOM () LIMIT 1', (prec_word,current_word,))
                try:
                    next_word = c.fetchone()[0]
                except:
                    try:
                        if (gen_word <= int (meanLineLen) - 4): # far from desired lenght. Let nextWord exist
                            c.execute('SELECT `word` FROM assoc WHERE `precWord` = ? AND `word` != "" AND `nextWord` != ? ORDER BY RANDOM () LIMIT 1', (prec_word,current_word,))
                        elif (gen_word == int (meanLineLen)): #approching to meanLineLen. nextWord can be unexistent
                            c.execute('SELECT `word` FROM assoc WHERE `precWord` = ? AND `word` != "" ORDER BY RANDOM () LIMIT 1', (current_word,))
                        else: #last needed word. Force it not to exist
                            c.execute('SELECT `word` FROM assoc WHERE `precWord` = ? AND `word` != "" AND `nextWord` == "" ORDER BY RANDOM () LIMIT 1', (current_word,))
                    except:
                        try:
                            next_word = c.fetchone()[0]
                        except:
                            next_word = ""
                            break
                if is_number(next_word):
                    randint(0,int(next_word))
                print next_word.encode("utf-8"),
                
            print "\n",
        print "\n"


    
# Save (commit) the changes
db.commit()

# We can also close the connection if we are done with it.
# Just be sure any changes have been committed or they will be lost.
#db.close()
