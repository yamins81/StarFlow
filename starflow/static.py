#!/usr/bin/env python
"""
Module for storing static data structures
"""
import os
import tempfile

GLOBAL_TMP_DIR = tempfile.gettempdir()
DEBUG_FILE = os.path.join(GLOBAL_TMP_DIR, 'starflow-debug.log')


##non-configurable settings
##global
GLOBAL_CFG_DIR = os.path.join(os.path.expanduser('~'), '.starflowcfg')
GLOBAL_CFG_FILE = os.path.join(GLOBAL_CFG_DIR, 'config')
GLOBAL_TEMPLATE_DIR = os.path.join(GLOBAL_CFG_DIR,'templates')
GLOBAL_REGISTRY_FILE = os.path.join(GLOBAL_CFG_DIR,'.registry')
##local
LOCAL_CFG_DIR = '.starflow'
LOCAL_CFG_FILE = os.path.join(LOCAL_CFG_DIR, 'config')
LOCAL_TMP_DIR = os.path.join(LOCAL_CFG_DIR,'.tmp')
LOCAL_ARCHIVE_DIR = os.path.join(LOCAL_CFG_DIR,'.archive')
LOCAL_METADATA_DIR = os.path.join(LOCAL_CFG_DIR,'.metadata')
LOCAL_LINKS_DIR = os.path.join(LOCAL_CFG_DIR,'.links')
LOCAL_MODULES_DIR = os.path.join(LOCAL_CFG_DIR,'.modules')
LOCAL_SETUP_MODULE = 'setupfunctions'
LOCAL_SETUP_FILE = os.path.join(LOCAL_CFG_DIR,LOCAL_SETUP_MODULE + '.py')
LOCAL_LIVE_MODULE_FILTER_FILE = os.path.join(LOCAL_CFG_DIR,'live_module_filters')
LOCAL_LIVE_MODULE_FILTER_FUNCTION = 'get_live_modules'
LOCAL_METADATA_PROCESSOR = 'process_metadata'
LOCAL_METADATA_GENERATOR = 'generate_metadata'
LOCAL_TEMP_DIR = 'Temp'

##names,types,default values for configurable settings
##global
GLOBAL_SETTINGS = {
    # setting: (type, required, default)
    'python_executable' : (str, True, 'python',None),
    'pythonpath' : (str, True, '',None),
    'default_callmode' : (str, True, 'DIRECT',None)
}
##local
LOCAL_SETTINGS = {
    'system_mode' : (str, True, 'EXPLORATORY',None),
    'protection': (str, True, 'ON',None),
    'live_module_filters' : (str,True,'',None),
    'generated_code_dir': (str, True, 'generated_code',None),
    'gmail_account_name' : (str,False,'%(gmail_account_name)s',None),
    'gmail_account_passwd' : (str,False,'%(gmail_account_passwd)s',None),
    'name' : (str,True,'%(name)s',None)
}
 
##default text for setup.py module 
LOCAL_SETUP_TEXT = """
from starflow.utils import RecursiveFileList,CheckInOutFormulae

def get_live_modules(LiveModuleFilters):
	'''
	Function for filtering live modules that is fast by avoiding looking 
	through directories that will be irrelevant.
	'''
	FilteredModuleFiles = []
	Avoid = ['^RawData$','^Data$','^.svn$','^ZipCodeMaps$','.data$','^scrap$']
	FilterFn = lambda z,y : y.split('.')[-1] == 'py' and CheckInOutFormulae(z,y)
	for x in LiveModuleFilters.keys():
	    Filter = lambda y : FilterFn(LiveModuleFilters[x],y) 
		FilteredModuleFiles += filter(Filter,RecursiveFileList(x,Avoid=Avoid))
	return FilteredModuleFiles
"""