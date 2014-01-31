import subprocess
import time

format = "\033[91m\033[1m"
end = "\033[0m"

while True:
    try:
        fileIn = open(sys.argv[1])
    except:
        fileIn = open('gdiAccounts')
    
    urls = set()
    delay = 1200
    
    content = fileIn.readlines()
    
    print format+"\n\n(Re)Loading URL list",end
    
    for line in content:
        if '.url=' in line.replace(' ',''):
            urls.add(line[line.index('https://'):-1])
        
    print format + "GDI URLS:", urls,end
    running = set()
    
    ps = subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE).communicate()[0]
    processes = ps.split('\n')
    
    print "\n"
    for process in processes:
        if 'python' in process:
            for url in urls:
                if url in process:
                    foundUrl = process[process.index('https://'):]
                    print format+"RUNNING:",foundUrl,end
                    running.add(foundUrl)
    
    notRunning = set.difference(urls,running)
    for item in notRunning:
        print format+"NOT RUNNING:",item.replace('\n',''),end
    print "\n"
    for url in notRunning:
        subprocess.Popen(['python','TwitterSpout.py', url])
        time.sleep(30)
        None
    time.sleep(delay)