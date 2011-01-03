#!/usr/bin/env python
'''
Static analysis routines. 

'''

import compiler, inspect
from starflow.utils import *


def GetFullUses(FilePath):
	'''
	Adds information about actual paths in  existence in the file system to further 
	refine results of the GetUses function. 
	
	Argument:
	--FilePath = path to file of module to do static analysis of. 
		
	Returns:
	If call to GetUses Fails, then: None, else, a dictionary F, where:
	-- the keys are names of objects defined in the module in FilePath
	and
	-- for the key 'Obj', the value F['Obj']  is a list of pairs 
		
		(objname,file) 
		
		where objname is the name of an object that is referenced 
		somwhere in the definition of 'Obj' and file is the name of the
		file where objname is defined. 
			
	'''

	ModuleName = FilePath.lstrip('../').rstrip('.py').replace('/','.')
	try:
		[F,M,N] = GetUses(FilePath=FilePath)
	except:
		return None
	else:
		pass


	Mentions = ListUnion(F.values())
	
	#internals as those things in mentions that are in N.keys() + F.keys()
	ModuleName = FilePath[3:-3].replace('/','.')
	Internals = set(Mentions).intersection(N.keys() + F.keys())
	InternalRefs = dict([(x,(ModuleName+'.'+x,FilePath)) for x in Internals])
	
	
	[Externals,StarUses,MoreInternals] = usechecking(Mentions,M,N,FilePath,ModuleName,Internals,'__module__')


	FF = {}
	for k in F.keys():
		[LocalExternals, LocalStarUses, LocalMoreInternals] = usechecking(Mentions,M,N,FilePath,ModuleName,Internals,k)
		LocalExternals.update(Externals) ; LocalStarUses.update(StarUses) ; LocalMoreInternals.update(MoreInternals)
		
		A = []
		for t in [InternalRefs,LocalExternals,LocalStarUses,LocalMoreInternals]:
			A += [t[l] for l in F[k] if l in t.keys()]
		A = uniqify(A)
		B = [l for l in F[k] if l not in InternalRefs.keys() + LocalExternals.keys() + LocalStarUses.keys() + LocalMoreInternals.keys()]
		FF[k] = [A,B]
	for k in N.keys():
		[LocalExternals, LocalStarUses, LocalMoreInternals] = usechecking(Mentions,M,N,FilePath,ModuleName,Internals,k)
		LocalExternals.update(Externals) ; LocalStarUses.update(StarUses) ; LocalMoreInternals.update(MoreInternals)
		A = []
		for t in [InternalRefs,Externals,StarUses,MoreInternals]:
			A += [t[l] for l in N[k] if l in t.keys()]
		A = uniqify(A)
		B = [l for l in N[k] if l not in InternalRefs.keys() + LocalExternals.keys() + LocalStarUses.keys() + LocalMoreInternals.keys()]
		FF[k] = [A,B]
		
	return FF


def usechecking(Mentions,M,N,FilePath,ModuleName,Internals,key):

	if key in M.keys():
		M = M[key]
		Imported = [] ; Imports = []	
		for x in Mentions:
			if x in M.keys():
				Imported += [(x,M[x])]
				Imports += [(x,x)]
			elif any([x.startswith(m + '.') for m in M.keys()]):
				H =  [m for m in M.keys() if x.startswith(m + '.')]
				Imports += [(x,h) for h in H]
				Imported += [(x,M[h] + x[len(h):]) for h in H]
		Externals = {}
		for (x,y) in Imported:
			
			paths1 = ['../' + '/'.join(y.split('.')[:j]) + '.py' for j in range(len(y.split('.'))) if IsFile('../' + '/'.join(y.split('.')[:j]) + '.py')] 
			paths2 = ['../' + '/'.join(y.split('.')[:j])  + '/' for j in range(1,len(y.split('.'))) if IsDir('../' + '/'.join(y.split('.')[:j]))]
			
			if paths1:
				Externals[x] = (y,paths1[-1])
			elif paths2:
				Externals[x] = (y,paths2[-1])
			
				
		MoreInternals = dict([(x,(ModuleName + '.' + h,FilePath)) for (x,h) in Imports])
			
		Remainder = set(Mentions).difference(set([x[0] for x in Imports]).union(Internals))
		StarUses = []
		if len(Remainder) > 0:
			StarImports = [y[:-2] for y in N.keys() if is_string_like(y) and y.endswith('.*')]
			for si in StarImports:
				sip = '../' + si.replace('.','/') + '.py'
				if IsFile(sip):
					[F1,M1,N1] = GetUses(FilePath = sip)
					StarUses += [(r,(si + '.' + r,sip)) for r in Remainder.intersection(F1.keys() + N1.keys())]
					
		StarUses = dict(StarUses)
	else:
		Externals = {} ; StarUses = {}; MoreInternals = {}

	return [Externals,StarUses,MoreInternals]


def GetUses(AST = None,FilePath=None):
	'''
	Gets information about the names referenced in a python module or AST
	fragment by doing static code analysis. 
	
	ARGUMENTS:
	--AST = pre-compiler parse tree code object, 
		e.g. result of calling compiler.parse() on some code fragment
	--FilePath = Path to python module
	One or the other but not both of these two arguments must be given
		
	RETURNS:
	None, if FilePath is given and call to compiler.parseFile() fails, else:
	AST is either given or generated frm the FilePath code returns a 3-element
	list [F,M,N] where:
	---F = dictionary, where:
		the keys are names of scopes (e.g. classes and functions) defined in the AST
		the values are names of functions and names mentioned in the functions
	--M = list of modules imported or used in the AST
	--N = dictionary where
		-- the keys are names of non-scoping names (those besides functions or classes) 
		defined in the AST
		-- the value associated with key 'X' is list of other names
		by which X is known in the AST scope, including its definition
		in terms of imported modules
	'''

	if AST == None:
		assert FilePath != None, 'FilePath or AST must be specified'
		try:
			AST = compiler.parseFile(FilePath)
		except:
			print FilePath, 'failing to compile.'
			return None
		else:
			pass
	NameDefs = {}
	NamesUsage = {}
	ModuleUsage = {}
	GetUsesFromAST(AST,NameDefs, ModuleUsage, NamesUsage,'__module__')
	return [NamesUsage,ModuleUsage,NameDefs]
	
	
def GetUsesFromAST(e, NameDefs, ModuleUsage, NamesUsage , CurScopeName):
	'''
		Recursive function which implements guts of static analysis.  
	'''

	if isinstance(e,compiler.ast.Import):

		for l in e.getChildren()[0]:
			if CurScopeName not in ModuleUsage:
				ModuleUsage[CurScopeName] = {}
			if l[1] != None:
				NameDefs[l[1]] = [l[1]]

				ModuleUsage[CurScopeName][l[1]] = l[0]
			else:
				NameDefs[l[0]] = [l[0]]
				ModuleUsage[CurScopeName][l[0]] = l[0]
			
			
	elif isinstance(e,compiler.ast.From):
		modulename = e.getChildren()[0]
		for f in e.getChildren()[1]:
			attname = f[0]
			fullname = modulename + '.' + attname
			localname = f[0] if f[1] is None else f[1]
			localname = localname if localname != '*' else fullname
			NameDefs[localname] = [localname]
			if CurScopeName not in ModuleUsage:
				ModuleUsage[CurScopeName] = {}
			ModuleUsage[CurScopeName][localname] = fullname
			
			
	elif isinstance(e,compiler.ast.If):
		NewND = NameDefs.copy()
		Children = ProperOrder(e.getChildNodes())
		for f in Children:
			GetUsesFromAST(f,NewND,ModuleUsage, NamesUsage,CurScopeName)
		for l in NewND.keys():
			if not NewND[l] is None:
				DictionaryOfListsAdd(NameDefs,l,NewND[l])


	elif isinstance(e,compiler.ast.Class):
		NewND = NameDefs.copy()
		fname = e.getChildren()[0]
		if fname not in NamesUsage.keys():
			NamesUsage[fname] = []
		Children = ProperOrder(e.getChildNodes())
		NewFU = {}
		for f in Children:
			GetUsesFromAST(f,NewND,ModuleUsage,NewFU,'__module__')
		for l in NewFU.keys():
			NamesUsage[fname] += NewFU[l]


	elif isinstance(e,compiler.ast.Function):
		NewND = NameDefs.copy()
		fname = e.getChildren()[1]
		fvars = e.getChildren()[2]
		if fname not in NamesUsage.keys():
			NamesUsage[fname] = []
		Children = ProperOrder(e.getChildNodes())
		NewFU = {}
		for f in Children:
			GetUsesFromAST(f,NewND,ModuleUsage, NewFU,fname)
		for l in NewFU.keys():
			NamesUsage[fname] += [g for g in NewFU[l] if g.split('.')[0] not in fvars and g not in NewFU.keys()]
		
	elif isinstance(e,compiler.ast.Lambda):
		NewND = NameDefs.copy()
		fvars = e.argnames
		Children = ProperOrder(e.getChildNodes())
		for f in Children:
			GetUsesFromAST(f,NewND,ModuleUsage, NamesUsage,CurScopeName)
		NamesUsage[CurScopeName] = [g for g in NamesUsage[CurScopeName] if g.split('.')[0] not in fvars]
	
	elif isinstance(e,compiler.ast.ListComp):
		ForLoops = e.getChildren()[1:]
		LoopVars = [f.getChildren()[0].getChildren()[0] for f in ForLoops]
		Children = ProperOrder(e.getChildNodes())
		for f in Children:
			GetUsesFromAST(f,NameDefs,ModuleUsage, NamesUsage,CurScopeName)
		NamesUsage[CurScopeName] = [g for g in NamesUsage[CurScopeName] if g.split('.')[0] not in LoopVars]
		
	elif isinstance(e,compiler.ast.For):
		if isinstance(e.getChildren()[0],compiler.ast.AssTuple):
			LoopControlVars = [ee.getChildren()[0] for ee in e.getChildren()[0].getChildren()]
		else:
			LoopControlVars = [e.getChildren()[0].getChildren()[0]]
		Children = ProperOrder(e.getChildNodes())
		for f in Children:
			GetUsesFromAST(f,NameDefs,ModuleUsage, NamesUsage,CurScopeName)		
		NamesUsage[CurScopeName] = [g for g in NamesUsage[CurScopeName] if g.split('.')[0] not in LoopControlVars]
		

	elif isinstance(e,compiler.ast.Assign):
		Children = ProperOrder(e.getChildNodes())
		for f in Children:
			GetUsesFromAST(f,NameDefs,ModuleUsage, NamesUsage,CurScopeName)
			
		if isinstance(e.getChildren()[0],compiler.ast.AssList) or isinstance(e.getChildren()[0],compiler.ast.AssTuple):
			newnames = [ee.getChildren()[0] for ee in e.getChildren()[0].getChildren()]
			targs = e.getChildren()[1]
			if isinstance(targs, compiler.ast.List) or isinstance(targs, compiler.ast.Tuple):
				assignmenttargets = e.getChildren()[1].getChildren()
				assert len(newnames) == len(assignmenttargets), 'Wrong number of values to unpack.'
				for (newname,assignmenttarget) in zip(newnames,assignmenttargets):
					INT = interpretation(assignmenttarget,NameDefs)
					if INT == [] and CurScopeName == '__module__':
						NameDefs[newname] = [newname]
					else:
						NameDefs[newname] = INT
			else:
				assignmenttarget = e.getChildren()[1]
				INT = interpretation(assignmenttarget,NameDefs)
				for newname in newnames:		
					if INT == [] and CurScopeName == '__module__':
						NameDefs[newname] = [newname]
					else:
						NameDefs[newname] = INT
				
		else:
			newname = e.getChildren()[0].asList()[0]
			assignmenttarget = e.getChildren()[1]
			INT = interpretation(assignmenttarget,NameDefs)[:]
			if INT == [] and CurScopeName == '__module__':
				NameDefs[newname] = [newname]
			else:
				NameDefs[newname] = INT


	elif isinstance(e,compiler.ast.Getattr) or isinstance(e,compiler.ast.Name):
		attnameset = interpretation(e,NameDefs)[:]
		if not (attnameset is None):
			DictionaryOfListsAdd(NamesUsage,CurScopeName,attnameset)	

		if attnameset != []:
			Children = ProperOrder(e.getChildNodes())[1:]
		else:
			Children = ProperOrder(e.getChildNodes())
		for f in Children:
			GetUsesFromAST(f,NameDefs,ModuleUsage, NamesUsage,CurScopeName)
		

	else:
		Children = ProperOrder(e.getChildNodes())
		for f in Children:
			GetUsesFromAST(f,NameDefs,ModuleUsage, NamesUsage,CurScopeName)


def ProperOrder(NodeList):
	'''
	Order a list of AST nodes so that their analysis happens in proper for name defintions to be taken into account -- e.g. nonscope nodes first, then scope nodes. 
	'''

	SameScopeChildren = [e for e in NodeList if not (isinstance(e,compiler.ast.Function) or isinstance(e,compiler.ast.Class))]
	NewScopeChildren = [e for e in NodeList if isinstance(e,compiler.ast.Function) or isinstance(e,compiler.ast.Class)]
	return SameScopeChildren + NewScopeChildren


def interpretation(n, NameDefs):
	''' 
	determine "real" name(s) of a getattr or name ast node
	in terms of names of its pieces 
	'''

	if isinstance(n,compiler.ast.Getattr) or isinstance(n,compiler.ast.Name):
		nameseq = UnrollGetatt(n)
		if nameseq != None:
			if nameseq[0] in NameDefs.keys():
				if len(nameseq) > 1:
					return [l + '.' + '.'.join(nameseq[1:]) for l in NameDefs[nameseq[0]]]
				else:
					return NameDefs[nameseq[0]]
			else:
				return ['.'.join(nameseq)]
		else:
			return []
	else:
		return []
	

	
def UnrollGetatt(getseq):
	''' 
	unrolls a Name or GetAttr compiler ast node into a dot-separated string name. 
	'''

	if isinstance(getseq,compiler.ast.Name):
		return [getseq.getChildren()[0]]
	elif isinstance(getseq,compiler.ast.Getattr):
		lowerlevel = UnrollGetatt(getseq.getChildren()[0])
		if not (lowerlevel is None):
			return lowerlevel + [getseq.getChildren()[1]]


def DictionaryOfListsAdd(D,key,newitem):
	if key in D.keys():
		intersect = list(set(newitem).difference(D[key]))
		if len(intersect) > 0:
			D[key].extend(intersect)
	else:
		D[key] = newitem
		

# def FastTopNames(FilePath):
# 	try:
# 		AST = compiler.parseFile(FilePath)
# 	except:
# 		print FilePath, 'failing to compile.'
# 		return None
# 	else:
# 		pass
# 	Scopes = [l for l in AST.getChildren()[1] ]
	
	
