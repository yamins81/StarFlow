import sys
import optparse
import os

import starflow
from starflow.logger import log
from starflow import de

from base import CmdBase

class CmdClean_Registry(CmdBase):
    """
    clean_registry
    
    Clean out the central registry of DEs. 
    
    Example:
    
        $ starflow clean_registry
    """
    names = ['clean_registry']
    
    def execute(self,args):
    
        de_manager = de.DataEnvironmentManager()
                        
        de_manager.clean_registry()