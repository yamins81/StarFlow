import optparse
import os
import shutil
import cPickle as pickle

from starflow import utils
from starflow.logger import log
from starflow import static
from starflow import de

from base import CmdBase

class CmdInit(CmdBase):
    """
    init name path

    Initialize a StarFlow Data Environment

    Example: 

        $ starflow init MyNewDataEnvironment /home/users/me/dataenvironment
    """
    names = ['init']

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

    def addopts(self, parser):
        opt = parser.add_option("-n","--local-name", dest="local_name",
            action="store", default=False, help="local name for the data environment")

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
                                 
        argdict["local_name"] = self.opts.local_name if self.opts.local_name else argdict["name"]
                
        de_manager = de.DataEnvironmentManager()

        de_manager.init_de(**argdict)
  