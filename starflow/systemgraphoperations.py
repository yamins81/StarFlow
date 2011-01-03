'''
Rountines for constructing meta-data graphs describing the
link structure local to a give path in the Data Enviroment. 

The primary use of the graphs constructed by this module are
in the Graphical Browser .
'''


from __future__ import division
import numpy, time, os, cPickle
from starflow.utils import *
from starflow.linkmanagement import *
from starflow.metadata import metadatapath, opmetadatapath
import tabular as tb
import os

import starflow.de as de
DE_MANAGER = de.DataEnvironmentManager()
WORKING_DE = DE_MANAGER.working_de

os.chdir(WORKING_DE.temp_dir)

GraphIsTooLarge = 500

def MakeLocalLinkList(Path,depends_on = os.path.join(WORKING_DE.relative_links_dir,'StoredTimes'), creates = (WORKING_DE.relative_metadata_dir,)):
    '''
    Given, Path, a path string describing a location in the Data Environment, 
    get the 2-neighborhood graph of the linklist local to that path.
    
    It uses the linklist loaded from the Live Modules. 
    
    This function outputs the result, as a numpy sub- record array of 
    the Linklist, to a pickled file whose path is given by:
    
        MetaPathDir(Path) + 'LocalLinkList.pickle'
    
    This path is in in the meta-data directory associated with Path.
    
    It also outputs the file MetaPathDir(Path) + 'LiveModuleList.pickle', 
    which is used to cache this computation for future recomputations of it. 
    
    RETURNS:
        LinkPath = path where the locallink file was created
        (i.e. MetaPathDir(Path) + 'LocalLinkList.pickle')
    
    '''
    metapathdir = MetaPathDir(Path) 
    LinkPath = metapathdir + 'LocalLinkList.pickle'
    LiveModulePath = metapathdir + 'LiveModuleList.pickle'

    if not PathExists(metapathdir):
        MakeDirs(metapathdir)   
    
    Remake = False
    Updated = False
    FileList = WORKING_DE.load_live_modules()
    LinkList = LinksFromOperations(FileList,AddImplied=True)
    if not IsFile(LinkPath) or not IsFile(LiveModulePath):
        SeedFiles = FileList
        OldLocalLinkList = LinkList[0:0]
    else:
        StoredFileList = cPickle.load(open(LiveModulePath,'rb'))
        PathTime = os.path.getmtime(LinkPath)
        OldLocalLinkList = numpy.load(LinkPath)
        ExistingScriptFiles = uniqify(OldLocalLinkList['UpdateScriptFile'])
        if not all([PathExists(x) and x in FileList for x in ExistingScriptFiles]) or not isinstance(StoredFileList,dict):
            SeedFiles = FileList
        else:   
            SeedFiles = [x for x in FileList if not x.split('/')[-1] == '__init__.py' and (x not in StoredFileList.keys() or os.path.getmtime(x) > StoredFileList[x])]      
            
    F = open(LiveModulePath,'wb')
    SFileDict = dict([(x[0],x[1]) for x in numpy.load(os.path.join(WORKING_DE.links_dir,'StoredTimes')) if x[0] in FileList])
    cPickle.dump(SFileDict,F)
    F.close()
    

    if len(SeedFiles) > 0:
        print 'Computing local links . . . '
        
        SeedFiles = numpy.array(SeedFiles)
        FileList = numpy.array(FileList)
        
        SeedLinkList = LinkList[fastisin(LinkList['UpdateScriptFile'],SeedFiles)]
        
        PP = numpy.array([Path])
        F1 = numpy.append(getpathalongs(PP,SeedLinkList['LinkSource']),getpathalongs(PP,SeedLinkList['SourceFile']))
        F2 = numpy.append(getpathalongs(PP,SeedLinkList['LinkTarget']),getpathalongs(PP,SeedLinkList['TargetFile']))
        NewLinks1S = SeedLinkList[F1]
        NewLinks1T = SeedLinkList[F2]
        
        if len(NewLinks1S) > 0:
            More = numpy.array(uniqify(NewLinks1S['LinkTarget']))
            NewLinks2S = SimpleStack1([NewLinks1S,GetEQ(More,LinkList,['LinkSource'])])
        else:
            NewLinks2S = NewLinks1S
        if len(NewLinks1T) > 0:
            More = numpy.array(uniqify(NewLinks1T['LinkSource']))
            NewLinks2T = SimpleStack1([NewLinks1T,GetEQ(More,LinkList,['LinkTarget'])])
        else:
            NewLinks2T = NewLinks1T
        NewLinks = SimpleStack1([NewLinks2S,NewLinks2T])
        if len(NewLinks) > 0:
            [DD,ss] = FastRecarrayUniqify(NewLinks)
            NewLinks = (NewLinks[ss])[DD]
    
            
        ToRemove = fastisin(OldLocalLinkList['UpdateScriptFile'],SeedFiles) | numpy.invert(fastisin(OldLocalLinkList['UpdateScriptFile'],FileList))
        NewLocalLinkList = SimpleStack1([OldLocalLinkList[numpy.invert(ToRemove)],NewLinks])

        if not PathExists(LinkPath) or len(ToRemove.nonzero()[0]) > 0 or len(NewLinks) > 0:
            NewLocalLinkList.dump(LinkPath)
            
    return LinkPath     
        
def MakeLocalLinkGraph(Path,Mode='ColDir',ShowUses='No',ShowImplied='No'):
    '''
    Takes a local link list as made by MakeLocalLinkList and turns it a 
    graph .svg file.  (also creates an html-ized version of the local linkgraph list.
    
    The basic strategy of this functions is:
        1) load the local link list created in a numpy pickle file 
            at the path Linkpath
        2) Cluster the nodes based on the mode:  
            -- if Mode = 'ColDir' then collapse nodes within directories
            -- if Mode = 'ColPro' the collapse nodes based on their being part of 
            protocols
            -- if Mode = 'All' then do no collapsing
        3) Create an html reprsentation of the link graph (with the collapsed
            clusters notated in it)
        4) Create a graph with the collapsed nodes as an object of the form 
            
            G = [Nodes,Edges, NodeAttributes,EdgeAttributes]
        
        5) convert the G object into .dot and then .svg files.
        
    
    ARGUMENTS:
    --Path : path to make graph of local link list for
    --Mode : string, which "graph quotienting" mode to use
    --ShowUses : boolean, whether to include uses links or not
    --ShowImplied : boolean, whether to include implied links or not
    
    RETURNS:    
    [message,metapath,G,metapathhtml], where:
            
        message is an error message, if any (blank '' char if no error message)
        metapath = path where .svg file has been created
        
        G = [N,E,NAttrs,EAttrs]
        
        where N and E is a list of the graph nodes and edges,
        as a python list, and NAttrs and EAttrs are corresponding
        lists of node and edge attributes (for .dot graph format)
        
        metapathhtml = path where an html representation of the link 
        list has been stored
                
    
    '''
    LinkPath = MakeLocalLinkList(Path)
    
    
    if not PathExists(LinkPath):
        return ['No Links','',None,None]
    else:
        T2 = os.path.getmtime(LinkPath)
        
        graphmetapathdir = MetaPathDir(Path) + '__LocalLinkGraphs/'
        metapathdot = graphmetapathdir + '/LocalLinkGraph' + Mode + ('_ShowUses' if ShowUses == 'Yes' else '') + ('_ShowImplied' if ShowImplied == 'Yes' else '') + '.dot'
        metapath = graphmetapathdir + '/LocalLinkGraph' + Mode + ('_ShowUses' if ShowUses == 'Yes' else '') + ('_ShowImplied' if ShowImplied == 'Yes' else '') + '.svg'
        metapathpickle = graphmetapathdir + '/LocalLinkGraph' + Mode + ('_ShowUses' if ShowUses == 'Yes' else '') + ('_ShowImplied' if ShowImplied == 'Yes' else '') + '.pickle'
        metapathhtml = graphmetapathdir + '/LocalLinkListHtml' + Mode + ('_ShowUses' if ShowUses == 'Yes' else '') + ('_ShowImplied' if ShowImplied == 'Yes' else '') + '.html'
    
        T = -1*numpy.inf if not PathExists(metapathdot) else os.path.getmtime(metapathdot)
        T1 = -1*numpy.inf if not PathExists(metapath) else os.path.getmtime(metapath)
        T3 = -1*numpy.inf if not PathExists(metapathpickle) else os.path.getmtime(metapathpickle)
        T4 = -1*numpy.inf if not PathExists(metapathhtml) else os.path.getmtime(metapathhtml)
    
        if min([T,T3,T4]) < T2:     
            print 'Rendering Graph . . . '
            LinkList = numpy.load(LinkPath)
            if len(LinkList) > 0:
                ClusterTags = GetClusterTagDict(Path,LinkList,Mode)
                if ShowUses != 'Yes':
                    LinkList = LinkList[LinkList['LinkType'] != 'Uses']
                if ShowImplied != 'Yes':
                    LinkList = LinkList[LinkList['LinkType'] != 'Implied']  
                if len(LinkList) == 0:
                    return ['There are only uses or implied links.', '',None,None]
                if not IsDir(graphmetapathdir):
                    MakeDirs(graphmetapathdir)  
                MakeLinkListHtml(LinkList,ClusterTags,Path,metapathhtml,Mode,ShowUses,ShowImplied)
                if len(uniqify(ClusterTags.values())) <= GraphIsTooLarge:
                    G = LabeledGraphFromLinks(LinkList,Path,ClusterTags,Mode,ShowUses,ShowImplied)  
                    WriteOutGraphDot(G,metapathdot)
                    F = open(metapathpickle,'w')
                    cPickle.dump(G,F)
                    F.close()
                    E = os.system('/usr/local/bin/dot -Tsvg -o ' + metapath + ' ' + metapathdot)
                    return ['',metapath,G,metapathhtml]
                else:
                    return ['Graph is too large to render.', '',None,metapathhtml]
            else:
                return ['No Links','',None,None]
        else:       
            if T1 < T:

                E = os.system('/usr/local/bin/dot -Tsvg -o ' + metapath + ' ' + metapathdot)
                if not PathExists(metapath):
                    print 'ERROR: System seems to having trouble running "dot" to make svg file of graph from .dot file.'
            G = cPickle.load(open(metapathpickle,'r'))
            return ['',metapath,G,metapathhtml]
        
    
def MakeLinkListHtml(LinkList,ClusterTags,inpath,outpath,Mode,ShowUses,ShowImplied):
    '''
    takes a data dependency linklist and a list of cluster tags, and 
    outputs an html representation of the linklist file (basically as
    a clickable html table) 
    
    ARGUMENTS:
    --LinkList = the linklist to reresent, a numpy record array
    --ClusterTags = dictionary of clusters (output for example of
        the GetClusterTagDict function)
    --inpath = path that the LinkList is a representation of
    --outpath = place to store the resulting Html file
    --Mode = Name of the cluster collapse mode
    --ShowUses, ShowImplied are as in MakeLocalLinkGraph
        
    returns:
        nothing
            
    
    '''

    LinkGen = lambda s,sp,sum,frag,rep,mode,su,si :  '<a target = _top href="/.starflow/CGI-Executables/main_gui.cgi?Path=' + sp + '&Summary=' + sum + '&Fragment=' + frag + '&Representation=' + rep + '&Mode=' + mode + '&ShowUses=' + su + '&ShowImplied=' + si + '"/>' + s + '</a>'

    names = ['LinkType','LinkSource','SourceFile','LinkTarget','TargetFile','SourceCluster','TargetCluster']
    Recs = []   
    for i in range(len(LinkList)):
        s = LinkList['LinkSource'][i] ; sp = LinkList['SourceFile'][i] if IsDir(LinkList['SourceFile'][i]) else DirName(LinkList['SourceFile'][i])
        ssum = opmetadatapath(s) if LinkList['LinkType'][i] == 'Uses' or LinkList['LinkType'][i] == 'CreatedBy' else metadatapath(s)
        srep = LinkList['SourceFile'][i] + ('@' + LinkList['LinkSource'][i].split('.')[-1] if IsDotPath(LinkList['LinkSource'][i],LinkList['SourceFile'][i]) else '')
        spsum = metadatapath(sp)
        t = LinkList['LinkTarget'][i] ; tp = LinkList['TargetFile'][i] 
        tsum = opmetadatapath(t) if LinkList['LinkType'][i] == 'Uses' or LinkList['LinkType'][i] == 'DependsOn' else metadatapath(t)
        trep = LinkList['TargetFile'][i] + ('@' + LinkList['LinkTarget'][i].split('.')[-1] if IsDotPath(LinkList['LinkTarget'][i],LinkList['TargetFile'][i]) else '')
        tpsum = metadatapath(tp)

        slink = LinkGen(s,sp,ssum,s,srep,Mode,ShowUses,ShowImplied)
        splink = LinkGen(sp,sp,spsum,sp,sp,Mode,ShowUses,ShowImplied)
        tlink = LinkGen(t,tp,tsum,t,trep,Mode,ShowUses,ShowImplied)
        tplink  = LinkGen(tp,tp,tpsum,tp,tp,Mode,ShowUses,ShowImplied)
    
        Recs.append([LinkList['LinkType'][i],slink,splink,tlink,tplink,ClusterTags[s] if s in ClusterTags.keys() else '',ClusterTags[t] if t in ClusterTags.keys() else ''])
    
    RecList = numpy.rec.fromrecords(Recs,names=names)
    RecList.sort(order=['SourceCluster','TargetCluster','LinkSource','LinkTarget'])
    tb.web.tabular2html(fname=outpath,X = RecList,title = 'Link Graph for ' + inpath,split=False)
    
    
def LabeledGraphFromLinks(LinkList,Path,ClusterTags=None,Mode='ColDir',ShowUses='No',ShowImplied='No'):
    '''
    Produces a graphical representation for use in producing a
    .dot file representation of a Linklist>
    
    ARGUMENTS: as is MakeLocalLinkGraph
    
    Returns:
        object G = [Nodes,Edges,NodeAttrs,EdgeAttrs]
    where
        Nodes is a python list of node names
        Edges is a python list of pairs of node names, representing node edges
        NodeAttrs is a dictionary of node attributes where:
            -- the keys are node names
            -- the value on a key 'n' is a dictionary of .dot format 
            key-value attribute pairs for node 'n', e.g. 
            {'color':'green','shape':'box', .... } 
        EdgeAttrs is a dictionary of edge  attributes, where:
            -- the keys are edge pairs
            -- the value on a key 'e' is a dictionary of .dot format 
            key-values attribute pairs for edge 'e', e.g. 
            {'color':'green','shape':'box', .... } 
    ''' 
    #add nodes and edges as required
    ClusterTags = {} if ClusterTags == None else ClusterTags

    CB = LinkList['LinkType'] == 'CreatedBy'
    U = LinkList['LinkType'] == 'Uses'
    DO = LinkList['LinkType'] == 'DependsOn'
    FB = CB | U
    FO = DO | U

    A = numpy.rec.fromrecords(uniqify(zip(LinkList['LinkSource'],LinkList['SourceFile'],CB,FB) + zip(LinkList['LinkTarget'],LinkList['TargetFile'],DO,FO)), names = ['Object','File','OpType','FuncType'])  

    CTags = dict([(a,a) for a in A['Object'] if a not in ClusterTags.keys()])
    CTags.update(ClusterTags)
    Y = numpy.array([CTags[a] for a in A['Object']])
    Nodes = uniqify(Y.tolist())
    s = Y.argsort()
    Y = Y[s]
    A = A[s]
    Diffs = numpy.append([-1],numpy.append((Y[1:] != Y[:-1]).nonzero()[0],[len(Y)-1]))
    NodeInfo = dict([(Y[Diffs[i]],A[Diffs[i-1]+1:Diffs[i]+1]) for i in range(1,len(Diffs))])
    
    X = zip(LinkList['LinkSource'], LinkList['LinkTarget'])
    Edges = uniqify([(CTags[a],CTags[b]) for (a,b) in uniqify(X)])
    Y = numpy.array([CTags[a] + '__;;__' + CTags[b] for (a,b) in X])
    s = Y.argsort()
    Y = Y[s]
    LinkList = LinkList[s]
    Diffs = numpy.append([-1],numpy.append((Y[1:] != Y[:-1]).nonzero()[0],[len(Y)-1]))
    EdgeInfo =  dict([(tuple(Y[Diffs[i]].split('__;;__')),LinkList[Diffs[i-1]+1:Diffs[i]+1]) for i in range(1,len(Diffs))])
    
    NodeAttrs= {}
    for n in Nodes:
        NodeAttrs[n] = dict(zip(['color','style','shape','label','width','height','target','URL'],NodePropertiesSelector(n,Path,ClusterTags,NodeInfo,Mode,ShowUses,ShowImplied)))

    EdgeAttrs = {}
    for e in Edges:
        EdgeAttrs[e] = dict(zip(['color','labelfloat','label','style'],EdgePropertiesSelector(e,EdgeInfo)))


    return [Nodes,Edges,NodeAttrs,EdgeAttrs]

    
def EdgePropertiesSelector(e,EdgeInfo):
    '''
        Technical dependency used in LabeledGraphFromLinks
    '''
    
    EdgeType = EdgeTypeDeterminer(e,EdgeInfo)
    if EdgeType == 'Uses':
        color = 'blue'
    elif EdgeType == 'DependsOn':
        color = 'crimson'
    elif EdgeType == 'CreatedBy':
        color = 'green'
    elif EdgeType == 'Implied':
        color = 'gray'  
    else:
        color = 'white' 
    label = ''
    labelfloat = 'false'
    style = 'solid'
    return [color,labelfloat,label,style]
    
    
def EdgeTypeDeterminer(e,EdgeInfo):
    '''
        Technical dependency used in LabeledGraphFromLinks
    '''
    E = EdgeInfo[e]
    EdgeType = MostCommonValue(E['LinkType'])   
    return EdgeType



def NodePropertiesSelector(n,Path,ClusterDict,NodeInfo,Mode,ShowUses,ShowImplied):
    '''
        Technical dependency used in LabeledGraphFromLinks
    '''
    
    [OpType,FunctionType,Exists,Other,URL] = NodeTypeDeterminer(n,NodeInfo,Mode,ShowUses,ShowImplied)

    IsCluster = n in ClusterDict.values() and len(NodeInfo[n]) > 1
    label = LabelFunc(n,Path,Other,IsCluster)
    if label.startswith('CURRENT Path'):
        color = 'crimson'
    elif Other:
        color = 'green'
    elif OpType:
        if IsCluster:
            color = 'coral'
        else:
            color = 'pink'
    elif FunctionType:
        if IsCluster:
            color = 'goldenrod'
        else:
            color = 'greenyellow'
    else:
        if IsCluster:
            color = 'lightslateblue'
        else:
            color = 'lightblue'
    if Exists:
        style = 'filled,dashed'
    else:
        style = 'filled'
    if OpType:
        shape = 'box'
    else:
        shape = 'ellipse'
    if shape == 'box':
        width = str(.11*len(label))
    else:
        width = str(.11*len(label))
    height = '0.5'
    target = '_top'
    return [color,style,shape,label,width,height,target,URL]
    


def NodeTypeDeterminer(n,NodeInfo,Mode,ShowUses,ShowImplied):
    '''
        Technical dependency used in LabeledGraphFromLinks
    '''
    N = NodeInfo[n]
    OpType = sum(N['OpType']) >= (1/2)*len(N)
    FunctionType = sum(N['FuncType']) >= (1/2)*len(N)
    OtherList = [OutsideFile(nn) for nn in N['Object']]
    Other = sum(OtherList) >= (1/2)*len(OtherList)  
    ExistsList = [PathExists(nn) for nn in N['File']]
    Exists = all(ExistsList)
    
    if FunctionType:
        A = [(N['Object'][i],N['File'][i],N['FuncType'][i]) if ExistsList[i] else 'NotExists' for i in range(len(N)) if N['FuncType'][i]]
    else:
        A = [(N['Object'][i],N['File'][i],N['FuncType'][i]) if ExistsList[i] else 'NotExists' for i in range(len(N)) if not N['FuncType'][i]]
    B = list(set(A).difference(['NotExists']))
    Path = 'NotExists' if len(B) == 0 else MaximalCommonPath([nn[1] if IsDir(nn[1]) else DirName(nn[1]) for nn in B])
    
    if len(B) == 0:
        Summary = Fragment = Representation = 'NotExists'
    else:
        Summary = MaximalCommonPath([opmetadatapath(nn[0]) if nn[2] else metadatapath(nn[0]) for nn in B])
        X = MaximalCommonPath([nn[0] for nn in B])
        Y = MaximalCommonPath([nn[1] + ('@' + nn[0].split('.')[-1] if nn[2] else '') for nn in B])  
        Fragment = X if X != '' else Y.strip('@')[0] if Y!= '' else '../'
        Representation = Y if Y!= '' else '../'
    
    URL  = '/.starflow/CGI-Executables/main_gui.cgi?Path=' + Path + '&Summary=' + Summary + '&Fragment=' + Fragment + '&Representation=' + Representation + '&Mode=' + Mode + '&ShowUses=' + ShowUses + '&ShowImplied=' + ShowImplied
    return [OpType,FunctionType,Exists,Other,URL]


def DeleteLinkGraphs():

    Y = RecursiveFileList(WORKING_DE.relative_metadata_dir)
    Z = uniqify([x[:x.find('__LocalLinkGraphs/')+18] for x in Y if '__LocalLinkGraphs/' in x])
    for z in Z:
        delete(z)
        
        
def DeleteLocalLinkLists():
    Y = RecursiveFileList(WORKING_DE.relative_metadata_dir)
    Z = uniqify([x for x in Y if x.endswith('LocalLinkList.pickle') or x.endswith('LocalLinkListAF.pickle') ])
    for z in Z:
        delete(z)

    
def inverse(S):
    '''
    inverts permutation described a numpy array
    '''
    T = numpy.arange(len(S))
    T = T[S]
    return T


def GetEQ(X,Y,taglist):
    X.sort()
    A = numpy.zeros((len(Y),),bool)
    for tag in taglist:
        A = A | fastisin(Y[tag],X)
    YY = Y.copy()
    return YY[A]



def ProcessTwoDicts(A,B):
    '''
        Technical dependency used in GetClusterTagDict
    '''
    T = [(l,A[l] + B[l] if (l in A.keys() and l in B.keys()) else A[l] if l in A.keys() else B[l]) for l in set(A.keys()).union(B.keys())]
    return dict([(a[0],','.join(numpy.sort(uniqify(a[1])))) for a in T if len(a[1]) > 0])


def MaximalCP(P):
    '''
        Technical dependency used in LabeledGraphFromLinks
    '''
    
    P1 = [p for p in P if p.startswith('../')]
    P2 = [p.replace('.','/') for p in P if not p.startswith('../')]
    
    if len(P1) > 0 and len(P2) > 0:
        mp =  MaximalCommonPath(P1) + ', ' + MaximalCommonPath(P2).replace('/','.').strip('.')
    elif len(P1) > 0:
        mp =  MaximalCommonPath(P1)
    elif len(P2) > 0:
        mp =  MaximalCommonPath(P2).replace('/','.').strip('.')
    else:
        mp = None
        
    if mp == '':
        mp = 'Cluster'
    
    return mp
        

def SPathAlong(p1,p2):
    '''
        Technical dependency used in GetClusterTagDict
    '''
    if p1.startswith('../') and p2.startswith('../'):
        return PathAlong(p1,p2)
    elif '/' not in p1 and '/' not in p2:
        return PathAlong(p1.replace('.','/'),p2.replace('.','/'))
    else:
        return False
    

def GetClusterTagDict(Path,LinkList,Mode):
    '''
    Given a  LinkList and a mode for collapsing the Linklist, 
    produce a dictionary of node cluster tags. 
    
    ARGUMENTS:
        Path -- path that the LinkList corresponds to
        LinkList -- list of Links as a numy record array
        Mode -- Mode by which to cluster the link nodes
        
    RETURNS:
        ClusterDict, a dictionary in which:
        -- the keys are (some of the) link sources or targets in the 
            LinkList (e.g. potential nodes in the graph of the linklist)
        -- value on a key is a "cluster name " which represents a set 
        of nodes that will collapsed together
        
    The "mode" determines which collapsing algorithm should be used.  
        
    '''
    if Mode == 'All':
        #no collapsing
        return {}
    elif Mode == 'ColDir':
        #collapse files within directory (except for files/subdirectories in 'Path', which are all not collapsed)
        t = time.time()
        if IsDir(Path):
            LinkList = LinkList.copy()
            
            K = uniqify(LinkList['LinkSource'].tolist() + LinkList['LinkTarget'].tolist())
            OutSides = numpy.array([k for k in K if OutsideFile(k)])
            ClusterDict = {}
            OutSides.sort()
            NotOutSide = numpy.invert(fastisin(LinkList['LinkSource'],OutSides))
            LinkList = LinkList[NotOutSide]
            splitpath = Path.split('/')
            L = []
            for j in range(1,len(splitpath)):
                p = '/'.join(splitpath[:j])
                L += [p + '/' + l + ('/' if IsDir(p + '/' + l) else '') for l in os.listdir(p) if p + l != '/'.join(splitpath[:j+1])]
            L += [Backslash(Path) + l  + ('/' if IsDir(Backslash(Path) + l) else '') for l in os.listdir(Path)] 

            K = uniqify(LinkList['LinkSource'].tolist() + LinkList['LinkTarget'].tolist())
            
            #ClusterDict.update(dict([(k,[l for l in L if SPathAlong(k,l)][-1]) for k in K if len([l for l in L if SPathAlong(k,l)]) > 0]))
            
            ClusterDict = {}
            if Path.startswith('../'):
                ModK = [k for k in K if k.startswith('../')]    
                L = numpy.array(L)
                C = maximalpathalong(ModK,L)
                ClusterDict.update(dict([(ModK[i],C[i]) for i in range(len(ModK)) if C[i] != '']))          
                
            else:
                K = [k for k in K if not k.startswith('../')]
                ModK = [k.replace('.','/') for k in K]  
                L = numpy.array(L)
                C = maximalpathalong(ModK,L)
                ClusterDict.update(dict([(K[i],C[i]) for i in range(len(K)) if C[i] != '']))
            
            LinkList.sort(order=['LinkSource'])
            LS = LinkList.copy()
            LSDiffs = numpy.append(numpy.append([-1],(LS['LinkSource'][1:] != LS['LinkSource'][:-1]).nonzero()[0]),[len(LS)])
            LinkList.sort(order=['LinkTarget'])
            LT = LinkList.copy()
            LTDiffs = numpy.append(numpy.append([-1],(LT['LinkTarget'][1:] != LT['LinkTarget'][:-1]).nonzero()[0]),[len(LT)])
            for ii in range(2):
                SClusterDict2 = dict([(LS['LinkSource'][LSDiffs[i]],[ClusterDict[l] for l in LS['LinkTarget'][LSDiffs[i]:LSDiffs[i+1]] if l in ClusterDict.keys()]) for i in range(len(LSDiffs)-1) if LS['LinkSource'][LSDiffs[i]] not in ClusterDict.keys()])
                TClusterDict2 = dict([(LT['LinkTarget'][LTDiffs[i]],[ClusterDict[l] for l in LT['LinkTarget'][LTDiffs[i]:LTDiffs[i+1]] if l in ClusterDict.keys()]) for i in range(len(LTDiffs)-1) if LT['LinkTarget'][LTDiffs[i]] not in ClusterDict.keys()])
                ClusterDict2 = ProcessTwoDicts(SClusterDict2,TClusterDict2)
                C2K = numpy.array(ClusterDict2.keys())
                C2V = numpy.array(ClusterDict2.values())
                s = C2V.argsort()
                C2V = C2V[s]
                C2K = C2K[s]
                Diffs = numpy.append(numpy.append([-1],(C2V[1:] != C2V[:-1]).nonzero()[0]),[len(C2V)])
                NewTags = dict(zip(C2K.tolist(),ListUnion([[MaximalCP(C2K[Diffs[i]+1:Diffs[i+1]+1])]*(Diffs[i+1] - Diffs[i]) for i in range(len(Diffs)-1)])))
                ClusterDict.update(NewTags)
            if len(OutSides) > .1*len(uniqify(ClusterDict.values())) and len(OutSides) > 4:
                ClusterDict.update(dict([(k,'External Files') for k in OutSides]))
            return ClusterDict
        else:
            return {}
    elif Mode == 'ColPro':

        #collapse based on protocol tags
        ClusterDict = {}
        Targets = uniqify(LinkList['LinkTarget'].tolist() + LinkList['LinkSource'].tolist())
        for target in Targets:
            metapaths = [opmetadatapath(target) + '/AssociatedMetaData.pickle',opmetadatapath(target) + '/AttachedMetaData.pickle']
            for metapath in metapaths:
                if PathExists(metapath):
                    MetaData = pickle.load(open(metapath,'r'))
                    if isinstance(MetaData,dict) and 'ProtocolTags' in MetaData.keys():
                        ProtocolTags = MetaData['ProtocolTags']
                        if isinstance(ProtocolTags,dict):
                            ClusterDict.update(ProtocolTags)   

        return ClusterDict
    else:
        print 'No graph plotting mode selected.'
        return {}


def MetaPathDir(Path):
    if Path.startswith('../') or OutsideFile(Path):
        return Backslash(metadatapath(Path))
    else:
        return Backslash(opmetadatapath(Path))
    
    

def WriteOutGraphDot(G,outpath):
    '''
    Writes out graph in the [N,E,Nattrs,Eattrs] format to a .dot file
    
    ARGUMENTS:

    object G = [Nodes,Edges,NodeAttrs,EdgeAttrs], where
        Nodes is a python list of node names
        Edges is a python list of pairs of node names, representing node edges
        NodeAttrs is a dictionary of node attributes where:
            -- the keys are node names
            -- the value on a key 'n' is a dictionary of .dot format 
            key-value attribute pairs for node 'n', e.g.
            {'color':'green','shape':'box', .... } 
        EdgeAttrs is a dictionary of edge  attributes, where:
            -- the keys are edge pairs
            -- the value on a key 'e' is a dictionary of .dot format 
            key-values attribute pairs for edge 'e', e.g. 
            {'color':'green','shape':'box', .... } 

        
    outpath -- path where .dot will be put
        
    RETURNS:
        nothing
    
    '''

    [Nodes,Edges,NodeAttrs,EdgeAttrs] = G
    
    S = 'strict digraph{\n'
    
    for node in Nodes:
        S += '"' + str(node) + '"' + '  [' + ','.join([att + '="' + NodeAttrs[node][att] + '"' for att in NodeAttrs[node].keys()]) + ']\n' 

    for edge in Edges:
        S += '"' + str(edge[0]) + '"' + ' -> ' + '"' + str(edge[1]) + '"    [' + ','.join([att + '="' + EdgeAttrs[edge][att] + '"' for att in EdgeAttrs[edge].keys()]) + ']\n'
    
    S += '}'
    
    F = open(outpath,'w')
    F.write(S)
    F.close()

        
def LabelFunc(n,Path,Other,IsCluster):
    '''
    Technical dependency of LabeledGraphFromLinks
    '''
    C = 15
    s = str(n)
    s.strip(' ,')
    if IsDotPath(s):
        if len(s) > C:
            return s[s[:-1*C].rfind('.')+1:]
        else:
            return s
    elif Other:
        return s
    elif PathStrictlyAlong(s,Path + ('/' if Path[-1] != '/' else '')):
        ss = s[len(Path):]
        return ss if ss[0] != '/' else ss[1:]
    elif (n == Path) or (n == Path + '/') or (n == Path[:-1]):
        return 'CURRENT Path: ' + s
    else:
        if s.startswith('../'):
            if len(s) > C:
                i = s[:-1*C].rfind('/')
                if i > 0:
                    return s[i:]
                else:
                    return s
            else:
                return s
        elif IsProtocolPath(s):
            X = s.split(',\ ')
            if ':' in X[1]:
                return X[1].split('Apply')[-1]
            else:
                return X[1].split('\\n')[0] + ' Output'
        else:
            return s
            
    
    return (n.split('/')[-1] if n.startswith('../') else n.split('.')[-1])
    
def IsProtocolPath(s):
    '''
    Technical dependency of LabelFunc
    '''
    return s.startswith('Protocol\ ')


def MostCommonValue(D):
    '''
    Given numpy array D, determines most common value D
    
    '''
    V = uniqify(D)
    countdict = {}
    for a in V:
        countdict[a] = sum(D == a)
    m = max(countdict.values())
    argmax = countdict.values().index(m)
    return countdict.keys()[argmax] 
    
def OutsideFile(path):
    '''
    Determines for purposes of graph coloring whether a file is an "outside" file -- 
    right now, the only kind of "outside" file that is recognized are web files.  
    Perhaps direct connections to servers and databases should be added
    here for various formats eventually.
    '''
    return path.startswith('http://') or path.startswith('https://')