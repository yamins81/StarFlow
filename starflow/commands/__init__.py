#!/usr/bin/env python
from init import CmdInit
from shell import CmdShell
from help import CmdHelp
from listDEs import CmdListDEs
from makeDE import CmdMakeDE
from register import CmdRegister
from clean_registry import CmdClean_Registry

all_cmds = [
	CmdInit(),
	CmdHelp(),
	CmdShell(),
	CmdListDEs(),
	CmdMakeDE(),
	CmdRegister(),
	CmdClean_Registry()
]
