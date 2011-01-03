#!/usr/bin/env python
"""
Manager for StarFlow data environments
"""
import os
import sys
import cPickle as pickle

from starflow.config import DataEnvironmentConfig, StarFlowConfig
from starflow import managers
from starflow.utils import RecursiveFileList,CheckInOutFormulae, delete, is_string_like, copy_contents, is_unique
from starflow import static
from starflow import exception
from starflow.logger import log

class DataEnvironmentManager(StarFlowConfig):

    def __init__(self):
        StarFlowConfig.__init__(self)
        self.load()
        self._data_environments = None
        
    def load(self):
        StarFlowConfig.load(self)
        self.load_registry()
        
    def load_registry(self):
        registry = pickle.load(open(static.GLOBAL_REGISTRY_FILE))
        self.validate_registry(registry)
        self.registry = registry

    def validate_registry(self,registry):
        names = [v["local_name"] for v in registry.values()]
        if not is_unique(names):
            raise exception.RegistryCorrupted("Local names not unique, try cleaning?")
         
    @property    
    def data_environments(self):
        if self._data_environments is None:
            self.clean_registry()
            self._data_environments = []
            for path in self.registry:
                self._data_environments.append(self.verify(path,raise_error=False))    
        return self._data_environments
            
        
    @property
    def local_names(self):
        return [v["local_name"] for v in self.registry.values()]
                      
    def get_data_environment(self,path=None,local_name=None):
        if path is None and local_name is not None:
            reg_info =  self.get_registry_info(local_name = local_name)
            path = reg_info["root_dir"]
        
        data_environment = DataEnvironment(path = path)
        path = data_environment.root_dir
        
        if not path in self.registry:
            log.info("Unregistered data environment at %s, registering." 
                      % path)
            reg_info = {"name":data_environment.name}
            if data_environment.name not in self.local_names:
                reg_info['local_name'] = data_environment.name
                log.info("using local name from de internal name: %s"
                         % data_environment.name)
            else:
                log.info("No local name selected.  Using set local name command \
                          if you want.")
                
            self.register(path,reg_info)
        
        return data_environment
        
        
    def clean_registry(self,path=None,local_name=None,strong=False,force=False):
        
        if path is None and local_name is None:
            infolist = [{"path":p} for p in self.registry]
        else:
            infolist = [{"path":path,"local_name":local_name}]

            
        for info in infolist:
            reg_info = self.get_registry_info(**info)
                 
            path = reg_info["root_dir"]
                       
            if force or not os.path.exists(path):
                self.deregister(path)
            elif strong:
                try:
                    data_environment = self.verify(path)
                except exception.ValidationError:
                    self.degister(path)
                else:
                    log.info("Data environment %s at %s passes." % 
                    (data_environment.name,data_environment.root_dir))
            
            
    def get_registry_info(self,path=None,local_name=None): 
        if path is not None:
            if path not in self.registry:
                raise exception.PathNotInRegistryError(path)
        elif local_name in self.local_names:
            path = [k for k in self.registry if self.registry[k].get('local_name') == local_name][0]
        else:
            raise exception.NameNotInRegistryError(local_name)   
        reg_info = self.registry[path].copy()
        reg_info['root_dir'] = path
        return reg_info
                          
    @property
    def working_de(self):
        path = os.environ.get("WORKING_DE_PATH")
        data_environment = self.get_data_environment(path = path)
        os.environ["WORKING_DE_PATH"] = data_environment.root_dir
        return data_environment
              
    def verify(self,path,raise_error=True):
   
        try:
            data_environment = DataEnvironment(path = path)
        except (exception.ConfigError,exception.DataEnvironmentNotFound),e:
            error = exception.ValidationError(path,e)
            if raise_error:
                raise error
            return error
        else:
            return data_environment
                
    def name_format_check(self,name):
        return is_string_like(name)    
    
    def location_format_check(self,path):
        return is_string_like(path)
        
    @property
    def name_format_rules(self):
        return ["must be string-like"]
    
    @property
    def location_formation_rules(self):
        return ["must be string-like"]                
            
    
    def init_de(self,**arg_dict):
    
        path = arg_dict["root_dir"]
        
        name = arg_dict["name"]
        
        local_name = arg_dict["local_name"]
        
        if not self.location_format_check(path):
            raise exception.DELocationFormatError(name,self.location_format_rules)   
            
        if not self.name_format_check(name):
            raise exception.DENameFormatError(name,self.name_format_rules)
            
        if local_name is not None and not self.name_format_check(local_name):
            raise exception.DENameFormatError(local_name,self.name_format_rules)
               
        try:
            self.make_de(path,arg_dict) 
            self.register(path,arg_dict)
        except (exception.ValidationError,exception.RegistryError),e:
            log.info("An error occured during creation process (see below). There\
            may be detritus of a partially created data enviroment at %s" % path)
            raise e
        else:
            log.info("Data environment %s successfully initialized." % path)
           
        
    def make_de(self,path,cfg_dict): 
        if os.path.exists(path):
            raise exception.PathAlreadyExistsError(path)
        os.makedirs(path)
        copy_contents(static.GLOBAL_TEMPLATE_DIR,path)
        cfg_dir = os.path.join(path,static.LOCAL_CFG_DIR)    
        local_cfg_file = os.path.join(path,static.LOCAL_CFG_FILE)
        local_cfg = open(local_cfg_file,'r').read()
        local_cfg = local_cfg % cfg_dict
        new_local_cfg_fh = open(local_cfg_file,'w')
        new_local_cfg_fh.write(local_cfg)
        new_local_cfg_fh.close()  
        
        self.verify(path)
        
        
    def register(self,path,reg_info):
        log.info("Registering %s" %path)
        reg_info = reg_info.copy()
        if "root_dir" not in reg_info:
            reg_info["root_dir"] = path 
        local_name = reg_info.get("local_name")
        if local_name in self.local_names:  
            other_reg_info = self.get_registry_info(local_name = local_name)
            other_path = other_reg_info["root_dir"]
            if path != other_path:
                raise exception.NameAlreadyInRegistryError(local_name)
        self.registry[path] = reg_info
        registry_fh = open(static.GLOBAL_REGISTRY_FILE,'w')
        pickle.dump(self.registry,registry_fh)
        registry_fh.close()   
        

    def deregister(self,path):
        log.info("Deregistering %s" %path)
        self.registry.pop(path)
        registry_fh = open(static.GLOBAL_REGISTRY_FILE,'w')
        pickle.dump(self.registry,registry_fh)
        registry_fh.close()   
        

class DataEnvironment(DataEnvironmentConfig):

    def __init__(self,path=None):
        DataEnvironmentConfig.__init__(self,path=path)
        self.load()
        if self.root_dir not in sys.path:
            sys.path.insert(0,self.root_dir)
            sys.path.insert(0,self.config_dir)

    @property
    def root_dir(self):
        return self._root_dir
                               
    @property
    def config_dir(self):
        return self._cfg_dir

    @property
    def archive_dir(self):
        return self._create_dir(self._archive_dir)

    @property
    def metadata_dir(self):
        return self._create_dir(self._metadata_dir)

    @property
    def modules_dir(self):
        return self._create_dir(self._modules_dir)

    @property
    def links_dir(self):
        return self._create_dir(self._links_dir)

    @property
    def tmp_dir(self):
        return self._create_dir(self._tmp_dir)

    @property
    def temp_dir(self):
        return self._create_dir(self._temp_dir)
                
        
    @property
    def session_id_file(self):
        self.tmp_dir()
        return self._create_file(self._ssid_file)

    @property
    def generated_code_dir(self):
        return self._create_dir(self._generated_code_dir)   
    
    def __repr__(self):
        return '<DataEnvironment> ' + self.name + ' at ' + self.root_dir
    
    def __str__(self):
        return self.config_dir
                       
    def _create_file(self, path):
        if not os.path.exists(path):
            open(path,'a').close()
        return path

    def _create_dir(self,path):
        if not os.path.exists(path):
            os.makedirs(path)
        return path

     
    def load_live_modules(self,filters=None):
    
        if filters is None:
            self.load_live_module_filters()
            filters = self.live_module_filters
        
        FilteredModuleFiles = [] 
        
    
        try: 
            Module = __import__(static.LOCAL_SETUP_MODULE)
            reload(Module)
            fn = getattr(Module,static.LOCAL_LIVE_MODULE_FILTER_FUNCTION)    
            Files =  fn(filters)
        except: 
            traceback.print_exc()
            print 'Due to the error in the loading of the live modules. Using default filtering process.'  
        else:
            return Files
    
        for x in filters.keys():
            RawModuleFiles = [y for y in RecursiveFileList(x) if y.split('.')[-1] == 'py']
            FilteredModuleFiles += [y for y in RawModuleFiles if CheckInOutFormulae(filters[x],y)]
    
        return FilteredModuleFiles
        

    def __getattr__(self,attr):
        if attr.startswith('relative_'):
            attrname = attr[9:]
            return os.path.relpath(getattr(self,attrname),self.temp_dir)
        else:
            raise AttributeError(attr)
            
    
        

if __name__ == "__main__":
    WORKING_DE = DataEnvironment()
    print WORKING_DE.config_dir
    print WORKING_DE.archive_dir
    print WORKING_DE.metadata_dir
    print WORKING_DE.stored_modules_dir
    print WORKING_DE.stored_links_dir
    print WORKING_DE.session_id_file
    print WORKING_DE.generated_code_dir
