import copy
import json

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
      
def cleanJson(jsonIn, keep, types):
    userKeys = []
    toDelete = []
    for pos in range(len(keep)):
        key = keep[pos]
        if "user['" in key:
            userKeys.append(key.replace("user['",'').replace("']",''))
            toDelete.insert(0,pos)
    if toDelete != []:
        for pos in toDelete:
            del keep[pos]        
    for row in range(len(jsonIn)):
        loaded = json.loads(jsonIn[row])
        userData = loaded['user']
        del loaded['user']
        tempJson = dict([(i, loaded[i]) for i in keep if i in loaded])
        if userKeys != []:
            for item in userKeys:
                if item in userData:
                    tempJson[item] = userData[item]
        jsonIn[row] = tempJson
        jsonIn[row]['tweetType'] = types[row]
    for item in jsonIn:
        print "Filtered Out", item
    print
        
        
#Loads configuration from file config
def getConfig(directory):
    keepKeys = {}
    params = {'StopTime':0,'StopCount':15,'KeepRaw':True,
                'KeepKeys':keepKeys,'FileName':'filtered',
                'OutDir':'outPut/','KeepKeys':'all',
                'KeepAccepted':True,'KeepPartial':True,'KeepExcluded':True}
    
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
        params['KeepKeys'] = textToList(params['KeepKeys'])
    except:
        None
        
    for key,item in params.iteritems():
        print '\t*', key,':', item
    
    if params['Lat1']>params['Lat2']:
        params['Lat1'],params['Lat2'] = params['Lat2'],params['Lat1']
    if params['Lon1']>params['Lon2']:
        params['Lon1'],params['Lon2'] = params['Lon2'],params['Lon1']
    
    found = False
    for entry in params['KeepKeys']:
        if entry.startswith('user['):
            found = True
            break
    if found:
        params['KeepKeys'].append('user')
    while params['KeepKeys'].count('user') > 1:
        del params['KeepKeys'][params['KeepKeys'].index('user')]
    return params
    
    
#List from text
def textToList(string):
    text = string.replace(',','')
    while '  ' in text:
        text = text.replace('  ',' ')
    listed = text.split(' ')
    return listed
        