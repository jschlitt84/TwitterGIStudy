import gdata.docs
import gdata.docs.service
import gdata.spreadsheet.service
import sys 
import os

import requests

isPrivate = True



# CONNECTS TO OWNED PRIVATE SPREADSHEET

def spreadConnect(userName, __password, fileName):
    client = gdata.spreadsheet.service.SpreadsheetsService()
    client.email = userName
    client.password = __password
    __password = "*"*len(__password)
    client.ssl = False
    client.source = fileName
    try:
        client.ProgrammaticLogin()
        print "Connected to Google Spreadsheet via username %s & password %s" % (userName,__password)
    except:
        print "Error, Google Spreadhseet Login Failed, username %s & password %s" % (userName,__password)
        client.password = None
        quit()
    return client
    

# CONNECTS TO OWNED PRIVATE GDOCS ACCOUNT        
    
def googConnect(userName, __password, fileName):
    client = gdata.docs.service.DocsService()
    client.email = userName
    client.password = __password
    __password = "*"*len(__password)
#    client.ssl = False
    client.source = fileName
    try:
        client.ProgrammaticLogin()
        print "Connected to Google Docs via username %s & password %s" % (userName,__password)
    except:
        print "Error, Google Docs Login Failed, username %s & password %s" % (userName,__password)
        client.password = None
        quit()
    return client


# PULLS PRIVATE SPREADSHEET TO TEMPORARY FILE

def getFile(userName, __password, fileName):
    gd_client = googConnect(userName, __password, fileName)
    spreadsheets_client = spreadConnect(userName, __password, fileName)
    __password = None
    
    q = gdata.spreadsheet.service.DocumentQuery()
    q['title'] = fileName
    q['title-exact'] = 'true'
    feed = spreadsheets_client.GetSpreadsheetsFeed(query=q)
    
    spreadsheet_id = feed.entry[0].id.text.rsplit('/',1)[1]
    print "Accessing Spreadsheet ID:", spreadsheet_id
    feed = spreadsheets_client.GetWorksheetsFeed(spreadsheet_id)
    
    tempFile = "googtemp.csv"
    uri = 'http://docs.google.com/feeds/documents/private/full/%s' % spreadsheet_id

    entry = gd_client.GetDocumentListEntry(uri)
    docs_auth_token = gd_client.GetClientLoginToken()
    gd_client.SetClientLoginToken(spreadsheets_client.GetClientLoginToken())
    gd_client.Export(entry, tempFile)
    gd_client.SetClientLoginToken(docs_auth_token)


# RETURNS PUBLIC SPREADSHEET AS LIST OF STRINGS   
                       
def getPublicFile(userName, fileName):
    
    try:
        fileName = fileName[:fileName.index('#gid')]
    finally:
        fileName += '&output=csv'

    print "\nLoading public file", fileName
    
    response = requests.get(fileName)
    assert response.status_code == 200, 'Wrong status code'
    data = response.content.split('\n')
    toDelete = []
    for pos in range(len(data)):
        data[pos] =  data[pos].replace('"','')
        if data[pos].count(',') == len(data[pos]):
            toDelete.append(pos)
    for pos in reversed(toDelete):
        del data[pos]
        
    return data


# RETURNS LINE NUMBERS WITHIN LIST OF STRINGS CONTAINED BY START AND STOP STRINGS

def getPos (start, stop, script):
    length = len(script)
    startPos = 0
    stopPos = len(script)
    if isinstance(start, str) and not isinstance(stop, str):
        foundStart = False
        foundStop = True
        stopPos = int(stop)
        for pos in range(length):
            if start in script[pos]:
                startPos = pos + 1
                foundStart = True
                break
    if not isinstance(start, str) and isinstance(stop, str):
        foundStart = True
        foundStop = False
        startPos = int(start)
        for pos in range(length):
            if stop in script[pos]:
                stopPos = pos
                foundStop = True
                break
    if isinstance(start, str) and isinstance(stop, str):
        foundStart = False
        foundStop = False
        for pos in range(length):
            if start in script[pos]:
                startPos = pos + 1
                foundStart = True
            if stop in script[pos]:
                stopPos = pos
                foundStop = True
    if not foundStart:
        print "Error, start string '", start, "' not found, defaulting to pos 0"
        startPos = 1
    elif not foundStop:
        print "Error, stop string '", stop, "' not found, defaulting to pos", length
        stopPos = length

    return {'start':startPos,'stop':stopPos}

"""def isEmpty(script) :
    script  = [item for item in script if len(filter(bool,item)) != 0]
    return len(script) == 0"""
       
# LOADS DATA FROM PUBLIC LIST OR PRIVATE TEMP FILE, PARSES BY CLEANTYPE & RETURNS LIST OF NUMERIC VALUES OR STRINGS  
    
def loadNClean(isPrivate,publicData, start, end, cleanType):
    if isPrivate:
        tempFile = open("googtemp.csv")
        script = tempFile.readlines()
        tempFile.close()
        os.remove("googtemp.csv")
    else:
        script = publicData
    
    pos = 0
    length = len(script)
    while pos < length:
        if "#" in script[pos] and "#IGNORE" not in script[pos] or len(script[pos].replace(",",''))<1:
            del script[pos]
            length -= 1
        else:
            pos +=1
                                
    if isinstance(start, str) or isinstance(end, str):
        holder = getPos(start, end, script)
        start = int(holder['start'])
        end = int(holder['stop'])
        hasEnd = True
    try:
        if int(end) >= 1 and int(end) > int(start):
            hasEnd= True
        else:
            hasEnd = False
    except:
        start = 0
        hasEnd = False        
                            
    length = len(script)
    
    if length < start:
        print "Error: no values found, invalid block index"
        quit()
    elif start == end:
        print "\n*** Warning: block is empty ***\n"
        return "null"
                
    script = script[start:length+1]
    length -= start
    end -= start
    pos = 0
    print "Google content loaded, parsing to internal format"
    
    if cleanType == "single line":
        hasEnd = True
        end = 1
    
    if hasEnd:
        if end < length:
            del script[end:length+1]
            length = end  
      
    while pos < length:
        script[pos]= script[pos].replace('\n','')
        if "#IGNORE" in script[pos]:
            del script[pos:length+1]
            break
        """if "#" in script[pos] or len(script[pos].replace(",",''))<1:
            del script[pos]
            pos -= 1
            length -= 1"""


# CONVERTS INTERVENTION/ ENUMERATION SCRIPT TO INTERNAL STRING FORMAT               
                
        if cleanType == "intervention script":
            if "enum" in script[pos]:
                script[pos] = script[pos].replace(',',' ')
                script[pos] = script[pos].replace('enum enum','enum')
                script[pos] = script[pos].replace('enum 0','enum')
                pos += 1
                while "#" in script[pos] or len(script[pos].replace(",",''))<1:
                    del script[pos]
                    pos -= 1
                    length -= 1
                
                
                script[pos] = script[pos].replace('","',' ; ')
                script[pos] = script[pos].replace('"','')
                script[pos] = script[pos].replace(':',' ')
                script[pos] = script[pos].replace('-',' ') 
                
    
            script[pos] = script[pos].replace(',',' ')
            script[pos] = script[pos].replace('  ',' ')
        pos += 1
    
    print
       
# CLEANS UP WHITESPACE AT END OF ENTRIES

#    while pos < len(script):
#        while " \n" in script[pos] or "  " in script[pos]:
#            script[pos] = script[pos].replace(' \n','\n')
#            script[pos] = script[pos].replace('  ',' ')
#        print script[pos].replace('\n','')
#       pos += 1
#    print
    
    
# RETURNS CSV LIST OF LISTS OF STRING VALUES

    if cleanType == "default":
        listScript = []
        for line in script:
            listScript.append(line.split(","))
        listScript  = [item for item in listScript if len(filter(bool,item)) != 0]
        if listScript:
            return listScript
        else:
            return 'null'
        
        
# RETURNS CSV LIST OF STRING VALUES
    
    elif cleanType == "single line":
        return script[0].split(",")
    else:
        return script
  

# RETURNS SINGLE LINE FOLLOWING WORDS/ LINE NUMBER
    
def getLine(userName, __password, fileName, line, isPoly, polyScript):
    if __password == "null" and "https://docs.google.com" in fileName:
        
        publicData = getPublicFile(userName, fileName)
        isPrivate = False
        
    elif not isPoly:
        getFile(userName, __password, fileName)
        isPrivate = True
        publicData = []
    else:
        isPrivate = False
        publicData = polyScript
           
    __password = None
    
    return loadNClean(isPrivate, publicData, line, 0, "single line")      


# RETURNS SCRIPT/ VALUES BASED UPON PASSED LOADTYPE                  
            
def getScript(userName, __password, fileName, start, end, loadType, isPoly, polyScript):
    if __password == "null" and "https://docs.google.com" in fileName:
        
        publicData = getPublicFile(userName, fileName)
        isPrivate = False
        
    elif not isPoly:
        getFile(userName, __password, fileName)
        isPrivate = True
        publicData = []
    else:
        isPrivate = False
        publicData = polyScript
        
    __password = None

    return loadNClean(isPrivate, publicData, start, end, loadType)            
    
    
if __name__ == '__main__':
    getScript (sys.argv[1], sys.argv[2], sys.argv[3])
    sys.argv[3]= None
