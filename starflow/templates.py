#!/usr/bin/env python
from starflow import static


DASHES='-'*10

dictk = lambda d,k : dict([(key,val[k]) for (key,val) in d.items()])

def copy_paste(templ):
    return DASHES + ' COPY BELOW THIS LINE ' + DASHES + '\n' + templ + '\n' + \
    DASHES + ' END COPY ' + DASHES + '\n'
    
GLOBAL_CONFIG = """
########################################
## StarFlow Global Configuration File ##
########################################

[global]
python_executable=%(python_executable)s
default_callmode=%(default_callmode)s
""" % dictk(static.GLOBAL_SETTINGS,2)

LOCAL_CONFIG = """
#######################################
## StarFlow Local Configuration File ##
#######################################

[local_systemwide]
system_mode=%(system_mode)s
protection=%(protection)s
generated_code_dir=%(generated_code_dir)s
name=%(name)s
gmail_account_name=%(gmail_account_name)s
gmail_account_passwd=%(gmail_account_passwd)s
""" % dictk(static.LOCAL_SETTINGS,2)

LOCAL_SETUP_TEXT = static.LOCAL_SETUP_TEXT

LOCAL_LIVE_MODULE_FILTER_TEXT = """
#This is a configuration file for the system.  Each of the lines contains 
#specially formatted expressions used to determine which directories the 
#system searches to find python modules to analyze and include in the 
#system updating.  See manual for more detailed information. 
#Lines beginning with a hash mark (like this one) will be ignored.
%(lmf)s
""" % {"lmf" : static.LOCAL_SETTINGS["live_module_filters"][2]}