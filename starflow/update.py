#!/usr/bin/env python
'''
Functions for automatic updating of data in the Data Environment by calling 
scripts indicated by data dependency links. 
    
The basic flow of information is that the functions in this module are 
fed by data produced by the functions from the module 
System.LinkManagement module.  Specifically, LinkManagement functions
(like GetLinksBelow) generate sequences of data dependency links 
representing progations up or downward in the directed acyclic graph
formed by the set of all Data Dependency links.  These functions 
can be passed parameters that have them qualify the links they return 
by timestamps to show only those links that actually _need_ updating, 
or be unqualified and actually show the full down- or upstream propagations. 

The data dependency link sequences come in the following form:

    [L1, L2, L3 ... , LN]

where each LI is (essentially) a numpy record array of dependency 
links meant to be called at stage i of an update -- because things at 
stage i-1 are input dependencies to things at stage i, which are in turn 
inputs to things at stage i + 1.   Within the LI, the records links 
represented (essentially) as:

    (Source,Target,Script)

where "Script" is the procedure that needs to be called to produce
Target from Source. 

Once the sequences of links are returned to functions here, the 
UpdateLInks function calls the scripts indicated by these links,
in the rounds indicated by the sequence. 

There are two basic approaches to automatic updating that are 
supported by the routines provided here.

1) "Downstream Updating," in which the user asks the system to detect 
changes have been made, either to data or scripts, since an update was 
last run, and then propagate the results of these changes downstream 
through the data dependency graph.  This functionality is implemented
by the "FullUpdate" function. 
    
2) "Upstream Updating," in which the user specifies a target or set of
targets that he wishes to remake; then the system determines which 
upstream elements have been modified since the last creation of the 
target, and runs those that need updating in the proper order.  This 
functionality -- which is similar in spirit to the traditional "makefile" 
commands available for many code-compilation schemes -- is
implemented by the "MakeUpdated" function. 

The "FindOutWhatWillUpdate" function displays what scripts will be 
called, given various options to the updater, without actually calling
any updates. 

The user can blend the two updating styles along a seemless
continuum.  The is done is via Automatic Updates filtering.  The 
user specifies in a configuration file (whose path is set at the 
AutomaticUpdatesPath environment variable) those scripts or 
script-name patterns that should or should not be updated upon
downstream propation.  Then, when calling a MakeUpdated command
to a set of targets, Upstream changes are included, as well as 
downstream propagations from those upstream changes that are 
allowed by the Automatic Updates settings.   

The advantage of Downstream Updating is that it does not require 
the user to think about the implications of the changes he's making: 
he merely makes changes to data and scripts, and then calls FullUpdate,
regardless of what the changes were; he does not have to remember 
which files the changes are bound to affect and then make sure 
those are updated.  On the other hand, this style of updating means 
that the user ends up having to modify the "Automatic Updates" 
settings occasionally to prevent unwanted updates from occuring, 
as well to enable wanted updates to actual happen.  It also means 
that he often will want to call "FindOutWhatWillUpdate" before 
"FullUpdate" to make see ahead of time to see which unwated
automatic updates (if any) he may have to disable.    Downstream
Update "purists" will typically want to set the "Automatic Updates"
file to enable updating of most of what they're working on at any
given period, and then only call the two commands "FindOutWhatWillUpdate"
and "FullUpdate" repeatedly. 

The Upstream style has the advantage of being more targeted -- and 
requiring no interaction (if not wanted) with the automatic update 
settings.   The Upstream Update "purists" -- those for example who 
may be familiar with the idea of Makefiles and want to use that style
in the data analysis work -- will typically want to set the Automatic 
Updates setting to contain little or nothing, and then call 
MakeUpdated(Target) for whatever end-point target they ultimately 
want to keep updated. 

In either case, the user can _force_ updating by setting the Force options
to True (this is like the "make clean" option in make systems); or have
the system update just those things that the system thinks really need 
updating.   

'''

import os
import time
import sys
import inspect
import re
import subprocess
import traceback
import cPickle as pickle

import numpy

import starflow.de as de
from starflow.gmail import Gmail
from starflow.utils import *
from starflow.linkmanagement import *
from starflow.metadata import MakeRuntimeMetaData
from starflow.config import StarFlowConfig

nan = numpy.nan 


DE_MANAGER = de.DataEnvironmentManager()
PATH_TO_PYTHON = DE_MANAGER.python_executable
DEFAULT_CALLMODE = DE_MANAGER.default_callmode
WORKING_DE = DE_MANAGER.working_de


# places for runtime temporary things -- should be configurable based on updating engine
TEMPFOLDER = WORKING_DE.tmp_dir
SsIDFile = os.path.join(TEMPFOLDER,'ssid')   #session id

RUNTIMESTORAGE = os.path.join('Storage','RuntimeStorage') # old creates go here so they are not over-written
RUNSTDOUT = 'MostRecentRun'                     # stdout is stored here
RUNSTDOUTINSESSION = RUNSTDOUT + ".InSession"   # in-session stdout/err produced by executed things
RUNTEMPOUTPUT = 'RUNTEMP'                       # pickled output before sent to metadata 
TEMPCMDFILE = 'CMDTEMP'                         # file storing command for DRMAA
TEMPMETAFILE='METATEMP'                         # metadata (e.g. resource-usage) for each job
                                                # used by the updater
ARCHIVE_DIR = WORKING_DE.archive_dir

try:
    import drmaa
except ImportError:
    print("DRMAA not available")
else:
    print("DRMAA loaded")

def SetupRun(creates=(WORKING_DE.relative_archive_dir,WORKING_DE.relative_tmp_dir)):

        
    SsID = GetSessionID()
    SsName=str(SsID)
    SsTemp = os.path.join(TEMPFOLDER, SsName + '/')
    MakeDir(SsTemp)

    SsRTStore = SsTemp + RUNTIMESTORAGE
    if not PathExists(SsRTStore):
        MakeDirs(SsTemp + RUNTIMESTORAGE)       
        
    TempStdOut = SsTemp + RUNSTDOUT     
    if PathExists(TempStdOut):
        delete(TempStdOut)  
    
    return [SsID,SsName,SsTemp,SsRTStore,TempStdOut]


def GetSessionID():
    if not PathExists(TEMPFOLDER):
        MakeDir(TEMPFOLDER)
    if not PathExists(SsIDFile):
        F = open(SsIDFile,'w')
        F.write('0')
        F.close()
        return 0
    else:
        F = open(SsIDFile,'a+b')
        F.seek(0)
        N = F.read().strip().strip(',').split(',')
        if N != ['']:
            SsID = max([int(x) for x in N]) + 1
            F.write(',' + str(SsID))
            F.close()
            return SsID
        else:
            F.write('0')
            F.close()
            return 0    
        
    
def ReleaseSessionID(idn):
    if PathExists(SsIDFile):
        N = open(SsIDFile,'r').read().strip().strip(',').split(',')
        if str(idn) in N:
            N.remove(str(idn))
            F = open(SsIDFile,'w')
            F.write(','.join(N))
            F.close()
        

def MakeUpdated(Targets,Exceptions = None, Simple = True, Forced = False,
                       Pruning=True,ProtectComputed = False,EmailWhenDone=None,
                   CallMode=DEFAULT_CALLMODE,depends_on = WORKING_DE.relative_root_dir):    
    '''
    Implements the upstream updating style 
    
    ARGUMENTS:
    --Targets = List of targets to update upstream from
    --Simple = if true, look for changes just at the top level of declared 
        dependencies (e.g. modifitions to the directories named in the
        dependency lists);  otherwise, look for changes below (in the 
        file-system sense of "below") these top-level dependency path names 
    --Forced = rebuild the entire upstream tree, regardless of what 
        appears to be need rebuilding to handle changes. 
    --ProtectComputed = rebuilding downstream things that appear to 
        have changed since their last official build and therefore (might be)
        corrupted.
    --EmailWhenDone = email address to send report of system update to,
        upon completion (including error reports of scripts that fail)
        
    '''
    
    USL = UpstreamLinks(Targets)
    USFs = uniqify(USL['SourceFile'].tolist() + USL['LinkSource'].tolist())
    if Exceptions is None:
        Exceptions = []
    Exceptions += list(set(USL['UpdateScript']).difference(['None']))
    LinkUpdate(USFs, Exceptions = Exceptions, Simple =Simple, Forced=Forced,Pruning=Pruning,ProtectComputed=ProtectComputed,EmailWhenDone=EmailWhenDone,CallMode=CallMode)


def FullUpdate(Seed = ['../'],AU = None,Exceptions = None,Simple = True,Forced=False,Pruning=True,ProtectComputed = False,EmailWhenDone=None,CallMode=DEFAULT_CALLMODE):    
    '''
    Implements the downstream updating style.
    
    ARGUMENTS:
    --Seed = set of initial targets to go downstream from.  
    --Simple = if true, look for changes just at the top level of declared 
        dependencies (e.g. modifitions to the directories named in the
        dependency lists);  otherwise, look for changes below (in the
        file-system sense of "below") these top-level dependency path names
    --Forced = rebuild the entire upstream tree, regardless of what appears 
        to be need rebuilding to handle changes. 
    --ProtectComputed = rebuilding downstream things that appear to 
        have changed since their last official build and therefore 
        might be corrupted.
    --EmailWhenDone = email address to send report of system update to,
        upon completion (including error reports of scripts that fail)
    '''
    if isinstance(Seed,str):
        Seed = Seed.split(',')
    LinkUpdate(Seed, AU = AU, Exceptions = Exceptions, Simple = Simple,Forced=Forced,Pruning=Pruning,ProtectComputed = ProtectComputed,EmailWhenDone=EmailWhenDone,CallMode=CallMode)


def FindOutWhatWillUpdate(Seed = ['../'], AU = None, Exceptions = None, Simple = True, Forced = False, Pruning=True,ProtectComputed = False):
    '''
    Determine and print out readable report indicating which files 
    downstream of a seed will update (without making the actual update). 
    
    ARGUMENTS:
    --Seed = set of initial targets to go downstream from.  
    --Simple = if true, look for changes just at the top level 
        of declared dependencies (e.g. modifitions to the directories named
        in the dependency lists);  otherwise, look for changes below (in 
        the file-system sense of "below") these top-level dependency path names
    --Forced = act as if rebuilding the entire upstream tree, regardless of what 
        appears to be need rebuilding to handle changes. 
    --ProtectComputed = include downstream things that appear to have 
        changed since their last official build and therefore might be corrupted.
    '''
    ScriptsToCall = WhatWillUpdate(Seed, AU = AU, Exceptions=Exceptions, Simple=Simple, Forced=Forced, Pruning=Pruning,ProtectComputed=ProtectComputed)
    if len(Union(ScriptsToCall)) > 0:
        print '\nThe system would call the following operations, in ' + str(len([l for l in ScriptsToCall if len(l) > 0])) + ' round(s):\n' + printscriptrounds(ScriptsToCall)
    else:
        print '\nNothing would be called.'

def WhatWillUpdate(Seed = ['../'], AU = None, Exceptions = None, Simple = True, Forced = False, Pruning=True,ProtectComputed = False):
    if isinstance(Seed,str):
        Seed = Seed.split(',')
    ActivatedLinkListSequence = GetLinksBelow(Seed, AU = AU, Exceptions = Exceptions , Forced=Forced , Simple = Simple, Pruning=Pruning,ProtectComputed = ProtectComputed)
    ScriptList = [set(l['UpdateScript']) for l in ActivatedLinkListSequence]
    ScriptsToCall = ReduceListOfSetsOfScripts(ScriptList)
    return ScriptsToCall
    

def LinkUpdate(Seed,AU = None, Exceptions = None,Simple=False,Forced = False,
                 Pruning = True,ProtectComputed = False,EmailWhenDone = None,
CallMode=DEFAULT_CALLMODE,depends_on=WORKING_DE.relative_root_dir,creates = WORKING_DE.relative_config_dir):    
    '''
    Given a seed and some options, call GetLinksBelow routine from LinkManagement, 
    and feed the result of that to the automatic updater. 
    
    This function is not usually called directly, but is called with arguments 
    set by either MakeUpdated or FullUpdate. 
    
    ARGUMENTS:
    --Seed = set of initial targets to go downstream from.  
    --Simple = if true, look for changes just at the top level of declared 
        dependencies (e.g. modifitions to the directories named in the 
        dependency lists);  otherwise, look for changes below (in the file-system 
        sense of "below") these top-level dependency path names
    --Forced = act as if rebuilding the entire upstream tree, regardless of what appears 
        to be need rebuilding to handle changes. 
    --ProtectComputed = include downstream things that appear to have changed 
    since their last official build and therefore (might be) corrupted.     

    '''
    if isinstance(Seed,str):
        Seed = Seed.split(',')
    ActivatedLinkListSequence = GetLinksBelow(Seed, AU = AU, Exceptions = Exceptions , Forced=Forced , Simple = Simple, Pruning=Pruning,ProtectComputed = ProtectComputed)
    UpdateLinks(ActivatedLinkListSequence,Seed,AU = AU, Exceptions = Exceptions,Simple=Simple,Pruning=Pruning,Forced=Forced,ProtectComputed = ProtectComputed,EmailWhenDone=EmailWhenDone,CallMode=CallMode)

     
def UpdateLinks(ActivatedLinkListSequence, Seed, AU = None, Exceptions = None, 
                 Simple=None,Pruning=None,Forced=None,ProtectComputed = False, 
  EmailWhenDone = None,CallMode=DEFAULT_CALLMODE,depends_on=WORKING_DE.relative_root_dir,
  creates = WORKING_DE.relative_config_dir):    
    ''' This function is the main driver of automatic updating in the system.  It takes in a
    sequence of sets of links, and applies the scripts indicated by those links in the 
    proper order.  If possible, it saves previous outputs of these scripts in a safe 
    place so that if a script fails, the previous output can be reverted to.  It 
    keeps track of success or failure along the way, and if failure occurs,
    downstream updates are cancelled.   It also has a built-in diff-checker, 
    so that if outputs of a given script are not different from previous runs, 
    downstream files are merely touched (i.e., have their timestamps updated) 
    but not recomputed.  
    
    This function is not usually called directly by the user, but instead with its 
    arguments et by LinkUpdate. 
    
    Arguments:
    --ActivatedLinkListSequence -- a sequence of recarrays of 
        links (as produced, e.g. by GetLinksBelow).  
    --Seed:  the original files updates to which set off the linklist activation.  
        This is used for recomputing when failure or no difference occurs. 
                
    '''

    ScriptsToCall = ReduceListOfSetsOfScripts([set(l['UpdateScript']) for l in ActivatedLinkListSequence]) 
    
    if len(Union(ScriptsToCall)) > 0:
    
        [SsID,SsName,SsTemp,SsRTStore,TempStdOut] = SetupRun()
        sys.stdout = multicaster(TempStdOut,sys.__stdout__,New=True)
        print '\nThe system is planning to call the following operations, in ' + str(len([l for l in ScriptsToCall if len(l) > 0])) + ' round(s):\n' + printscriptrounds(ScriptsToCall)
        print 'Output during the run will be stored in', SsTemp
        RemainingLinkList = numpy.rec.fromrecords(uniqify(ListUnion([l.tolist() for l in ActivatedLinkListSequence])), names = ActivatedLinkListSequence[0].dtype.names)   
        RemoveScriptsToBeCreated(RemainingLinkList,ScriptsToCall)
        [CreateDict,IsFastDict] = GetCreatesAndIsFast(RemainingLinkList)
        DepList = numpy.array(uniqify(RemainingLinkList[RemainingLinkList['LinkType'] == 'DependsOn']['LinkSource']))
        TouchList = set([])  
        Round = 0
        TotalNoDiff = {}
        NewlyCreatedScripts = set([])
        MetaDataObject = []

        for J in ScriptsToCall:  #for each "round" of scripts to call,  
    
            if len(J) > 0:
                print 'Calling round', Round, '... '
                ToRemove = []  
                NoDiff = {}
                ResourceUsageDict = {}
        
                DepListJ = dict([(k,DepList[getpathalongs(numpy.array(CreateDict[k]),DepList)]) for k in J])

                if CallMode == 'DIRECT':
                    for (i,j) in enumerate(J):
                        
                        DoOp(i,j,SsName,SsTemp,SsRTStore,CreateDict[j],IsFastDict[j],CallMode,TouchList,DepListJ[j].tolist(), EmailWhenDone)
                        ResourceUsageDict[j] = {}
                        HandleChildJobs(j,SsTemp,EmailWhenDone,SsName,SsRTStore,IsFastDict[j],CallMode)
                
                elif CallMode == 'DRMAA':
                    Session = drmaa.Session()
                    Session.initialize()
                    
                    jobids = {}
                    for (i,j) in enumerate(J):
                        jt = Session.createJobTemplate()
                        jt.remoteCommand = PATH_TO_PYTHON
                        jt.workingDirectory = os.getcwd() 
                        argstr = "from starflow.production import *; import starflow.update as U ; U.DoOp(" + ",".join([repr(x) for x in [i,j,SsName,SsTemp,SsRTStore,CreateDict[j],IsFastDict[j],CallMode,TouchList,DepListJ[j].tolist(), EmailWhenDone]]) + ")"
                        jt.args = ["-c",argstr]
                        jt.joinFiles = True
                        jt.jobEnvironment = dict([(k,os.environ[k]) for k in ['PYTHONPATH','PATH'] if k in os.environ])
                        TempSOIS = os.path.join(SsTemp , RUNSTDOUTINSESSION + '_' + j)
                        jt.outputPath = ':' + TempSOIS
                        jt.jobName = j
                        jobids[j] = Session.runJob(jt)
                        print 'Loading job', j , 'with job id', jobids[j]
                        
                    for j in jobids.keys():
                        retval = Session.wait(jobids[j],drmaa.Session.TIMEOUT_WAIT_FOREVER)
                        print 'Job', j, 'returned.'
                        ResourceUsageDict[j] = retval.resourceUsage 
                
                        HandleChildJobs(j,SsTemp,EmailWhenDone,SsName,SsRTStore,IsFastDict[j],CallMode)
                        
                        #TODO:  make resource usage reflect child jobs if any
                    
                    Session.exit()  


                for (i,j) in enumerate(J):
                    TempSOIS = SsTemp + RUNSTDOUTINSESSION + '_' + j
                    InSessionStdOutToStdOut(TempSOIS,TempStdOut)
                    TempMetaFile = SsTemp + TEMPMETAFILE + '_' + j
                    if PathExists(TempMetaFile):
                        MetaData = pickle.load(open(TempMetaFile,'r'))
                        NewlyCreatedScripts.update(MetaData['NCS'])
                        NoDiff.update(dict([(f,MetaData['OriginalTimes'][f]) for f in MetaData['IsDifferent'].keys() if not MetaData['IsDifferent'][f]]))
                        if MetaData['ExitType'] == 'Failure':
                            ToRemove.append(j)

                RemainingLinkList = RemoveDownstreamOfFailures(RemainingLinkList,ScriptsToCall,Round,ToRemove,Seed,Simple,Pruning,ProtectComputed)          
                RemainingLinkList = MakeTouchList(RemainingLinkList,ScriptsToCall,TouchList,TotalNoDiff,NoDiff,Seed,Simple,Pruning,ProtectComputed)
                Round += 1
            else:
                Round += 1
        
        if len(NewlyCreatedScripts) > 0:
            print '\n\nDuring the update just completed, the following python operation files were either created newly or overwritten:\n\n', NewlyCreatedScripts, '\n\nThe system will now perform an update on these scripts.\n\n'

            LinkUpdate(list(NewlyCreatedScripts) + Seed, AU = AU, Exceptions = Exceptions,Simple=Simple,Pruning=Pruning,Forced=Forced,ProtectComputed = ProtectComputed,EmailWhenDone = EmailWhenDone,CallMode=CallMode)
    
        sys.stdout = sys.__stdout__
        
        EmailResults(EmailWhenDone,SsName,TempStdOut)
            
        ReleaseSessionID(SsID)

    else:
        print "No scripts to be called."
        
    sys.stdout = sys.__stdout__


def DoOp(i,j,SsName,SsTemp,SsRTStore,CreatesList,IsFast,CallMode,TouchList,DepListj, EmailWhenDone,creates = WORKING_DE.relative_root_dir):

    Creates = CreatesList

    Targets = uniqify(Creates + DepListj)

    NewlyCreatedScripts = set([])
    IsDifferent = dict([(jj,False) for jj in Targets])
    
    [OriginalTimes,OrigDirInfo,TempSOIS,TempOutput,TempMetaFile] = SetupOp(j,Creates + DepListj,SsTemp) 
    ModName = '.'.join(j.split('.')[:-1]) ; OpName = j.split('.')[-1] ; ModDirName = '../' + '/'.join(j.split('.')[:-2])
    OldATime = os.path.getatime(ModDirName) ; OldMTime = os.path.getmtime(ModDirName)
    Command = GetCommand(j,ModName,OpName,TempSOIS,TempOutput,CallMode)
    
    if j not in TouchList: 
        MoveToTemp(Creates,IsFast,SsRTStore)        
                        
    if j not in TouchList:
        print '\n\nCalling ' , j, ', which makes ',  ','.join(Creates) , '...\n'
        Before = time.time()
        ExitStatus = os.system(PATH_TO_PYTHON + " -c " + Command)
        After = time.time()
        os.utime(ModDirName,(OldATime,OldMTime))
        RunOutput = pickle.load(open(TempOutput,'r')) if PathExists(TempOutput) else None   
        child_jobs = isinstance(RunOutput,dict) and RunOutput.get('child_jobs') 
        if not child_jobs:
            FinishUp(j,ExitStatus,RunOutput,Before,After,Creates,DepListj,OriginalTimes,OrigDirInfo,TempSOIS,TempMetaFile,CallMode,EmailWhenDone,SsName,SsRTStore,IsFast)        
        else:
            RecordPendingStatus(ExitStatus,RunOutput,child_jobs,Before,After,Creates,DepListj,OriginalTimes,OrigDirInfo,TempSOIS,TempMetaFile)
    
    else:   
        ExitStatus = None
        RunOutput = None
        Before = time.time()
        After = Before
        print 'Just Touching outputs of', j, ':', Creates
        FinishUp(j,ExitStatus,RunOutput,Before,After,Creates,DepListj,OriginalTimes,OrigDirInfo,TempSOIS,TempMetaFile,CallMode,EmailWhenDone,SsName,SsRTStore,IsFast)


def HandleChildJobs(j,SsTemp,EmailWhenDone,SsName,SsRTStore,IsFast,CallMode):
    TempMetaFile = os.path.join(SsTemp , TEMPMETAFILE + '_' + j)
    if PathExists(TempMetaFile):
        MetaData = pickle.load(open(TempMetaFile,'r'))
        child_jobs = MetaData.get('child_jobs')
        
        if child_jobs:
            print('... but found child jobs', child_jobs, 'so now waiting for those...')
            ExitStatus = MetaData['ExitStatus']
            
            statuses = wait_and_get_statuses(child_jobs)
            if not all([ces == 0 for ces in statuses]):
                ExitStatus = -1
            
            FinishUp(j,ExitStatus,MetaData['RunOutput'],
                                MetaData['Before'],
                                MetaData['After'],
                                MetaData['Creates'],
                                MetaData['DepListj'],
                                MetaData['OriginalTimes'],
                                MetaData['OrigDirInfo'],
                                MetaData['TempSOIS'],
                                TempMetaFile,CallMode,
                                EmailWhenDone,
                                SsName,SsRTStore,IsFast,
                                child_jobs = child_jobs)

import BeautifulSoup
import re
SGE_STATUS_INTERVAL = 5
SGE_EXIT_STATUS_PATTERN = re.compile('exit_status[\s]*([\d])')
import tempfile
from starflow import exception

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

def FinishUp(j,ExitStatus,RunOutput,Before,After,Creates,DepListj,OriginalTimes,OrigDirInfo,TempSOIS,TempMetaFile,CallMode,EmailWhenDone,SsName,SsRTStore,IsFast,child_jobs = None):

    Targets = uniqify(Creates + DepListj)

    NewlyCreatedScripts = set([])
    IsDifferent = dict([(jj,False) for jj in Targets])
    
    if ExitStatus == None:
        ExitType = 'Touch'  
        for f in Creates:
            if PathExists(f):                   
                os.utime(f,(FindAtime(f),max(FindMtime(f),Before)))     
                
    else:  
        TrueSuccess = (ExitStatus == 0) and all([PathExists(f) for f in Creates])
        
        if not TrueSuccess:  
            ExitType = 'Failure'
            printfailuremessage(j,Creates,ExitStatus)               
            MoveOutGarbage(Creates,SsRTStore)
            RevertToOldFiles(Creates,SsRTStore,IsFast,OrigDirInfo)                      
            
        else:  
            ExitType = 'Success'
            printsuccessmessage(j,Creates)
            for f in Creates:
                os.utime(f,(FindAtime(f),max(FindMtime(f),Before)))  
            NewlyCreatedScripts.update(set(ListUnion([[path for path in RecursiveFileList(f) if path.split('.')[-1] == 'py'] for f in Creates])))
            CheckDiffs(j,Creates,SsRTStore,IsFast,RunOutput,IsDifferent,Targets)
            for g in OrigDirInfo.keys():
                if listdir(g) == OrigDirInfo[g][1]:
                    os.utime(g,(FindAtime(g),OrigDirInfo[g][0]))        
        
    MakeRuntimeMetaData(j,Creates,OriginalTimes,OrigDirInfo,RunOutput,ExitType,ExitStatus,Before,After,IsDifferent,TempSOIS)
    F = open(TempMetaFile,'w')
    TempMetaData = {'NCS':NewlyCreatedScripts,'OriginalTimes':OriginalTimes,'ExitType':ExitType,'IsDifferent':IsDifferent}
    
    if child_jobs:
        TempMetaData['child_jobs'] = child_jobs
    pickle.dump(TempMetaData,F) 
    F.close()
    
    print("FINISH UP",TempMetaFile,TempMetaData)
    
    if CallMode == 'DRMAA':
        EmailResults(EmailWhenDone,'Call to ' + j + ', run ' + SsName ,TempSOIS)
        


def RecordPendingStatus(ExitStatus,RunOutput,child_jobs,Before,After,Creates,DepListj,OriginalTimes,OrigDirInfo,TempSOIS,TempMetaFile):
    F = open(TempMetaFile,'w')
    TempMetaData = {'ExitStatus':ExitStatus,
                    'RunOutput':RunOutput,
                    'child_jobs':child_jobs,
                    'Before':Before,
                    'After':After,
                    'Creates':Creates,
                    'DepListj':DepListj,
                    'OriginalTimes':OriginalTimes,
                    'OrigDirInfo':OrigDirInfo,
                    'TempSOIS':TempSOIS,
                    'TempMetaFile':TempMetaFile
                    }
    pickle.dump(TempMetaData,F) 
    F.close()
    
def CheckDiffs(j,Creates,SsRTStore,IsFast,RunOutput,IsDifferent,Targets):
    
    for f in Creates:
        temp_name = redirect(f,SsRTStore)
        tset = [t for t in Targets if PathAlong(t,f)]
        for t in tset:  
            temp_path = temp_name if f == t else temp_name + ('/' if not temp_name.endswith('/') else '') + t[len(f):]
            if PathExists(temp_path):
                Differences = os.popen('diff -rq ' + temp_path + ' ' + t,'r').read()
                IsDifferent[t] = len(Differences) > 0
                if not IsDifferent[t]: 
                    print 'No differences were detected between the newly created version of', t, 'and the most recent previous version.' 
                
            elif IsFast and isinstance(RunOutput,dict) and 'Diffs' in RunOutput.keys() and t in RunOutput['Diffs'].keys() and RunOutput['Diffs'][t] == ():      
                print 'The fast algorithm', j , 'reported no differences between the newly created version of', t, 'and the most recent previous version.' 
            elif PathExists(t):
                IsDifferent[t] = True
        
        if PathExists(temp_name):
            TS = TimeStamp(FindMtime(temp_name)) #move stored version to archive if it hasn't already been moved
            archive_name = os.path.join(WORKING_DE.archive_dir,f[3:].replace('/','__') + TS)
            if not PathExists(archive_name):
                os.rename(temp_name,archive_name)

    return IsDifferent

def RevertToOldFiles(Creates,SsRTStore,IsFast,OriginalDirInfo):                 
    if not IsFast:  
        for f in Creates:
            temp_name = redirect(f,SsRTStore)
            if PathExists(temp_name):
                print 'Reverting to most recent previous versions of', f
                os.rename(temp_name,f)
        for g in OriginalDirInfo.keys():
            os.utime(g,(FindAtime(g),OriginalDirInfo[g][0]))    

def MoveOutGarbage(Creates,SsRTStore):
    for f in Creates: 
        if PathExists(f):
            temp_name = redirect(f,SsRTStore) 
            garbagename = (temp_name[:-1] if temp_name[-1] == '/' else temp_name) +  '_Garbage_' + TimeStamp(time.time())
            print 'Moving partially created output to', garbagename
            os.rename(f,garbagename)

def printsuccessmessage(op,Creates):
    print '... appears to have successfully run', op, ', creating' , ','.join(Creates)

def printfailuremessage(op,Creates,ExitStatus):
    UncreatedFiles = [f for f in Creates if not PathExists(f)]              
    FailureStatement = 'threw an exception during attempted execution (see above for details).' if ExitStatus != 0 else 'ran without throwing an exception, but for some reason the outputs ' + ', '.join(UncreatedFiles) + ' never got created.'
    print op , FailureStatement , 'System will consider this run a failure and (if possible) will revert to old versions of ' , ','.join(Creates) , '.  Downstream updates will be cancelled.'  

    

def InSessionStdOutToStdOut(TempStdOutInSession,TempStdOut):

    if PathExists(TempStdOutInSession):
        runstdtext = open(TempStdOutInSession,'r').read() 
    else:
        runstdtext = None
    if runstdtext:
        statement = 'During the run, the following output was printed to stdout and stderr:\n\n\n' + runstdtext +  '\n\n'
    else:
        statement = 'During the run, no output was written to stdout or stderr.\n\n'
    F = open(TempStdOut,'a')
    F.write(statement)
    F.close()


def GetCommand(j,ModuleName,OpName,TempStdOutInSession,TempOutput,CallMode=DEFAULT_CALLMODE):


    Commands = ["'import pickle,traceback",
            "creates = (\"" + TempStdOutInSession + "\",\"" + TempOutput + "\")", 
            "from starflow.production import *",
            "import starflow.utils",
            "sys.stdout = starflow.utils.multicaster(\"" + TempStdOutInSession + "\",sys.__stdout__)",
            "sys.stderr = starflow.utils.multicaster(\"" + TempStdOutInSession + "\",sys.__stderr__)",          
            "from " + ModuleName + " import " + OpName,
#           "exec \"V = " + OpName + "()",
            "try:\n\texec \"V = " + OpName + "()\"\nexcept:\n\ttraceback.print_exc()\n\traise Error",
            "F = open(\"" + TempOutput + "\",\"w\")", 
            "try:\n\tpickle.dump(V,F)\nexcept:\n\tprint \"Output of " + j + " cannot be pickled\"", 
            "F.close()'"]
    Command = '\n'.join(Commands)



    return Command

def MoveToTemp(Creates,IsFast,SsRTStore):
    for f in Creates: 
        temp_name = redirect(f,SsRTStore) 
        temp_name = temp_name[:-1] if temp_name[-1] == '/' else temp_name
        if PathExists(temp_name): 
            garbage_name = temp_name + '_OLD_' + TimeStamp(time.time())
            os.rename(temp_name,garbage_name)
        if PathExists(f) and not IsFast:  
            os.rename(f,temp_name)   
                

def SetupOp(j,CreateList,SsTemp,creates=WORKING_DE.relative_tmp_dir):
    OriginalTimes = {}
    OriginalDirInfo = {}    
    for f in uniqify(CreateList):
        OriginalTimes[f] = FindMtime(f) if PathExists(f) else nan           
        if PathExists(DirName(f)):
            OriginalDirInfo[DirName(f)] = (FindMtime(DirName(f)),listdir(DirName(f)))
    
    TempStdOutInSession = SsTemp + RUNSTDOUTINSESSION + '_' + j
    TempOutput = SsTemp + RUNTEMPOUTPUT  + '_' + j
    TempMetaFile = SsTemp + TEMPMETAFILE + '_' + j

    if PathExists(TempOutput):
        delete(TempOutput)
    if PathExists(TempMetaFile):
        delete(TempMetaFile)
            
    return [OriginalTimes,OriginalDirInfo,TempStdOutInSession,TempOutput,TempMetaFile]
    

def GetCreatesAndIsFast(RemainingLinkList):

    CreateLinks = RemainingLinkList[RemainingLinkList['LinkType'] == 'CreatedBy']
    s = CreateLinks['UpdateScript'].argsort();  CreateLinks = CreateLinks[s]
    changes = (CreateLinks['UpdateScript'][1:] != CreateLinks['UpdateScript'][:-1]).nonzero()[0]
    changes = numpy.append([-1],numpy.append(changes,[len(CreateLinks) - 1]))
    CreateDict = dict([(CreateLinks['UpdateScript'][changes[i]+1],uniqify(CreateLinks['LinkTarget'][changes[i]+1:changes[i+1]+1].tolist())) for i in range(len(changes)-1)])
    IsFastDict = dict([(CreateLinks['UpdateScript'][changes[i]+1],CreateLinks['IsFast'][changes[i]+1]) for i in range(len(changes)-1)]) 
    
    for j in CreateDict.keys():
        CreateDict[j].sort()
    
    return [CreateDict,IsFastDict]
    
    
def MakeTouchList(RemainingLinkList,ScriptsToCall,TouchList,TotalNoDiff,NoDiff,Seed,Simple,Pruning,ProtectComputed):

    if len(NoDiff) > 0:     
        TotalNoDiff.update(NoDiff)
        RemainingLinkList = RemainingLinkList[[i for i in range(len(RemainingLinkList)) if RemainingLinkList['LinkSource'][i] not in NoDiff.keys()]]    
        R = RemainingLinkList[RemainingLinkList['LinkType'] != 'Dummy']
        RemainingLinkListSequence = [ll[ll['Activated']] for ll in PropagateThroughLinkGraphWithTimes(Seed,R, Simple=Simple,Pruning=Pruning,ProtectComputed = ProtectComputed)]     
        TouchList.update(Union(ScriptsToCall).difference(Union([set(l['UpdateScript']) for l in RemainingLinkListSequence])))

        
    return RemainingLinkList
    

def RemoveDownstreamOfFailures(RemainingLinkList,ScriptsToCall,Round,ToRemove,Seed,Simple,Pruning,ProtectComputed):
    if len(ToRemove) > 0:       
        TTT = numpy.array(ToRemove)
        TTT.sort()
        RemainingLinkList = RemainingLinkList[numpy.invert(fastisin(RemainingLinkList['UpdateScript'],TTT))]
        RemainingLinkListSequence = [ll[ll['Activated']] for ll in PropagateThroughLinkGraphWithTimes(Seed,RemainingLinkList,Simple=Simple,Pruning=Pruning,ProtectComputed = ProtectComputed)]
        RemainingScripts = Union([set(l['UpdateScript']) for l in RemainingLinkListSequence])
        ScriptsToRemove = Union(ScriptsToCall).difference(ToRemove).difference(RemainingScripts)
        for JJ in ScriptsToCall[Round+1:]:
            for kk in ScriptsToRemove:
                if kk in JJ:
                    JJ.remove(kk)
                    print 'Removing call to script', kk, 'due to failure of at least one of the scripts:', ToRemove 
                    
    return RemainingLinkList
    
    
def EmailResults(EmailWhenDone,SsName,FileName):

    account = WORKING_DE.gmail_account_name
    password =  WORKING_DE.gmail_account_passwd
    EmailList = [account + '@gmail.com']
    if isinstance(EmailWhenDone,str):
        EmailWhenDone = EmailWhenDone.split(',')
    if EmailWhenDone:
        EmailList += EmailWhenDone 
    if EmailList:
        try:
            Gmail(account,password,EmailList,subject = WORKING_DE.name + ' Run ID#: ' + SsName, FileName=FileName)
        except:
            print 'No email sent.'
            traceback.print_exc()
            

def RemoveScriptsToBeCreated(TotalLinkList,ScriptsToCall):
    TotalLinkList.sort(order=['UpdateScriptFile'])
    T = TotalLinkList.copy();   T = T[T['LinkType'] == 'CreatedBy'];  T.sort(order=['TargetFile'])
    [A,B] = getpathalong(T['TargetFile'],TotalLinkList['UpdateScriptFile'])
    BadLines = ListUnion([range(A[i],B[i]) for i in range(len(A))])
    BadSeedScripts = list(set(TotalLinkList[BadLines]['UpdateScript']).difference(['None']))                        
    if len(BadSeedScripts) > 0:
        P = PropagateThroughLinkGraph(BadSeedScripts,TotalLinkList)
        BadScripts = list(set(ListUnion([l['UpdateScript'] for l in P])).difference(['None']))
        print 'Calls to the following scripts will be cancelled because they are automatically generated python .py files and they\'re about to be overwritten:\n', BadScripts, '\n' 
        for JJ in ScriptsToCall:
            for kk in BadScripts:
                if kk in JJ:
                    JJ.remove(kk)   

def printscriptrounds(ScriptsToCall):
    S = [list(l) for l in ScriptsToCall if len(l) > 0]
    RoundStartLines = ['------------------------------Round ' + str(i+1) + '----------------------------------\n' for i in range(len(S))]
    RoundEndLines = ['\n------------------------------End Round ' + str(i+1) + '------------------------------\n' for i in range(len(S))]
    
    return '\n'.join([RoundStartLines[i] + '\n'.join(S[i]) + RoundEndLines[i] for i in range(len(S))])
