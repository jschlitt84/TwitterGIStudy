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