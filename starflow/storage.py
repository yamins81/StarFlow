'''
===========
Routines for storing and retrieving information about files and python objects. 
===========

In the Data Environment, which is devoted to understanding and managing dependency links, 
routines throughout the system often require stored information about files, directories, 
functions, and data structures.   This information may include:
        
1) Information that can't directly be determined by analyzing the file or directory:  
for example, the file's last modification-time or create-time.    This information is 
often necessary to determine when an object has changed, so as to know when to 
trigger the re-running of a process that depends on the object.   This is the case
with the function PropagateThroughLinkGraphWithTimes, in the LinkManagement 
module, which needs to compare link target's mod times to link source's mod 
times to know when to re-run a data-creation script. 

or,     

2) Information that is that _is_ possible to glean upon complex introspection but hard 
to obtain otherwise: for example, the list of names of python functions that might be called 
by another function during its run.  This information is useful to analyze an object to 
determine what its dependencies are in the first place.   This is the case with the function 
ComputeLinksFromOperations, which determines the data "depends_on" and "creates", 
and functional "uses",  from a python function's code.  
        
This module provides a unified interface to obtain such information so that  it can be 
called up wherever needed.   The key realizaion is that providing unified access to the
relevant information about the objects boils down to having a unified method for 
_storing_ and retrieving "stylized versions" of those objects,  versions that contain 
somewhat detailed information about the objects' parts, as well as information about
when those parts were last modified.   

The reasons we've decided to make this as unified interface to storage data are:

1) if you need to get information about when an object has changed, you'll need to have a 
stored version that can be compared to the current version to detect chages, together 
with timing information about each of those stored parts so that if the part _hasn't_ 
changed you can tell what the last actual mod-time of the part was. 

and     

2) to provide easy access to complex introspected information, it makes sense to 
compute that introspection only once per object per modification, and store the
results of that introspection in a standardized format in a single place. 
        
The  "data model" behind our approach to doing this enables us to be as lazy as possible, 
leaving as much to operating system as we can.  The basic idea is that every object 
stored on disk in the Data Environment file system is one of two things:
    1) A directory or a file inside a directory  -- whose properties are "at the operating system level" 
        and which don't need to be made "live" to access
or
    2) an implied object __inside__ a file -- whose properties are "more specific than
    the operating system level" and which require some form of "being live" to access
        
For instance, a python package consists of a directory containing python .py files, and
in turn each py file is a module containing python objects.  Or a relational database, 
which is at one level a filesystem, but which at a lower level consists of records. 

Now, for information about things at the files and directories levels, we are able to 
rely mostly on things provided by the operating system: it obviously already stores 
the files themselves, and provides access to file and directory modification 
information, through things like the 'stat' and 'diff' utilities.     However, for finer 
detail, we need to supplement the operating system.   The basic strategy is:
    -- for each of several "Special Supported File Types", store information about the 
    more detailed parts of the supported file type
and then
    -- provide an _extension_ of the stat and diff utilities that allows queries to specify 
    both a file path, as well as a more detailed  part-name.

For instance, the standard python implementation of the path mod-time function is 
'getmtime' function in the the os.path module.  The function os.path.getmtime takes
as argument a single path, and returns the time of last modification of that path.   
Here, we extend that function to the FindMtime function which takes both a pathname 
argument, as well as an "object-name" argument, and which returns the mod-time of 
that specific object.  For the moment, we only have one "Special Supported File Type":  
python modules ; so the "objectname" argument boils down to a "function-name" 
argument that allows one to find the mod-time for a given function in a module.   
All other files are treated at the atomic level.  (In the future, other kinds of file parts
could be stored, e.g. records in a database by integrating database query routines .... etc...)
    
'''


from starflow.utils import *
import marshal
import cPickle
import os
import types
import hashlib
import traceback
import starflow.staticanalysis
import starflow.de as de
DE_MANAGER = de.DataEnvironmentManager()
WORKING_DE = DE_MANAGER.working_de

def FindMtime(path,objectname= '',HoldTimes = None,Simple=True,
          depends_on = WORKING_DE.relative_modules_dir,creates = WORKING_DE.relative_modules_dir):

    ''' 
    This is the main unified interface to path and path-part mod times that 
    is to be used throughout the system.  
    
    ARGUMENTS:
    --path = path whose mod-time is to be assessed  
    --objectname = name of object within that path, whose mod-time is to be assessed. 
    --HoldTimes = Dictionary, where:
        --keys are paths
        --HoldTimes[Path] is a timestamp that the system is meant to "pretend" 
        is the mod time of Path, if Path comes up as a source or target during the 
        propagation process, instead of computing the real mod time. 
    -- Simple = Boolean : if True, only looks just at the modtime of path; if False, 
    and if path is a directory, it looks recursively through the mod times of files
    inside path and returns the maximum.  

    RETURNS:
    -- floating point number representing a mod-time, in seconds since the start of the  
    Unix Epoch.  (Jan 1, 1970 at 00:00:00 GMT). 
        
    NB: For the moment, the object name parameter only does anything if the path
    is a python module, and if then only if the objectname names an object defined 
    in that python module.   The way this is determined is by a combination of
    "live analysis" -- e.g importing the python module and inspecting its contents 
    via introspection methods;  and "static analysis" which relies on analyzing 
    python code without importing the module but which does require building 
    the compiler parse tree for the code.  If either the importing step or the 
    compiler parse-tree step fails, the function just returns the mod-time of the 
    file that the module is in.  [All of this is sort of built haphazardly in to the 
    way the FindMtime function and its depedencies are written.  In the future, 
    to accommodate other "Special File Types", the way this and associatd 
    functions are written would be to be made more modular.] 

'''


    if Simple or IsFile(path):  
        if HoldTimes == None or not path in HoldTimes.keys():
            pname = path[3:-3].replace('/','.')     
            if not IsFile(path) or objectname == '' or not (path.split('.')[-1] == 'py' and objectname.startswith(pname + '.')):
                return os.path.getmtime(path)
            else:
                objectname = objectname[len(pname)+1:]
                StoredModuleTimes = GetStoredModuleTimes(path)
                if StoredModuleTimes != None and objectname in StoredModuleTimes.keys():
                    return StoredModuleTimes[objectname]
                else:
                    return os.path.getmtime(path)
        else:
            return HoldTimes[path]
    elif IsDir(path):
        if path[-1] != '/':
            path += '/'
        Mtime = FindMtime(path,objectname=objectname,HoldTimes=HoldTimes,Simple=True)
        if len(listdir(path)) > 0:
            return max(Mtime,max([FindMtime(path + element,objectname=objectname,HoldTimes=HoldTimes,Simple=False) for element in listdir(path)]))
        else:
            return Mtime

def ListFindMtimes(FileParts,HoldTimes = None,Simple=True,
          depends_on = WORKING_DE.relative_modules_dir,creates = WORKING_DE.relative_modules_dir):
    '''
    Given a list of files and objects within those files, computes mtimes for them. 
    This is an optimization on top of FindMtimes, by inspecting a list of file/object pairs,
    then analyzing the uniquely mentioned files only once. 
    
    ARGUMENTS:
    --FileParts: a python list of pairs (FileName, ObjectName) each of which is to 
    be analyzed for mod-time.   If only a FileName is meant to provided, 
    e.g. no subpart is to be looked for, just the mod-tiem fo the whole file, 
    than ObjectName should be set to equal FileName.  
        
    For instance to get the modtime of the function "GetBasketBallTeams"
    in the file:
    
    '../Users/Elaine/Playbox/Sports/ESPN_NBA/NBA_Teams.py' 
    
    you'd include in the list the pair:
    
    ('../Users/Elaine/Playbox/Sports/ESPN_NBA/NBA_Teams.py',
    'Users.Elaine.Playbox.Sports.ESPN_NBA.NBA_Teams.GetBasketBallTeams')
    
    but to get the modtime of the file:
    
    '../Users/Elaine/Playbox/Sports/ESPN_NBA/NBATeamData.data', 
    
    you'd include the pair
    
    ('../Users/Elaine/Playbox/Sports/ESPN_NBA/NBATeamData.data', '../Users/Elaine/Playbox/Sports/ESPN_NBA/NBATeamData.data')
        
    --HoldTimes, Simple are the same as the correpsonding FindMtimes arguments
    --Parallel = boolean indicating whether the function should be executed in 
    parallel on multiple processors in a machine (if available)
    
    Returns:
    A dictionary, where:
        --the keys are the unique object names (which are same as the
        file names when no specific sub-object is to be given) 
        --the value at a key is the same as would be there if 
        FindMtims(FileName,ObjectName) were called. 
    
    '''
    
    FileParts = numpy.rec.fromrecords(FileParts,names = ['File','Object'])
    FileParts.sort(order = ['File'])
    F = FileParts['File']
    Diffs = numpy.append([0],(F[1:] != F[:-1]).nonzero()[0] + 1)
    
    UniqueFiles = F[Diffs]
    TimesDict = dict([(f,FindMtime(f,HoldTimes=HoldTimes,Simple=Simple) if PathExists(f) else numpy.nan) for f in UniqueFiles])
    
    SpecialFiles = numpy.array([f for f in UniqueFiles if IsFile(f) and f.split('.')[-1] == 'py'])
            
    if len(SpecialFiles) > 0:
        UpdateModuleStorage(SpecialFiles)
            
    Mtimes = numpy.zeros(F.shape)   
    for i in range(len(Diffs)-1):
        Mtimes[Diffs[i]:Diffs[i+1]] = TimesDict[F[Diffs[i]]]
    Mtimes[Diffs[-1]:] = TimesDict[F[Diffs[-1]]]
    
    G = fastisin(Diffs,fastisin(F,SpecialFiles).nonzero()[0]).nonzero()[0]
    A = zip(G,Diffs[G])
    
    for (K,i) in A:
        [StoredModulePath,StoredModuleTimesPath]  = GetStoredPathNames(F[i])
        if PathExists(StoredModuleTimesPath):
            TD = cPickle.load(open(StoredModuleTimesPath,'rb'))
            TDK = numpy.array(TD.keys())
            TDK.sort()
            next = Diffs[K+1] if K+1 < len(Diffs) else len(F)
            path = F[i]
                        
            pname = path[3:-3].replace('/','.')
            EE = numpy.array([FileParts['Object'][j].startswith(pname + '.') for j in range(i,next)])
            sfnames = numpy.array([str(FileParts['Object'][j][len(pname)+1:]) for j in range(i,next)])

            E = EE & fastisin(sfnames,TDK)
            
            OnF = sfnames[E]

            On = numpy.array(range(i,next))[E]
            Mtimes[On] = numpy.array([TD[fn] for fn in OnF])
            
    
    return dict(zip(FileParts['Object'],Mtimes))


def BlockUpdateModuleStorage(L):
    for l in L:
        UpdateModuleStorage(l)
        


def GetStoredModule(path):
    '''
    Returns stored module for the python module whose file is at 'path'.   
    If the module storage update process fails, this function returns None. 
    The format of the returned object is a dictionary where each key is the 
    name of the module parts, and the value at the key is the instance of the 
    StoredModulePart class for that part.  (see below in StoredModulePart for details)
    '''

    UpdateModuleStorage(path)
    [StoredModulePath,StoredModuleTimesPath]  = GetStoredPathNames(path)
    try:
        return cPickle.load(open(StoredModulePath,'rb'))
    except:
        return 
    else:
        return
        
def GetStoredModuleTimes(path):
    '''
    Returns stored module's mod times for the python module whose file is at 'path'.   
    If the module storage update process fails, this function returns None. 
    The format of the returned object is: a dictionary whose keys are the 
    same as the keys of the stored module dctionary, and whose values on
    those keys are mod times for the parts.   (There's an extra key called '__hash__' 
    which stores a hash of the stored module dictionary to ensure data integrity
    upon update.) 
        
    '''
    UpdateModuleStorage(path)
    [StoredModulePath,StoredModuleTimesPath]  = GetStoredPathNames(path)
    try:
        return cPickle.load(open(StoredModuleTimesPath,'rb'))
    except:
        return 
    else:
        return
    
    
def GetNestedObject(name,Members):
    '''
        Technical dependency of ExtractParts
    '''

    if name in Members.keys():
        return Members[name]
    else:
        for mname in Members.keys():
            if is_string_like(name) and name.startswith(mname + '.') and isinstance(Members[mname],types.ModuleType):
                return GetNestedObject(name[len(mname)+1:],dict(inspect.getmembers(Members[mname])))
    
    
def GetExtendedMembers(obj,Static):
    '''
        Technical dependency of ExtractParts
    '''
    
    if isinstance(obj,dict):
        Members = obj
    else:
        Members = dict(inspect.getmembers(obj))
    
    for k in Static.keys():
        obj = GetNestedObject(k,Members)
        if obj != None:
            Members[k] = obj
            
    return Members
    
    
def GetExtendedExecedNames(Execed,Static):
    '''
        Technical dependency of ExtractParts
    '''
    
    Names = Execed.keys()

    for k in Static.keys():
        obj = GetNestedObject(k,Execed)
        if obj != None:
            Names.append(k)
            
    return Names
    
    
def ExtractParts(obj,Execed=None,Static=None,ScopeName=None):
    '''
    Given a python object obj, extract it for storage.   This is called by the function
    UpdateModuleStorage and the class StoredModulePart. 
    
    ARGUMENTS:
    --obj = the python object to get stored parts of --- as "made live" by having 
        been imported in a module ultimately in UpdateModuleStorage.   
    --Execed = an _execfile'd__ version of the same object, as opposed to imported.  
    --Static = the static analysis version of the object. 
        
    Returns:
    --Dictionary whose keys are the names of parts of the object and whose 
    values on each key are the stored versions of the part with that name.
        
    NOTE:  The execfiled and static analysis objects supplement and 
    verify the information stored about the object. 
    '''


    if Static == None:
        Static = {}
        
        
    if not ScopeName and hasattr(obj,'__name__'):
        ScopeName = obj.__name__

    Members = GetExtendedMembers(obj,Static)

    if Execed == None:
        Allowed = Members.keys()
    else:
        Allowed = GetExtendedExecedNames(Execed,Static)
    AllowedNames = set(Members.keys()).intersection(Allowed)

    Parts = dict([(k,StoredModulePart(Members[k],ScopeName=ScopeName,Static = Static[k] if k in Static.keys() else None)) for k in AllowedNames])
    
    return Parts
            
        
        
def UpdateModuleStorage(path,creates = WORKING_DE.relative_root_dir):  
    '''
    Updates the file storing the module at path 'path', as well
    as the file storing the mod-times for those parts.   
    
    ARGUMENT:
    -- path = the path of the module whose storage is to be updated 
            
    RETURNS:
    -- Nothing.  But it updates the module storage.   To get at the 
    stored objects you use one of the two functions 
    (GetStoredModule or GetStoredModuleTines)
            
    The basic format of storage is:  given a module file, to associate 
    two storage files with it:  
        1) a file containing a pickling of a StoredModule dictionary 
        containing stored versions of the parts of the module, 
        at path StoredModulePath, and 
        2) a file containing a pickling of a StoredModuleTimes dictionary
        containing the Modtimes for each of the stored parts, 
        at path StoredTimesPath.  
    
    The StoredModule dictionary's format is to associated to each part-name
    an instance of the StoredModulePart class:
        StoredModule[ part-name ] =   StoredModulePart(part), 
    See comments in StoredModulePart class for details. 
            
    The StoredModuleTimes format is a dictionary whose keys are the same
    as the keys of the StoredMdule dictionary, and whose values on those
    keys are mod times for the parts.   
    (There's an extra key called '__hash__' which stores a hash of the stored
    module dictionary to ensure data integrity upon update.) 
        
    The reason that the StoredTimes file is stored separately from the 
    StoredModules file, instead of in one big dictionary is that this way, 
    the much smaller StoredTimes dictionary can be loaded for use in 
    evaluating functions like FindMtime, without having to lead the 
    whole module storage.  
    
    This function basically has two stages:
    
    1) First, determine whether the module's object storage is:
        -- Update to date, in which case nothing has to be done
        -- In OK format but may not be up to date, in which
            case the module nees to be imported and analyzed, 
            the results compared to the stored version
        -- Non-existent or somehow contaminated or in the wrong format,
            in which case it needs to be remade from scratch.               
                
    2) Having determined which state the storage is in, and if the 
    module storage needs to be updated, act upon that.    
    The action consists of:
        - pickle-loading the StoredModule already on disk if it exists, 
            (as well as the stored module mod times, which is already 
            unpickled in stage 1 of this function) 
        -- computing a new version of the stored module,
        -- for each part in the new Stored module, comparing it to the stored 
            version already on disk, and if the part hasn't changed, retain the old mod time,
            but if it has changed or is a new part not yet stored, set the stored 
            mod time the mod time of the file the module is in. 
            -- if the part has been removed, remove it from storage. 
            
    Along the way, the function prints out small messages describing
    the modification state of parts, if any modifications appear to have been made.             
    '''

    
    if is_string_like(path):
        paths = path.split(',')
    else:
        paths = path
    paths = uniqify(paths)

    for path in paths:
        if PathExists(path):
            [StoredModulePath,StoredTimesPath]  = GetStoredPathNames(path)
            DirName = os.path.dirname(StoredModulePath)
            assert DirName == os.path.dirname(StoredTimesPath), "dirnames don't match"
            if not PathExists(DirName):
                MakeDirs(DirName)           
            Remake = False
            if not PathExists(StoredTimesPath):
                Remake = True
            else:
                try:
                    StoredTimes = cPickle.load(open(StoredTimesPath,'rb'))
                except:
                    Remake = True
                else:   
                    if not PathExists(StoredModulePath) or not isinstance(StoredTimes,dict) or not '__hash__' in StoredTimes.keys():
                        Remake = True
                    else:
                        Hashmark = StoredTimes['__hash__'] 
                        if hashlib.sha1(open(StoredModulePath,'rb').read()).digest() != Hashmark:
                            Remake = True
        
            if Remake or  os.path.getmtime(path) > os.path.getmtime(StoredTimesPath):
            
                if Remake:
                    StoredTimes = {}
                    StoredModule = {}
                elif os.path.getmtime(path) > os.path.getmtime(StoredTimesPath):    
            
                    StoredModule = cPickle.load(open(StoredModulePath,'rb'))
                    if set(StoredTimes.keys()) != set(['__hash__']).union(set(StoredModule.keys())):
                        StoredTimes = {}
                        StoredModule = {}
                    
                ModuleName = '.'.join(path.split('/')[1:-1] + [ inspect.getmodulename(path) ])
                    
                try:     
                    AddInitsAbove(path)
                    exec('import ' + ModuleName + ' as Module') 
                    print reload(Module)
                    L = {}
                    execfile(path,L)
                    Static = starflow.staticanalysis.GetFullUses(path)
                except:
                    print 'The Module', ModuleName, 'isn\'t compiling, nothing stored.  Specifically:'
                    print traceback.print_exc()
                    return
                else:
                    Parts = ExtractParts(Module,Execed=L,Static=Static)
                    
                    MissingParts = set(StoredModule.keys()).difference(Parts.keys())
                    if len(MissingParts) > 0:
                        print [ModuleName + '.' + x for x in MissingParts], 'appear to have disappeared.'
                    
                    NewStoredModule = {}
                    NewStoredTimes = {}
                    for p in Parts.keys():
                        part = Parts[p]
                        NewStoredModule[p] = part
                        if p in StoredModule.keys():
                            if part == StoredModule[p]:
                                NewStoredTimes[p] = StoredTimes[p]
                            else:
                                NewStoredTimes[p] = os.path.getmtime(path)
                                print ModuleName + '.' + p , 'appears to have changed.' 
                                
                        else:
                            print ModuleName + '.' + p, 'appears to have been added.'
                            NewStoredTimes[p] = os.path.getmtime(path)
                                  
                    F = open(StoredModulePath,'w')
                    cPickle.dump(NewStoredModule,F)
                    F.close()
                    
                    NewStoredTimes['__hash__'] = hashlib.sha1(open(StoredModulePath,'r').read()).digest()           
            
                    F = open(StoredTimesPath,'w') 
                    cPickle.dump(NewStoredTimes,F)      
                    F.close()
        
    
    
class StoredModulePart():
    '''
    This class defines the storage for a module.    
    Calling StoredModulePart(object) creates a storable version of the live object. 
        
    If it were possible to pickle all kinds of python objects,  this class would be 
    unnecessary -- we'd just use the Pickle.dumps method.   However, it is not 
    possible to run standard python pickling on all python objects.  
    
    This is for two reasons:
            
    1) Some python objects require special pickling methods -- e.g. code objects
    require "marshal" -- because cPickle wasn't built to handle them 
    (for good reason).  But since we want to store many objects types together, 
    we have to have a single interface for all the various kinds of storing. 
            
    2) The standard of "being picklable" means that the pickle.load method 
    has to completely restore the unpickled object to fully functional form.  
    This is basically impossible for things like functions or class methods or 
    modules because they rely on defined names in the module context or 
    from other modules, so no pickling method for them exists.   But for our 
    purposes we don't actually need to require so high a standard of our 
    storage: we don't need to use the stored objects as live substitutes for 
    the real objects, we merely need just to be able to recover enough detail 
    to be able to determine whether the live real object differs in some
    material way from the stored one.  
        
    This StoredModulePart class basically does two things therefore: 
    1) unifies all the various pickling methods to do exist into a single interface, and 
    2) extracts data about the objects into a set of objects that are "dry" enough 
    that they _can_ be pickled, but which are descriptive enough to provide the 
    ability to make meaningful comparisons to check for modifications.  
        
    '''
    
    
    __module__ =  'starflow.storage'    #<-- this is specified so that instances of this class pickle correctly, even if they're instantiated at the command prompt.  pickled class instances are pickled with a reference to the module where the instance was made, and unless sthis is set, the value is wrong in the pickled object.  Unfortunately this is inconvenient because if you change the location of this class you have to change the setting of this function, invalidating all the pickled class instances .... ugh.  A better solution is required. 
    def __init__(self,obj,ScopeName=None,Static=None,recursive = False):
        self.static = Static
        self.typestr = repr(type(obj))
        self.eqmethod = ''
        if type(obj) == types.CodeType:
            [self.loadmethod, self.descr, self.content, self.eqmethod] =  ['marshal','Code Object',marshal.dumps(obj),'CodeEquals']
        elif type(obj) == types.FunctionType:
            if not ScopeName or obj.__module__ == ScopeName:
                [self.loadmethod, self.descr, self.content] =  ['Reconstitute','Internal Function',FunctionDumps(obj)]      
            else:
                [self.loadmethod, self.descr, self.content] =  ['','Imported Function', {'__name__':obj.__name__,'__module__':obj.__module__}]
        elif type(obj) == types.ClassType:
            if not ScopeName or obj.__module__ == ScopeName:
                [self.loadmethod, self.descr, self.content] =  ['Reconstitute','Internal Class', ExtractParts(obj)]
            else:
                [self.loadmethod, self.descr, self.content] =  ['','Imported Class', {'__name__':obj.__name__,'__module__':obj.__module__}]
        elif type(obj) == types.MethodType:
            [self.loadmethod, self.descr, self.content] =  ['Reconstitute','Class Method', ClassMethodDumps(obj)]
        elif type(obj) == types.ModuleType:
            self.loadmethod = ''
            self.descr = 'Imported Module'
            self.content = obj.__name__
        elif recursive:
            P = ExtractParts(obj,ScopeName=ScopeName)
            [self.loadmethod, self.descr, self.content] = ['Reconstitute','StoredObj',P]        
        else: 
            try:
                c = cPickle.dumps(obj)
            except:
                [self.loadmethod, self.descr, self.content] = [None,'Unpicklable',repr(obj)]    
            else:
                [self.loadmethod, self.descr, self.content,self.eqmethod] = ['cPickle','',c,'cPickle']
        
        
    def reconstitute(self):
        if self.loadmethod in [None,'']:
            return self.content
        elif self.loadmethod == 'marshal':
            return marshal.loads(self.content)
        elif self.loadmethod == 'cPickle':
            return cPickle.loads(self.content)
        elif self.loadmethod == 'Reconstitute':
            return dict([(p,self.content[p].reconstitute()) if 'reconstitute' in dir(self.content[p]) else (p,self.content[p])  for p in self.content.keys()])
        else:
            print 'Load method not recognized'
            return None
        
        
    def __eq__(self,other):
        if isinstance(other,type(self)):
            if self.static != other.static:
                return False
            if self.eqmethod == '':
                return self.content == other.content
            elif self.eqmethod == 'CodeEquals':
                c1 =self.reconstitute(); c2 = other.reconstitute()
                return CodeEquals(c1,c2)
            elif self.eqmethod == 'ModuleNameEquals':
                return ModuleNameEquals(self.content,other.content)
            elif self.eqmethod == 'cPickle':
                if self.content == other.content:
                    return True
                else:
                    return self.reconstitute() == other.reconstitute()
            else:
                print 'eqmethod not recognized'
        else:
            return False
        
def ClassMethodDumps(obj):  
    '''
        Storage method for class methods. 
    '''
    return {'__classname__':obj.im_class.__name__, 'im_func': StoredModulePart(obj.im_func)}

def FunctionDumps(obj):
    '''
        Storage method for functions.
    '''
    
    
    A = {'__name__':obj.__name__,'__module__':obj.__module__,'func_code':StoredModulePart(obj.func_code),'func_defaults':StoredModulePart(obj.func_defaults)}
    if obj.func_dict != {}:
        #A['func_dict'] = dict([(k,StoredModulePart(v)) for (k,v) in obj.func_dict.items()])
         A['func_dict'] = StoredModulePart(obj.func_dict,recursive = True,ScopeName=obj.__module__)
    
    return  A
        
        
def CodeEquals(c1,c2):
    '''
        Equality testing for code objects. 
    '''

    if isinstance(c1,types.CodeType) and isinstance(c2,types.CodeType):
        con1 = c1.co_consts[1:]; con2 = c2.co_consts[1:]
        return (c1.co_code == c2.co_code) and len(con1) == len(con2) and all([CodeEquals(a,b) for (a,b) in zip(con1,con2)]) and  (c1.co_flags == c2.co_flags) and  (c1.co_varnames == c2.co_varnames)
    else:
        return c1 == c2
        
def ModuleNameEquals(s,o):
    m = min(len(s),len(o))
    return abs(len(s) - len(o)) <= 1 and o[:m-2] == s[:m-2]
    

def StoredDocstring(path):
    Docstring = ''
    if IsDotPath(path):
        ModPath = '../' + path[:path.rfind('.')].replace('.','/') + '.py'
        Fnname = path.split('.')[-1]
        StoredModule = GetStoredModule(ModPath)
        if StoredModule != None:
            if Fnname in StoredModule.keys():
                StoredFn = StoredModule[Fnname]
                ds =  StoredFn.content['func_code'].reconstitute().co_consts[0]
                if isinstance(ds,str):
                    Docstring += ds
    elif IsPythonFile(path):
        StoredModule = GetStoredModule(path)
        if StoredModule != None:
            if '__doc__' in StoredModule.keys():
                Docstring += StoredModule['__doc__'].reconstitute()
                
    return Docstring

def GetStoredPathNames(path):
    '''
        Determines path names from stored module and stored module times obects, 
        from path name of the module to be stored. 
    '''

    StoredPath = os.path.join(WORKING_DE.modules_dir, path.strip('../').replace('/','__') )
    return [os.path.join(StoredPath ,'.ModuleStorage'), os.path.join(StoredPath,'.ModuleTimes')]
