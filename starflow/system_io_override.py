#!/usr/bin/env python
'''
Intercept system i/o functions and analyze stack that made i/o calls. 

One of the main purposes of the Data Environment to understand 
and manage data dependencies.  At a basic level, these data 
dependencies involve reading and writing files to disk.  To this end, 
it is useful to be able to determine exactly which files are being read 
and written, realtime -- by during processes of individual users doing 
exploratory data analysis as well as by automatic system updates.  
One wants not only to know which i/o streams are being started, but
also which high-level processes and functions are doing the reading and writing.    

This module provides routines for:
    1) intercepting i/o streams at a low level
    2) analyzing the call stack above those streams
    3) integrating the information from 1 and 2 to:
        -- store data about which files were read/written, and 
        therefore enable run-time determination of _undeclared_ 
        data dependency links
    and 
        -- impose controls on which files can be written by which 
        processes, thereby enabling the enforcement of _declared_ 
        data dependency links. 
    
The idea behind the imposition of controls is not to give the Data Enviroment 
an account security interface whereby Data Environment users can be 
flexibly prevented by Data Environment administrators from doing things
with files that don't belong to them. (Such things are probably better 
administered at the operating system level by real user accounts.)  
Instead, the idea is to allow the users to impose controls on themselves 
so that they, and others using their data, can be assured that the 
LinkLists that the Data Environment builds from the users' declarations
are an accurate reflection of the way the data was actually produced 
-- and have errors raised when dependency violations occur.  This allows 
users to easily see where they've forgotten to declare dependencies properly, 
and trivially know how to remedy the issue. 

The majority of the routines in this file are the system i/o intercepts themselves.  
The idea in each case is to implement for a standard i/o function, the
following three-step "redefinition" procedure: 
    1) take the standard __builtin__ I/O functions and save it to a "hold name" 
        (e.g. by prefixing "old_" to the name)
    2) redefine a new i/o function with PRECISELY the same interface as 
        the old one, and whichn calls the function at the "holding name" after
        first having passed the inputs and outputs through an I/O interception 
        and check that uses information from the GetDependsCreates() call 
        stack analyzer function. 
    3) redefine the system's standard I/O name as the new i/o function.
    
Step 2) can either implement:
    a) a "control" -- meaning that an i/o function that is called without being 
        covered by a declared dependency will raise a "BadCheckError" that
        prevents the I/O operation from occuring and prints information about the 
        violation, 
or 
    b) a "logging" operation -- meaning that data about the i/o request, together 
        with the stack inforamtion about where it was made and whether it was
        consistent with declarations -- is stored in some standard format and place.
-- and of course, it can do both.  

The slightly complex 3-step redefinition procedure is used to prevent 
problematic infinite recursions.  It also must be handled with care because,
once these intercepts are activated, ALL calls to these system functions 
will be passed through the intercepts.   This means that:
    -- protections can't be set too widely,
    -- interfaces of the functions must be preversed EXACTLY,
so that programs indirected called by the user as dependencies to 
other functions, and that require resources "outside" the system, are 
not bizarrely restricted from performing their work. (This is especially 
the case for automatic logging and other interactive features of enhanced 
python shells like iPython, which I tend to want to use.) 
'''

import __builtin__
import sys
import inspect
import shutil
import os
import types

from os import getcwd
from os.path import normpath

from starflow.utils import PathAlong, funcname, MakeT, caller, BadCheckError

def IsntProtected(r):
    '''
    If the environment variable "PROTECTION" is set to "ON"
    (see comments in i/o GetDependsCreates), this function looks 
    to see whether an environment variable called "ProtectedPathsListFile'
    has been set. This is a path to a user configuration file which would list, 
    in lines, the list of directories on which the user wishes i/o protection 
    to be enforced.   If no such path variable is set, the system looks uses 
    DataEnvironmentDirectory as the default, e.g everything in the 
    DataEnvironment would be protected if the PROTECTION variable
    is set at 'ON'.
    '''
    env = os.environ
    if isinstance(r,str) and len(r) > 0:
        if r[0] != '/':
            r = normpath(getcwd() + '/' + r)
            
        if 'ProtectedPathsListFile' in env.keys():
            ProtList = [x for x in open(env['ProtectedPathsListFile'],'r').split('\n') if not x.strip(' ').startswith('#')]
        else:
            ProtList = [WORKING_DE.root_dir]

            
        return not any([PathAlong(r,x) for x in ProtList])
    else:
        return False


def GetDependsCreates():

    """
    This function performs call stack analysis looking to capture and 
    aggregate the settings of the two protected key-word variables 
    "depends_on' and "creates" that are present up the stack. 
    
    RETURNS:
    --[dlist,clist] where:
    If the "PROTECTION" variable is set to 'ON':
        dlist is the aggregate tuple of depends_on values seen 
        up the stack tree, and clist is the aggregate tuple of 
        creates values. 
        
        If 'SystemMode' environment variable is set at 'Exploratory', 
        it adds '../' to the dlist, (which will be interpreted to allow
        unlimited read access) -- the idea being that at the user prompt, 
        mostly the user will want to be able to at least read whatever 
        files he/she wants, even he/she cannot then write back to those
        paths.   
        
    else:
        clist and dlist are set to '../', which will be interpreted by system 
        i/o intercepting functions that call GetDependsCreates to mean 
        that unlimited read/write access is granted. 
        
    '../Temp' is appended to clist and dlist in all cases, to allow the user 
    to read and write whatever is desired in working Temp directory. 
        
    Probably a more flexible and less hard-coded way of allowing the
    user to set these read-write protections would be useful in the future.
    """

    level = 0
    dlist = ('../Temp/',)
    clist = ('../Temp/',)
    AtTop = False
    while not AtTop:
        Fr = sys._getframe(level)
        name = Fr.f_code.co_name
        if name in Fr.f_globals.keys():
            func = Fr.f_globals[name]
            if hasattr(func, '__depends_on__'):
                dlist += MakeT(func.__depends_on__)
            if hasattr(func, '__creates__'):
                clist += MakeT(func.__creates__)
        if 'depends_on' in Fr.f_locals and not isinstance(Fr.f_locals['depends_on'], types.FunctionType):
            dlist += MakeT(Fr.f_locals['depends_on'])
        if 'creates' in Fr.f_locals and not isinstance(Fr.f_locals['creates'], types.FunctionType):
            clist += MakeT(Fr.f_locals['creates'])
    
        if sys._getframe(level).f_code.co_name !=  '<module>':
            level += 1
        else:
            AtTop = True
            
    __env = os.environ
    if sys._getframe(level).f_code.co_name ==  '<module>':
        Fr = sys._getframe(level)
        if WORKING_DE.protection == 'ON':
            if WORKING_DE.system_mode == 'EXPLORATORY':
                dlist += ('../',)
        else:
            clist += ('../',)
            dlist += ('../',)
    return [dlist,clist]

def io_override(DE):
    global WORKING_DE
    WORKING_DE = DE
    old_open = __builtin__.open
    def system_open(ToOpen,Mode='r',bufsize=1):
        [DependencyList,CreatesList] = GetDependsCreates()
        if IsntProtected(ToOpen) or any([PathAlong(ToOpen,r) for r in CreatesList]) if ('w' in Mode or 'a' in Mode) else any([PathAlong(ToOpen,r) for r in CreatesList + DependencyList]):  
            return old_open(ToOpen,Mode,bufsize)
        else:
            print funcname(),caller(3),ToOpen if ('w' in Mode or 'a' in Mode) else None,DependencyList,CreatesList
            raise BadCheckError(funcname(),ToOpen if 'r' in Mode else None,ToOpen if ('w' in Mode or 'a' in Mode) else None,DependencyList,CreatesList)
    __builtin__.open = system_open
    
    
    old_copy = shutil.copy
    def system_copy(tocopy,destination):
        [DependencyList,CreatesList] = GetDependsCreates()
        Check = (IsntProtected(tocopy) or any([PathAlong(tocopy,r) for r in DependencyList+CreatesList])) and (IsntProtected(destination) or any([PathAlong(destination,r) for r in CreatesList]))
        if Check:
            old_copy(tocopy,destination)    
        else: 
            raise BadCheckError(funcname(),tocopy,destination,DependencyList,CreatesList)
    shutil.copy = system_copy   
    
    
    old_copy2 = shutil.copy2
    def system_copy2(tocopy,destination):
        [DependencyList,CreatesList] = GetDependsCreates()
        Check = (IsntProtected(tocopy) or any([PathAlong(tocopy,r) for r in DependencyList+CreatesList])) and (IsntProtected(destination) or any([PathAlong(destination,r) for r in CreatesList]))
        if Check:
            old_copy2(tocopy,destination)   
        else: 
            raise BadCheckError(funcname(),tocopy,destination,DependencyList,CreatesList)
    shutil.copy2 = system_copy2 
    
    
    old_copytree = shutil.copytree
    def system_copytree(tocopy,destination,symlinks=False):
        [DependencyList,CreatesList] = GetDependsCreates()
        Check = (IsntProtected(tocopy) or any([PathAlong(tocopy,r) for r in DependencyList+CreatesList])) and (IsntProtected(destination) or any([PathAlong(destination,r) for r in CreatesList]))
        if Check:
            old_copytree(tocopy,destination,symlinks=symlinks)  
        else: 
            raise BadCheckError(funcname(),tocopy,destination,DependencyList,CreatesList)
    shutil.copytree = system_copytree
    
    
    old_mkdir = os.mkdir
    def system_mkdir(DirName,mode=0777):
        CreatesList = GetDependsCreates()[1]
        if IsntProtected(DirName) or sum([PathAlong(DirName,r) for r in CreatesList]) > 0:
            old_mkdir(DirName,mode)
        else:
            raise BadCheckError(funcname(),None,DirName,[],CreatesList)
    os.mkdir  = system_mkdir
    
    
    
    def old_makedirs(DirName,mode=0777):
        if not old_exists(DirName):
            DirName = DirName.rstrip('/')
            [cont,loc] = os.path.split(DirName)
            if not old_exists(cont):
                old_makedirs(cont)
            old_mkdir(DirName)
        else:
            raise ValueError, "Directory already exists."
    
    def system_makedirs(DirName,mode=0777):
        CreatesList = GetDependsCreates()[1]
        if IsntProtected(DirName) or any([PathAlong(DirName,r) or PathAlong(r,DirName) for r in CreatesList]):
            old_makedirs(DirName,mode)   
        else:
            raise BadCheckError(funcname(),None,DirName,[],CreatesList)
    os.makedirs = system_makedirs

    def old_makedirs2(DirName,mode=0777):
        if not old_exists(DirName):
            DirName = DirName.rstrip('/')
            [cont,loc] = os.path.split(DirName)
            if not old_exists(cont):
                old_makedirs(cont)
            old_mkdir(DirName)
    
    def system_makedirs2(DirName,mode=0777):
        CreatesList = GetDependsCreates()[1]
        if IsntProtected(DirName) or any([PathAlong(DirName,r) or PathAlong(r,DirName) for r in CreatesList]):
            old_makedirs2(DirName,mode)   
        else:
            raise BadCheckError(funcname(),None,DirName,[],CreatesList)
    os.makedirs2 = system_makedirs2
    
    
    
    old_rename = os.rename
    def system_rename(old,new):
        CreatesList = GetDependsCreates()[1]
        if (IsntProtected(old) or any([PathAlong(old,r) for r in CreatesList])) and (IsntProtected(new) or any([PathAlong(new,r) for r in CreatesList])):       
            old_rename(old,new)
        else:
            raise BadCheckError(funcname(),None,[old,new],[],CreatesList)
    os.rename = system_rename
    
    old_remove = os.remove
    def system_remove(ToDelete):
        CreatesList = GetDependsCreates()[1]
        if IsntProtected(ToDelete) or any([PathAlong(ToDelete,r) for r in CreatesList]):
            old_remove(ToDelete)
        else:
            raise BadCheckError(funcname(),None,ToDelete,[],CreatesList)
    os.remove = system_remove
            
    old_rmtree = shutil.rmtree
    def system_rmtree(ToDelete,ignore_errors=False,onerror=None):
        CreatesList = GetDependsCreates()[1]
        if IsntProtected(ToDelete) or any([PathAlong(ToDelete,r) for r in CreatesList]):
            old_rmtree(ToDelete,ignore_errors=ignore_errors,onerror=onerror)
        else:
            raise BadCheckError(funcname(),None,ToDelete,[],CreatesList)        
    shutil.rmtree = system_rmtree
    
    old_exists = os.path.exists
    def system_exists(ToCheck):
        [DependencyList,CreatesList] = GetDependsCreates()
        if IsntProtected(ToCheck) or any([PathAlong(ToCheck,r) for r in DependencyList+CreatesList]):
            return old_exists(ToCheck)
        else:
            raise BadCheckError(funcname(),ToCheck,None,DependencyList+CreatesList,None)
    os.path.exists = system_exists
    
    
    old_listdir = os.listdir
    def system_listdir(ToList):
        [DependencyList,CreatesList] = GetDependsCreates()
        if IsntProtected(ToList) or any([PathAlong(ToList,r) for r in DependencyList+CreatesList]):
            return old_listdir(ToList)
        else:
            raise BadCheckError(funcname(),ToList,None,DependencyList+CreatesList,None)
    os.listdir = system_listdir
            
            
    old_isfile = os.path.isfile 
    def system_isfile(ToCheck):
        [DependencyList,CreatesList] = GetDependsCreates()
        if IsntProtected(ToCheck) or any([PathAlong(ToCheck,r) for r in DependencyList+CreatesList]):
            return old_isfile(ToCheck)
        else:
            BadCheckError(funcname(),ToCheck,None,DependencyList+CreatesList,None)  
    os.path.isfile  = system_isfile     
    
    
    old_isdir = os.path.isdir
    def system_isdir(ToCheck):
        [DependencyList,CreatesList] = GetDependsCreates()  
        if IsntProtected(ToCheck) or any([PathAlong(ToCheck,r) for r in DependencyList+CreatesList]):
            return old_isdir(ToCheck)
        else:
            BadCheckError(funcname(),ToCheck,None,DependencyList+CreatesList,None)
    os.path.isdir = system_isdir
    
    
    old_mtime = os.path.getmtime
    def system_getmtime(ToAssay):
        [DependencyList,CreatesList] = GetDependsCreates()
        if IsntProtected(ToAssay) or any([PathAlong(ToAssay,r) for r in DependencyList+CreatesList]):
            return old_mtime(ToAssay)
        else:
            BadCheckError(funcname(),ToAssay,None,DependencyList+CreatesList,None)
    os.path.getmtime = system_getmtime
    
    
    old_atime = os.path.getatime
    def system_getatime(ToAssay):
        [DependencyList,CreatesList] = GetDependsCreates()  
        if IsntProtected(ToAssay) or any([PathAlong(ToAssay,r) for r in DependencyList+CreatesList]):
            return old_atime(ToAssay)
        else:
            BadCheckError(funcname(),ToAssay,None,DependencyList+CreatesList,None)
    os.path.getatime = system_getatime  
    
    
    
    
    
    
    
    
    
    
    
