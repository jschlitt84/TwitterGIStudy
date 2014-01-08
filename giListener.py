import tweepy
import datetime, time
import json
import os


from GISpy import *



class giSeeker():
    def __init__(self, conditions, qualifiers, exclusions, api, cfg, name, testSpace):
        self.delay = 30
        self.qualifiers = qualifiers
        self.conditions = conditions
        self.api = api
        self.name = name
        self.exclusions = exclusions
        self.cfg = cfg
        self.searchDelay = 3000
        self.testSpace = testSpace
        self.runDay = localTime(datetime.datetime.today(),self.cfg).strftime("%A %d")
        self.lastWrite = 'null'
        giSeeker.flushTweets(self)
        giSeeker.makeQueries(self)
        self.geo = str(getGeo(cfg)).replace(' ','')[1:-1]+'mi'
        self.center = [self.geo[1],self.geo[0]]
        self.radius = self.geo[2]
        print "\nInitiated seeker '%s' with %s conditions, %s qualifiers, and %s exclusions" % (name, len(conditions), len(qualifiers), len(exclusions))
        
        self.pathOut = self.cfg['OutDir']+'search/'
        if not os.path.exists(self.pathOut):
            os.makedirs(self.pathOut)   
            
        fileOut = openWhenReady(self.pathOut + 'checkbits','w')
        fileOut.write('DayFinished = False')
        fileOut.close()
            
        giSeeker.getLastID(self)
    
    
    def closeDay(self):
        print "Closing tweet collection for", self.startDay, '\n'
        fileOut = openWhenReady(self.pathOut + 'checkbits','w')
        directory = self.cfg['directory']
        fileOut = open(self.pathOut + 'checkbits','w')
        fileOut.write('DayFinished = True') 
        fileOut.write('ConditionsVersion = ' + time.ctime(os.stat(directory + self.cfg['Conditions']).st_mtime))
        fileOut.write('QualifiersVersion = ' + time.ctime(os.stat(directory + self.cfg['Qualifiers']).st_mtime))
        fileOut.write('ExclusionsVersion = ' + time.ctime(os.stat(directory + self.cfg['Exclusions']).st_mtime))
        fileOut.close()
        
        
        if self.runDay != localTime(datetime.date.today(),self.cfg).strftime("%A %d"):
            print "End of day noted, updating word banks & reformating past filtered output"
            lists = updateWordBanks(directory, self.cfg)
            reformatOld(directory, lists, self.cfg)
            self.conditions = lists['conditions']
            self.qualifiers = lists['qualifiers']
            self.exclusions = lists['exclusions']
            self.runDay = localTime(datetime.date.today(),self.cfg).strftime("%A %d")
            
        
        
            
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
        
    
    def saveTweets(self):
        meaningful =  self.jsonAccepted*self.cfg['KeepAccepted'] + self.jsonPartial*self.cfg['KeepPartial'] + self.jsonExcluded*self.cfg['KeepExcluded']
        
        print "\nDumping tweets to file, contains %s tweets with %s accepted, %s rejected, %s partial matches, and %s irrelevant" % (len(meaningful),
                        self.acceptedCount,
                        self.excludedCount,
                        self.partialCount,
                        self.irrelevantCount)        
       
        if self.cfg['TweetData'] != 'all':
            cleanJson(meaningful,self.cfg,self.tweetTypes)
            
        #timeStamp = datetime.date.today().strftime("%A")
        timeStamp = self.startTime
        self.lastWrite = self.startDay
        
        if self.cfg['KeepRaw']:
            with open(self.pathOut+'Raw_'+self.cfg['FileName']+'_'+timeStamp+'.json', 'w') as outFile:
                json.dump(self.jsonRaw,outFile)
            outFile.close()

        with open(self.pathOut+'FilteredTweets_'+self.cfg['FileName']+'_'+timeStamp+'.json', 'w') as outFile:
            json.dump(meaningful,outFile)
        outFile.close()
        
        print 'Json text dump complete, buffering....'    
        time.sleep(1)
        
        
        giSeeker.flushTweets(self)



    def getLastID(self):
        """Open newest file, finds last ID of tweet recorded"""
        print "\nChecking for last tweet ID loaded..."
        try:
            fileList = os.listdir(self.pathOut)
            fileList = [i for i in fileList if (".json" in i.lower() and i.lower().startswith('raw'))]
            fileList = filter(lambda i: not os.path.isdir(self.pathOut+i), fileList)
            newest = self.pathOut + max(fileList, key=lambda i: os.stat(self.pathOut+i).st_mtime)
            print "\tNewest File:", newest
            inFile = open(newest)
            listed = json.load(inFile)
            jsonToDictFix(listed)
            
            ids = set()
            for tweet in listed:
                ids.add(tweet['id'])
            self.lastTweet = max(ids)
        except:
            print "Unable to find last tweet batch, using ID 0"
            self.lastTweet = 0
        print "\tLast tweet:", self.lastTweet
    
    
    
    def makeQueries(self):
        """Formats query list and splits into < 1k character segments"""
        self.queries = []
        text = '"'+self.conditions[0]+'"'
        for item in self.conditions[1:]:
            entry = ' OR "' + item + '"'
            if len(text + entry) >= 250:
                self.queries.append(text + ' -"rt @"')
                text = '"'+item+'"'
            else:
                text += entry
        self.queries.append(text + ' -"rt @"')
        for item in self.queries:
            print "Query Length: %s\tContents:\n%s\n" % (len(item), item)
                
    def run(self):
        newDay = False
        print "\nPreparing to run..."
        print "Geographic Selection:", self.geo, '\n\n'
        while True:
            collected = []
            for query in self.queries:
                
                #Issue of stream pagination currently unresolved
                #https://github.com/tweepy/tweepy/pull/296#commitcomment-3404913
                
                #Method 1: Unlimited backstream, may have overlap or rate limiting issues
                """for tweet in tweepy.Cursor(self.api.search,q=query,
                    geocode= self.geo,
                    since_id= str(0),
                    result_type="recent").items():
                    
                    print tweet.text
                    collected.append(tweet)
                    
                for item in collected:
                    print item.text, item.coordinates, item.geo"""

                #Method 2: Since id stream, may miss if keyword set yields over 100 new results
                collected += self.api.search(q = query, 
                                        since_id = self.lastTweet,  
                                        geocode = self.geo,
                                        result_type="recent",
                                        count = 100)
               
            idList = set()            
            inBox = mappable = 0
            
            hasResults = len(collected) != 0
            collected = uniqueJson(collected)
            
            if hasResults:
                self.startDay = localTime(collected[0].created_at,self.cfg).strftime("%A %d")
                self.startTime = localTime(collected[0].created_at,self.cfg).strftime(timeArgs)
                if self.lastWrite != 'null' and self.lastWrite != self.startDay:
                    print "Good morning! New day noted, preparing to save tweets."
                    newDay = True
                                   
            for status in collected:
                idList.add(int(status.id))
                if self.startDay != localTime(status.created_at,self.cfg).strftime("%A %d") or self.tweetCount >= self.cfg['StopCount'] or newDay:
                    newDay = False
                    giSeeker.saveTweets(self)
                    if self.startDay != localTime(status.created_at,self.cfg).strftime("%A %d"):
                        giSeeker.closeDay(self)
                        self.startDay = localTime(status.created_at,self.cfg).strftime("%A %d")
                        self.startTime = localTime(status.created_at,self.cfg).strftime(timeArgs)
                    
                text = status.text.replace('\n',' ')
                tweetType = checkTweet(self.conditions, self.qualifiers, self.exclusions, text)
                #print json.loads(status.json).keys()
                percentFilled = (self.tweetCount*100)/self.cfg['StopCount']
                
                geoInfo = isInBox(self.cfg,status.coordinates)
                tweetLocalTime = outTime(localTime(status,self.cfg))
                inBox += geoInfo['inBox']
                
                loginInfo = "\033[94m%s:%s:%s%%\033[0m" % (self.name,geoInfo['text'],percentFilled)
                if tweetType == "accepted":
                    print loginInfo, "\033[1m%s\t%s\t%s\t%s\033[0m" % (text, 
                                status.author.screen_name, 
                                tweetLocalTime, 
                                status.source,)
                    if geoInfo['inBox']:
                        mappable += 1
                    self.tweetCount += self.cfg['KeepAccepted']
                    self.acceptedCount += 1
                    self.jsonAccepted.append(status.json)
                elif tweetType == "excluded":
                    print loginInfo, "\033[91m%s\t%s\t%s\t%s\033[0m" % (text, 
                                status.author.screen_name, 
                                tweetLocalTime, 
                                status.source,)
                    self.tweetCount += self.cfg['KeepExcluded']
                    self.excludedCount += 1
                    self.jsonExcluded.append(status.json)
                elif tweetType == "partial":
                    print loginInfo, "%s\t%s\t%s\t%s" % (text, 
                                status.author.screen_name, 
                                tweetLocalTime, 
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
                    self.tweetTypes.append({'geoType':geoInfo,'tweetType':tweetType,'localTime':tweetLocalTime}) 
            
            
            if hasResults:
                self.lastTweet = max(max(list(idList)), self.lastTweet)
                if len(idList) > 1:
                    tweetsPerHour = float(len(idList)*3600)/((collected[-1].created_at-collected[0].created_at).seconds)
                else:
                    tweetsPerHour = "NA"
            else:
                tweetsPerHour = 0
            print "\nFound %s tweets with %s geolocated and %s mappable hits, will sleep %s seconds until next search" % (len(idList),inBox, mappable,self.searchDelay)
            if hasResults:
                print "\tFirst tweet: %s\tLast tweet: %s\t\tTweets Per Hour: %s" % (collected[0].created_at, collected[-1].created_at, tweetsPerHour)
            time.sleep(self.searchDelay)
            
    
    
    
    
    
    
    
    
    
    
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
            
        fileOut = openWhenReady(self.pathOut + 'checkbits','w')
        fileOut.write('DayFinished = False')
        fileOut.close()
            
    def closeDay(self):
        fileOut = openWhenReady(self.pathOut + 'checkbits','w')
        directory = self.cfg['directory']
        fileOut = open(self.pathOut + 'checkbits','w')
        fileOut.write('DayFinished = True') 
        fileOut.write('ConditionsVersion = ' + time.ctime(os.stat(directory + self.cfg['Conditions']).st_mtime))
        fileOut.write('QualifiersVersion = ' + time.ctime(os.stat(directory + self.cfg['Qualifiers']).st_mtime))
        fileOut.write('ExclusionsVersion = ' + time.ctime(os.stat(directory + self.cfg['Exclusions']).st_mtime))
        fileOut.close()
        
        lists = updateWordBanks(directory, self.cfg)
        self.conditions = lists['conditions']
        self.qualifiers = lists['qualifiers']
        self.exclusions = lists['exclusions']
        
        
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
        self.startTime = localTime(datetime.datetime.now(),self.cfg).strftime(timeArgs)
        self.startDay = localTime(datetime.date.today(),self.cfg).strftime("%A")

    
    def saveTweets(self):
        print "\nDumping tweets to file, contains %s tweets with %s accepted, %s rejected, %s partial matches, and %s irrelevant" % (self.cfg['StopCount'],
                        self.acceptedCount,
                        self.excludedCount,
                        self.partialCount,
                        self.irrelevantCount)
        print '\tJson text dump complete....\n'
                
        meaningful =  self.jsonAccepted*self.cfg['KeepAccepted'] + self.jsonPartial*self.cfg['KeepPartial'] + self.jsonExcluded*self.cfg['KeepExcluded']
        
        if self.cfg['TweetData'] != 'all':
            cleanJson(meaningful,self.cfg,self.tweetTypes)
            
        #timeStamp = datetime.date.today().strftime("%A")
        timeStamp = self.startTime
        
        if self.cfg['KeepRaw']:
            with open(self.pathOut+'Raw_'+self.cfg['FileName']+'_'+timeStamp+'.json', 'w') as outFile:
                json.dump(self.jsonRaw,outFile)
            outFile.close()

        with open(self.pathOut+'FilteredTweets_'+self.cfg['FileName']+'_'+timeStamp+'.json', 'w') as outFile:
            json.dump(meaningful,outFile)
        outFile.close()
        giListener.flushTweets(self)  
    
    def on_status(self, status):
        try:
            if self.startDay != localTime(datetime.date.today(),self.cfg).strftime("%A") or self.tweetCount >= self.cfg['StopCount']:
                giListener.saveTweets(self)
            text = status.text.replace('\n',' ')
            tweetType = checkTweet(self.conditions, self.qualifiers, self.exclusions, text)
            #print json.loads(status.json).keys()
            percentFilled = (self.tweetCount*100)/self.cfg['StopCount']
            loginInfo = "\033[94m%s:%s%%\033[0m" % (self.name,percentFilled)
            tweetLocalTime = outTime(localTime(status,self.cfg))
            if tweetType == "accepted":
                print loginInfo, "\033[1m%s\t%s\t%s\t%s\033[0m" % (text, 
                            status.author.screen_name, 
                            tweetLocalTime, 
                            status.source,)
                self.tweetCount += self.cfg['KeepAccepted']
                self.acceptedCount += 1
                self.jsonAccepted.append(status.json)
            elif tweetType == "excluded":
                print loginInfo, "\033[91m%s\t%s\t%s\t%s\033[0m" % (text, 
                            status.author.screen_name, 
                            tweetLocalTime, 
                            status.source,)
                self.tweetCount += self.cfg['KeepExcluded']
                self.excludedCount += 1
                self.jsonExcluded.append(status.json)
            elif tweetType == "partial":
                print loginInfo, "%s\t%s\t%s\t%s" % (text, 
                            status.author.screen_name, 
                            tweetLocalTime, 
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
