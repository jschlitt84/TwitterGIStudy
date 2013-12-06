import sys, os
import json
import tweepy
import time
import random

#from tweepy.streaming import StreamListener
from GISpy import checkTweet
from multiprocessing import Process, Queue

expected = ['Lat1','Lat2','Lon1','Lon2','Logins','Conditions','Qualifiers','Exclusions']


#Hacky patch for raw json access, not granted in newest tweepy version
#Method: http://willsimm.co.uk/saving-tweepy-output-to-mongodb/
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
    fileIn = open(directory)
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
        

def getStream(ear,auth,cfg,name,out_q):
    print "Starting stream:", name
    stream = tweepy.Stream(auth, ear, timeout=30.0)   
    while True:
        try:
            stream.filter(locations=[cfg['Lat1'],cfg['Lon1'],cfg['Lat2'],cfg['Lon2']], track = ear.conditions)
            break
        except Exception, e:
            delay = 30*random.random()
            print "Filter failed, sleeping", int(delay), "seconds..."
            print e
            time.sleep(delay) 
                        
                        
                        
def getTweets(logins, cfg, conditions, qualifiers, exclusions):
    print "Setting up listeners"
    ears = {}
    out_q = Queue()
    processes = []
    
    for key,login in logins.iteritems():
        try:
            ears[key] = giListener(conditions,qualifiers,exclusions,login['api'],key)
            print "Logging in via", key,"credentials file"
        except:
            print "Could not login via", key, "credentials file"""
            
    for key, ear in ears.iteritems():
        time.sleep(random.random()*4) 
        p = Process(target = getStream, args = (ear, logins[key]['auth'], cfg, key, out_q))
        processes.append(p)
        p.start() 
    merged = {}
    """for key in ears.keys():
        merged.update(out_q.get())
    for p in processes:
        p.join()"""
             
             
class giListener(tweepy.StreamListener):
    def __init__(self, conditions, qualifiers, exclusions, api,name):
        self.qualifiers = qualifiers
        self.conditions = conditions
        self.api = api
        self.name = name
        self.exclusions = exclusions
        print "Initiated listener '%s' with %s conditions, %s qualifiers, and %s exclusions" % (name, len(conditions), len(qualifiers), len(exclusions))
    
    def on_status(self, status):
        try:
            text = status.text.replace('\n',' ')
            tweetType = checkTweet(self.conditions, self.qualifiers, self.exclusions, text)
            if tweetType == "accepted":
                print "\033[94m%s\033[0m" % (self.name), "\033[1m%s\t%s\t%s\t%s\033[0m" % (text, 
                            status.author.screen_name, 
                            status.created_at, 
                            status.source,)
            elif tweetType == "excluded":
                print "\033[94m%s\033[0m" % (self.name), "\033[91m%s\t%s\t%s\t%s\033[0m" % (text, 
                            status.author.screen_name, 
                            status.created_at, 
                            status.source,)
            elif tweetType == "partial":
                print "\033[94m%s\033[0m" % (self.name), "%s\t%s\t%s\t%s" % (text, 
                            status.author.screen_name, 
                            status.created_at, 
                            status.source,)
            elif tweetType == "retweet":
                None
        except Exception, e:
            print "Encountered exception:", e
            pass
        except KeyboardInterrupt:
            print "Got keyboard interrupt"

    def on_error(self, status_code):
        print "\033[91m***Stream '%s' encountered error with status code %s***\033[0m" % (self.name,status_code)
        return True

    def on_timeout(self):
        print >> sys.stderr, 'Timeout...'
        return True


def main():
    try:
        temp = sys.argv[1]
        print "\nTaking user parameters"
        directory = '/'.join(temp.split('/')[:-1])
        configFile = temp.split('/')[-1]
        if directory == '':
            directory = os.getcwd() + '/'
    except:
        print "Taking default parameters"
        directory = os.getcwd() + '/'
        configFile = 'config'
    print "Loading parameters from config file '%s' in directory '%s'" % (configFile, directory)
    cfg = getConfig(directory+configFile)
    logins = getLogins(directory, cfg['Logins'])
    conditions = getWords(directory, cfg['Conditions'])
    print "\nLoaded Conditions:", conditions
    qualifiers = set(getWords(directory, cfg['Qualifiers']))
    print "\nLoaded Qualifiers:", qualifiers
    exclusions = set(getWords(directory, cfg['Exclusions']))
    print "\nLoaded Exclusions:", exclusions
    for key,login in logins.iteritems():
        temp = getAuth(logins[key])
        logins[key]['auth'] = temp['auth']
        logins[key]['api'] = temp['api']
    print "\nPress [ENTER] when ready...", raw_input()
    getTweets(logins,cfg,conditions,qualifiers,exclusions)

main()