import sys, os
import json
import tweepy
import datetime
import time
import random

from copy import deepcopy
from GISpy import *
from giListener import *

#from multiprocessing import Process, Queue

expected = ['Lat1','Lat2','Lon1','Lon2','Logins','Conditions','Qualifiers','Exclusions']


@classmethod
def parse(cls, api, raw):
    """#Hacky patch for raw json access, not granted in newest tweepy version
        #Method: http://willsimm.co.uk/saving-tweepy-output-to-mongodb/"""
    status = cls.first_parse(api, raw)
    setattr(status, 'json', json.dumps(raw))
    return status

tweepy.models.Status.first_parse = tweepy.models.Status.parse
tweepy.models.Status.parse = parse



def getLogins(directory, files):
    """gets login parameters from list & directory passed on by config file"""
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
    

   
def stripWords(text):
    """Filters out non alphanumeric characters, leaves hashtags"""
    listed = ''.join((c if (c.isalnum()) else ' ') for c in text).split()
    return listed
    
    

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

    

def getAuth(login):
    """Return authorization object"""
    auth1 = tweepy.auth.OAuthHandler(login['consumerKey'],login['consumerSecret'])
    auth1.set_access_token(login['accessToken'],login['accessTokenSecret'])
    api = tweepy.API(auth1)
    return {'auth':auth1,'api':api}



def postTweet(api,text,image):
    """Posts a tweet"""
    if image != None and image != 'null':
        api.update_status(text)
        print "posted tweet:", text
        

                                                      
def getTweets(login, cfg, conditions, qualifiers, exclusions):
    """selects method of tweet aquisition"""
    if cfg['Method'].lower() == 'stream':
        getViaStream(login, cfg, conditions, qualifiers, exclusions)
    elif cfg['Method'].lower() == 'search':
        getViaSearch(login, cfg, conditions, qualifiers, exclusions)
    getViaStream(login, cfg, conditions, qualifiers, exclusions)
        
        
        

def getViaSearch(login, cfg, conditions, qualifiers, exclusions):
    """acquires tweets via search method"""
    print "\nSetting up searc(es)"
    name = login['name']    
    filterType = cfg['FilterType'].lower()
    seeker = giSeeker(conditions,qualifiers,exclusions,login['api'],cfg,name,'null')
    print "HUZZAH1"
    seeker.run()
    print "HUZZAH2"
        
        
               
def getViaStream(login, cfg, conditions, qualifiers, exclusions):
    """acquires tweets via geo stream"""
    print "\nSetting up listener(s)"
    name = login['name']
    filterType = cfg['FilterType'].lower()

    ear = giListener(conditions,qualifiers,exclusions,login['api'],cfg,name,'null')
    print "Logging in via", name,"credentials file"
        
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