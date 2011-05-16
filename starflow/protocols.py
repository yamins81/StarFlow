#!/usr/bin/env python
'''
Functions for implementing data protocols.
'''


import sys
import os
import inspect
import time
import shutil
import types
import pickle
import re

import numpy

import starflow.metadata
from starflow import exception
from starflow.utils import *
from starflow import de
DE_MANAGER = de.DataEnvironmentManager()
WORKING_DE = DE_MANAGER.working_de

def actualize(OpThing, outfilename = None, outfiledir = None, WriteMetaData = True, importsOnTop = True, instance_id = None):

    '''
    Function which implements the basic protocol concept.  
    Given an 'OpThing', which is a set of descriptions of operations 
    and corresponding arguments to be passed to the operations, 
    this writes out a python module with functions making the calls.
    
    ARGUMENTS:
    outfilename = pathname for the output python module, must end with .py
    OpThing = dictionary or list.  
    1) if dictionary, then:
    -- the keys are strings representing names for the concrete operations in the
        written-out python file 
    -- for each key, say 'FName' the value is a 3-tuple: (function, internal arguments,  external arguments)
        where:
    --function is the function -- the actual python function object, NOT the just the
        function name -- to be called as the body of FName
                    
    --internal arguments are values for the arguments to be pased to FName
    The internal arguments can be given in one of several forms:
        --a tuple of positional arguments
        --a dictionary of keyword arguments
        --a 2-element list [t,d] where t is a tuple 
        of positional arguments and d is a
        dictionary of keyword arguments
    
    --external arguments is a dictionary where:
        the keys are names of keyword arguments for FName
        the values are the default values for the keyword arguments
                        
    2) if a list then:
        each element of the list is a 4-tuple
        
        (FName, function, internal arguments, external arguments)
        
        where all these are as described just above.  
        The only difference between the list-frmat input and 
        the dictionary format input is that the list format
        takes the keys of th dictionary and makes the
        first element of the tuples in the list 
        (which are now 4-tuples, as opposed to 3-tuples in 
        the dictionary case). 
        
        The reason for the list format is that it the operations 
        are written out to the file in the order specified in the list,
        whereas with a dictionary the order is  determined by the 
        order of writing out the keys of the dictionary, which is
        often not the "natural" ordering. 
    
    WriteMetaData: boolean, which if true has the operations write 
    metadata for th operations in the outputted module.
        
    RETURNS:
        NOTHING
    '''

    outfiledir = outfiledir or infer_instances_directory()
    prepare_instance_dir(outfiledir)
    
    if outfilename is None:
        outfilename = get_outfile(instance_id,outfiledir)


    if isinstance(OpThing,dict):
        OpList = [[s] + list(OpThing[s]) for s in OpThing.keys()]
    else:
        OpList = [list(x) for x in OpThing]
        
    OpList = OpListUniqify(OpList)
    ModulesToImport = uniqify([op[1].__module__ for op in OpList])
    
    oplines = []

    TagDicts = {}
    D = WORKING_DE.root_dir
    
    ProtocolName = callermodule()[len(D):].rstrip('.py').replace('/','.').lstrip('.') + '.' + caller()
    
    uses_args = False
    
    for i in range(len(OpList)):
        OpTagDict = {}
        
        assert len(OpList[i]) in [3,4], 'stepname and func and args must be specified'
        if len(OpList[i]) == 4:
            [stepname,func,args,deflinedict] = OpList[i]
        else:
            [stepname,func,args] = OpList[i]
            deflinedict = {}
            
        [argdict, deflinedict, LiveDict] = get_argdict(func, args, deflinedict)
            
        livetoimport = [func.__module__]
        if len(LiveDict) > 0:
            for (var,obj) in LiveDict.items():
                if isinstance(obj,str):
                    mod = '.'.join(obj.split('.')[:-1])
                else:
                    mod = obj.__module__
                    name = obj.__name__
                    argdict[var] = (mod + '.' + name) if mod != '__builtin__' else name
                if mod not in livetoimport and mod != '__builtin__':
                    livetoimport.append(mod)
                    
        internalimports = list(set(livetoimport).difference(ModulesToImport))
        if internalimports:
             if importsOnTop:
                op_importline = ''
                ModulesToImport += internalimports
             else:  
                op_importline = '\timport ' + ','.join(internalimports)
        else:
            op_importline = ''
            
        pickledict = {}
        for (k,v) in argdict.items():
            if not isinstance(v,str) or k not in LiveDict.keys():
                rep = repr(v)
                try:
                    is_equal = (eval(rep) == v)
                except:
                    is_equal = False
                
                if is_equal:
                    argdict[k] = repr(v)
                else:
                    uses_args = True
                    import cPickle
                    vname = get_vname(k)
                    picklefile = get_argfile(stepname,k,instance_id,outfiledir)
                    remake = True
                    if os.path.exists(picklefile):
                        try:
                            existing_v = cPickle.loads(open(picklefile).read())
                        except:
                            print('unpickling error for ', picklefile)
                        else:
                            if v  == existing_v:
                                remake = False
                    
                    if remake:
                        picklefh = open(picklefile,'w')
                        try:    
                            cPickle.dump(v,picklefh)
                        except:
                            picklefh.close()
                            os.remove(picklefile)
                            raise exception.ProtocolPickleError(k,v)
                        else:
                            picklefh.close()
                                           
                    pickledict[k] = (vname,picklefile)
                    argdict[k] = vname
                    deps = deflinedict.get('depends_on')
                    if deps:
                        if is_string_like(deps):
                            deflinedict['depends_on'] = (deps,picklefile)
                        else:
                            deflinedict['depends_on'] = deps + (picklefile,)
                    else:
                        deflinedict['depends_on'] = picklefile
                             
        intvals = [k for k in argdict.keys() if isinstance(k,int)]
        intvals.sort()
        posargs = tuple([argdict[k] for k in intvals])
        kwargs = dict([(k,v) for (k,v) in argdict.items() if not isinstance(k,int)])

        defline = 'def ' + stepname + '(' + ','.join([key + '=' + repr(deflinedict[key]) for key in deflinedict]) + '):'

        ArgList = list(posargs) + [k + '=' + v for (k,v) in kwargs.items()]
        ArgString = '(' + ','.join(ArgList) + ')'
        picklelines = '\n'.join(['\t' + vname + ' = cPickle.loads(open("' + picklefile + '").read())' for (vname,picklefile) in pickledict.values()])
        callline = '\tOpReturn = ' + func.__module__ + '.' + func.__name__ + ArgString
        returndefline = '\tReturnDict = OpReturn or {}\n\tReturnDict["__protocol_metadata__"] = {}'
        metadatadeflines = []
        StepTag = deflinedict['StepTag'] if 'StepTag' in deflinedict.keys() else stepname
        if 'creates' in deflinedict.keys():
            createlist = MakeT(deflinedict['creates'])
            for j in range(len(createlist)):
                metadatadeflines += ['\tReturnDict["__protocol_metadata__"]["' + createlist[j] + '"] = "This file is an instance of the output of step ' + StepTag + ' in protocol ' + ProtocolName + '."']
        metadatalines = '\n'.join(metadatadeflines)
        returnline = '\treturn ReturnDict'
        oplines.append( '\n'.join([defline, op_importline, picklelines, callline, returndefline, metadatalines, returnline]))
        
        Fullstepname = outfilename.lstrip('../').rstrip('.py').replace('/','.') + '.' + stepname
        OpTagDict[Fullstepname] = 'Protocol\ ' + ProtocolName + ',\ ' + StepTag + ':\\nApply ' + func.__name__
                
        if 'creates' in deflinedict.keys():
            createlist = MakeT(deflinedict['creates'])
            for j in range(len(createlist)):
                OpTagDict[createlist[j]] =  'Protocol\ ' + ProtocolName + ',\ ' + StepTag + '\\n Output\ ' + str(j)
                            
        TagDicts[Fullstepname]  = OpTagDict

    if uses_args:
        ModulesToImport.append('cPickle')
        
    importline = 'import ' + ','.join(uniqify(ModulesToImport))
    
    optext = importline + '\n\n\n' + '\n\n\n'.join(oplines)
    
    F = open(outfilename,'w')
    F.write(optext)
    F.close()
    
    AttachMetaData = starflow.metadata.AttachMetaData
    
    OpFileMetaData = {}
    OpFileMetaData['description'] = 'This python module was created by applying ' + funcname() + ' on the protocol ' + ProtocolName + '.'
    AttachMetaData(OpFileMetaData,FileName = outfilename)
    
    if WriteMetaData:
        for Fullstepname in TagDicts.keys():
            OpMetaData = {}
            OpMetaData['ProtocolTags'] = TagDicts[Fullstepname]
            OpMetaData['description'] = 'This operation is an instance of protocol ' + ProtocolName + '.'
            AttachMetaData(OpMetaData,OperationName = Fullstepname)

def infer_instances_directory():
    k = 2
    pathlist = []
    namelist = []
    while True:
        try:
            F = sys._getframe(k)
        except ValueError:
            raise exception.CannotInferProtocolTargetError(pathlist,namelist)
        else:
            path = F.f_code.co_filename
            pathlist.append(path)
            name = F.f_code.co_name
            namelist.append(name)
            func = F.f_globals[name]
            if hasattr(func,'__creates__'):
                break
            else:
                k += 1 
    instances_directory = func.__creates__[0]
    if not IsDir(instances_directory):  
        MakeDirs(instances_directory)   
    return instances_directory

def prepare_instance_dir(instances_directory):
    x = listdir(instances_directory)
    for y in x:
        if y.endswith(('.py','.pyc')):
            to_delete = os.path.join(instances_directory,y)
            print('deleting',to_delete)
            os.remove(to_delete)

def get_instance_id(instances_directory, instance_id):
    if instance_id == None:
        existing_ids = [f.split('.py')[0].split('_')[-1] for f in listdir(instances_directory)]
        existing_ids = [int(i) for i in existing_ids if i.isdigit()]
        if len(existing_ids) > 0:
            instance_id = max(existing_ids) + 1
        else:
            instance_id = 0
            
    return instance_id

def get_argfile(stepname,argname,instance_id,outfiledir):
    instances_dir = outfiledir or infer_instances_directory()   
    instance_id = get_instance_id(instances_dir,instance_id)
    return os.path.join(instances_dir,'instance_' + str(instance_id) + '_' + stepname + '_argument_' + str(argname) + '.pickle')

        
def get_outfile(instance_id,outfiledir):
    instances_directory = outfiledir or infer_instances_directory()
    instance_id = get_instance_id(instances_directory,instance_id)
    outfilename = os.path.join(instances_directory , 'instance_' + str(instance_id) + '.py')
    
    print("Inferred filename for target to be", outfilename)
    return outfilename

def get_vname(argname):
    if isinstance(argname,int):
        return '__value__' + str(argname)
    else:
        return argname

def get_argdict(func, args, deflinedict={}):

    if isinstance(args,list):
        assert len(args) == 2 and isinstance(args[0],tuple) and isinstance(args[1],dict)
        posargs = args[0]
        kwargs = args[1]
    elif isinstance(args,tuple):
        posargs = args
        kwargs = {}
    else:
        assert isinstance(args,dict)
        kwargs = args
        posargs = ()

    Info = inspect.getargspec(func)
    Args = Info[0]
    Defaults = Info[3]
    NumPosArgs = len(Args) - (len(Defaults) if Defaults else 0)
    Kwargs = Args[NumPosArgs:]

    assert len(posargs) == NumPosArgs or (len(posargs) > NumPosArgs and Info[1])
    assert set(kwargs.keys()) <= set(Kwargs) or (Info[2] and all([isinstance(k,str) for k in kwargs.keys()]))

    argdict = dict(list(enumerate(posargs)))
    argdict.update(kwargs)
    
    if Kwargs:
        for (k,d) in zip(Kwargs,Defaults):
            if k not in argdict:
                argdict[k] = d

    if 'depends_on' not in deflinedict.keys() and '__dependor__' in func.func_dict.keys():
        deflinedict['depends_on'] = func.__dependor__(argdict)
    if 'creates' not in deflinedict.keys() and '__creator__' in func.func_dict.keys():
        deflinedict['creates'] = func.__creator__(argdict)
        
    livedict = {}
    if '__objector__' in func.func_dict.keys():
        livedict = func.__objector__(argdict)
        assert isinstance(livedict,dict) and livedict <= argdict, '__objector__ decoration must return subdictionary of input dictionary'       
    livedict.update(dict([(var,obj) for (var,obj) in argdict.items() if (isinstance(obj,types.FunctionType) or isinstance(obj,types.BuiltinFunctionType) or isinstance(obj,types.ClassType) or isinstance(obj,types.TypeType)) and var not in livedict.keys()]))
        
    return [argdict, deflinedict, livedict]

                                
def OpListUniqify(OpList):
    '''
        When the OpList in the ApplyOperations2 contains multiple functions
        that are the same, e.g. have the same contents, but perhaps not the 
        same FName,this optimizes and retains only one of each. 
    '''
    OList = numpy.array([';'.join([str(a[1]),str(a[2]),str(a[3])]) if len(a) == 4 else ';'.join([str(a[1]),str(a[2]),''])  for a in OpList])
    [D,s] = FastArrayUniqify(OList)
    si = PermInverse(s)
    R = [i for i in range(len(OList)) if D[si[i]]]
    return [OpList[r] for r in R]
    
    
def protocolize():
    return lambda f: protocol_creates_directory(f)

def protocol_creates_directory(f):
    absolute_path = inspect.getfile(f)
    name = f.__name__
    DEdir = WORKING_DE.root_dir
    
    relative_path = os.path.relpath(absolute_path,DEdir).rstrip('/')
    assert relative_path.endswith('.py'), 'Path must end with .py'
    generated_code_dir = WORKING_DE.relative_generated_code_dir
    
    #return append_decorated_attribute(f, '__creates__', os.path.join(generated_code_dir,relative_path[:-3] ,  name + '/' ))
    f = append_decorated_attribute(f, '__creates__', os.path.join(generated_code_dir,relative_path[:-3] ,  name + '/' ))
    return add_decorated_attribute(f, '__is_fast__', 1)
    

