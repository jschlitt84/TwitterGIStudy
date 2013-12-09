def checkTweet(conditions, qualifiers, exclusions, text):
  text = text.lower()
  foundCondition = False
  foundQualifier = False
  
  if "rt @" in text:
    type = "retweet"
  else:
    for word in exclusions:
      if word in text:
        return "excluded"
    for word in conditions:
      if word in text:
        foundCondition = True
        break
    for word in qualifiers:
      if word in text:
        foundQualifier = True
        break
    if foundCondition and foundQualifier:
      return "accepted"
    else:
      return "partial"
      
def cleanJson(json, keep):
    """print keep
    userInfo = []
    toDelete = []
    for pos in range(len(keep)):
        key = keep[pos]
        if "user['" in key:
            userInfo.append(key.replace("user['",'').replace(']',''))
            toDelete.append(pos)
    print "huzzah1"
    if toDelete != []:
        for pos in toDelete.reverse():
            del keep[pos]
    print "huzzah2"            
    for row in range(len(json)):
        json[row] = {key: json[row][key] for key in keep}
        print "huzzah3"
        if userInfo != []:
            for item in userInfo:
                json[row][item] = json[row]['user'][item]
        print json[row]"""
        