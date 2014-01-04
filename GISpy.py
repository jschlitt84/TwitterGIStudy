import json
import random
import datetime,time
import os, shutil

from copy import deepcopy
from geopy.distance import great_circle

timeArgs = "%A_%m-%d-%y_%H-%M-%S"


def uniqueJson(rawResults):
    """ returns a tweet json filtered for unique IDS and sorted"""
    collected = rawResults[:]
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
    print
    return logins
    

def getWords(directory, name):
    """Loads & cleans phrases from text file"""
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



#Pulls word lists from local directory
def updateWordBanks(directory, cfg): 
    try:
        if cfg.has_key('UsageMode'):
            if cfg['UsageMode'] == 'gdoc':
                None
        else:
            print "Attempting file update of local directory"
            os.system('git pull')
            print "Git pull successful"
    except:
        print "Unable to update list files via git"
    
    print "Preparing to load updated list files\n"
    conditions = getWords(directory, cfg['Conditions'])
    print "\nLoaded Conditions:", conditions
    qualifiers = set(getWords(directory, cfg['Qualifiers']))
    print "\nLoaded Qualifiers:", qualifiers
    exclusions = set(getWords(directory, cfg['Exclusions']))
    print "\nLoaded Exclusions:", exclusions, '\n'
    
    return {'conditions':conditions,"qualifiers": qualifiers, 'exclusions': exclusions}
    

#Trys to open a file, if unable, waits five seconds and tries again
def openWhenReady(directory, mode):
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

#Returns true if coord is within lat/lon box, false if not
def isInBox(cfg,pos):
    try:
        pos = pos['coordinates']
    except:
        return {'inBox':False,'text':'NoCoords'}
    try:
        if sorted([cfg['Lat1'],cfg['Lat2'],pos[1]])[1] != pos[1]:
            return {'inBox':False,'text':'HasCoords'}
        if sorted([cfg['Lon1'],cfg['Lon2'],pos[0]])[1] != pos[0]:
            return {'inBox':False,'text':'HasCoords'}
        return {'inBox':True,'text':'InBox'}
    except:
        return {'inBox':False,'text':'Error'}


# Finds center and radius in miles of circle than covers lat lon box
def getGeo(cfg):
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
    print "Converting search box to radius search"
    print "\tCenter:", center
    print "\tRadius(mi):", radius
    return [center[1],center[0],radius]
    
    

#Checks if tweet matches search criteria
def checkTweet(conditions, qualifiers, exclusions, text):
  text = text.lower()
  foundCondition = False
  foundQualifier = False
  foundExclusion = False
  
  if "rt @" in text:
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
    for row in range(len(jsonIn)):
        if type(jsonIn[row]) is str or type(jsonIn[row]) is unicode:
            jsonIn[row] = json.loads(jsonIn[row])
            
def dictToJsonFix(jsonOut):
     for row in range(len(jsonOut)):
        if type(jsonOut[row]) is dict:
            jsonOut[row] = json.dump(jsonOut[row])   

def reformatOld(directory, lists, cfg):
    homeDirectory = directory
    keepTypes = ['accepted']*cfg['KeepAccepted']+['partial']*cfg['KeepPartial']+['excluded']*cfg['KeepExcluded']
    
    print "Preparing to reformat from raw tweets..."
    if 'output' not in directory.lower():
        directory += 'output/' + cfg['Method'] + '/'
    if not os.path.exists(directory):
        os.makedirs(directory)
        fileList = []
    else:
        fileList = os.listdir(directory)
        oldFiltered = [i for i in fileList if i.lower().startswith('filteredtweets')]
        fileList = [i for i in fileList if i.lower().startswith('raw')]
    
    
    if len(fileList) != 0:
        
        """
        # backup old filtered files
        
        timeStamp = datetime.datetime.now().strftime(timeArgs)
        newDir = directory+'Old_Filtered_Tweets/Moved_On_'+timeStamp
        os.makedirs(newDir)
        print "Moving old files to", newDir
        for oldFile in oldFiltered:
            print "\t",oldFile
            shutil.move(directory+oldFile,newDir)
        print "archiving complete"
        """
        
        lists = updateWordBanks(homeDirectory, cfg)
            
        fileList = filter(lambda i: not os.path.isdir(directory+i), fileList)
        for fileName in fileList:
            inFile = open(directory+fileName)
            content = json.load(inFile)
            outName = fileName.replace('Raw','FilteredTweets')
            types = []
            filteredContent = []
            
            print "Reclassifying", fileName, "by updated lists"
            
            if lists != "null":
                jsonToDictFix(content)
            
            for tweet in content:
                tweetType = checkTweet(lists['conditions'],lists['qualifiers'],lists['exclusions'], tweet['text'])
                if tweetType in keepTypes:
                    geoType = isInBox(cfg,tweet['coordinates'])
                    types.append({'tweetType':tweetType,'geoType':geoType['text']})
                    filteredContent.append(tweet)
            
            cleanJson(filteredContent,cfg,types)
            
            print "\tSaving file as", outName
            
            with open(directory+outName, 'w') as outFile:
                json.dump(filteredContent,outFile)
            outFile.close()
    else:
        print "Directory empty, reformat skipped"

      
#Removes all but select parameters from tweet json. If parameter is under user params, brings to main params                  
def cleanJson(jsonIn, cfg, types):
    tweetData = cfg['TweetData']
    userData = cfg['UserData']
    keepUser = len(userData) > 0 and 'user' not in tweetData
    userKeys = []
    toDelete = []
    
    jsonToDictFix(jsonIn)
    
    if len(tweetData + userData) > 0:
        for row in range(len(jsonIn)):
            loaded = jsonIn[row]
            loadedUser = loaded['user']
            del loaded['user']
            tempJson = dict([(i, loaded[i]) for i in tweetData if i in loaded])
            userJson = dict([(i, loadedUser[i]) for i in userData if i in loadedUser])
            if keepUser:
                for key in userJson.keys():
                    tempJson['user_' + key] = userJson[key]
            jsonIn[row] = tempJson
            if type(types[row]) is str:
                jsonIn[row]['tweetType'] = types[row]
            elif type(types[row]) is dict:
                for key in types[row].keys():
                    jsonIn[row][key] = types[row][key]        
        
        
#Loads configuration from file config
def getConfig(directory):
    TweetData = 'all'
    UserData = {}
    params = {'StopTime':0,'StopCount':15,'KeepRaw':True,
                'TweetData':TweetData, 'UserData':UserData,
                'FileName':'filtered','OutDir':'outPut/',
                'KeepAccepted':True,'KeepPartial':True,
                'KeepExcluded':True, 'method':'stream'}
    
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
        
        
    for key in sorted(params.keys()):
        print  '\t*', key,':', params[key]
    
    if params['Lat1']>params['Lat2']:
        params['Lat1'],params['Lat2'] = params['Lat2'],params['Lat1']
    if params['Lon1']>params['Lon2']:
        params['Lon1'],params['Lon2'] = params['Lon2'],params['Lon1']
    
    return params
    
    
    
#List from text
def textToList(string):
    text = string.replace(',','')
    while '  ' in text:
        text = text.replace('  ',' ')
    listed = text.split(' ')
    return listed
        