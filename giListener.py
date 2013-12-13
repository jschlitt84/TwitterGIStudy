import tweepy
import datetime
import json
import os
from GISpy import *

class giSeeker():
    def __init__(self, conditions, qualifiers, exclusions, api, cfg, name, testSpace):
        self.qualifiers = qualifiers
        self.conditions = conditions
        self.api = api
        self.name = name
        self.exclusions = exclusions
        self.cfg = cfg
        self.testSpace = testSpace
        giSeeker.flushTweets(self)
        giSeeker.makeQueries(self)
        area = getCircle(cfg)
        self.center = area['center']
        self.radius = area['radius']
        print "\nInitiated seeker '%s' with %s conditions, %s qualifiers, and %s exclusions" % (name, len(conditions), len(qualifiers), len(exclusions))
        
        self.pathOut = self.cfg['OutDir']+'search/'
        if not os.path.exists(self.pathOut):
            os.makedirs(self.pathOut)   
            
        giSeeker.getLastID(self)
            
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
        self.startTime = datetime.datetime.now().strftime("%A_%m-%d-%y_%H-%M-%S")
        self.startDay = datetime.date.today().strftime("%A")

#open newest file via http://ubuntuforums.org/showthread.php?t=1526010 method 
    
    def getLastID(self):
        print "\nChecking for last tweet ID loaded..."
        try:
            filelist = os.listdir(self.pathOut)
            filelist = filter(lambda x: not os.path.isdir(self.pathOut+x), filelist)
            newest = self.pathOut + max(filelist, key=lambda x: os.stat(self.pathOut+x).st_mtime)
            print "\tNewest File:", newest
            inFile = open(newest)
            listed = json.load(inFile)
            self.lastTweet = listed[-1]['id']
        except:
            print "Unable to find last tweet batch, using ID 0"
            self.lastTweet = 0
        print "\tLast tweet:", self.lastTweet
    
    def makeQueries(self):
        self.queries = []
        text = '"'+self.conditions[0]+'"'
        for item in self.conditions[1:]:
            entry = ' OR "' + item + '"'
            if len(text + entry) >= 1000:
                self.queries.append(text)
                text = '"'+item+'"'
            else:
                text += entry
        self.queries.append(text)
        for item in self.queries:
            print "QUERY LENGTH: %s\tCONTENTS:\n%s\n" % (len(item), item)
                
    def getTweets(self):
        None 
    
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
        
        self.pathOut = self.cfg['OutDir']+'stream/'
        if not os.path.exists(self.pathOut):
            os.makedirs(self.pathOut)    
        
        
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
        self.startTime = datetime.datetime.now().strftime("%A_%m-%d-%y_%H-%M-%S")
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
            with open(self.pathOut+'Raw_'+timeStamp, 'w') as outFile:
                json.dump(self.jsonRaw,outFile)

        with open(self.pathOut+self.cfg['FileName']+'_'+timeStamp, 'w') as outFile:
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
