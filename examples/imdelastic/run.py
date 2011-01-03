#/usr/bin/env python
import os,sys,shutil
import signal

class Command(object):
    def __init__(self):
        self.config = {}
        self.config['dir'] = os.path.dirname(sys.argv[0])
        if self.config['dir'] == '':
            self.config['dir'] = '.'
        pass
    def perform(self):
        """Stub code for performing the command.
        Must be overridden in the subclass"""
        pass

class MakeCrystal(Command):
    def __init__(self, args):
        #USER:
        #x   	#Dimension_x (even integer > 0)
        #y  	#Dimension_y (even integer > 0)
        #z  	#Dimension_z (even integer > 0)
        #crack_length  	#Crack length ratio (aa/length_x)
        #crack_slope  	#Crack slope m
        #vacuum_space  	#Vacuum space (to the right and left)
        #x_strain  	#Strain in x direction (e.g. 1.10 for 10%))

        #DEFAULTS:
        #mode    crack
        #out_file    OUT.xyz #created
        #box_file    BOX.prop #created
        #col_x   4
        #col_y   5
        #png_file    Crystal.png #created

        super(MakeCrystal,self).__init__()

        self.config['x'] = args[0]  	#Dimension_x (even integer > 0)
        self.config['y'] = args[1] 	#Dimension_y (even integer > 0)
        self.config['z'] = args[2] 	#Dimension_z (even integer > 0)
        self.config['crack_length'] = 0  	#Crack length ratio (aa/length_x)
        self.config['crack_slope'] = 0  	#Crack slope m
        self.config['vacuum_space'] = 0  	#Vacuum space (to the right and left)
        self.config['x_strain'] = 1 	#Strain in x direction (e.g. 1.10 for 10%))
        self.config['mode'] = 'elastic'
        self.config['out_file'] = 'OUT.xyz' #created
        self.config['box_file'] = 'BOX.prop' #created
        self.config['col_x'] = 4
        self.config['col_y'] = 5
        self.config['png_file'] = 'crystal.png' #created

    def perform(self):
        os.system('perl %(dir)s/makecrystal-run.pl %(mode)s %(out_file)s %(box_file)s %(x)s %(y)s %(z)s %(crack_length)s %(crack_slope)s %(vacuum_space)s %(x_strain)s %(col_x)d %(col_y)d %(png_file)s' % self.config)
        #print 'perl %(dir)s/makecrystal-run.pl %(mode)s %(out_file)s %(box_file)s %(x)s %(y)s %(z)s %(crack_length)s %(crack_slope)s %(vacuum_space)s %(x_strain)s %(col_x)d %(col_y)d %(png_file)s' % self.config

class IMDGetElastic(Command):
    def __init__(self, args):

        #USER 
        #r_cut #Cutoff of potential 
        #lj_epsilon  #Lennard-Jones epsilon parameter 
        #lj_sigma  #Lennard-Jones sigma parameter 
        #lindef_inter     #Nr of steps after which is linear deformation matrix applied 
        #lindef_xx     #Strain increments X 
        #lindef_yy     #Strain increments Y 
        #lindef_zz     #Strain increments Z 


        super(IMDGetElastic,self).__init__()

        self.config['r_cut'] = args[0] 	
        self.config['lj_epsilon'] = args[1] 	
        self.config['lj_sigma'] = args[2] 	
        self.config['lindef_inter'] = args[3] 	
        self.config['lindef_xx'] = args[4]	
        self.config['lindef_yy'] = args[5] 	
        self.config['lindef_zz'] = args[6] 	

        #DEFAULTS:
        self.config['input_filename']  =  'Tr_IN_Elastic'  #(in lib folder)
        self.config['output_file'] = 'Tr_Elastic1.prop' #created

    def perform(self):
        os.system('perl %(dir)s/imdgetelastic-run.pl %(dir)s/%(input_filename)s %(r_cut)s %(lj_epsilon)s %(lj_sigma)s %(lindef_inter)s %(lindef_xx)s %(lindef_yy)s %(lindef_zz)s %(output_file)s' % self.config)
        #print 'perl %(dir)s/imdgetelastic-run.pl %(dir)s/%(input_filename)s %(r_cut)s %(lj_epsilon)s %(lj_sigma)s %(lindef_inter)s %(lindef_xx)s %(lindef_yy)s %(lindef_zz)s %(output_file)s' % self.config

class IMDGetCommon(Command):
    def __init__(self, args):
        #USER:
            #maxsteps  	#maximum # of steps
            #timestep 	#timestep (in 1.018E-014 sec)
            #pbc_x 	#periodic BCs in X
            #pbc_y 	#periodic BCs in Y
            #pbc_z 	#periodic BCs in Z
            #eng_int 	#How often is energy & stress information written
            #checkpt_int 	#How often is chkpt information written
            #startingtemp 	#Starting temperature
        #DEFAULTS:
            #input_filename  Tr_Elastic1.prop #created from IMDGetElastic
            #coord_filename  OUT.xyz #created from MakeCrystal
            #box_filename    BOX.prop #created from MakeCrystal    

        super(IMDGetCommon,self).__init__()

        self.config['maxsteps'] = args[0]  	#maximum # of steps
        self.config['timestep'] = args[1] 	#timestep (in 1.018E-014 sec)
        self.config['pbc_x'] = args[2] 	#periodic BCs in X
        self.config['pbc_y'] = args[3] 	#periodic BCs in Y
        self.config['pbc_z'] = args[4] 	#periodic BCs in Z
        self.config['eng_int'] = args[5]	#How often is energy & stress information written
        self.config['checkpt_int'] 	= args[6] #How often is chkpt information written
        self.config['startingtemp'] = args[7] 	#Starting temperature
        self.config['input_filename'] = 'Tr_Elastic1.prop' #created from IMDGetElastic
        self.config['coord_filename'] = 'OUT.xyz'  #created from MakeCrystal
        self.config['box_filename'] = 'BOX.prop'  #created from MakeCrystal    
        self.config['output_file'] = 'Tr_Elastic.prop'  #created

    def perform(self):
        os.system('perl %(dir)s/imdgetcommon-run.pl %(input_filename)s %(coord_filename)s %(maxsteps)s %(timestep)s %(pbc_x)s %(pbc_y)s %(pbc_z)s %(box_filename)s %(eng_int)s %(checkpt_int)s %(startingtemp)s %(output_file)s' % self.config)
        #print 'perl %(dir)s/imdgetcommon-run.pl %(input_filename)s %(coord_filename)s %(maxsteps)s %(timestep)s %(pbc_x)s %(pbc_y)s %(pbc_z)s %(box_filename)s %(eng_int)s %(checkpt_int)s %(startingtemp)s %(output_file)s' % self.config

class IMDRun(Command): 
    def __init__(self):
        #parameters_filename     Tr_OUT.prop #created from IMDGetCommon
        #xyz_filename    OUT.xyz #created from MakeCrystal

        super(IMDRun,self).__init__()
        
        self.config['parameters_filename'] = 'Tr_Elastic.prop' #created from IMDGetCommon
        self.config['xyz_filename'] = 'OUT.xyz' #created from MakeCrystal
        self.config['output_zip'] = 'Checkpoints.zip' #created
        self.config['xyzout_file'] = 'out.xyz' #created
        self.config['mode'] = 'elastic'
    
    def perform(self):
        os.system('perl %(dir)s/imdrun-run.pl %(mode)s %(parameters_filename)s %(xyz_filename)s %(output_zip)s %(xyzout_file)s' % self.config)
        #print 'perl %(dir)s/imdrun-run.pl %(mode)s %(parameters_filename)s %(xyz_filename)s %(output_zip)s %(xyzout_file)s' % self.config

class IMDAnimationXY(Command):
    def __init__(self, args):
        super(IMDAnimationXY,self).__init__()

        self.config['inputfilename']= 'Checkpoints.zip'
        self.config['outputfile'] = 'MovieXY.gif'
        self.config['energyCutoff'] = args
        self.config['delay'] = 10
        self.config['colX'] = 4
        self.config['colY'] = 5
        self.config['colDX'] = 7
        self.config['colDY'] = 8
        self.config['energyCol'] = 10

    def perform(self):
        os.system('perl %(dir)s/imdanimation-run.pl %(inputfilename)s %(outputfile)s %(delay)s %(colX)s %(colY)s %(colDX)s %(colDY)s %(energyCol)s %(energyCutoff)s' % self.config)
        #print 'perl %(dir)s/imdanimation-run.pl %(inputfilename)s %(outputfile)s %(delay)s %(colX)s %(colY)s %(colDX)s %(colDY)s %(energyCol)s %(energyCutoff)s' % self.config

class IMDAnimationXZ(Command): 
    def __init__(self, args):
        super(IMDAnimationXZ,self).__init__()

        self.config['inputfilename']= 'Checkpoints.zip'
        self.config['outputfile'] = 'MovieXZ.gif'
        self.config['energyCutoff'] = args
        self.config['delay'] = 10
        self.config['colX'] = 4
        self.config['colY'] = 6
        self.config['colDX'] = 7
        self.config['colDY'] = 9
        self.config['energyCol'] = 10

    def perform(self):
        os.system('perl %(dir)s/imdanimation-run.pl %(inputfilename)s %(outputfile)s %(delay)s %(colX)s %(colY)s %(colDX)s %(colDY)s %(energyCol)s %(energyCutoff)s' % self.config)
        #print 'perl %(dir)s/imdanimation-run.pl %(inputfilename)s %(outputfile)s %(delay)s %(colX)s %(colY)s %(colDX)s %(colDY)s %(energyCol)s %(energyCutoff)s' % self.config

class IMDAnimationYZ(Command):  
    def __init__(self, args):
        super(IMDAnimationYZ,self).__init__()

        self.config['inputfilename']= 'Checkpoints.zip'
        self.config['outputfile'] = 'MovieYZ.gif'
        self.config['energyCutoff'] = args
        self.config['delay'] = 10
        self.config['colX'] = 5
        self.config['colY'] = 6
        self.config['colDX'] = 8
        self.config['colDY'] = 9
        self.config['energyCol'] = 10

    def perform(self):
        os.system('perl %(dir)s/imdanimation-run.pl %(inputfilename)s %(outputfile)s %(delay)s %(colX)s %(colY)s %(colDX)s %(colDY)s %(energyCol)s %(energyCutoff)s' % self.config)
        #print 'perl %(dir)s/imdanimation-run.pl %(inputfilename)s %(outputfile)s %(delay)s %(colX)s %(colY)s %(colDX)s %(colDY)s %(energyCol)s %(energyCutoff)s' % self.config


def cleanup():
    os.remove('cmd.sh')
    os.remove('mycwd')
    os.remove('BOX.prop')
    os.remove('Tr_Elastic1.prop')
    shutil.move('Tr_Elastic.prop','ELASTIC-INPUTFILE.txt')

def test():
    os.system('echo "caught signal" > signalCAUGHT')

if __name__ == "__main__":
    # Collect arguments
    #signal.signal(signal.SIGTRAP,test)
    makecrystal_args = sys.argv[1:4]
    imdgetelastic_args = sys.argv[4:11]
    imdgetcommon_args = sys.argv[11:19]
    imdanimation_xy_args = sys.argv[19]
    imdanimation_xz_args = sys.argv[20]
    imdanimation_yz_args = sys.argv[21]

    # Pipelines
    mc = MakeCrystal(makecrystal_args)
    mc.perform()

    nano = IMDGetElastic(imdgetelastic_args)
    nano.perform()

    common = IMDGetCommon(imdgetcommon_args)
    common.perform()

    run = IMDRun()
    run.perform()

    animation_xy = IMDAnimationXY(imdanimation_xy_args)
    animation_xy.perform()

    animation_xz = IMDAnimationXZ(imdanimation_xz_args)
    animation_xz.perform()

    animation_yz = IMDAnimationYZ(imdanimation_yz_args)
    animation_yz.perform()

    cleanup()
