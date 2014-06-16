# -*- coding: utf-8 -*-
import json, csv
import random
import datetime,time
import os, shutil
import unicodedata
import tweepy
import smtplib
import cPickle
import TweetMatch

import gDocsImport as gd

from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email import Encoders

from copy import deepcopy, copy
from geopy.distance import great_circle
from geopy import geocoders
from dateutil import parser
from math import pi, cos, ceil
from multiprocessing import Process, Queue, cpu_count, Manager
from operator import itemgetter

#timeArgs = "%A_%m-%d-%y_%H-%M-%S"
timeArgs = '%a %d %b %Y %H:%M:%S'

gdiEmail = 'Subscriber Email,CC Email'
gdiParams = 'Param Name,Param Key'
gdiLists = 'Conditions,Qualifiers,Exclusions'
pickleName = "GeoPickle.txt"



def updateGeoPickle(dictionary,fileRef):
    """Updates file & memory version of geoPickle"""
    loadedLength = length1 = len(dictionary.keys())
    pickleExists = os.path.isfile(fileRef)
    if pickleExists:
        pickleIn = openWhenReady(fileRef, "rb")
        pickleLoaded = cPickle.load(pickleIn)
        length1 = len(pickleLoaded.keys())
        pickleIn.close()
        if dictionary.keys() != pickleLoaded.keys():
            dictionary.update(pickleLoaded)
            needsWrite = True
        else:
            needsWrite = False      
    else:
        needsWrite = True
    
    length2 = len(dictionary.keys())
    if needsWrite and loadedLength != 0 and (length2-length1) > 25:
        print "Updating master geoPickle,", length2-length1,"new locations added with",length2,"total in cache"
        pickleOut = openWhenReady(fileRef,"wb")
        cPickle.dump(dictionary, pickleOut)
        pickleOut.close()
        time.sleep(.5)
    
    

def getDelay(self,elapsed):
    """Calculates optimum stacked search delay for API rate limits"""
    secPerSearch = min(max(float(self.rateIncrement-elapsed)/self.rateLimit,0.05),20)
    if self.multiAPI:
	secPerSearch = secPerSearch/len(self.api.keys())
    return secPerSearch


def fillBox(cfg,self):
    #Adapting method from https://gist.github.com/flibbertigibbet/7956133
    """Fills large search area with stacked subsearches of 50km radius"""
    box = []
    minLat = min([cfg['Lat1'],cfg['Lat2']])
    maxLat = max([cfg['Lat1'],cfg['Lat2']])
    minLon = min([cfg['Lon1'],cfg['Lon2']])
    maxLon = max([cfg['Lon1'],cfg['Lon2']])
    inr = 43301.3 # inradius
    

    circumr = 50000.0 # circumradius (50km)
    circumrMiles = int((0.621371 * circumr)/1000+1)
        
    circumOffset = circumr * 1.5 # displacement to tile
    earthr = 6378137.0 # Earth's radius, sphere
    lat = minLat
    lon = minLon
    
    # coordinate offsets in radians
    dlat = (inr*2)/earthr
    dlon = circumOffset/(earthr*cos(pi*lat/180))
    
    isOffset = False
    while lon < maxLon:
        #print(str(lat) + ", " + str(lon))
        while lat < maxLat:
            lat += dlat * 180.0/pi
            #print('\t' + str(lat) + ", " + str(lon))
            box.append([lat, lon, circumrMiles])
 
        lat = minLat
        lon += (circumOffset/(earthr*cos(pi*lat/180))) * 180.0/pi
        isOffset = not isOffset
        if isOffset:
            lat -= (inr/earthr) * 180.0/pi
    
    """try:
        secPerSearch = float(self.rateIncrement)/self.rateLimit
        queries = len(self.queries); locations = len(box)
        searchPerHour = 3600/secPerSearch
        completePerHour = float(searchPerHour)/(queries*box)
        print "%s queries generated with %s locations and %s total searches per cycle" % (queries,box,queries*box)
        print "%s Total area searches possible per hour" % (completePerHour)
    finally:
        return {"list":box,'radius':circumrMiles}"""
    
    secPerSearch = float(self.rateIncrement)/self.rateLimit
    if self.multiAPI:
	secPerSearch = secPerSearch/len(self.api.keys())
    queries = len(self.queries); locations = len(box)
    searchPerHour = 3600/secPerSearch
    completePerHour = float(searchPerHour)/(queries*locations)
    print "%s queries generated with %s locations and %s total searches per cycle" % (queries,locations,queries*locations)
    print "%s Total area searches possible per hour" % (completePerHour)
    return {"list":box,'radius':circumrMiles}
    



def sendCSV(cfg, directory):
    #Adapting method from http://kutuma.blogspot.com/2007/08/sending-emails-via-gmail-with-python.html
    """Emails results to GDI subscriber(s)"""
    outName = cfg['FileName']+"_CollectedTweets"
    attachment = cfg['OutDir']+outName+'.csv'

    print "Preparing to send CSV file:", attachment
        
    msg = MIMEMultipart()
    
    msg['From'] = cfg['GDI']['UserName']
    msg['To'] = cfg['GDI']['Email']
    msg['Cc'] = cfg['GDI']['CC']
    msg['Subject'] = cfg['FileName'] + ' collected tweets for ' + datetime.datetime.now().strftime("%A %d")
    
    text = "Please find csv spreadsheet file attached for study: " + cfg['FileName']
    text += "\nParameters & configuration accessible at: " + cfg['GDI']['URL']
    text += "\n\nAll changed parameters are updated after midnight & will not influence collection & parsing until the following day"
    msg.attach(MIMEText(text))
    
    directory += cfg['OutDir'] + cfg['Method'] + '/'
    outName = cfg['FileName']+"_CollectedTweets"
    attachment = directory+outName+'.csv'
    
    
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(open(attachment, 'rb').read())
    Encoders.encode_base64(part)
    
    part.add_header('Content-Disposition',
            'attachment; filename="%s"' % os.path.basename(attachment))
    msg.attach(part)
    
    mailServer = smtplib.SMTP("smtp.gmail.com", 587)
    mailServer.ehlo()
    mailServer.starttls()
    mailServer.ehlo()
    mailServer.login(cfg['GDI']['UserName'], cfg['GDI']['Password'])
    mailServer.sendmail(cfg['GDI']['UserName'],[msg['To'],msg['Cc']], msg.as_string())
    mailServer.close()
    print "File sent succesfully!"


    
def loadGDIAccount(gDocURL,directory):
    """Pulls subscriber info & settings from local config file"""
    fileIn = open(directory+'gdiAccounts')
    content = fileIn.readlines()
    found = False
    public = True
    _userName_ = _password_ = 'null'
    
    for line in content:
        if line.lower().startswith('username'):
            _userName_ = line.split(' = ')[1].replace(' ','').replace('\n','')
        if line.lower().startswith('password'):
            _password_ = line.split(' = ')[1].replace(' ','').replace('\n','')
        if line.lower().startswith('public'):
            public = line.split(' = ')[1].lower().replace(' ','').startswith('true')
        
    for line in content:
        if gDocURL in line:
            urlLine = line
            found = True
            break
    if not found:
        print "Error: GDoc URL", gDocURL, "not found"
        quit()
        
    experimentName = urlLine.split('.')[0].replace(' ','')
    
    found = False
    for line in content:
        if experimentName+'.file' in line:
            fileLine = line
            found = True
            break
    if not found:
        print "Error, filename not specified"
        quit()
    else:
        fileName = fileLine.split(' = ')[1].replace(' ','').replace('\n','')
    
    found = False
    for line in content:
        if experimentName+'.login' in line:
            loginLine = line
            found = True
            break
    if not found:
        login = 'login5'
    else:
        login =  loginLine.split(' = ')[1].replace(' ','').replace('\n','')
        if ',' in login:
            login = login.split(',')
        
    found = False
    for line in content:
        if experimentName+'.frequency' in line:
            freqLine = line
            found = True
            break
    if not found:
        frequency = 900
    else:
        frequency = int(freqLine.split(' = ')[1].replace(' ','').replace('\n',''))
    
    found = False
    for line in content:
        if experimentName+'.sanitize' in line:
            sanLine = line
            found = True
            break
    if not found:
        sanitize = False
    else:
        sanitize = 'true' in sanLine.lower()
    
    return {'name':experimentName,
        'login':login,
        "userName": _userName_,
        'password': _password_,
        'frequency': frequency,
        'fileName': fileName,
        'sanitize': sanitize,
        'public':public}
        
    
    

def giSpyGDILoad(gDocURL,directory):
    """Updates user config & lists for GDI seeker"""
    gdi = {}
    print "Loading user account info from local directory"
    account = loadGDIAccount(gDocURL,directory)
    public = account['public']
    
    print "Loading email lists from local directory"
    
    if not public:
        emails = gd.getLine(account['userName'], account['password'], account['fileName'], gdiEmail, False, [])
    else:
        emails = gd.getLine('null', 'null', gDocURL, gdiEmail, False, [])
    
    try:
        gdi['Email'] = emails[0].replace(' ',',')
    except:
        gdi['Email'] = ""
    try:
        gdi['CC'] = emails[1].replace(' ',',')
    except:
        gdi['CC'] = ""
        
    gdi['URL'] = gDocURL
    gdi['UserName'] = account['userName']
    gdi['Password'] = account['password']
    gdi['FileName'] = account['fileName']
    try:
        gdi['Frequency'] = int(emails[2])
    except:
        gdi['Frequency'] = account['frequency']
    
    print "Loading word lists from local directory"
    
    if not public:
        config = gd.getScript(account['userName'], account['password'], account['fileName'], gdiParams, gdiLists, "default", False, [])
    else:
        config = gd.getScript('null', 'null', gDocURL, gdiParams, gdiLists, "default", False, [])
        
    cfg = getConfig(config)
    cfg['OutDir'] = account['name'] + '/'
    cfg['FileName'] = account['name']
    cfg['Sanitize'] =  account['sanitize']
    
    if type(account['login']) is list:
        cfg['Logins'] = account['login']
    else:
        cfg['Logins'] = [account['login']]
    cfg['GDI'] = gdi
    cfg['UseGDI'] = True
    
    #if cfg['OnlyKeepNLTK'] != False and cfg['OnlyKeepNLTK'] != 'null':
    #    if type(cfg['OnlyKeepNLTK']) != list:
    #        cfg['OnlyKeepNLTK'] = [str(cfg['OnlyKeepNLTK'])]
    
    if not public:
        uglyLists = gd.getScript(account['userName'], account['password'], account['fileName'], gdiLists, -1, "default", False, [])
    else:
        uglyLists = gd.getScript('null', 'null', gDocURL, gdiLists, -1, "default", False, [])

    conditions = []
    qualifiers = set()
    exclusions = set()
    for pos in range(len(uglyLists)):
        row = uglyLists[pos]
        if len(str(row[0])) != 0:
            conditions.append(row[0])
        if len(str(row[1])) != 0:
            qualifiers.add(row[1])
        if len(str(row[2])) != 0:
            exclusions.add(row[2])
    lists = {'conditions':conditions,'qualifiers':qualifiers,'exclusions':exclusions}
    return {'lists':lists,'config':cfg,'login':account['login']}
    
    
    
    
def getAuth(login):
    """Log in via twitter dev account"""
    """Return authorization object"""
    auth1 = tweepy.auth.OAuthHandler(login['consumerKey'],login['consumerSecret'])
    auth1.set_access_token(login['accessToken'],login['accessTokenSecret'])
    api = tweepy.API(auth1)
    return {'auth':auth1,'api':api}




def stripUnicode(text):
    """Strips unicode special characters for text storage (smileys, etc)"""
    if text == None:
        return "NaN"
    else:
        if type(text) == unicode:
            return str(unicodedata.normalize('NFKD', text).encode('ascii', 'ignore'))
        else:
            return text




def outTime(dtobject):
    """quick, standardized time string out"""
    return {'full':dtobject.strftime(timeArgs),'day':dtobject.strftime('%A'),
        'date':dtobject.strftime('%m-%d-%y'),'time':dtobject.strftime('%H:%S')}
    
    
    
    
def localTime(timeContainer, offset):
    """returns local time offset by timezone"""
    typeTC = type(timeContainer)
    if typeTC != datetime.datetime and typeTC != datetime.time and typeTC != datetime.date:
        if typeTC is dict:
            utcTime =timeContainer['created_at']
        elif typeTC is str:
            utcTime = parser.parse(utcTime)
        else:
            utcTime = timeContainer.created_at  
        if type(utcTime) is str or type(utcTime) is unicode:
            utcTime = parser.parse(utcTime)    
    else:
        utcTime = timeContainer 

    if type(offset) is dict:
        offsetReal = offset['TimeOffset']
    else:
        offsetReal = offset
    
    if abs(offsetReal) <= 12:
        offsetReal *= 3600

    corrected =  utcTime + datetime.timedelta(seconds=offsetReal)   
    
    return corrected
    #return {'dt':corrected,'text':corrected.stroftime(timeArgs)}




def uniqueJson(rawResults):
    """ returns a tweet json filtered for unique IDS and sorted"""
    collected = rawResults[:]
    if len(collected) == 0:
        return []
    if type(collected[0] ) is dict:
        collected = dict([(tweet['id'], tweet) for tweet in collected]).values()
        collected = sorted(collected, key=lambda k: k['id'])
    else:
        collected = dict([(tweet.id, tweet) for tweet in collected]).values()
        collected = sorted(collected, key=lambda k: k.id)
    return collected

    


def getLogins(directory, files):
    """gets login parameters from list & directory passed on by config file"""
    logins = {}
    print
    for fileName in files:
        params = {'description':'null'}
        if directory == "null":
            directory = ''
        print "Loading login file:", directory + fileName
        try:
            try: 
                fileIn = open(directory+'/logins/' + fileName)
            except:
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
        except:
            print "\tlogin file not found"
    print
    return logins
    



def getWords(directory, name):
    """Loads & cleans phrases from text file"""
    try:
        with open (directory+'/lists/'+name, 'r') as fileIn:
            text=fileIn.read().lower()
            while '  ' in text:
                text = text.replace('  ',' ')
    except:
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




def updateWordBanks(directory, cfg): 
    """Pulls word lists from local directory or GDI"""
    useGDI = False
    try:
        if cfg.has_key('UseGDI'):
            if cfg['UseGDI']:
                useGDI = True
        else:
            print "Attempting file update of local directory"
            os.system('git pull')
            print "Git pull successful"
    except:
        print "Unable to update list files via git"
    
    if useGDI:
        print "Loading word lists via GDI\n"
        return giSpyGDILoad(cfg['GDI']['URL'],directory)['lists']
    else:
        print "Preparing to load updated list files from text\n"
        conditions = getWords(directory, cfg['Conditions'])
        print "\nLoaded Conditions:", conditions
        qualifiers = set(getWords(directory, cfg['Qualifiers']))
        print "\nLoaded Qualifiers:", qualifiers
        exclusions = set(getWords(directory, cfg['Exclusions']))
        print "\nLoaded Exclusions:", exclusions, '\n'
    
        return {'conditions':conditions,"qualifiers": qualifiers, 'exclusions': exclusions}
    



def openWhenReady(directory, mode):
    """Trys to open a file, if unable, waits five seconds and tries again"""
    attempts = 0
    while True:
        try:
            fileOut = open(directory,mode)
            break
        except:
            time.sleep(5)
            attempts += 1
            if attempts == 1000:
                print "Error: Unable to open", directory, "for 5000 seconds, quiting now"
                quit()
    return fileOut
    
    
   
    
def geoString(geo):
    """Returns twitter search request formatted geoCoords"""
    return str(geo).replace(' ','')[1:-1]+'mi'   




def patientGeoCoder(request,cfg):
    """Patient geocoder, will wait if API rate limit hit"""
    gCoder = geocoders.GoogleV3()
    tries = 0
    limit = 1
    delay = 5
    if "Cores" in cfg.keys():
        delay *= cfg['Cores']
    while True:
        try:
            return gCoder.geocode(request)
        except:
            tries +=1
            if tries == limit+1 or not cfg['PatientGeocoding']:
                if 'Cores' not in cfg.keys():
                    print "\nUnable to geoCode", request, '\n'
                return "timeOut", ('NaN','NaN')
            time.sleep(delay)
            
            
            

def isInBox(cfg,geoCache,status):
    """Returns true if coord is within lat/lon box, false if not"""
    #http://code.google.com/p/geopy/wiki/GettingStarted
    #gCoder = geocoders.GoogleV3()
    hasCoords = False
    hasPlace = False
    coordsWork = False
    place = 'NaN'
    fromFile = False

    if type(status) is dict:
        userLoc = status['user']['location']
        coordinates = status['coordinates']
        if type(coordinates) is dict:
            coordinates = coordinates['coordinates']
            hasCoords = True
    else:
        userLoc = status.user.location
        coordinates = status.coordinates
        if type(coordinates) is dict:
            coordinates = coordinates['coordinates']
            hasCoords = True
    
    cacheRef = (unicode(coordinates) + unicode(userLoc)).lower()
    if cacheRef in geoCache.keys():
        if 'Cores' not in cfg.keys():
            print "DEBOOO: Inboxed from memory", cacheRef
        loaded = geoCache[cacheRef]
        if loaded['lat'] != 'NaN' and loaded['lon'] != 'NaN':
            place = loaded['place']
            coordinates = [loaded['lon'],loaded['lat']]
            hasPlace = True
            hasCoords = True
            coordsWork = True
        else:
            return loaded
    elif 'Cores' not in cfg.keys():       
        print "DEBOOO: Looking up", cacheRef
    
    
    if type(coordinates) is list:
        coordsWork = len(coordinates) == 2
        
            
    if (type(userLoc) is unicode or type(userLoc) is str) and userLoc != None and userLoc != "None" and not coordsWork:
        userLoc = stripUnicode(userLoc)
        if ':' in userLoc:
            coordinates = str(userLoc[userLoc.index(':')+1:]).split(',')[::-1]
            try:
                coordinates[0],coordinates[1] = float(coordinates[0]),float(coordinates[1])
                hasCoords = True
            except:
                None
        if not hasCoords:
            #lookup coords by location name
            try:
                userLoc = str(userLoc).replace('Va','Virginia')
                place, (lat, lng) = patientGeoCoder(userLoc,cfg)
                time.sleep(.15); coordinates = [lng,lat] 
                hasPlace = True
                hasCoords = True
            except:
                output = {'inBox':False,'text':'NoCoords','place':'NaN','lat':'NaN','lon':'NaN','trueLoc':coordsWork}
                geoCache[cacheRef] = output
                return output
   
    if not hasCoords:
        output = {'inBox':False,'text':'NoCoords','place':'NaN','lat':'NaN','lon':'NaN','trueLoc':coordsWork}
        geoCache[cacheRef] = output
        return output
    else:
        #status['coordinates'] = coordinates
        if not hasPlace:
            try:
                place, (lat, lng) = patientGeoCoder(str(coordinates[1])+','+str(coordinates[0]),cfg)
                time.sleep(.15)
            except:
                None
    
    if place == None or place == 'None':
        place = 'NaN'
    
    if place == "timeOut":
        return {'inBox':False,'text':'NoCoords','place':'NaN','lat':'NaN','lon':'NaN','trueLoc':coordsWork}
        
    try:
        if sorted([cfg['Lat1'],cfg['Lat2'],coordinates[1]])[1] != coordinates[1]:
            output = {'inBox':False,'text':'HasCoords','place':place,'lat':coordinates[1],'lon':coordinates[0],'trueLoc':coordsWork}
            geoCache[cacheRef] = output
            return output
        if sorted([cfg['Lon1'],cfg['Lon2'],coordinates[0]])[1] != coordinates[0]:
            output = {'inBox':False,'text':'HasCoords','place':place,'lat':coordinates[1],'lon':coordinates[0],'trueLoc':coordsWork}
            geoCache[cacheRef] = output
            return output
        output =  {'inBox':True,'text':'InBox','place':place,'lat':coordinates[1],'lon':coordinates[0],'trueLoc':coordsWork}
        geoCache[cacheRef] = output
        return output
    except:
        output = {'inBox':False,'text':'Error','place':place,'lat':coordinates[1],'lon':coordinates[0],'trueLoc':coordsWork}
        geoCache[cacheRef] = output
        return output



def getGeo(cfg):
    """Generates geo queries to cover lat/lon box"""
    lat1 = cfg['Lat1']
    lat2 = cfg['Lat2']
    lon1 = cfg['Lon1']
    lon2 = cfg['Lon2']
    lonMid = (lon1+lon2)/2
    latMid = (lat1+lat2)/2
    if abs(lat1) > abs(lat2):
        latPt = lat1
    else:
        latPt = lat2
    center = [lonMid,latMid]
    corner = [lon1,latPt]
    radius = int(great_circle(center,corner).miles + 1)
    if radius > 40 and cfg['Method'].lower() == 'search':
        print "Radius too large for single search, using stacking algorithm"
        return "STACK"
    else:
        print "Converting search box to radius search"
        print "\tCenter:", center
        print "\tRadius(mi):", radius
        return [center[1],center[0],radius]
    
    


def checkTweet(conditions, qualifiers, exclusions, text, cfg):
  """Checks if tweet matches search criteria"""
  text = text.lower()
  foundCondition = False
  foundQualifier = False
  foundExclusion = False
  
  if "rt @" in text and not cfg['KeepRetweets']:
    return "retweet"
  else:
    for word in exclusions:
      if word in text:
        foundExclusion = True
    for word in conditions:
      if word in text:
        foundCondition = True
        break
    for word in qualifiers:
      if word in text:
        foundQualifier = True
        break
    if foundCondition and foundExclusion:
        return "excluded"
    elif foundCondition and foundQualifier:
      return "accepted"
    elif foundCondition:
      return "partial"
    else:
        return "irrelevant"
        
        
        

def jsonToDictFix(jsonIn):
    """Error hardy json converter"""
    if type(jsonIn) is list:
        for row in range(len(jsonIn)):
            if type(jsonIn[row]) is str or type(jsonIn[row]) is unicode:
                jsonIn[row] = json.loads(jsonIn[row])
    elif type(jsonIn) is dict:
        None
    else:
	jsonIn = json.loads(jsonIn)
    return jsonIn    
            
            
            
def dictToJsonFix(jsonOut):
     """Error tolerant json converter"""
     for row in range(len(jsonOut)):
        if type(jsonOut[row]) is dict:
            jsonOut[row] = json.dump(jsonOut[row])   


def getReformatted(directory, lists, cfg, pickleMgmt, fileList, core, out_q, keepTypes, NLTKClassifier):
    count = 0
    collectedContent = []
    collectedTypes = {}
    geoPickle = dict(pickleMgmt.items())
    
    useNLTK = NLTKClassifier != 'null' and NLTKClassifier != False
    
    for fileName in fileList:
            inFile = open(directory+fileName)
            content = json.load(inFile)
            filteredContent = []
            
            print "Core", core, "reclassifying", fileName, "by updated lists"
            
            if lists != "null":
                jsonToDictFix(content)
            
            if  cfg['DaysBack'] != 'all' and type(cfg['DaysBack']) is int:
                leftBound = datetime.datetime.utcnow() - datetime.timedelta(days = cfg['DaysBack'])
                content = [item for item in content if parser.parse(item['created_at']).replace(tzinfo=None) > leftBound]
            
            for tweet in content:
                count += 1
                if count%250 == 0:
                    print "\tCore",core,count,"tweets sorted"
                #if count%cfg['PickleInterval'] == 0:
                #    updateGeoPickle(pickleMgmt,cfg['Directory']+pickleName)
                tweet['text'] = tweet['text'].replace('\n',' ')
                tweetType = checkTweet(lists['conditions'],lists['qualifiers'],lists['exclusions'], tweet['text'], cfg)
                if tweetType in keepTypes:
                    geoType = isInBox(cfg,geoPickle,tweet)
                    if geoType['inBox'] or cfg['KeepUnlocated']:
                        timeData = outTime(localTime(tweet,cfg))
                        collectedTypes[str(tweet['id'])] = {'tweetType':tweetType,
                            'geoType':geoType['text'],
                            'lat':geoType['lat'],
                            'lon':geoType['lon'],
                            'fineLocation':geoType['trueLoc'],
                            'place':geoType['place'],
                            'day':timeData['day'],
                            'time':timeData['time'],
                            'date':timeData['date']}
                        if useNLTK:
                            collectedTypes[str(tweet['id'])]['nltkCat'] = str(TweetMatch.classifySingle(tweet['text'],NLTKClassifier))
                        
                    filteredContent.append(tweet)
            
            collectedContent += filteredContent  
            #print "DEBOOO123", useNLTK,cfg['OnlyKeepNLTK'],count,len(collectedContent) , len(collectedTypes)              
            filteredContent = cleanJson(filteredContent,cfg,collectedTypes)
            
            outName = fileName.replace('Raw','FilteredTweets')

            if cfg['MakeFilteredJson']:
                print "\tSaving file as", outName
                with open(directory+outName, 'w') as outFile:
                    json.dump(filteredContent,outFile)
                outFile.close()
            
    collectedContent = cleanJson(collectedContent,cfg,collectedTypes)
    pickleMgmt = Manager().dict(geoPickle)        
    #out_q.put({'content'+str(core):collectedContent,'types'+str(core):collectedTypes})
    print "Core", core, "tasks complete!"
    out_q.put({'content'+str(core):collectedContent})        


def reformatOld(directory, lists, cfg, geoCache, NLTKClassifier):
    """Keeps old content up to date with latests queries & settings"""
    keepTypes = ['accepted']*cfg['KeepAccepted']+['partial']*cfg['KeepPartial']+['excluded']*cfg['KeepExcluded']
    homeDirectory = directory
    manager = Manager()
    pickleMgmt = manager.dict(geoCache)
    
    print "Preparing to reformat from raw tweets..."
    if cfg['OutDir'] not in directory.lower():
        directory += cfg['OutDir'] + cfg['Method'] + '/'
    if not os.path.exists(directory):
        os.makedirs(directory)
        fileList = []
    else:
        fileList = os.listdir(directory)
        oldFiltered = [i for i in fileList if i.lower().startswith('filteredtweets')]
        fileList = [i for i in fileList if i.lower().startswith('raw')]
    
    
    if len(fileList) != 0:
        if lists == 'null':
            lists = updateWordBanks(homeDirectory, cfg)
        
        collectedContent = []
        fileList = filter(lambda i: not os.path.isdir(directory+i), fileList)
        random.shuffle(fileList)
        cores = cpu_count()
        cfg['Cores'] = cores
        out_q = Queue()
        block =  int(ceil(len(fileList)/float(cores)))
        processes = []

        for i in range(cores):
        #for i in range(1):
            p = Process(target = getReformatted, args = (directory, lists, cfg, pickleMgmt, fileList[block*i:block*(i+1)], i, out_q, keepTypes, NLTKClassifier))
            
            processes.append(p)
            p.start() 
        merged = {}
        for i in range(cores):
            merged.update(out_q.get())
        for p in processes:
            p.join()
        
        print "Processes complete, merging output"
           
        for i in range(cores):
            #print merged['content'+str(i)]
	    collectedContent += merged['content'+str(i)]
            #collectedTypes.append(merged['types'+str(i)])
            
        print "Returning updated geoPickle"
        geoCache = dict(pickleMgmt.items())
        updateGeoPickle(geoCache,cfg['Directory']+pickleName)
       
	outName = cfg['FileName']+"_CollectedTweets"
        
        print "Writing collected tweets to "+outName+".json"
        with open(directory+outName+'.json', 'w') as outFile:
                json.dump(collectedContent,outFile)
        outFile.close()
        print "...complete"
        
        jsonToDictFix(collectedContent)
	collectedContent = uniqueJson(collectedContent)        
        
        if len(collectedContent) == 0:
            print "No tweets match criteria, csv will not be generated"
            return geoCache
        else:
            orderedKeys = sorted(collectedContent[0].keys())
            orderedKeys.insert(0,orderedKeys.pop(orderedKeys.index('text')))
            
   	    if cfg['OnlyKeepNLTK'] != False:
  		addKeys = []
            else:
  		addKeys = ["score","check3","check2","check1"]
            
   	    for key in addKeys:
                if key not in orderedKeys:  
                    orderedKeys.insert(1,key)
                    
            for pos in range(len(collectedContent)):
                for key in orderedKeys:
                    if key not in collectedContent[pos].keys():
                        collectedContent[pos][key] = 'NaN'
                    else:
                        collectedContent[pos][key] = stripUnicode(collectedContent[pos][key])
        
            if cfg['OnlyKeepNLTK'] != False and not cfg['KeepDiscardsNLTK']:
  		collectedContent = [entry for entry in collectedContent if str(entry['nltkCat']) in cfg['OnlyKeepNLTK']]
  		
            if cfg['Sanitize'] != False:
                collectedContent = [sanitizeTweet(tweet) for tweet in collectedContent]
            
            
            print "Writing collected tweets to "+outName+".csv"   
            outFile = open(directory+outName+'.csv', "w") 
            csvOut = csv.DictWriter(outFile,orderedKeys)
            csvOut.writer.writerow(orderedKeys)
            csvOut.writerows(collectedContent)

            #DEBOO TAG TRACKING
            getTags(cfg,collectedContent)
            
            
            """for row in collectedContent:
                print row
                csvOut.writerow(row)
                print "complete"""
                
            outFile.close()
            print "...complete"
            return geoCache
             
    else:
        print "Directory empty, reformat skipped"
        return geoCache




def getTags(cfg,data):
    """Pulls top n tags for last m days"""
    dates = [parser.parse(entry['created_at']) for entry in data]
    rightBound = max(dates)
    leftBound = rightBound - datetime.timedelta(days = cfg['TrackHashDays'])
    data = [entry for entry in data if leftBound < parser.parse(entry['created_at']) < rightBound]
    tags = countHashTags(data,cfg['TrackHashCount'])
    print "Top",cfg['TrackHashCount'], "hashtags for past", cfg['TrackHashDays'], "days:", tags
    return tags
    
    
    
    
def countHashTags(data,number):
    """Pulls top tags from data sample"""
    entries = [entry['text'] for entry in data]
        
    counts = dict()
    toReturn = []
    for entry in entries:
        words = entry.split(' ')
        for word in words:
            if word.startswith('#'):
                if word not in counts.keys():
                    counts[word] = 1
                else:
                    counts[word] += 1
                    
    sortedCounts= sorted(counts.iteritems(), key=itemgetter(-1))[-number:]
    return [count[0] for count in reversed(sortedCounts)]

      
      
      
def cleanJson(jsonOriginal, cfg, types):
    """Returns filtered json with only desired data & derived data"""
    tweetData = cfg['TweetData']
    userData = cfg['UserData']
    keepUser = len(userData) > 0 and 'user' not in tweetData
    jsonIn = []
    
    if len(tweetData + userData) > 0:
        for row in range(len(jsonOriginal)):
            loaded = jsonToDictFix(deepcopy(jsonOriginal[row]))
            ID = str(loaded['id'])
	    loadedUser = loaded['user']
            del loaded['user']
            tempJson = dict([(i, loaded[i]) for i in tweetData if i in loaded])
            userJson = dict([(i, loadedUser[i]) for i in userData if i in loadedUser])
            if keepUser:
                for key in userJson.keys():
                    tempJson['user_' + key] = userJson[key]
            jsonIn.append(tempJson)
            if ID in types.keys():
	        for key in types[ID].keys():
                    jsonIn[row][key] = types[ID][key]
        
	jsonIn = [row for row in jsonIn if str(row['id']) in types.keys()] 
        uniqueJson(jsonIn)
    
    return jsonIn
        
        


def getConfig(directory):
    """Loads configuration from file config"""
    hidden = ['Sanitize','login']
    TweetData = 'all'
    UserData = {}
    #default values
    params = {'StopTime':0,'StopCount':15,'KeepRaw':True,
                'TweetData':TweetData, 'UserData':UserData,
                'FileName':'filtered','OutDir':'outPut/',
                'KeepAccepted':True,'KeepPartial':True,
                'KeepExcluded':True, 'method':'search',
                'Logins':'NoLoginsFound','UseGDI':False,
                'UseStacking':False,'KeepUnlocated':False,
                'PickleInterval':500,'PatientGeocoding':True,
                'OnlyKeepNLTK':False,'MultiLogin':False,
                'KeepRetweets':False,'StrictGeoFilter':False,
                'StrictWordFilter':False,'Sanitize':False,
                'KeepDiscardsNLTK':False,'DiscardSampleNLTK':0,
                'MakeFilteredJson':False,'SendEvery':1,
                'TrackHashTags':False,'TrackHashDays':10,
                'TrackHashCount':5,'DaysBack':'all'}
    
    if type(directory) is str:
        if directory == "null":
            directory = ''
        fileIn = open(directory)
        content = fileIn.readlines()
        useGDI = False
        for pos in range(len(content)):
            item = content[pos]
            if ' = ' in item:
                while '  ' in item:
                    item = item.replace('  ',' ')
                while '\n' in item:
                    item = item.replace('\n','')
                line = item.split(' = ')
            content[pos] = line

    elif type(directory) is list:
        content = directory
        useGDI = True
    
    content = [line for line in content if str(line[0]) not in hidden]

    for line in content:
        if len(str(line[0])) != 0 and len(str(line[1])) != 0 and not str(line[0]).startswith('#'):
            try:
                line[1] = float(line[1])
                if line[1] == int(line[1]):
                    line[1] = int(line[1])
            except:
                if isinstance(line[1], str):
                    if line[1].lower() == 'true':
                        line[1] = True
                    elif line[1].lower() == 'false':
                        line[1] = False
            
            params[line[0]] = line[1]
    print "\nLoaded params:"
    
    params['Logins'] = textToList(params['Logins'])    
    try:
        params['TweetData'] = textToList(params['TweetData'])
    except:
        None
    try:
        params['UserData'] = textToList(params['UserData'])
    except:
        None
        
    try:
        params['KeepDiscardsNLTK'] = 0 < float(params['DiscardSampleNLTK']) <= 1
    except:
        None
        
        
    for key in sorted(params.keys()):
        print  '\t*', key,':', params[key]
    
    if params['Lat1']>params['Lat2']:
        params['Lat1'],params['Lat2'] = params['Lat2'],params['Lat1']
    if params['Lon1']>params['Lon2']:
        params['Lon1'],params['Lon2'] = params['Lon2'],params['Lon1']
    
    return params
    
    
    

def textToList(string):
    """Loads lists from text scripting"""
    text = string.replace(',','')
    while '  ' in text:
        text = text.replace('  ',' ')
    listed = text.split(' ')
    return listed
    
def sanitizeTweet(tweet):
    words = tweet['text'].split(' ')
    words = [wordSwap(word) for word in words]
    tweet['text'] = ' '.join(words)
    if 'user_screen_name' in tweet.keys():
        tweet['user_screen_name'] = "ATweeter"
    if str(tweet['lat']).lower() != 'nan' and len(str(tweet['lat'])) > 6:
        tweet['lat'] = float(str(tweet['lat'])[:-2])
    if str(tweet['lon']).lower() != 'nan' and len(str(tweet['lon'])) > 6:
        tweet['lon'] = float(str(tweet['lon'])[:-2])
    tweet['id'] = int(str(tweet['id'])[:-2]+'00')
    return tweet
    
def wordSwap(word):
    if len(word) > 0:
        if word[0] == '@':
            return "@ATweeter"
    return word