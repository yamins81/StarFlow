# -*- coding: iso-8859-1 -*-
from starflow.Utils import activate, MakeDir
from starflow.Protocols import ApplyOperations2

from examples.convolution.hinton import hinton

root = '../Data/convolution/'

@activate(lambda x: [], lambda x: x[2])
def create_image(width, height, out):
    import numpy
    w = numpy.random.randn(width,height)
    hinton(w, out)

@activate(lambda x: x[0], lambda x: x[3])
def convolve_image(input, kernel_width, kernel_height, out):
    f = open(out,'w')
    f.write('convolve')
    f.close()

@activate(lambda x: x[0], lambda x: x[3])
def crop_image(input, width, height, output):
    f = open(output,'w')
    f.write('crop')
    f.close()
    
def instantiator(creates='../Protocol_Instances/convolution/protocol_instances.py'):
    L = []
    for id in range(0,10):
        # The data created by each instance will go in a separate directory
        id = str(id)
        idroot = root + id + '/'
        width, height, kwidth, kheight, cwidth, cheight = 5, 5, 5, 5, 5, 5

        L += [('MakeDir_' + id, MakeDir, (idroot,))]
        L += [(
            'CreateImage_' + id, 
            create_image, 
            (width, height, idroot + 'original_image.png'),
        )]
        L += [(
            'ConvolveImage_' +id,
            convolve_image,
            (idroot + 'original_image.png', kwidth, kheight, idroot + 'convolved_image.png'),
            )]
        L += [(
            'CropImage_' + id,
            crop_image,
            (idroot + 'convolved_image.png', cwidth, cheight, idroot + 'cropped_image.png'),
        )]

    ApplyOperations2(creates, L)
