#!/usr/bin/env python
"""
starflow Exception Classes
"""
import os
from starflow import static
from starflow.logger import log


class BaseException(Exception):
    def __init__(self, *args):
        self.msg = args[0]
    def __str__(self):
        return self.msg
    def explain(self):
        return "%s: %s" % (self.__class__.__name__, self.msg)
        

class CommandNotFound(BaseException):
    """Raised when command is not found on the system's PATH """
    def __init__(self, cmd):
        self.msg = "command not found: '%s'" % cmd
        

class ConfigError(BaseException):
    """Base class for all config related errors"""        

class DENameFormatError(ConfigError):
    """Raised when DE name choice is not in correct format """
    def __init__(self, name, rules):
        self.msg = "name: '%s' does not meet proper data enviroment naming \
        convention rules:\n%s" % (cmd,'\n'.join(['* ' + r for r in rules]))


class DELocationFormatError(ConfigError):
    """Raised when DE path choice is not in correct format """
    def __init__(self, name, rules):
        self.msg = "path: '%s' does not meet proper data enviroment location \
        convention rules:\n%s" % (cmd,'\n'.join(['* ' + r for r in rules]))       
  
class PathAlreadyExistsError(BaseException):
    def __init__(self,path):
        self.msg = "Something's already at the path %s, can't create anything there." % path
  
class ConfigSectionMissing(ConfigError):
    pass

class ConfigHasNoSections(ConfigError):
    def __init__(self, cfg_file):
        self.msg = "No valid sections defined in config file %s" % cfg_file

class ConfigNotFound(ConfigError):
    def __init__(self, *args, **kwargs):
        super(ConfigNotFound, self).__init__(*args, **kwargs)
        self.cfg_file = args[0]
        self.config_object = args[1]
        self.msg = "config file %s not found" % self.cfg_file
 
class GlobalConfigNotFound(ConfigNotFound):
    def display_options(self):
        print 'Options:'
        print '--------' 
        print '[1] Show the starflow global config template'
        print '[2] Write config template to %s' % self.cfg_file
        print '[q] Quit'
        resp = raw_input('\nPlase enter your selection: ')
        if resp == '1':
            print self.config_object.display_config()
        elif resp == '2':
            self.config_object.create_global_config()
            
class LocalConfigNotFound(ConfigNotFound):
    def display_options(self):
        print 'Options:'
        print '--------' 
        print 'What to do now?'

class DataEnvironmentNotFound(BaseException):
    pass

class KeyNotFound(ConfigError):
    def __init__(self, keyname):
        self.msg = "key %s not found in config" % keyname


class PluginError(BaseException):
    """Base class for plugin errors"""

class PluginLoadError(PluginError):
    """Raised when an error is encountered while loading a plugin"""

class PluginSyntaxError(PluginError):
    """Raised when plugin contains syntax errors"""


class ValidationError(BaseException):
    """Base class for validation related errors"""
    
    def __init__(self, path,error):
        self.error = error
        self.msg = "Directory at %s failed to validate as a data environment.  The error was: %s" % (path,self.error.msg)
        
    def __repr__(self):
        return self.msg
        
        
class RegistryError(BaseException):
    """Base class for registry errors"""
    
class RegistryCorrupted(RegistryError):
    def __init__(self,msg):
        self.msg = msg
    
class NameNotInRegistryError(RegistryError):
    
    def __init__(self,name):
        
         self.msg = "The name %s could not be found in the registry." % name
         
class PathNotInRegistryError(RegistryError):
    
    def __init__(self,path):
        
         self.msg = "The path %s could not be found in the registry." % path
        
class RegistrationMismatchError(RegistryError):
    
    def __init__(self,attrdict):
        
        self.attrdict = attrdict
        
        s = '\n'.join([attr + ': ' + val[0] + ' (local) vs. ' + val[1] + ' (registry).' for (attr,val) in self.attrdict.items()])
        
        self.msg = "The following attributes to do not match between the registry and the local config file:\n" + s

class NameAlreadyInRegistryError(RegistryError):
    """Raised when DE path choice is not in correct format """
    def __init__(self, name):
        self.msg = "something with the local name %s already is in local DE registry;\
        either choose a different name use -n option to specify different local name,\
        or use the remove command." % name

class ProtocolError(BaseException):
    """Base class for protocol-related errors"""

class ProtocolPickleError(ProtocolError):
    def __init__(self,argname,argval):
        self.msg = """Argument %s with value %s cannot be used as a protocol argument because:
                         A) it can't be stringified properly, 
                         B) it is not a function or class method, and 
                         C) it cannot be pickled.""" % (argname,argval)
   
class CannotInferProtocolTargetError(ProtocolError):
    def __init__(self, pathlist,namelist):
        self.msg = "Cannot infer protocol __creates__ target anywhere along this stack: %s." % \
        '; '.join([a + ': ' + b for (a,b) in zip(pathlist,namelist)])
            
            
class QacctParsingError(Exception):
    def __init__(self,job,name):
        self.msg = "Can't parse exit status from " + repr(name) + " for job " + repr(job) + "."