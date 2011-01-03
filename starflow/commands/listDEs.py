import optparse
import os
import shutil
import cPickle as pickle

from starflow import utils
from starflow.logger import log
from starflow import static
from starflow import de

from base import CmdBase

class CmdListDEs(CmdBase):
    """
    list data environments

    Pretty-print a list of all data environments registered on this computer

    Example: 

        $ starflow listDEs
    """
    names = ['listDEs']

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
        log.info("Listing DEs ...")

        de_manager = de.DataEnvironmentManager()

        print('\n\n'.join(map(repr,de_manager.data_environments)))
  