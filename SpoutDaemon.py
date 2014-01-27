import sys
import subprocess

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
        urls.add(line[line.index('https://'):]
        
print "GDI URLS:", urls

running = set()
#ps = subprocess.Popen(['ps', 'aux', '|', 'grep', 'python'], stdout=subprocess.PIPE).communicate()[0]
ps = subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE).communicate()[0]
processes = ps.split('\n')

for process in processes:
    if 'python' in process:
        for url in urls:
            if url in process:
                foundUrl = process[process.index('https://'):]
                print foundUrl
                running.add(foundUrl)