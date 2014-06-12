import nltk
import csv
import sys
import unicodedata
import pandas as pd

import nltk.classify.util
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.corpus import stopwords

#Analys Methods from: 
#http://www.slideshare.net/ogrisel/nltk-scikit-learnpyconfr2010ogrisel#btnPrevious
#http://streamhacker.com/2010/05/10/text-classification-sentiment-analysis-naive-bayes-classifier/
#n-gram generation
#http://locallyoptimal.com/blog/2013/01/20/elegant-n-gram-generation-in-python/

textColumn = 'text'
categoryColumn = 'check1'
defaultFile = 'NLTK_Ready_Tweets.csv'
classMode = 'naive bayes'
degreesToUse = [1,2,3,4]
cutoff = .75
#resultKey = {1:"no suspicion of infectious illness",2:"suspicion of infectious illness, type unknown",3:"suspicion of infectious GI illness"}
resultKey = {1:"Category 1",2:"Category 2",3:"Category 3"}



def stripUnicode(text):
    """Strips unicode special characters for text storage (smileys, etc)"""
    if text == None:
        return "NaN"
    else:
        if type(text) == unicode:
            return str(unicodedata.normalize('NFKD', text).encode('ascii', 'ignore'))
        else:
            return text

def loadFile(text):
    outPut = []
    if text == "null":
        text = defaultFile
    try:
        if type(text) is list:
            fileIn = open(text[1],'rU')
        else:
            fileIn = open(text,'rU')
    except:
        fileIn = open(defaultFile,'rU')
    
    loaded = pd.read_csv(fileIn)
    
    for pos in loaded.index:
        outPut.append({'text': loaded[textColumn][pos], 'category': loaded[categoryColumn][pos]})
    
    print "Loaded",len(outPut),"entries"
    return outPut
    

def lemList(listed):
    lmtzr = WordNetLemmatizer()
    listed = [word for word in listed if len(word)>1]
    for pos in range(len(listed)):
        listed[pos] = lmtzr.lemmatize(listed[pos])
        
    
def prepText(content):
    for pos in range(len(content)):
        content[pos]['text'] = prepTweet(content[pos]['text'])
    return content
        
        
def prepTweet(word):
    
    word =  stripUnicode(word)
    original = text = str(word).lower() #switch to lowercase
        
    text = text.replace("&amp",'&') #cleanup conversion bug
    
    punctuations = ".,\"-_%!=+\n\t:;()*&$"
    
    """for char in punctuations:
        text = text.replace(char,' ')
    while '  ' in text:
        text = text.replace('  ',' ')
    while text.startswith(' '):
        text = text[1:]
    while text.endswith(' '):
        text = text[:-1]"""
    
    #Remove accentuated characters
    text = unicode(text)
    text = ''.join(char for char in unicodedata.normalize('NFD', text) if unicodedata.category(char) != 'Mn')
        
    #End of string operations, continuing with list ops.    
    listed = text.split(' ')
    
    for pos in range(len(listed)):
        if not listed[pos].startswith('http'):
            for char in punctuations:
                text = listed[pos].replace(char,' ')
                while '  ' in text:
                    text = text.replace('  ',' ')
                while text.startswith(' '):
                    text = text[1:]
                while text.endswith(' '):
                    text = text[:-1]
            listed[pos] = text
        
    if "@" in original: #track presence of conversations but remove screen names
        listed = [word for word in listed if '@' not in word]
        listed.append('@user')
        
    lemList(listed) #Lemmatize list to common stem words
    
    stop = stopwords.words('english') #Remove stopwords, common words of little relevance
    listed = [word for word in listed if word not in stop]  
    
    return listed
    
        
def prepClassifications(content):
    classifications = set()
    totals = dict()
    prepped = dict()
    
    for entry in content:
        category = entry['category']
        classifications.add(category)
        if category not in totals.keys():
            totals[category] = 0
        totals[category] += 1
        
    print "Unique classifications found:",classifications 
    print "Occurrences:", totals
        
    prepped = dict()
    for classification in classifications:
        prepped[classification] = [entry for entry in content if entry['category'] == classification]
    return prepped
    
    
def getNGrams(listed, degreesUsed):
    NGrams = dict()
    for degree in degreesUsed:
        NGrams.update(dict([(ngram, True) for ngram in zip(*[listed[i:] for i in range(degree)])]))
    return NGrams
    
    
def collectNGrams(categorized, degreesUsed):
    collected = dict()
    for key in categorized.keys():
        collected[key] = [(getNGrams(entry['text'], degreesUsed),entry['category']) for entry in categorized[key]]
    return collected
                                             
 
def classifySingle(text, classifier):
    temp = getNGrams(prepTweet(text),degreesToUse)
    result = classifier.classify(temp)
    if __name__ == '__main__':
        print "Query:", text
        try:
            print "Result:", resultKey[result]
        except:
            print "Result:", result
    return str(result)
     
def getClassifier(tweetfile):
    print "Loading content & preparing text"
    content = prepText(loadFile(tweetfile))
    print "Categorizing contents"
    categorized = prepClassifications(content)
    print "Deriving NGrams"
    NGrammized = collectNGrams(categorized,degreesToUse)
    print "Compiling Results"
    readyToSend = []
    for category in NGrammized.keys():
        readyToSend += NGrammized[category]
        
    print "Attempting Classification"
    if classMode == 'naive bayes':
        from nltk.classify import NaiveBayesClassifier
        classifier = NaiveBayesClassifier.train(readyToSend)
    elif classMode == 'max ent':
        from nltk.classify import MaxentClassifier
        classifier = MaxentClassifier.train(readyToSend)
        
    print
    classifier.show_most_informative_features(n=200)
    classifier.show_most_informative_features()
    return classifier

def main(tweetfile):
    testMode = False
    try:
        if sys.argv[1] == 'test':
            testMode = True
    except:
        testMode = False
        
    classifier = getClassifier(tweetfile)
    
    if testMode:
        print "\nInitiating testing mode\n"
        while True:
            query = str(raw_input("Please enter a test sentence: \t"))
            if query.lower() == 'quit':
                quit()
            classifySingle(query, classifier)


if __name__ == '__main__':
    main(sys.argv[2])
