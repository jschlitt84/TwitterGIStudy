import sys, os
import json
import tweepy
import tweepy.streaming
import time

conditions = []
qualifiers = {}
expected = ['Lat1','Lat2','Lon1','Lon2']


#Hacky patch for raw json access, not granted in newest tweepy version
@classmethod
def parse(cls, api, raw):
	status = cls.first_parse(api, raw)
	setattr(status, 'json', json.dumps(raw))
	return status

tweepy.models.Status.first_parse = tweepy.models.Status.parse
tweepy.models.Status.parse = parse


#Loads configuration from file config
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
    
    if params['Lat1']>params['Lat2']:
        params['Lat1'],params['Lat2'] = params['Lat2'],params['Lat1']
    if params['Lon1']>params['Lon2']:
        params['Lon1'],params['Lon2'] = params['Lon2'],params['Lon1']
        
    return params


   
#Filters out non alphanumeric characters, leaves hashtags   
def stripWords(text):
    listed = ''.join((c if (c.isalnum()) else ' ') for c in text).split()
    return listed
    
    
#Loads & cleans phrases from text file  
def getWords(directory, name):
    with open (directory+name, 'r') as fileIn:
        text=fileIn.read().lower()
        while '  ' in text:
            text = text.replace('  ',' ')
    data = text.split('\n')
    toDelete = []
    for pos in range(len(data)):
        entry = data[pos]
        while entry.startswith(' '):
            entry = entry[1:]
        while entry.endswith(' '):
            entry = entry[:-1]
        if entry == '':
            toDelete.append(pos)
        data[pos] = entry
    if len(toDelete) != 0:
        toDelete.reverse()
        for ref in toDelete:
            del data[ref]
    print toDelete
    return data

    
#Return authorization object
def getAuth(cfg):
    auth1 = tweepy.auth.OAuthHandler(cfg['consumerKey'],cfg['consumerSecret'])
    auth1.set_access_token(cfg['accessToken'],cfg['accessTokenSecret'])
    api = tweepy.API(auth1)
    return {'auth':auth1,'api':api}


#Posts a tweet
def postTweet(api,text,image):
    if image != None and image != 'null':
        api.update_status(text)
        print "posted tweet:", text
        
        
def getTweets(login, cfg):
    print "Setting up listener"
    ear = giListener(tweepy.StreamListener,)
    print "Starting stream"
    stream = tweepy.Stream(login['auth'], ear, timeout=30.0)
    print "Filtering stream"
    stream.filter(locations=[cfg['Lat1'],cfg['Lon1'],cfg['Lat2'],cfg['Lon2']], track = conditions)
    
    """while True:
        try:
            #stream.filter(locations=[cfg['lat1'],cfg['lon1'],cfg['lat2'],cfg['lon2']], async=False, track = conditions)
            stream.filter(locations=[cfg['lat1'],cfg['lon1'],cfg['lat2'],cfg['lon2']], async=False, track = [])
            break
        except Exception, e:
            delay = 30
            print "Filter failed, sleeping", delay, "seconds..."
            print e
            time.sleep(delay) """
             
             
class giListener(tweepy.StreamListener):
    def on_status(self, status):
        if True:
            text = status.text.lower()
            found = False
            if "rt @" not in text:
                for word in qualifiers:
                    if word in text:
                        found = True
                        break
            if found == True:
                print "\033[1m%s\t%s\t%s\t%s\033[0m" % (status.text, 
                            status.author.screen_name, 
                            status.created_at, 
                            status.source,)
            else:
                 print "%s\t%s\t%s\t%s" % (status.text, 
                            status.author.screen_name, 
                            status.created_at, 
                            status.source,)
        """except Exception, e:
            print "Encountered exception:", e
            pass"""

    def on_error(self, status_code):
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
    conditions = getWords(directory, 'conditions')
    print "Loaded Conditions:", conditions
    qualifiers = set(getWords(directory, 'qualifiers'))
    print "Loaded Qualifiers:", qualifiers
    login = getAuth(cfg)
    print "Ready to run...", raw_input()
    getTweets(login,cfg)

main()