import sys
import optparse
import os

import starflow
from starflow.logger import log
from starflow import de

from base import CmdBase

class CmdShell(CmdBase):
    """
    shell

    Load interactive IPython shell for StarFlow
    
    The following objects are automatically available at the prompt:

    All starflow modules are automatically imported in the IPython session
    """
    names = ['shell']
    def execute(self,args):
            
        
        DE_MANAGER = de.DataEnvironmentManager()             
        if args:
            local_name = args[0]
            reg_info = DE_MANAGER.get_registry_info(local_name = local_name) 
            os.environ["WORKING_DE_PATH"] = reg_info["root_dir"]
             
        WORKING_DE = DE_MANAGER.working_de
                 
        for modname in starflow.__all__:
            log.info('Importing module %s' % modname)
            fullname = starflow.__name__ + '.' + modname
            try:
                __import__(fullname)
                locals()[modname] = sys.modules[fullname]
            except ImportError,e:
                log.error("Error loading module %s: %s" % (modname, e))
        log.info("Importing data environment manager object as DE_MANAGER")
        locals()["DE_MANAGER"] = DE_MANAGER
        log.info("Importing working dataenvironment object as WORKING_DE")
        locals()["WORKING_DE"] = WORKING_DE
       
     
        from starflow.system_io_override import io_override
        io_override(WORKING_DE)
        
        os.chdir(WORKING_DE.temp_dir)
        
        print '\n... done loading.  May the Organization be with you as you journey through the Land of Data.' 
                                    
        try:
            import IPython.Shell
            ipy_shell = IPython.Shell.IPShellEmbed(argv=[])
            ipy_shell()
        except ImportError,e:
            def ipy_shell():
                log.error("Unable to load IPython.")
                log.error("Please check that IPython is installed and working.")
                log.error("If not, you can install it via: easy_install ipython")
