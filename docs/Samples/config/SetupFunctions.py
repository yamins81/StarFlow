'''
Contains functions I use for configuring the  Data Environment.
'''
import System.LinkManagement as LM
from System.Utils import RecursiveFileList, CheckInOutFormulae, getpathalong, uniqify, ListUnion

SERVERNAME = 'DataEnvironment'
	
def GetLiveModules(LiveModuleFilters):
	'''
	Function for filtering live modules that is fast by avoiding looking through directories i know will be irrelevant.
	'''
	#for each thing in live modulefilter
	FilteredModuleFiles = []
	for x in LiveModuleFilters.keys():
		RawModuleFiles = [y for y in RecursiveFileList(x,Avoid=['^RawData$','^Data$','^.svn$','^ZipCodeMaps$','.data$','^scrap$']) if y.split('.')[-1] == 'py']
		FilteredModuleFiles += [y for y in RawModuleFiles if CheckInOutFormulae(LiveModuleFilters[x],y)]
	return FilteredModuleFiles
	

def GetSVNFiles(SVNPaths=None):
	'''
	Function for filtering files to put in the SVN repository.
	'''

	if SVNPaths == None:
		SVNPaths = []

	LinkList = LM.LinksFromOperations(LM.LoadLiveModules())
	
	Things = numpy.array(uniqify(LinkList['TargetFile'].tolist() + LinkList['SourceFile'].tolist() + LinkList['UpdateScriptFile'].tolist()))
	Things.sort()
	
	CreatedThings = LinkList[LinkList['LinkType'] == 'CreatedBy']['LinkTarget']
	CreatedThings.sort()
	
	[A,B] = getpathalong(CreatedThings,Things)
	C = uniqify(ListUnion([range(a,b) for (a,b) in zip(A,B) if b > a]))
	D = numpy.ones((len(Things),), bool) ; D[C] = False
	[A,B] = getpathalong(Things,CreatedThings)
	GoodThings = Things[D & (B == A)]
		
	SVNPaths = uniqify(SVNPaths + GoodThings.tolist())
	
	Files = uniqify([x for x in ListUnion([RecursiveFileList(x) for x in SVNPaths]) if '.svn/' not in x and '.DS_Store' not in x])
	
	return [Files,SVNPaths]