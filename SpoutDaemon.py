import subprocess
import time

try:
    fileIn = open(sys.argv[1])
except:
    fileIn = open('gdiAccounts')

urls = set()
delay = 1200

content = fileIn.readlines()

print "Loading URL list"

for line in content:
    if '.url=' in line.replace(' ',''):
        urls.add(line[line.index('https://'):-1])
        
print "GDI URLS:", urls

while True:
    running = set()
    ps = subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE).communicate()[0]
    processes = ps.split('\n')
    
    for process in processes:
        if 'python' in process:
            for url in urls:
                if url in process:
                    foundUrl = process[process.index('https://'):]
                    print "RUNNING:",foundUrl
                    running.add(foundUrl)
    
    notRunning = set.difference(urls,running)
    print "\nNOT RUNNING:", notRunning
    print "'"+url+"'"
    for url in notRunning:
        subprocess.Popen(['python','TwitterSpout.py', url])
        None
    time.sleep(delay)