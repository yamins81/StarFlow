#!/usr/bin/env python


class Manager(object):
    """
    Base class for all Manager classes in StarFlow
    """
    def __init__(self, cfg):
        self.cfg = cfg
