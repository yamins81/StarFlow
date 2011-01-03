from examples.imdelastic.run import MakeCrystal, IMDGetElastic, IMDGetCommon, IMDRun, IMDAnimationXY, IMDAnimationXZ, IMDAnimationYZ

from System.Utils import MakeDir
from System.Protocols import ApplyOperations2

root = '../imdelastic/protocol/'
perlroot = root + 'perl/'


def mc(args):
    MakeCrystal(args).perform()

def nano(args):
    IMDGetElastic(args).perform()
    
def common(args):
    IMDGetCommon(args).perform()
    
def run():
    IMDRun().perform()
    
def animation_xy(args):
    IMDAnimationXY(args).perform()

def animation_xz(args):
    IMDAnimationXZ(args).perform()

def animation_yz(args):
    IMDAnimationYZ(args).perform()


def make_fake_inputs(n_inputs = 3, creates = root + 'inputs.csv'):
	"""
	Make a CSV file where each row corresponds to the set of input parameters for one instance of a pipeline run.
	Each row has 22 columns:  an ID followed by 21 inputs.
	"""
	header = ['id']
	header += ['makecrystal_' + str(i) for i in range(1,4)]
	header += ['imdgetelastic_' + str(i) for i in range(4,11)]
	header += ['imdgetcommon_' + str(i) for i in range(11,19)]
	header += ['imdanimation_xy_' + '19']
	header += ['imdanimation_xz_' + '20']
	header += ['imdanimation_yz_' + '21']
	data = [['instance_' + str(i)] + [str(i)]*(len(header)-1) for i in range(n_inputs)]
	F = open(creates, 'w')
	F.write('\n'.join([','.join(line) for line in [header] + data]))
	F.close()
    

def protocol(args, id, idroot):	
	
	# Collect arguments
	makecrystal_args = args[1:4]
	imdgetelastic_args = args[4:11]
	imdgetcommon_args = args[11:19]
	imdanimation_xy_args = args[19]
	imdanimation_xz_args = args[20]
	imdanimation_yz_args = args[21]    	
	
	L = []
	
	L += [('MakeDir_' + id, MakeDir, (idroot,), {'creates': idroot})]
	L += [('MakeCrystal_' + id, mc, (makecrystal_args,), {'depends_on': perlroot + 'makecrystal-run.pl', 'creates': (idroot + 'OUT.xyz', idroot + 'BOX.prop') + tuple([root + i + '_crystal.png' for i in ['XY', 'XZ', 'YZ', 'XYZ']])})]
	L += [('IMDGetElastic_' + id, nano, (imdgetelastic_args,), {'depends_on': ('Tr_IN_Elastic', perlroot + 'imdgetelastic-run.pl'), 'creates': idroot + 'Tr_Elastic1.prop'})] # 'Tr_IN_Elastic' in lib folder
	L += [('IMDGetCommon_' + id, common, (imdgetcommon_args,), {'depends_on': (idroot + 'Tr_Elastic1.prop', idroot + 'OUT.xyz', idroot + 'BOX.prop', perlroot + 'imdgetcommon-run.pl'), 'creates': idroot + 'Tr_Elastic.prop'})]
	L += [('IMDRun_' + id, run, (), {'depends_on': (idroot + 'Tr_Elastic.prop', idroot + 'OUT.xyz', perlroot + 'imdrun-run.pl'), 'creates': (idroot + 'Checkpoints.zip', idroot + 'out.xyz')})]
	L += [('IMDAnimationXY_' + id, animation_xy, (imdanimation_xy_args,), {'depends_on': (idroot + 'Checkpoints.zip', perlroot + 'imdanimation-run.pl'), 'creates': idroot + 'MovieXY.gif'})]
	L += [('IMDAnimationXZ_' + id, animation_xz, (imdanimation_xz_args,), {'depends_on': (idroot + 'Checkpoints.zip', perlroot + 'imdanimation-run.pl'), 'creates': idroot + 'MovieXZ.gif'})]
	L += [('IMDAnimationYZ_' + id, animation_yz, (imdanimation_yz_args,), {'depends_on': (idroot + 'Checkpoints.zip', perlroot + 'imdanimation-run.pl'), 'creates': idroot + 'MovieYZ.gif'})]
	
	return L

    
def instantiator(depends_on = root + 'inputs.csv', creates = root + 'protocol_instances.py'):

	# I've assumed the inputs for each pipeline (protocol) instance correspond to one row in the inputs.csv file
    F = open(depends_on, 'r').read().strip().split('\n')
    header = F[0].split(',')
    data = [line.split(',') for line in F[1:]]
    
    OpList = []
    
    for args in data:

		# The data created by each instance will go in a separate directory
		id = args[0]
		idroot = root + id + '/'
	
		# Pipelines
		OpList += protocol(args, id, idroot)

    ApplyOperations2(creates, OpList)