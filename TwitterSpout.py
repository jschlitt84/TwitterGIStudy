import sys, os
import json
import tweepy

paramsNeeded = ['consumerToken','consumerSecret']

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
    return params
    

def getAuth(cfg):
    auth1 = tweepy.auth.OAuthHandler(cfg['consumerKey'],cfg['consumerSecret'])
    auth1.set_access_token(cfg['accessToken'],cfg['accessTokenSecret'])
    api = tweepy.API(auth1)
    api.update_status('Tweepy: Hello World')
    return api




def main():
    try:
        directory = sys.argv[1]
    except:
        directory = os.getcwd() + '/'
    cfg = getConfig(directory)
    api = getAuth(cfg)


main()