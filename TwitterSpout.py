import sys, os
import json
import tweepy as tw
import tweepy.streaming
import time


def getConfig(directory):
    params = {}
    if directory == "null":
        directory = ''
    fileIn = open(directory+'config')
    content = fileIn.readlines()
    for item in content:
        if ' = ' in item:
            while '  ' in item:
                item = item.replace('  ',' ')
            while '\n' in item:
                item = item.replace('\n','')
            line = item.split(' = ')
            try:
                line[1] = float(line[1])
                if line[1] == int(line[1]):
                    line[1] = int(line[1])
            except:
                None
            params[line[0]] = line[1]
    print "\nLoaded params:"
    for key,item in params.iteritems():
        print '\t*', key,':', item
    return params
    
    
def stripWords(text):
    listed = ''.join((c if (c.isalnum() or c == '#') else ' ') for c in text).split()
    return listed
    
    
def getWords(directory, name):
    with open (directory+'words', 'r') as fileIn:
        data=fileIn.read().replace('\n', ' ')
    return(stripWords(data))
    
    
def getAuth(cfg):
    auth1 = tw.auth.OAuthHandler(cfg['consumerKey'],cfg['consumerSecret'])
    auth1.set_access_token(cfg['accessToken'],cfg['accessTokenSecret'])
    api = tw.API(auth1)
    return {'auth':auth1,'api':api}


def postTweet(api,text,image):
    if image != None and image != 'null':
        api.update_status(text)
        print "posted tweet:", text
        
        
def getTweets(login, cfg, words, qualifiers):
    print "DEBUG 1"
    ear = giListener()
    print "DEBUG 2"
    stream = tw.Stream(login['auth'], ear, timeout=30.0)
    print "DEBUG 3"
    #stream.filter(locations=[cfg['lat1'],cfg['lon1'],cfg['lat2'],cfg['lon2']], async=False, track = [])
    stream.filter(track = words)
    print "DEBUG 4"
    
    """while True:
        try:
            #stream.filter(locations=[cfg['lat1'],cfg['lon1'],cfg['lat2'],cfg['lon2']], async=False, track = words)
            stream.filter(locations=[cfg['lat1'],cfg['lon1'],cfg['lat2'],cfg['lon2']], async=False, track = [])
            break
        except Exception, e:
            delay = 30
            print "Filter failed, sleeping", delay, "seconds..."
            print e
            time.sleep(delay) """
             
             
class giListener(tw.StreamListener):
    def on_status(self, status):
        # We'll simply print some values in a tab-delimited format
        # suitable for capturing to a flat file but you could opt 
        # store them elsewhere, retweet select statuses, etc
        try:
            print "%s\t%s\t%s\t%s" % (status.text, 
                                      status.author.screen_name, 
                                      status.created_at, 
                                      status.source,)
        except Exception, e:
           # print >> sys.stderr, 'Encountered Exception:', e
            print "Encountered exception:", e
            pass

    def on_error(self, status_code):
        #print >> sys.stderr, 'Encountered error with status code:', status_code
        print "Encountered error with status code:", status_code
        return True # Don't kill the stream

    def on_timeout(self):
        print >> sys.stderr, 'Timeout...'
        return True # Don't kill the stream

# Create a streaming API and set a timeout value of 60 seconds.


def main():
    try:
        directory = sys.argv[1]
    except:
        directory = os.getcwd() + '/'
    cfg = getConfig(directory)
    words = getWords(directory, 'keywords')
    print "Loaded Keywords:", words
    qualifiers = getWords(directory, 'qualifiers')
    print "Loaded Qualifiers:", qualifiers
    login = getAuth(cfg)
    getTweets(login,cfg,words,qualifiers)

main()