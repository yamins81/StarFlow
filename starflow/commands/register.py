import sys
import optparse
import os

import starflow
from starflow.logger import log
from starflow import de

from base import CmdBase

class CmdRegister(CmdBase):
    """
    register
    
    Register an existing but unregistered DE, e.g. after pulling from a repo.
    
    Example:
    
        $ starflow register /home/users/me/new_dataenvironment -n my_new_de
    """
    names = ['register']
    
    def addopts(self, parser):
        opt = parser.add_option("-n","--local-name", dest="local_name",
        action="store", default=False, help="local name for the data environment")

    def execute(self,args):
    
        de_manager = de.DataEnvironmentManager()
        
        if args:
            path = args[0]
            data_environment = de.DataEnvironment(path=path)
        else:
            data_environment = de.DataEnvironment()
            path = data_environment.root_dir
            
        name = data_environment.name
        
        local_name = self.opts.local_name if self.opts.local_name else name
                
        de_manager.register(path,{'name':name,'local_name':local_name})