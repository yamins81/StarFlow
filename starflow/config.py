import os
import ConfigParser
from starflow import utils
from starflow import static
from starflow import exception
from starflow.logger import log
from starflow.utils import AttributeDict

DEBUG_CONFIG = False


class ConfigObject(object):

    def __init__(self,fp):
        self._cfg_file = fp
        self._config = None
        
        self.exception_class = exception.ConfigNotFound


    def _get_bool(self, config, section, option):
        try:
            opt = config.getboolean(section, option)
            return opt
        except ConfigParser.NoSectionError:
            pass
        except ConfigParser.NoOptionError:
            pass
        except ValueError:
            raise exception.ConfigError(
                "Expected True/False value for setting %s in section [%s]" %
                (option, section))

    def _get_int(self, config, section, option):
        try:
            opt = config.getint(section, option)
            return opt
        except ConfigParser.NoSectionError:
            pass
        except ConfigParser.NoOptionError:
            pass
        except ValueError:
            raise exception.ConfigError(
                "Expected integer value for setting %s in section [%s]" %
                (option, section))

    def _get_string(self, config, section, option):
        try:
            opt = config.get(section, option)
            return opt
        except ConfigParser.NoSectionError:
            pass
        except ConfigParser.NoOptionError:
            pass

    def _get_list(self, config, section, option):
        val = self._get_string(config, section, option)
        if val:
            val = [v.strip() for v in val.split(',')]
        return val

    def __repr__(self):
        return "<ConfigFile: %s>" % self._cfg_file

    def _get_urlfp(self, url):
        log.debug("Loading url: %s" % url)
        try:
            fp = urllib.urlopen(url)
            if fp.getcode() == 404:
                raise exception.ConfigError("url %s does not exist" % url)
            fp.name = url
            return fp
        except IOError, e:
            raise exception.ConfigError(
                "error loading config from url %s\n%s" % (url, e))

    def _get_fp(self, cfg_file):
        log.debug("Loading file: %s" % cfg_file)
        if os.path.exists(cfg_file):
            if not os.path.isfile(cfg_file):
                raise exception.ConfigError(
                    'config %s exists but is not a regular file' % cfg_file)
        else:
            raise self.exception_class(cfg_file,self)
        return open(cfg_file)
        
    def __load_config(self):
        fp = self._cfg_file
        if utils.is_url(fp):
            cfg = self._get_urlfp(fp)
        else:
            cfg = self._get_fp(fp)
        try:
            cp = ConfigParser.ConfigParser()
            cp.readfp(cfg)
            return cp
        except ConfigParser.MissingSectionHeaderError:
            raise exception.ConfigHasNoSections(cfg.name)
        except ConfigParser.ParsingError, e:
            raise exception.ConfigError(e)

    @property
    def type_validators(self):
        return {
            int: self._get_int,
            str: self._get_string,
            bool: self._get_bool,
            list: self._get_list,
        }


    @property
    def config(self):
        if self._config is None:
            self._config = self.__load_config()
        return self._config
        

    def _load_settings(self, section_name, settings, store):
        """
        Load section settings into a dictionary
        """
        section = self.config._sections.get(section_name)
        if not section:
            raise exception.ConfigSectionMissing(
                'Missing section %s in config' % section_name)
        store.update(section)
        section_conf = store
        for setting in settings:
            requirements = settings[setting]
            func, required, default, options = requirements
            func = self.type_validators.get(func)
            value = func(self.config, section_name, setting)
            if value is not None:
                if options and not value in options:
                    raise exception.ConfigError(
                        '"%s" setting in section "%s" must be one of: %s' %
                        (setting, section_name,
                         ', '.join([str(o) for o in options])))
                section_conf[setting] = value
                
    def _check_required(self, section_name, settings, store):
        """
        Check that all required settings were specified in the config.
        Raises ConfigError otherwise.

        Note that if a setting specified has required=True and
        default is not None then this method will not raise an error
        because a default was given. In short, if a setting is required
        you must provide None as the 'default' value.
        """
        section_conf = store
        for setting in settings:
            requirements = settings[setting]
            required = requirements[1]
            value = section_conf.get(setting)
            if value is None and required:
                raise exception.ConfigError(
                    'missing required option %s in section "%s"' %
                    (setting, section_name))
                
    def _load_defaults(self, settings, store):
        """
        Sets the default for each setting in settings regardless of whether
        the setting was specified in the config or not.
        """
        section_conf = store
        for setting in settings:
            default = settings[setting][2]
            if section_conf.get(setting) is None:
                if DEBUG_CONFIG:
                    log.debug('%s setting not specified. Defaulting to %s' % \
                              (setting, default))
                section_conf[setting] = default                
                
    def _load_section(self, section_name, section_settings):
        """
        Returns a dictionary containing all section_settings for a given
        section_name by first loading the settings in the config, loading
        the defaults for all settings not specified, and then checking
        that all required options have been specified
        """
        store = AttributeDict()
        self._load_settings(section_name, section_settings, store)
        self._load_defaults(section_settings, store)
        self._check_required(section_name, section_settings, store)
        return store
        
    def _get_section_name(self, section):
        """
        Returns section name minus prefix
        e.g.
        $ print self._get_section('cluster smallcluster')
        $ smallcluster
        """
        return section.split()[1]

    def _get_sections(self, section_prefix):
        """
        Returns all sections starting with section_prefix
        e.g.
        $ print self._get_sections('cluster')
        $ ['cluster smallcluster', 'cluster mediumcluster', ..]
        """
        return [s for s in self.config.sections() if
                s.startswith(section_prefix)]

    def _load_sections(self, section_prefix, section_settings):
        """
        Loads all sections starting with section_prefix and returns a
        dictionary containing the name and dictionary of settings for each
        section.
        keys --> section name (as returned by self._get_section_name)
        values --> dictionary of settings for a given section

        e.g.
        $ print self._load_sections('volumes', self.plugin_settings)

        {'myvol': {'__name__': 'volume myvol',
                    'device': None,
                    'mount_path': '/home',
                    'partition': 1,
                    'volume_id': 'vol-999999'},
         'myvol2': {'__name__': 'volume myvol2',
                       'device': None,
                       'mount_path': '/myvol2',
                       'partition': 1,
                       'volume_id': 'vol-999999'},
        """
        sections = self._get_sections(section_prefix)
        sections_store = AttributeDict()
        for sec in sections:
            name = self._get_section_name(sec)
            sections_store[name] = self._load_section(sec, section_settings)
        return sections_store
        


class StarFlowConfig(ConfigObject):
    def __init__(self):
        self._cfg_dir = static.GLOBAL_CFG_DIR
        self._cfg_file = static.GLOBAL_CFG_FILE
        self._registry_file = static.GLOBAL_REGISTRY_FILE
        self._config = None
        self.exception_class = exception.GlobalConfigNotFound
    
    def load(self):  
        store = self._load_section('global', static.GLOBAL_SETTINGS)
        self.python_executable = store["python_executable"]
        self.default_callmode = store["default_callmode"]
        self.pythonpath = store["pythonpath"]    
            
    def create_global_config(self):
    
        cfg_file = self._cfg_file
        cfg_dir = self._cfg_dir
        if not os.path.exists(cfg_dir):
            os.makedirs(cfg_dir)
        import starflow.templates as templates
        cfg_fh = open(cfg_file, 'w')
        cfg_fh.write(templates.GLOBAL_CONFIG)
        cfg_fh.close()
        log.info("Global config file written to %s. Please customize this file." %
                 cfg_file)
        
        import cPickle as pickle
        empty_registry = {}
        registry_file = self._registry_file
        registry_fh = open(registry_file,'w')
        pickle.dump(empty_registry,registry_fh)
        registry_fh.close()
        log.info("Empty data environment registry written to %s. Please customize this file." %
                 registry_file)
        
        
        template_dir = static.GLOBAL_TEMPLATE_DIR
        os.makedirs(os.path.join(template_dir, static.LOCAL_CFG_DIR))
        
        local_cfg_template_file = os.path.join(template_dir, static.LOCAL_CFG_FILE)
        local_cfg_template_fh = open(local_cfg_template_file, 'w')
        local_cfg_template_fh.write(templates.LOCAL_CONFIG)
        local_cfg_template_fh.close()
        log.info(TEMPLATE_WRITTEN_MESSAGE % 
                                     ("local config", local_cfg_template_file))
                 
        local_lmf_template_file = os.path.join(template_dir, 
                                               static.LOCAL_LIVE_MODULE_FILTER_FILE)
        local_lmf_template_fh = open(local_lmf_template_file, 'w')
        local_lmf_template_fh.write(templates.LOCAL_LIVE_MODULE_FILTER_TEXT)
        local_lmf_template_fh.close()
        log.info(TEMPLATE_WRITTEN_MESSAGE % 
                              ("live module filters", local_lmf_template_file))        
                 
        local_setup_template_file = os.path.join(template_dir, static.LOCAL_SETUP_FILE)
        local_setup_template_fh = open(local_setup_template_file, 'w')
        local_setup_template_fh.write(templates.LOCAL_SETUP_TEXT)
        local_setup_template_fh.close()
        log.info(TEMPLATE_WRITTEN_MESSAGE % 
                              ("local setup.py file",local_setup_template_file))    
                 
    def display_config(self):
        import starflow.templates as templates
        return templates.copy_paste(templates.GLOBAL_CONFIG)
        
    def __repr__(self):
        return "<StarFlowConfig: %s>" % self._cfg_file           

TEMPLATE_WRITTEN_MESSAGE = \
"""Template for %s to:
            %s.
    Please customize this file."""                

class DataEnvironmentConfig(ConfigObject):

    def __init__(self,path = None):  
        self._root_dir = self._find_de_root(path)
        self._cfg_dir = os.path.join(self._root_dir, static.LOCAL_CFG_DIR)
        self._cfg_file = os.path.join(self._root_dir, static.LOCAL_CFG_FILE)
        self._archive_dir = os.path.join(self._root_dir, static.LOCAL_ARCHIVE_DIR)
        self._metadata_dir = os.path.join(self._root_dir, static.LOCAL_METADATA_DIR)
        self._links_dir = os.path.join(self._root_dir, static.LOCAL_LINKS_DIR)
        self._modules_dir = os.path.join(self._root_dir,static.LOCAL_MODULES_DIR)
        self._tmp_dir = os.path.join(self._root_dir, static.LOCAL_TMP_DIR)
        self._temp_dir = os.path.join(self._root_dir, static.LOCAL_TEMP_DIR)
        self._lmf_file = os.path.join(self._root_dir, static.LOCAL_LIVE_MODULE_FILTER_FILE)
        self._local_setup_file = os.path.join(self._root_dir, static.LOCAL_SETUP_FILE)    
        self._config = None 
        self.exception_class = exception.LocalConfigNotFound

    ##########loading 

    def load_live_module_filters(self):
        FilterPath = self._lmf_file
        F = [ll for ll in open(FilterPath,'rU').read().strip('\n').split('\n') if not ll.startswith('#')]
        for i in range(len(F)):
            l = [ll.strip(' ') for ll in F[i].split(':')]
            if len(l) == 1:
                l = [l[0],'^' + l[0] + '*']
            l[1] = [ll.strip(' ') for ll in l[1].split(',')]
            #l[0] = os.path.join(self._root_dir,l[0][3:])
            F[i] = l
        live_module_filters = dict(F)
        self.live_module_filters = live_module_filters     
           
    def load(self):
        """
        Populate this config object from the StarFlow config files
        """
        log.debug('Loading config')
        
        store = self._load_section('local_systemwide', {})
        self.name = store['name']
        self.system_mode = store['system_mode']
        self.protection = store['protection']
        self.gmail_account_name = store["gmail_account_name"]
        self.gmail_account_passwd = store["gmail_account_passwd"]
        self._generated_code_dir = os.path.join(self._root_dir,store["generated_code_dir"])
        self.load_live_module_filters()
         
        return self
        
              
    def reload(self):
        """
        Reloads the configuration file
        """

  
  
    ##########other utils
    def _getpwd(self, path):
        """Get parent working directory"""
        return os.path.normpath(os.path.join(path, '..'))

    def _walkup(self, path):
        prev = ''
        next = path
        while True:
            if len(prev) == len(next):
                break
            yield next
            prev = next
            next = self._getpwd(prev)

    def _get_parent_dirs(self, path):
        dirs = [ d for d in self._walkup(path) ]; dirs.reverse()
        return dirs

    def _find_de_root(self,path):
        if not path:
            path = os.getcwd()
        else:
            st = os.stat(path)
        self._path = path

        for d in self._get_parent_dirs(path):
            if os.path.exists(os.path.join(d, static.LOCAL_CFG_DIR)):
                return d
        raise exception.DataEnvironmentNotFound("Not a StarFlow data environment")
         
    def __repr__(self):
        return "<DataEnvironmentConfig: %s>" % self._cfg_file           

        
        

  
