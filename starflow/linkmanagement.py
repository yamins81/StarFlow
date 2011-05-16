#!/usr/bin/env python
'''
    Functions that are used to extract and explore data dependency links.
    
    The basic idea is that:   
    -- Some of these functions _FIND_ user-made python modules 
    (e.g. the scripts written by the user to make data computations
    -- Some of these functions __ANALYZE__ user-made python modules 
        to determine what data dependency links they contain
    -- Some of these functions allow you to __EXPLORE__ 
        the dependency network described by these links 
    
'''

import os
import re
import traceback
import subprocess
import time
import numpy

from starflow.utils import *
from starflow.metadata import FindPtime
from starflow.storage import *
import starflow.de as de

DE_MANAGER = de.DataEnvironmentManager()
WORKING_DE = DE_MANAGER.working_de

isnan = numpy.isnan
nan = numpy.nan

def LinksFromOperations(FileList,Aliases = None, AddImplied = False, 
                        AddDummies = False, FilterInternal = True, 
                        FilterNEs = True, Recompute=False,
                        depends_on = WORKING_DE.relative_root_dir,
                        creates = WORKING_DE.relative_links_dir):

    '''
    Analyzes a set of python modules to find data dependency links present in the 
    modules.   Overall, this function does two things:  
    
    1) it writes out files that cache the links computed, and uses these cached 
        versions to increase speed when the function is called again;
    and
    
    2) it returns the list of links, as a numpy record array.  
        
    Arguments:
    --FileList = list of python modules to analyze, as a list of path strings. 
    --AddImplied = Boolean, which if True, adds implied links to the numpy array 
        that is returned 
    --AddDummies = Boolean, which if True, adds Dummy links to the numpy record 
        array that is returned 
    --FilterInteral = Filter returned list of links so that links between 
        files and modules that are not in FileList are removed. 
    --Recompute = Boolean which if True causes the system to ignore 
        cached LinkLists and recompute everything from scratch.
        
    Returns:
        A
    where A is a numpy array describing the LinkList 
    '''

    #load up cached linklists
    
    STORED_LINKS_FILE = os.path.join(WORKING_DE.links_dir,'StoredLinks')
    if not PathExists(STORED_LINKS_FILE):
        names = ['LinkType','LinkSource','SourceFile','LinkTarget','TargetFile','UpdateScript','UpdateScriptFile','IsFast']
        StoredLinks = numpy.rec.fromarrays([[],[],[],[],[],[],[],[]],names=names, formats = ['int']*len(names))
    else:
        StoredLinks = numpy.load(STORED_LINKS_FILE)


    STORED_TIMES_FILE = os.path.join(WORKING_DE.links_dir,'StoredTimes') 
    if not PathExists(STORED_TIMES_FILE):
        names = ['FileName','ModTime']
        StoredTimes = numpy.rec.fromarrays([[],[]],names=names, formats = ['int']*len(names))
    else:
        StoredTimes = numpy.load(STORED_TIMES_FILE)    
           
    #only retain links from py files that still exist
    if len(StoredLinks) > 0:
        scriptfiles = uniqify(StoredLinks['UpdateScriptFile'].tolist() + StoredTimes['FileName'].tolist() + StoredLinks[StoredLinks['LinkType'] == 'Uses']['SourceFile'].tolist())
    else:
        scriptfiles = []
    ExistsDict = dict([(scriptfile,PathExists(scriptfile)) for scriptfile in scriptfiles])
    Retain = [i for i in range(len(StoredLinks)) if ExistsDict[StoredLinks['UpdateScriptFile'][i]]]
    ToDelete = numpy.ones((len(StoredLinks),),bool); ToDelete[Retain] = False; StoredLinksDeleted = StoredLinks[ToDelete]
    
    StoredLinksFiltered = StoredLinks[Retain] 
    Changes = len(StoredLinksFiltered) < len(StoredLinks)
    if len(StoredTimes):
        StoredTimesFiltered = StoredTimes[[i for i in range(len(StoredTimes)) if ExistsDict[StoredTimes['FileName'][i]]]]
    else:
        StoredTimesFiltered = StoredTimes[0:0] 
    
    #sort by updatescriptfile   
    StoredTimesFiltered.sort(order=['FileName'])    
    FileArray = numpy.array(FileList)
    FileArray.sort()

    A = fastisin(FileArray,StoredTimesFiltered['FileName'])
    CurrentTimes = numpy.array([os.path.getmtime(x) for x in StoredTimesFiltered['FileName']])
    B = CurrentTimes > StoredTimesFiltered['ModTime']
    
    if len(StoredLinksFiltered) > 0:
        NE = StoredLinksFiltered[StoredLinksFiltered['SourceFile'] == 'NOTEXIST'][['LinkSource','TargetFile']]
        NE = [x['TargetFile'] for x in NE if x['TargetFile'] in FileArray and any([IsFile('../' + '/'.join(x['LinkSource'].split('.')[:j]) + '.py') for j in range(1,len(x['LinkSource'].split('.')))])]
        DE = [x['TargetFile'] for x in StoredLinksFiltered[(StoredLinksFiltered['LinkType'] == 'Uses') & (StoredLinksFiltered['SourceFile'] != 'NOTEXIST')] if not ExistsDict[x['SourceFile']]]
    else:
        NE = []
        DE = [] 
    
    #determine which modules to recompute links about . 
    if Recompute:
        ToGet = uniqify(FileArray[numpy.invert(A)].tolist() + StoredTimesFiltered['FileName'].tolist() + NE + DE)
    else:
        ToGet = uniqify(FileArray[numpy.invert(A)].tolist() + StoredTimesFiltered['FileName'][B].tolist() + NE + DE)
        
    ToGet = [t for t in ToGet if not t.endswith('__init__.py')]
    
    #actually recompute links for selected modules
    [LinksToAdd,SucceededList] = ComputeLinksFromOperations(ToGet)
           
    #integrate resulting links into cached linklists    
    TimesToAdd = numpy.rec.fromarrays([SucceededList, [os.path.getmtime(x) for x in SucceededList]],names=['FileName','ModTime'])
    NewTimes = SimpleStack([StoredTimesFiltered[numpy.invert(B)],TimesToAdd])   
    LinksToAdd.sort(order=['UpdateScriptFile'])
    C = fastisin(StoredLinksFiltered['UpdateScriptFile'],LinksToAdd['UpdateScriptFile'])    

    if any(C):
        StoredLinksDeleted = SimpleStack([StoredLinksDeleted,StoredLinksFiltered[C]])
    
    RetainedLinks = StoredLinksFiltered[numpy.invert(C)]
    if len(LinksToAdd) > 0:
        NewLinks = SimpleStack([RetainedLinks,LinksToAdd])
    else:
        NewLinks = StoredLinksFiltered
    Changes = Changes or len(LinksToAdd) > 0    
    if Changes:
        NewLinks.dump(STORED_LINKS_FILE)
    NewTimes.dump(STORED_TIMES_FILE)
    

    #handle creation of Implied Links
    STORED_IMPLIED_FILE = os.path.join(WORKING_DE.links_dir,'StoredImpliedLinks')
    if not PathExists(STORED_IMPLIED_FILE):
        names = ['LinkType','LinkSource','SourceFile','LinkTarget','TargetFile','UpdateScript','UpdateScriptFile','IsFast']
        StoredImpliedLinks = numpy.rec.fromarrays([[],[],[],[],[],[],[],[]],names=names, formats = ['int']*len(names))
    else:
        StoredImpliedLinks = numpy.load(STORED_IMPLIED_FILE)
    ImpliedAdded = GetImpliedLinks(LinksToAdd,RetainedLinks)
    ImpliedDeleted = GetImpliedLinks(StoredLinksDeleted,StoredLinks)
    ImpliedNew = SimpleStack([FastRecarrayDifference(StoredImpliedLinks,ImpliedDeleted),ImpliedAdded])
    ImpliedNew.dump(STORED_IMPLIED_FILE)
    
    #handle creation of Dummy Links
    STORED_DUMMY_FILE = os.path.join(WORKING_DE.links_dir,'StoredDummyLinks') 
    if not PathExists(STORED_DUMMY_FILE):
        names = ['LinkType','LinkSource','SourceFile','LinkTarget','TargetFile','UpdateScript','UpdateScriptFile','IsFast']
        StoredDummyLinks = numpy.rec.fromarrays([[],[],[],[],[],[],[],[]],names=names, formats = ['int']*len(names))
    else:
        StoredDummyLinks = numpy.load(STORED_DUMMY_FILE)
    TT = time.time()
    DummyAdded = GetDummyLinks(LinksToAdd,RetainedLinks)
    DummyDeleted = GetDummyLinks(StoredLinksDeleted,StoredLinks)
    DummyNew = SimpleStack([FastRecarrayDifference(StoredDummyLinks,DummyDeleted),DummyAdded])
    DummyNew.dump(STORED_DUMMY_FILE)
    
    
    #determine which links to return (ALL links are cached, but only those desired related to the user specified FileList are actually returned by this function)
    D = fastisin(NewLinks['UpdateScriptFile'],FileArray)
    LinksToReturn = NewLinks[D]
    if AddImplied:
        LinksToReturn = SimpleStack1([LinksToReturn,ImpliedNew])

    if AddDummies:
        D = fastisin(DummyNew['TargetFile'],FileArray)
        LinksToReturn = SimpleStack1([LinksToReturn,DummyNew[D]])

    if len(LinksToReturn) > 0 and FilterNEs:
        LinksToReturn = LinksToReturn[LinksToReturn['SourceFile'] != 'NOTEXIST']

    if len(LinksToReturn) > 0 and FilterInternal:
        LinksToReturn = LinksToReturn[(LinksToReturn['LinkType'] != 'Uses') | fastisin(LinksToReturn['SourceFile'],FileArray)]
    
    return LinksToReturn
    
    

def GetImpliedLinks(NewLinks, LinkList):
    '''This computes the implied links --- assuming that all implied links in the "LinkList" argument have already by computed, it only computes the implied links that will be added by the addition of the NewLinks.   
    '''
    
    if len(NewLinks)>0:
        NL = NewLinks.copy()
        All = SimpleStack1([NL,LinkList])
            
        NewRecs = []
        for (S,T) in [(NL,All),(All,NL)]:
            TT = T[T['LinkType'] == 'CreatedBy'].copy()
            if len(S) > 0 and len(TT) > 0:
                L1 = numpy.rec.fromrecords(uniqify(zip(TT['LinkTarget'],TT['TargetFile'],TT['UpdateScript'],TT['UpdateScriptFile'])),names=['Object','ObjectFile','Script','ScriptFile'])
                L1.sort(order = ['ObjectFile'])
                L2 = numpy.rec.fromrecords(uniqify(zip(S['LinkSource'],S['SourceFile'])) + uniqify(zip(S['LinkTarget'],S['TargetFile'])),names=['Object','ObjectFile'])
                L2.sort(order = ['ObjectFile'])
                [A,B] = getpathalong(L1['ObjectFile'],L2['ObjectFile'])
                F1 = [range(A[i],B[i]) for i in range(len(L1))]
                NewRecs += ListUnion([[('Implied',L1['Object'][i],L1['ObjectFile'][i],L2['Object'][j],L2['ObjectFile'][j],L1['Script'][i],L1['ScriptFile'][i],0) for j in F1[i]] for i in range(len(F1))])
                
        if len(NewRecs) > 0:
            NR =  numpy.rec.fromrecords(uniqify(NewRecs),names=LinkList.dtype.names)
            NRs = numpy.array([n if n[-1] == '/' else n + '/' for n in NR['LinkSource']])
            NRt = numpy.array([n if n[-1] == '/' else n + '/' for n in NR['LinkTarget']])
            return NR[NRs != NRt]
        else:
            return LinkList[0:0]
    else:
        return LinkList[0:0]
        
        
def SameRoot(X,Y):
    XX = ['/'.join(x.split('/')[:-2]) if x[-1] != '/' else '/'.join(x.split('/')[:-2]) for x in X]
    YY = ['/'.join(x.split('/')[:-2]) if x[-1] != '/' else '/'.join(x.split('/')[:-2]) for x in Y]
    return fastequalspairs(XX,YY)
        
        
        
def GetDummyLinks(NewLinks,LinkList):
    '''This computes the dummy links --- assuming that all dummy links 
    in the "LinkList" argument have already by computed, it only computes 
    the dummy links that will be added by the addition of the NewLinks.  
    Dummy links are "creates-in-a-creates" scenario. 
    '''

    if len(NewLinks) > 0:
        Total = SimpleStack([NewLinks,LinkList])

        NewC = NewLinks[NewLinks['LinkType'] == 'CreatedBy'].copy()
        TotalC = Total[Total['LinkType'] == 'CreatedBy']

        if len(NewC) > 0:
            NewRecs = []
            for (NL,AllC) in [(NewC,TotalC),(TotalC,NewC)]:         
                L1 = numpy.rec.fromrecords(uniqify(zip(AllC['LinkTarget'],AllC['TargetFile'])),names = ['LinkTarget','TargetFile'])
                L2 = numpy.rec.fromrecords(uniqify(zip(NL['LinkTarget'],NL['TargetFile'],NL['UpdateScript'],NL['UpdateScriptFile'])),names = ['LinkTarget','TargetFile','UpdateScript','UpdateScriptFile'])
                            
                C = numpy.array([a + ' ; ' + b for (a,b) in zip(L2['UpdateScript'],L2['TargetFile'])])
                s = C.argsort(); C = C[s]; L2 = L2[s]
                [A,B] = getpathstrictlyalong(C,C)
                G = numpy.array(ListUnion([range(a,b) for (a,b) in zip(A,B)])); G.sort()
                D = numpy.arange(len(L2))
                L2 = L2[numpy.invert(fastisin(D,G))]
        
                [s1,s2,A,B] = getKalong(L1['LinkTarget'],L2['LinkTarget'],1)
                L1 = L1[s1]; L2 = L2[s2]
                NewRecs += ListUnion([[('Dummy',Backslash(L1['LinkTarget'][i]) + 'dummy',Backslash(L1['TargetFile'][i])+'dummy', L2['UpdateScript'][j],L2['UpdateScriptFile'][j],'None','None',0) for j in range(A[i],B[i])] for i in range(len(A))])           

            if len(NewRecs) > 0:    
                NR =  numpy.rec.fromrecords(uniqify(NewRecs),names=LinkList.dtype.names)
                return NR[NR['LinkSource'] != NR['LinkTarget']]
            else:
                return LinkList[0:0]
        else:
            return LinkList[0:0]
    else:
        return LinkList[0:0]



def GutsComputeLinks(FileList):
    '''
        This function actually computes the links contained
        in the files in FileList
        
        Argument: 
        FileList == list of modules to analysis
        
        Returns:
        LinkList == list of links computed
        Succeeded List = list of modules in FileList whose links 
            could be successfully obtained.
    '''

    LinkList = []; #<-- initialize
    SucceededList = []

    for opfile in FileList:  #<-- for each op in the list of operations,     
        StoredModule = GetStoredModule(opfile)  #<-- get stored version of information about the module -- GetStoredModules is defined in ../System/MetaData.py, see that for information.
        if StoredModule:   #<-- if stored version f information is sucessfully obtained,  go ahead
            SucceededList += [opfile]   
            ModuleName = '.'.join(opfile.split('/')[1:-1] + [inspect.getmodulename(opfile)])    #get name of module from file name, assuming it's in the system standard convention formation, starting with '../' relative to Temp directory
            for op in StoredModule.keys():   #for each function  or class defined in the stored module: 
                if StoredModule[op].descr == 'Internal Function' or  StoredModule[op].descr == 'Internal Class':    
                    opn = StoredModule[op].reconstitute()   #reconstitute the object, 
                    opname = ModuleName + '.' + op     
                    if StoredModule[op].descr == 'Internal Function':    # if its a function, strip out depends_on and creates  and uses notations  and produce links from them
                        DependsOn = MakeT(GetStoredDefaultVal(opn,'depends_on',NoVal = ())) + MakeT(GetStoredAttributes(opn,'__depends_on__',NoVal = ()))
                        Creates = MakeT(GetStoredDefaultVal(opn,'creates',NoVal = ())) + MakeT(GetStoredAttributes(opn,'__creates__',NoVal = ())) 
                        IsFast = GetStoredDefaultVal(opn,'IsFast',NoVal = 0) or GetStoredAttributes(opn,'__is_fast__',NoVal = 0) 
                        LinkList += [('CreatedBy',opname,opfile,b,b,opname,opfile,IsFast) for b in Creates]
                        LinkList += [('DependsOn',a,a,opname,opfile,'None',opfile,IsFast) for a in DependsOn]
                        SpecifiedUses = [(u,'../' + '/'.join(u.split('.')[:-1]) + '.py') if isinstance(u,str) else u for u in MakeT(GetStoredDefaultVal(opn,'uses',NoVal = ())) + MakeT(GetStoredAttributes(opn,'__uses__',NoVal = ()))]
                        
                    else:
                        SpecifiedUses = []
                        IsFast = 0
                    ComputedUses = StoredModule[op].static    #get system-computed Uses links determined by static analysis  on the funciton -- which is included in the StoredModule 
                    Uses = SpecifiedUses + (ComputedUses[0] if ComputedUses != None else [])  #add the system-computed Uses to the user-declared ones
                    OpPaths = [['../' + '/'.join(a[0].split('.')[:j]) + '.py' for j in range( 1, len(a[0].split('.'))) if IsFile('../' + '/'.join(a[0].split('.')[:j]) + '.py')] for a in Uses]
                    OpPaths = [x[0] if x else 'NOTEXIST' for x in OpPaths]
                    LinkList += [('Uses',a[0],oppath,opname,opfile,'None',opfile,IsFast) for (a,oppath) in zip(Uses,OpPaths) if a[0] != opname]   #and produce Uses links from them
        else:
            print  'No links for ', opfile, 'being processed because module failed to load properly.'
            
    return [LinkList,SucceededList]



def ComputeLinksFromOperations(FileList):
    '''
     Wrapper for GutsComputeLinks
    '''
    
    FileList = [ll for ll in FileList if not ll.endswith('__init__.py')]
    
    [LinkList,SucceededList] = GutsComputeLinks(FileList)

    Header = ['LinkType','LinkSource','SourceFile','LinkTarget','TargetFile','UpdateScript','UpdateScriptFile','IsFast']  #<-- the field types in the list of links
    #output 
    if len(LinkList) > 0:  
        return [numpy.rec.fromrecords(LinkList,names = Header),SucceededList]
    else:
        return [numpy.rec.fromarrays([[] for i in Header],names = Header),SucceededList]


def GetStoredAttributes(op,name,NoVal=None):
    if 'func_dict' in op.keys():
        if op['func_dict'] != None:
            return op['func_dict'].get(name,NoVal)
        else:
            return NoVal
    else:
        return NoVal

def GetStoredDefaultVal(op,name,NoVal=None):
    '''
    Given a python function in the form of a "Stored Operation", 
    return the function's default value for a given variable name, 
    returning NoVal if the variable doesn't exist for the function or doesn't 
    have a default value. 
        
    E.g. if the function is 
            def F(x, y=3): ... 
    Then if op is the "Stored Operation" form of F, 
        GetStoredDefaultVal(op,y) returns '3' , 
    while 
        GetStoredDefaultVal(op,x,[]) returns '[]'.
    
    ARGUMENTS:
    op -- a "Stored operation" -- Suppose you have a python function F.  
    Then the "Stored Operation" version of the function is a dictionary with:
    key 'func_code' -- so that 
        op['func_code'] = F.func_code, 
    the python code object associated with F, and key 'func_defaults'
    -- so that 
        op['func_defaults'] = F.func_defaults,
    the tuple of default values of F.       
    
    name -- name of variable that you want to determine default value if
        
    NoVal -- object to substitute in if the named variable does not exist for F 
    or if it that variable does not have a default value
        
    Returns 
        The default value when it exists, otherwise NoVal
    '''

    if op['func_defaults'] != None:
        numargs = op['func_code'].co_argcount
        vars = op['func_code'].co_varnames[:numargs]
        numdefaults = len(op['func_defaults'])
        defaultvars = dict(zip(vars[len(vars) - numdefaults:],op['func_defaults']))
        return defaultvars.get(name,NoVal)
    else:
        return NoVal




def ReduceListOfSetsOfScripts(ScriptList):
    '''
        Given a list of sets of scripts, produces a reduced version retaining 
        only the _last_ call to any given script.
    '''
    return [J.difference(['None']) for J in [S.difference(Union([T for (j,T) in enumerate(ScriptList) if j > i])) for (i,S) in enumerate(ScriptList)]]
    
    
    
def GetLinksBelow(Seed, AU = None, Exceptions = None, Forced = False, 
                         Simple=False, Pruning = True,ProtectComputed = False,
                         depends_on = WORKING_DE.relative_root_dir):
    '''
    Given a Seed list of paths, loads the LinkList of live modules, 
    and determines dowstream data dependency links by 
    propagating downstream through the LinkList, from paths that are in Seed.   
    
    ARGUMENTS:
    Seed = list of paths from which to propagate downstream.
    
    Forced = Boolean : if true, propagates links through LinkList without regard 
    to timestamps of files, catching _all_ downstream links, even if the files 
    they represent are up to date. If Forced is False -- which is the default 
    -- this progates down only through links
    that are in need of updating, as determined by time stamps.  
    (e.g. those link targets whose timestamps are old than their sources -- 
    and all the downstream files -- are included.) 

    Simple = Boolean : if True, only looks at paths listed explicitly in Seed; if False, 
    looks at all paths in Seed, as well as those in directories contained
    in the filesystem below  paths in Seed
    
    ProtectComputed = Boolean : if True, progates through links where target data files 
    of links have been modified _after_ they were last created by system update of the link, 
    e.g. as if the data had been corrupted after computation.   
    Such files have a newer timestamp than their sources, so merely propagating from 
    newer sources to older targets will not capture these files where computations 
    (may) have been corrupted.     Often times, one wishes to make a temporary change
    in a mid-stream file and see what its consequnces are, so in this case the 
    ProtectComputed option should be left at its default value of False.
    
    Exceptions = List : Before propagating downstream through the list, this function first 
    filters out links whose scripts that are not indicated for Automatic updating 
    (see below for comments in the function body).   
    Exceptions is a list of scripts whose links should be retained even if they are not 
    indicated for Automatic updating -- the point of this is mostly for the function 
    MakeUpdated (see comments in that function).  
        
        
    RETURNS:
    A = [L0,L1,L2 ...., LF]
    where A[i]  = Li is sublist of links in the LinkList, representing those links 
    activated at stage i in the downstream propagation 
    through the LinkList from the seed links in L0.  
    
    In words, this is a trace through the Directred Acyclic Graph
    represented by the LinkList.   
    Note that the same link can appear multiple times in different 
    stages because it might be activated first by itself (e.g. because 
    its source is in Seed and its target is older than its source) 
    and then by virtue of downstream propagation from some independently 
    activated link upstream. 
    '''
    t = time.time()
    if isinstance(Seed,str):
        Seed = Seed.split(',')  
    LinkList = LinksFromOperations(WORKING_DE.load_live_modules(),AddDummies=True)   
    LinkList = FilterForAutomaticUpdates(LinkList,AU=AU,Exceptions=Exceptions)

    if not Forced:  
        T = PropagateThroughLinkGraphWithTimes(Seed,LinkList,Simple=Simple, Pruning=Pruning,ProtectComputed = ProtectComputed)
        return [ll[ll['Activated']] for ll in T]
    else:
        return PropagateThroughLinkGraph(Seed,LinkList)


        
def GetII(LinkList,Seed):
    
    Seed = uniqify(Seed)
    PSeed = [ss for ss in Seed if not IsDotPath(ss)]
    
    if len(LinkList) > 0:
        S = LinkList.argsort(order = ['SourceFile'])
        LinkList = LinkList[S]
        
        if len(PSeed) > 0:
    
            PSeed = numpy.array(PSeed)
            PSeed.sort()
            II1 = [i for i in range(len(LinkList)) if PathExists(LinkList['SourceFile'][i])]
            [A,B] = getpathalong(LinkList['SourceFile'],PSeed)
            II2 = (B>A).nonzero()[0].tolist()
            [A,B] = getpathalong(PSeed,LinkList['SourceFile'])
            II3 = ListUnion([range(A[i],B[i]) for i in range(len(A))])
            #II = numpy.array(list(set(II1).intersection(II2 + II3)))
            II = numpy.array(list(set(II1).intersection(II3)))
            if len(II) > 0:
                IP = S[II]
            else:
                IP = numpy.array([],int)
        else:
            IP = numpy.array([],int)
    
        DSeed = [ss for ss in Seed if IsDotPath(ss)]
            
        if len(DSeed) > 0:
            LinkList = LinkList[PermInverse(S)]
            S = LinkList.argsort(order = ['LinkSource'])
            LinkList = LinkList[S]
            DSeed = numpy.array(DSeed)
            DSeed.sort()
            II1 = [i for i in range(len(LinkList)) if PathExists(LinkList['SourceFile'][i])]
            DSeedM = numpy.array(['../' + x.replace('.','/') for x in DSeed])
            USM = numpy.array(['../' + x.replace('.','/') for x in LinkList['UpdateScript']])
            [A,B] = getpathalong(DSeedM,USM)
            II3 = ListUnion([range(A[i],B[i]) for i in range(len(A))])      
            II = numpy.array(list(set(II1).intersection(II3)))
    
            if len(II):
                ID = S[II]
            else:
                ID = numpy.array([],int)
        else:
            ID = numpy.array([],int)
        
        IC = numpy.append(IP,ID)
    else:
        return []
    
    
    return IC

def UpdateGuts(UpdateList,LinkList,MtimesDict,PtimesDict,ProtectComputed):
    '''
    The guts of the downstream propagation through a linklist.   
    Used primarily by the function PropagateThroughLinkGraphWithTimes.
    
    ARGUMENTS:
    LinkList = A numpy record array of data dependency links.

    UpdateList = List of the form [(i1,t1),(i2,t2), ... , (in,tn)] where 
    each  i is an index in LinkList, and ti is a time stamp (or a 'numpy.nan')
    
    MtimesDict = Dictionary where:
    -- the keys are some of the elements of LinkList['LinkSource'] 
        or LinkList['LinkTarget'] 
       These are paths in filesystem, or subparts of paths. (e.g. functions inside .py 
       module files)
    -- the values values on key LinkList['LinkSource'][i] is 
    
    FindMtime(Linklist['SourceFile'][i],functionname=LinkList['LinkSource'][i]) 
    
    these are the timestamps associated with a path or a subpart of a path
                
    ProtectComputed = Boolean : if true, enables propagation along links 
    whose targets have been modified after creation
    
    PtimesDict = Dctionary used when ProtectComputed = True, where:
    -- the keys are paths in filesystem
    -- the values on a key P is the most recent time that the file or 
    directory at time P was successfully computed by the automatic 
    updating facility  
            
    RETURNS:
    TargetRecs a numpy record array of containing list of links in
    LinkList that are activated, relative to the information provided 
    in the UpdateList.  Essentially these are:
    
    -- all those links (source,target) in LinkList[i[0] for i in UpdateList]  
    such that MtimesDict[target] is less than then T, where T is maximum of:
        MtimesDict[source] 
    and
        the maximum of 
        
        [i[1] for i such that LinkList['LinkSource'][i[0]] == source]

    -- plus those that are activated when ProtecteComputed is True          
                
    Some Information is appended to each link that is activated, 
    including the "maximal propagation time" along the link -- which is:
        -- T, in the case of a "Uses" link   
        -- numpy.nan, in the case of "CreatedBy" link
            
    '''


    TargetRecs = []
    for i in UpdateList:
        if i[1]:
            TargetExists = PathExists(LinkList['TargetFile'][i[0]]) 
            TargetIsNotTooOld = TargetExists and i[1] <= MtimesDict[LinkList['LinkTarget'][i[0]]]
            Triggered = numpy.isnan(i[1])
            CreateLink = 'Create' in LinkList['LinkType'][i[0]]
            TargetIsNotTooYoung = (not ProtectComputed) or (TargetExists and (MtimesDict[LinkList['LinkTarget'][i[0]]] <= PtimesDict[LinkList['LinkTarget'][i[0]]] if not numpy.isnan(PtimesDict[LinkList['LinkTarget'][i[0]]]) else True)) 
            PassThrough = TargetExists and (not Triggered) and (not CreateLink or TargetIsNotTooOld) and (not CreateLink or TargetIsNotTooYoung)
            
            if PassThrough: 
                TimeVal = max(i[1],MtimesDict[LinkList['LinkTarget'][i[0]]])
                if not TargetIsNotTooOld:
                    Activated = True
                else:
                    Activated = False
            else: 
                Activated = True
                TimeVal = numpy.nan                         
            TargetRecs += [(str(i[0]),) + tuple(LinkList[i[0]]) + (i[1],TimeVal,i[2],MtimesDict[LinkList['LinkTarget'][i[0]]] if TargetExists else numpy.nan,  float(PtimesDict[LinkList['LinkTarget'][i[0]]]) if ProtectComputed else numpy.nan, Activated)]
    return TargetRecs


    
def PropagateThroughLinkGraphWithTimes(Seed,LinkList, Simple = False,
                                       Pruning = True, HoldTimes = None,
                                       ProtectComputed = False,
                                       depends_on = WORKING_DE.relative_root_dir):
    '''
    Given a Seed list of paths, and Linklist propagates downstream 
    through the LinkList from the Seeds, taking into account 
    timestamps along the way. 
    
    ARGUMENTS:
    Seed = List of paths to start with. 
    
    LinkList = numpy record array of data dependency Links.
    
    Simple = Boolean : if True, only looks at paths listed explicitly in Seed;
    if False, looks at all paths in Seed, as well as those in directories 
    contained in the filesystem below  paths in Seed
    
    ProtectComputed = Boolean : if True, progates through links 
    where target data files of links have been modified _after_ they 
    were last created by system update of the link, e.g. as if the data 
    had been corrupted after computation.  
    
    HoldTimes = Dictionary, where:
    -- keys are paths
    -- HoldTimes[Path] is a timestamp that the system is meant 
    to "pretend" is the mod time of Path, if Path comes up as a 
    source or target during the propagation process, 
    instead of computing the real mod time. 
            
    RETURNS:
        A = [L0,L1,L2 ...., LF]
    where A[i]  = Li is sublist of links in the LinkList, representing 
    those links activated at stage i in the downstream propagation 
    through the LinkList from the seed links in L0.  
    
    In words, this is a trace through the Directred Acyclic Graph 
    represented by the LinkList.   Note that the same link can appear 
    multiple times in different stages because it might be activated 
    first by itself (e.g. because its source is in Seed and its target is 
    older than its source) and then by virtue of downstream propagation 
    from some independently activated link upstream. 
        
    '''

    LinkList = RemoveColumns(LinkList,('LinkNumber','InMarkTime','OutMarkTime','LinkTriggers','TargetExists','TargetModTime','TargetLastCreateTime','Activated'))   
    
    LinkList.sort(order=['LinkSource'])
    
    if isinstance(Seed,str):    
        Seed = Seed.split(',')      

    II = list(GetII(LinkList,Seed))
    if len(II) == 0:
        return []
    Sources = uniqify(zip(LinkList['SourceFile'][II],LinkList['LinkSource'][II]))
    
    
    if Simple:
        print 'WARNING: Using "simple" mode;  propagation may not be complete.'
    
    MtimesDict = ListFindMtimes(Sources,HoldTimes,Simple)
    UpdateList = [(i,MtimesDict[LinkList['LinkSource'][i]],'') for i in II]
    UpdateLists = [UpdateList]
    
    LinkArraySequence = []  
    
    Header = ('LinkNumber',) + LinkList.dtype.names +  ('InMarkTime','OutMarkTime','LinkTriggers','TargetModTime','TargetLastCreateTime','Activated') 
    if ProtectComputed: PtimesDict = {}
    
    while len(UpdateList) > 0:  
        
        NewSources = [(LinkList['TargetFile'][i[0]], LinkList['LinkTarget'][i[0]]) for i in UpdateList if LinkList['LinkTarget'][i[0]] not in MtimesDict.keys()]
        
        if len(NewSources) > 0:
            NewMtimes = ListFindMtimes(NewSources,HoldTimes,Simple)
            MtimesDict.update(NewMtimes)
        if ProtectComputed:
            NewPtimes =  [(LinkList['LinkTarget'][i[0]], FindPtime(LinkList['LinkTarget'][i[0]],Simple=Simple)) for i in UpdateList if LinkList['LinkTarget'][i[0]] not in PtimesDict.keys()]   
            PtimesDict.update(dict(NewPtimes))
        else:
            PtimesDict = {}

        TargetRecs = UpdateGuts(UpdateList,LinkList,MtimesDict,PtimesDict,ProtectComputed)

        TargetArray = numpy.rec.fromrecords(TargetRecs,names=Header) if len(TargetRecs) > 0 else numpy.rec.fromarrays([[]]*len(Header),names=Header)
        LinkArraySequence += [TargetArray]
        if Pruning:
            TargetArray = TargetArray[TargetArray['Activated']]

        TargetArray.sort(order=['LinkTarget'])
        Targets = TargetArray['LinkTarget']; Times = TargetArray['OutMarkTime']; LinkNumbers = TargetArray['LinkNumber']        
        [A,B] = fastequalspairs(LinkList['LinkSource'],Targets)         
        L1 = [(i, Max(Times[range(A[i],B[i])]) , ','.join(uniqify(LinkNumbers[range(A[i],B[i])].tolist()))) for i in range(len(LinkList)) if A[i] < B[i]]
        CreateTargetArray = TargetArray[TargetArray['LinkType'] == 'CreatedBy']
        if len(CreateTargetArray) > 0:
            CreateTargets = CreateTargetArray['LinkTarget']; CreateTimes = CreateTargetArray['OutMarkTime']; CreateLinkNumbers = CreateTargetArray['LinkNumber']
            [A,B] = getpathalong(LinkList['LinkSource'],CreateTargets)      
            L2 = [(i, Max(CreateTimes[range(A[i],B[i])]), ','.join(uniqify(CreateLinkNumbers[range(A[i],B[i])].tolist()))) for i in range(len(LinkList)) if A[i] < B[i]]
            [A,B] = getpathalong(CreateTargets,LinkList['LinkSource']) 
            FF = [((A <= j) & (B > j)).nonzero()[0] for j in range(len(LinkList))]
            EE = ListUnion([range(A[l],B[l]) for l in range(len(A))])
            NewMtimes = [(LinkList['LinkSource'][i], FindMtime(LinkList['SourceFile'][i],objectname = LinkList['LinkSource'][i],Simple=Simple) if PathExists(LinkList['SourceFile'][i]) else nan) for i in EE if LinkList['LinkSource'][i] not in MtimesDict.keys()]
            MtimesDict.update(dict(NewMtimes))  
            if ProtectComputed:
                NewPtimes = [(LinkList['LinkSource'][i], FindPtime(LinkList['LinkSource'][i],Simple=Simple)) for i in EE if LinkList['LinkSource'][i] not in PtimesDict.keys()]
                PtimesDict.update(dict(NewPtimes))              
            L3 = [(i,Max(CreateTimes[FF[i]]),','.join(uniqify(CreateLinkNumbers[FF[i]].tolist()))) for i in range(len(LinkList)) if len(FF[i]) > 0]
            UpdateList = uniqify(L1 + L2 + L3)
        else:
            UpdateList = L1
        if any([set(l) <= set(UpdateList) for l in UpdateLists]):
            print 'There was a circularity involving at some of the links in' , uniqify(LinkList[[i[0] for i in UpdateList]]['LinkSource'].tolist()) , '. Further updates will be canceled.'
            return LinkList[0:0]
        else:
            UpdateLists += [UpdateList]
             
    return LinkArraySequence

def PropagateThroughLinkGraph(Seed,LinkList,depends_on = WORKING_DE.root_dir):
    '''
    Given a Seed list of paths, and Linklist propagates downstream 
    through the LinkList from the Seeds. 
    
    ARGUMENTS:
    --Seed = List of paths to start with.   
    --LinkList = numpy record array of data dependency Links.
                        
    RETURNS:
        A = [L0,L1,L2 ...., LF]
    where A[i]  = Li is sublist of links in the LinkList, 
    representing those links activated at stage i in the downstream 
    propagation through the LinkList from the seed links in L0.  
        
    In words, this is a trace through the Directred Acyclic Graph 
    represented by the LinkList.   Note that the same link can appear
    multiple times in different stages because it might be activated 
    first by itself (e.g. because its source is in Seed and its target is 
    older than its source) and then by virtue of downstream 
    propagation from some independently activated link upstream. 
            
    '''

    return PropagateSeed(Seed,LinkList,'LinkSource','LinkTarget','LinkSource','CreatedBy')
    
    

def PropagateUpThroughLinkGraph(Seed,LinkList,depends_on = WORKING_DE.relative_root_dir):

    '''
        Like PropagateThroughLinkGraph, but goes upstream from Seed instead of downstream.
    '''
    
    return PropagateSeed(Seed,LinkList,'LinkTarget','LinkSource','LinkTarget','CreatedBy')  
    
    
        
def PropagateSeed(Seed,LinkList,N1,N2,N3,Special):

    '''
    Does the maing propagation of a seed through a linklist.   
    A fairly general graph propagation function.  In words, 
    this is a (basically) a trace through the Directred Acyclic Graph 
    represented by interpreting (LinkList[N1],LinkList[N2]) as the 
    edges of a graph -- together with the implied paths by path inclusion.   
        
    ARGUMENTS:
    --Seed = List of paths to start with. 
    --LinkList = numpy record array of data dependency Links.   
    --N1 = Column header in LinkList ; Representing the "source" column
    --N2 = Column header in LinkList ; Representing the "target" column
            
    RETURNS:
        A = [L0,L1,L2 ...., LF]
    where A[i]  = Li is sublist of links in the LinkList, 
    representing those links activated at stage i in the propagation along
    direction N1 to N2 through the LinkList from the seed links in L0.  
            
    Note that the same link can appear multiple times in 
    different stages because it might be activated first by itself 
    (e.g. because its source is in Seed and its target is older than its source) 
    and then by virtue of downstream propagation from some 
    independently activated link upstream. 
            
    If the graph ends up being cyclic, it prints an error message and
    returns an empty recarray with the same fields as LinkList.
        
    '''

    UpdateList = GetI(LinkList[N3],Seed)    
    UpdateLists = [UpdateList]
    ActivatedLinkIndices = [UpdateList[:]]
    while len(UpdateList) > 0:
        TargetList = LinkList[UpdateList]
        s = TargetList[N2].argsort(); TargetList = TargetList[s]
        L1 = fastisin(LinkList[N1], TargetList[N2]).nonzero()[0].tolist() 
        [A,B] = getpathalong(LinkList[N1],TargetList[N2])
        L2 = [i for i in range(len(LinkList)) if (TargetList['LinkType'][A[i]:B[i]] == Special).any()]
        [A,B] = getpathalong(TargetList[N2],LinkList[N1])   
        L3 = set((TargetList['LinkType'] == Special).nonzero()[0]).intersection(ListUnion([range(a,b) for (a,b) in zip(A,B) if b > a]))
        UpdateList = uniqify(L1 + L2 + list(L3))
        if any([set(l) <= set(UpdateList) for l in UpdateLists]):
            print 'There was a circularity involving at least some of the links generated by the scripts' , set([LinkList['UpdateScript'][i] for i in UpdateList]) , '. Updates will be canceled.'
            return LinkList[0:0]
        else:
            UpdateLists += [UpdateList]
            ActivatedLinkIndices.append([UpdateList[:]])
    return [LinkList[[i for i in l]] for l in ActivatedLinkIndices]

    
    
def GetI(List,Seed):
    s = List.argsort() ; List = List[s]
    Seed = numpy.array(Seed) ; Seed.sort()
    [A,B] = getpathalong(List,Seed)
    C1 = (B > A).nonzero()[0].tolist()
    [A,B] = getpathalong(Seed,List)
    C2 = ListUnion([range(a,b) for (a,b) in zip(A,B) if b > a])
    I = numpy.array(uniqify(C1 + C2))
    if len(I) > 0:
        return s[I]
    else:
        return numpy.array([],int)
        
            
    
    
def GetConnected(Seed, level = -1, Filter = True,depends_on = WORKING_DE.relative_root_dir):
    '''
    Convenience function printing out targets at specified level away from seed in
    link depedency network, for the LinkList loaded from live modules. 
        
    ARGUMENTS:
    --Seed = List of paths to propagate away from.      
    --level = integer : level away from seed to find ; 
        -K means K leves upstream, +K means K levels downstream. 

    RETURNS:
    --Python set object containing paths of dependencies, if any.  
    (If none a message is printed.)

    '''
        


    if isinstance(Seed,str):
        Seed = Seed.split(',')  
        
    LinkList = LinksFromOperations(WORKING_DE.load_live_modules())   
    if Filter:
        LinkList = FilterForAutomaticUpdates(LinkList)
        
    if level > 0:
        P = PropagateThroughLinkGraph(Seed,LinkList)
        if len(P) < level:
            print 'There are no create targets', level, 'levels from the the seed', Seed, '.'
            return set([])
        else:
            return set(P[level-1]['LinkTarget'])
    elif level < 0:
        P = PropagateUpThroughLinkGraph(Seed,LinkList)
        if len(P) < abs(level):
            print 'There are no dependencies', level, 'levels from the the seed', Seed, '.'
            return set([])
        else:
            return set(P[abs(level+1)]['LinkSource'])


        
def FilterForAutomaticUpdates(LList,AU = None,Exceptions = None, ReturnIndices = False):
    '''
    Filters a link links removing links that are not meant to be 
    automatically updated when the system runs downstream 
    updating -- except allows "exceptions" to pass. 
    The strategy is to basically get the list of filters from a 
    user-specified configuration file whoe path is given by the 
    environment variable 'AutomaticUpdatesPath'.
    
    ARGUMENTS:
    --LList = LinkList as a numpy record array from which to filter. 
    --Excetions = List of paths of scripts that should not be filtered out, regardless. 
    --AutomaticUpdateFilters  : an optional list of filters can be passed in.  (but usually isn't)
    --ReturnIndices:  boolean which if true means that the function will return 
    the _indices_ in LinkList that are to be retained instead of the retained
    links themselves. 
        
    RETURNS:
    If ReturnIndices = False:
        A subarray of LList if 
    else:
        A numpy array of indices of LList. 
        

    '''
    TT = time.time()
    if len(LList) > 0:
        LinkList = LList.copy()
        Exceptions = [] if Exceptions == None else Exceptions
        if AU == None:
            AU = DefaultValueForAutomaticUpdates    
    
        AU = CompilerChecked(AU)    
        
        CIODict = dict([(t,CheckInOutFormulae(AU,t)) for t in uniqify(LinkList['LinkTarget'].tolist() + LinkList['UpdateScript'].tolist())])
        CIOT = numpy.array([CIODict[t] for t in LinkList['LinkTarget']])
        CIOS = numpy.array([CIODict[t] for t in LinkList['UpdateScript']])

        PExceptions = [x for x in Exceptions if not IsDotPath(x)]
        PExceptions = numpy.array(PExceptions,str)  
        if len(PExceptions) > 0:
            s = LinkList.argsort(order = ['LinkTarget'])
            LinkList = LinkList[s]
            [A,B] = getpathalong(Exceptions,LinkList['LinkTarget'])
            R = ListUnion([range(A[i],B[i]) for i in range(len(A))])
            if len(R) > 0:
                ExcpT = fastisin(numpy.arange(len(LinkList)),s[numpy.array(R)])
            else:
                ExcpT = numpy.zeros((len(LinkList),),bool)
            LinkList = LinkList[PermInverse(s)]
        else:
            ExcpT = numpy.zeros((len(LinkList),),bool)
        
        DExceptions = [x for x in Exceptions if IsDotPath(x)]
        if len(DExceptions) > 0:
            s = LinkList.argsort(order = ['UpdateScript'])
            LinkList = LinkList[s]
            LTM = numpy.array(['../' + ss.replace('.','/') for ss in LinkList['UpdateScript']])
            DEM = numpy.array(['../' + ss.replace('.','/') for ss in DExceptions])
            [A,B] = getpathalong(DEM,LTM)
            R = ListUnion([range(A[i],B[i]) for i in range(len(A))])
            if len(R) > 0:
                ExcpS = fastisin(numpy.arange(len(LinkList)),s[numpy.array(R)])
            else:
                ExcpS = numpy.zeros((len(LinkList),),bool)
            LinkList =  LinkList[PermInverse(s)]
        else:
            ExcpS = numpy.zeros((len(LinkList),),bool)

        
        Indices = ((ExcpT | CIOT) & (LinkList['UpdateScript'] == 'None')) | (ExcpS | CIOS)
    else:
        Indices = []        
    
    if ReturnIndices:
        return Indices
    elif len(Indices) > 0:
        return LinkList[Indices]
    else:
        return LList[0:0]
    

        
def UpstreamLinks(Targets,depends_on = WORKING_DE.relative_root_dir):   
    
    LinkList =  LinksFromOperations(WORKING_DE.load_live_modules())
    if isinstance(Targets,str): 
        Targets = Targets.split(',')
    P = PropagateUpThroughLinkGraph(Targets,LinkList)
    if len(P) > 0:
        return SimpleStack(P)
    else:
        return []       

        
DefaultValueForAutomaticUpdates = ['^.*']
DefaultValueForLiveModuleFilters = {'../Operations/' :  ['../*']} 
