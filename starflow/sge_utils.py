import BeautifulSoup
import re
SGE_STATUS_INTERVAL = 5
SGE_EXIT_STATUS_PATTERN = re.compile('exit_status[\s]*([\d])')
import tempfile
from starflow import exception
import os

def wait_and_get_statuses(joblist):

    f = tempfile.NamedTemporaryFile(delete=False)
    name = f.name
    f.close()
    
    jobset =  set(joblist)
    
    statuses = []
    while True:
        os.system('qstat -xml > ' + name)
        Soup = BeautifulSoup.BeautifulStoneSoup(open(name))
        running_jobs = [str(x.contents[0]) for x in Soup.findAll('jb_job_number')]
        if jobset.intersection(running_jobs):
            time.sleep(SGE_STATUS_INTERVAL)
        else:
            break
    
    
    for job in jobset:
        e = os.system('qacct -j ' + job + ' > ' + name)
        if e != 0:
            time.sleep(20)
        os.system('qacct -j ' + job + ' > ' + name)
        s = open(name).read()      
        try:
            res = SGE_EXIT_STATUS_PATTERN.search(s)
            child_exitStatus = int(res.groups()[0])
            statuses.append(child_exitStatus)
        except:
            raise exception.QacctParsingError(job,name)
        else:
            pass
    
    os.remove(name)
    return statuses
