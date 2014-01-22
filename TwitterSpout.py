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
   
   
   
def stripWords(text):
    """Filters out non alphanumeric characters, leaves hashtags"""
    listed = ''.join((c if (c.isalnum()) else ' ') for c in text).split()
    return listed
    


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
    print "\nSetting up search(es)"
    name = login['name']    
    filterType = cfg['FilterType'].lower()
    seeker = giSeeker(conditions,qualifiers,exclusions,login['api'],cfg,name,'null')
    seeker.run()
        
        
               
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
    usingGDoc = False
    try: 
        userLogin = sys.argv[2]
        print "Login '%s' passed explicitly" % (userLogin)
    except:
        userLogin = 'null'
    try:
        temp = sys.argv[1]
        if temp.startswith('http'):
            usingGDoc = True
            gDocURL = temp
            print "Preparing GDI Remote Access Loader"
        else:
            print "\nTaking user parameters"
            directory = '/'.join(temp.split('/')[:-1])
            configFile = temp.split('/')[-1]
            if directory == '':
                directory = os.getcwd() + '/'
    except:
        print "Taking default parameters"
        directory = os.getcwd() + '/'
        configFile = 'config'
        
    if usingGDoc:
        directory = os.getcwd() + '/'
        temp = giSpyGDILoad(gDocURL,directory)
        cfg = temp['config']
        lists = temp['lists']
        print temp['login']
        login = getLogins(directory,[temp['login']])[temp['login']]
        cfg['Directory'] = directory
        reformatOld(directory,lists,cfg)
        
    else: 
        print "Loading parameters from config file '%s' in directory '%s'" % (configFile, directory)
        cfg = getConfig(directory+configFile)
        cfg['Directory'] = directory
        logins = getLogins(directory, cfg['Logins'])
        lists = updateWordBanks(directory, cfg)
        
        reformatOld(directory,lists,cfg) 
        
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
    
    cfg['_login_'] = login    
    temp = getAuth(login)
    login['auth'] = temp['auth']
    login['api'] = temp['api']
    login['name'] = userLogin
    getTweets(login,cfg,lists['conditions'],lists['qualifiers'],lists['exclusions'])

main()