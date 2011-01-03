'''
this is a script that is used by the data Environment to initialize a python interpreter session during automatic updating.  Do not modify it unless you know what you're doing.   

'''

import os
import sys
import starflow.de as de
from starflow.logger import log

DE_MANAGER = de.DataEnvironmentManager()
WORKING_DE = DE_MANAGER.working_de

#Print a welcome message -- optional :) 
log.info('Loading StarFlow for production ...')

#set some environment variables
import os
os.chdir(WORKING_DE.temp_dir)
loc = os.getcwd()
assert loc == WORKING_DE.temp_dir, 'Local Directory Must be Temp'
#print 'Data Environment directory = ', Dir


#modify the pythonpath to ensure that commands from this data environment are used
import sys
sys.path.insert(0,WORKING_DE.root_dir)
sys.path.insert(0,WORKING_DE.config_dir)

WORKING_DE.system_mode = 'PRODUCTION'

from starflow.system_io_override import io_override
io_override(WORKING_DE)

PYTHONPATH = DE_MANAGER.pythonpath
for f in PYTHONPATH.split(':'):
    sys.path.insert(0,f)
