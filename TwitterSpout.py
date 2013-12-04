import sys, os
import json
import tweepy
from tweepy.streaming import StreamListener
import time
import multiprocessing

expected = ['Lat1','Lat2','Lon1','Lon2','Logins','Conditions','Qualifiers']


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
        
    logins = params['Logins'].replace(',','')
    while '  ' in logins:
        logins = logins.replace('  ',' ')
    params['Logins'] = logins.split(' ')
    
    if params['Lat1']>params['Lat2']:
        params['Lat1'],params['Lat2'] = params['Lat2'],params['Lat1']
    if params['Lon1']>params['Lon2']:
        params['Lon1'],params['Lon2'] = params['Lon2'],params['Lon1']
        
    return params

def getLogins(directory, files):
    logins = {}
    params = {}
    
    for fileName in files:
        if directory == "null":
            directory = ''
        print "\nLoading login file:", directory + fileName
        fileIn = open(directory+fileName)
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
        for key,item in params.iteritems():
            print '\t*', key,':', item
        logins[fileName] = params
    return logins
    

   
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
def getAuth(login):
    auth1 = tweepy.auth.OAuthHandler(login['consumerKey'],login['consumerSecret'])
    auth1.set_access_token(login['accessToken'],login['accessTokenSecret'])
    api = tweepy.API(auth1)
    return {'auth':auth1,'api':api}


#Posts a tweet
def postTweet(api,text,image):
    if image != None and image != 'null':
        api.update_status(text)
        print "posted tweet:", text
        
        
def getTweets(logins, cfg, conditions, qualifiers):
    print "Setting up listeners"
    ears = {}
    streams = {}
    for key,login in logins.iteritems():
        try:
            ears[key] = giListener(conditions,qualifiers,logins[key]['auth']['api'],key)
            print "Logging in via", key,"credentials file"
        except:
            print "Could not login via", key, "credentials file"""
        
    print ears.items()
    
    for key, ear in ears.iteritems():
        print "Starting stream:", key
        streams[key] = tweepy.Stream(logins[key]['auth']['auth'], ear, timeout=30.0)
    
    print streams.items()
    
    for key, stream in streams.iteritems():
        streams[key].filter(locations=[cfg['Lat1'],cfg['Lon1'],cfg['Lat2'],cfg['Lon2']], track = conditions)
    
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
    def __init__(self, conditions, qualifiers,api,name):
        self.qualifiers = qualifiers
        self.conditions = conditions
        self.api = api
        self.name = name
        print "Initiated listener", name, "with", len(qualifiers), "qualifiers and", len(conditions), "conditions"
    def on_status(self, status):
        try:
            text = (status.text).lower()
            found = False
            if "RT @" not in status.text:
                for word in self.qualifiers:
                    if word in text:
                        found = True
                        break
                if found == True:
                    print "\033[94m%s\033[0m" % (self.name), "\033[1m%s\t%s\t%s\t%s\033[0m" % (status.text, 
                                status.author.screen_name, 
                                status.created_at, 
                                status.source,)
                else:
                    print "\033[94m%s\033[0m" % (self.name), "%s\t%s\t%s\t%s" % (status.text, 
                                status.author.screen_name, 
                                status.created_at, 
                                status.source,)
        except Exception, e:
            print "Encountered exception:", e
            pass

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
    logins = getLogins(directory, cfg['Logins'])
    conditions = getWords(directory, cfg['Conditions'])
    print "Loaded Conditions:", conditions
    qualifiers = set(getWords(directory, cfg['Qualifiers']))
    print "Loaded Qualifiers:", qualifiers
    for key,login in logins.iteritems():
        logins[key]['auth'] = getAuth(logins[key])
    print "Ready to run...", raw_input()
    getTweets(logins,cfg,conditions,qualifiers)

main()