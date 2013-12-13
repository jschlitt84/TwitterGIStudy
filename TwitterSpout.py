import sys, os
import json
import tweepy
import datetime
import time
import random

from copy import deepcopy

#from tweepy.streaming import StreamListener
from GISpy import *
#from multiprocessing import Process, Queue

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
        #for key,item in params.iteritems():
        #    print '\t*', key,':', item
        logins[fileName] = deepcopy(params)
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
        

"""def getStream(ear,auth,cfg,name,out_q):
    print "Starting stream:", name
    stream = tweepy.Stream(auth, ear, timeout=30.0)   
    while True:
        try:
            stream.filter(locations=[cfg['Lon1'],cfg['Lat1'],cfg['Lon2'],cfg['Lat2']])
            break
        except Exception, e:
            delay = 30*random.random()
            print "Filter failed, sleeping", int(delay), "seconds..."
            print e
            time.sleep(delay) """
                        
                        
                        
def getTweets(login, cfg, conditions, qualifiers, exclusions):
    print "\nSetting up listeners"
    name = login['name']
    filterType = cfg['FilterType'].lower()

    if True:
        ear = giListener(conditions,qualifiers,exclusions,login['api'],cfg,name,'null')
        print "Logging in via", name,"credentials file"
    """except:
        print "Could not login via", name, "credentials file"
        quit()"""
        
    print "Starting stream:", name, '\n'
    stream = tweepy.Stream(login['auth'], ear, timeout=30.0)   
    while True:
        try:
            if filterType == "conditions":
                stream.filter(track = conditions)
            elif filterType == "location":
                stream.filter(locations=[cfg['Lon1'],cfg['Lat1'],cfg['Lon2'],cfg['Lat2']])
            break
        except Exception, e:
            delay = 30*random.random()
            print "Filter failed, sleeping", int(delay), "seconds..."
            print e
            time.sleep(delay) 
             
class giListener(tweepy.StreamListener):
    def __init__(self, conditions, qualifiers, exclusions, api, cfg, name, testSpace):
        self.qualifiers = qualifiers
        self.conditions = conditions
        self.api = api
        self.name = name
        self.exclusions = exclusions
        self.cfg = cfg
        self.testSpace = testSpace
        giListener.flushTweets(self)
        print "Initiated listener '%s' with %s conditions, %s qualifiers, and %s exclusions" % (name, len(conditions), len(qualifiers), len(exclusions))
    
    def flushTweets(self):
        self.tweetCount = 0
        self.acceptedCount = 0
        self.partialCount = 0
        self.excludedCount = 0
        self.irrelevantCount = 0
        self.jsonRaw = []
        self.jsonAccepted = []
        self.jsonPartial = []
        self.jsonExcluded = []
        self.tweetTypes = []
        self.startTime = datetime.datetime.now().strftime("%A %m.%d.%y %H:%M:%S")
        self.startDay = datetime.date.today().strftime("%A")

    
    def saveTweets(self):
        print "\nDumping tweets to file, contains %s tweets with %s accepted, %s rejected, %s partial matches, and %s irrelevant" % (self.cfg['StopCount'],
                        self.acceptedCount,
                        self.excludedCount,
                        self.partialCount,
                        self.irrelevantCount)
        print '\tJson text dump complete....\n'
                
        meaningful =  self.jsonAccepted*self.cfg['KeepAccepted'] + self.jsonPartial*self.cfg['KeepPartial'] + self.jsonExcluded*self.cfg['KeepExcluded']
        
        if self.cfg['KeepKeys'] != 'all':
            cleanJson(meaningful,self.cfg['KeepKeys'],self.tweetTypes)
            
        #timeStamp = datetime.date.today().strftime("%A")
        timeStamp = self.startTime
        
        if self.cfg['KeepRaw']:
            with open(self.cfg['OutDir']+'Raw_'+timeStamp, 'w') as outFile:
                json.dump(self.jsonRaw,outFile)

        with open(self.cfg['OutDir']+self.cfg['FileName']+'_'+timeStamp, 'w') as outFile:
            json.dump(meaningful,outFile)
        giListener.flushTweets(self) 
 
    
    def on_status(self, status):
        try:
            if self.startDay != datetime.date.today().strftime("%A") or self.tweetCount >= self.cfg['StopCount']:
                giListener.saveTweets(self)
            text = status.text.replace('\n',' ')
            tweetType = checkTweet(self.conditions, self.qualifiers, self.exclusions, text)
            #print json.loads(status.json).keys()
            percentFilled = (self.tweetCount*100)/self.cfg['StopCount']
            loginInfo = "\033[94m%s:%s%%\033[0m" % (self.name,percentFilled)
            if tweetType == "accepted":
                print loginInfo, "\033[1m%s\t%s\t%s\t%s\033[0m" % (text, 
                            status.author.screen_name, 
                            status.created_at, 
                            status.source,)
                self.tweetCount += self.cfg['KeepAccepted']
                self.acceptedCount += 1
                self.jsonAccepted.append(status.json)
            elif tweetType == "excluded":
                print loginInfo, "\033[91m%s\t%s\t%s\t%s\033[0m" % (text, 
                            status.author.screen_name, 
                            status.created_at, 
                            status.source,)
                self.tweetCount += self.cfg['KeepExcluded']
                self.excludedCount += 1
                self.jsonExcluded.append(status.json)
            elif tweetType == "partial":
                print loginInfo, "%s\t%s\t%s\t%s" % (text, 
                            status.author.screen_name, 
                            status.created_at, 
                            status.source,)
                self.tweetCount += self.cfg['KeepPartial']
                self.partialCount += 1
                self.jsonPartial.append(status.json)
            elif tweetType == "retweet":
                None
            else:
                self.irrelevantCount += 1
            if tweetType != "retweet" and self.cfg['KeepRaw'] == True:
                self.jsonRaw.append(status.json)
                self.tweetTypes.append(tweetType)               
                
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
        userLogin = sys.argv[2]
        print "Login '%s' passed explicitly" % (userLogin)
    except:
        userLogin = 'null'
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
    
    print "\nPlease choose login number:"
    if userLogin == 'null':
        listed = sorted(logins.keys()); i = 0
        for key in listed:
            print "\t%s - %s - %s" % (i,key,logins[key]['description'])
            i += 1
        while True:
            try:
                selection = int(raw_input('\n:'))
                userLogin = listed[selection]
                break
            except:
                None
 
    login = logins[userLogin]    
    temp = getAuth(login)
    login['auth'] = temp['auth']
    login['api'] = temp['api']
    login['name'] = userLogin
    getTweets(login,cfg,conditions,qualifiers,exclusions)

main()