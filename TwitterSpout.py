import sys, os
import json

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
    
getConfig('')