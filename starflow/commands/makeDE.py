import optparse
import os
import shutil
import cPickle as pickle

from starflow import utils
from starflow.logger import log
from starflow import static
from starflow import de

from base import CmdBase

class CmdMakeDE(CmdBase):
    """
    make a data environment 

    Creates a data environment without registering it (or checking if it can be
    registered under the given name without a conflict with existing registered
    DEs.)

    Example: 

        $ starflow makeDE MyNewDataEnvironment /home/users/me/dataenvironment
    """
    names = ['makeDE']

    tag = None

    @property
    def completer(self):
        if optcomplete:
            try:
                cfg = config.StarFlowConfig()
                cfg.load()
                return optcomplete.ListCompleter(cfg.get_cluster_names())
            except Exception, e:
                log.error('something went wrong fix me: %s' % e)

    def cancel_command(self, signum, frame):
        raise exception.CancelledInitRequest(self.tag)

    
    def execute(self, args):
        log.info("Initializing data environment ...")
        argdict = {}
                  
        argdict["root_dir"] = args[0]          
        argdict["name"] = args[1]
       
             
        if len(args) > 2:
            argdict["gmail_account_name"] = args[2]
            argdict["gmail_account_passwd"] = args[3]
                                 
        de_manager = de.DataEnvironmentManager()

        de_manager.make_de(**argdict)
  