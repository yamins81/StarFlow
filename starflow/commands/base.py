import os
import sys
#!/usr/bin/env python

import time
import signal
from starflow import optcomplete
from starflow.logger import log

class CmdBase(optcomplete.CmdComplete):
    parser = None
    opts = None
    gopts = None
    gparser = None
    subcmds_map = None

    @property
    def goptions_dict(self):
        return dict(self.gopts.__dict__)

    @property
    def options_dict(self):
        return dict(self.opts.__dict__)

    @property
    def specified_options_dict(self):
        """ only return options with non-None value """
        specified = {}
        options = self.options_dict
        for opt in options:
            if options[opt] is not None:
                specified[opt] = options[opt]
        return specified

    @property
    def cfg(self):
        return self.goptions_dict.get('CONFIG')

    def cancel_command(self, signum, frame):
        print
        log.info("Exiting...")
        sys.exit(1)

    def catch_ctrl_c(self, handler=None):
        handler = handler or self.cancel_command
        signal.signal(signal.SIGINT, handler)

    def warn_experimental(self, msg):
        for l in msg.splitlines():
            log.warn(l)
        num_secs = 10
        r = range(1,num_secs+1)
        r.reverse()
        print
        log.warn("Waiting %d seconds before continuing..." % num_secs)
        log.warn("Press CTRL-C to cancel...")
        for i in r:
            sys.stdout.write('%d...' % i)
            sys.stdout.flush()
            time.sleep(1)
        print
