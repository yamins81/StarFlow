from examples.imdelastic.run import MakeCrystal, IMDGetElastic, IMDGetCommon, IMDRun, IMDAnimationXY, IMDAnimationXZ, IMDAnimationYZ

from System.Utils import MakeDir

root = '../imdelastic/oneoff/'
configroot = root + 'config/'
perlroot = root + 'perl/'

def makeConfigFiles(depends_on = root + 'config.txt', creates = configroot):
	"""
	Split up input config file into separate config files for each pipeline step
	"""
	MakeDir(creates)
	config =  [x.strip().split('\n') for x in open('../imdelastic/oneoff/config.txt','rU').read().split('#') if x.strip()]
	names = ['makecrystal', 'imdgetelastic', 'imdgetcommon', 'imdrun', 'imdanimation']
	for c in config:
		assert c[0] in names, "Expected pipeline step in " + str(names) + " but got " + c[0]
		F = open(creates + c[0] + '-config.txt', 'w')
		F.write('\n'.join([line.strip() for line in c[1:] if line.strip()]))
		F.close()
		
def parseConfigFile(path, varlist):
	"""
	Parse configuration file corresponding to one pipeline step
	"""
	vars = dict([[y.strip() for y in tuple(x.split('='))] for x in open(path, 'rU').read().strip().split('\n') if len(x.split('=')) == 2])
	assert set(vars.keys()) == set(varlist), "Expected variables " + str(varlist) + " but read " + str(vars.keys()) + " from config file"
	return ' '.join([vars[v] for v in varlist])

def myMakeCrystal(depends_on = (perlroot + 'makecrystal-run.pl', configroot + 'makecrystal-config.txt'), creates = (root + 'OUT.xyz', root + 'BOX.prop') + tuple([root + i + '_crystal.png' for i in ['XY', 'XZ', 'YZ', 'XYZ']])):
	"""
	x				#Dimension_x (even integer > 0)
	y				#Dimension_y (even integer > 0)
	z				#Dimension_z (even integer > 0)
	crack_length	#Crack length ratio (aa/length_x)
	crack_slope		#Crack slope m
	vacuum_space	#Vacuum space (to the right and left)
	x_strain		#Strain in x direction (e.g. 1.10 for 10%))
	"""
	input = parseConfigFile(depends_on[-1], ['x', 'y', 'z'])
	MakeCrystal(input).perform()

def myIMDGetElastic(depends_on = ('Tr_IN_Elastic', perlroot + 'imdgetelastic-run.pl', configroot + 'imdgetelastic-config.txt'), creates = root + 'Tr_Elastic1.prop'): # 'Tr_IN_Elastic' in lib folder:
	"""
	r_cut			#Cutoff of potential 
	lj_epsilon		#Lennard-Jones epsilon parameter 
	lj_sigma		#Lennard-Jones sigma parameter 
	lindef_inter	#Nr of steps after which is linear deformation matrix applied 
	lindef_xx		#Strain increments X 
	lindef_yy		#Strain increments Y 
	lindef_zz		#Strain increments Z 
	"""        
	input = parseConfigFile(depends_on[-1], ['r_cut', 'lj_epsilon', 'lj_sigma', 'lindef_inter', 'lindef_xx', 'lindef_yy', 'lindef_zz'])
	IMDGetElastic(input).perform()
    
def myIMDGetCommon(depends_on = (root + 'Tr_Elastic1.prop', root + 'OUT.xyz', root + 'BOX.prop', perlroot + 'imdgetcommon-run.pl', configroot + 'imdgetcommon-config.txt'), creates = root + 'Tr_Elastic.prop'):
	"""
	maxsteps		#maximum # of steps
	timestep		#timestep (in 1.018E-014 sec)
	pbc_x			#periodic BCs in X
	pbc_y			#periodic BCs in Y
	pbc_z			#periodic BCs in Z
	eng_int			#How often is energy & stress information written
	checkpt_int		#How often is chkpt information written
	startingtemp	#Starting temperature
	"""
	input = parseConfigFile(depends_on[-1], ['maxsteps', 'timestep', 'pbc_x', 'pbc_y', 'pbc_z', 'eng_int', 'checkpt_int', 'startingtemp'])
	IMDGetCommon(input).perform()
    
def myIMDRun(depends_on = (root + 'Tr_Elastic.prop', root + 'OUT.xyz', perlroot + 'imdrun-run.pl'), creates = (root + 'Checkpoints.zip', root + 'out.xyz')):
	IMDRun().perform()
    
def myIMDAnimationXY(depends_on = (root + 'Checkpoints.zip', perlroot + 'imdanimation-run.pl', configroot + 'imdanimation-config.txt'), creates = root + 'MovieXY.gif'):
	input = parseConfigFile(depends_on[-1], ['energyCutoff'])
	IMDAnimationXY(input).perform()

def myIMDAnimationXZ(depends_on = (root + 'Checkpoints.zip', perlroot + 'imdanimation-run.pl', configroot + 'imdanimation-config.txt'), creates = root + 'MovieXY.gif'):
	input = parseConfigFile(depends_on[-1], ['energyCutoff'])
	IMDAnimationXZ(input).perform()
	
def myIMDAnimationYZ(depends_on = (root + 'Checkpoints.zip', perlroot + 'imdanimation-run.pl', configroot + 'imdanimation-config.txt'), creates = root + 'MovieXY.gif'):
	input = parseConfigFile(depends_on[-1], ['energyCutoff'])
	IMDAnimationYZ(input).perform()