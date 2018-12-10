import numpy as np
from pprint import pprint
import sys

# Auxiliary class for packaging input file options
class InputFile():
    def __init__(self,args=[]):
        try:
            inputfilename        = args.inputfilename
            inputfilestream      = open(inputfilename)
            inputtype            = inputfilestream.readline().strip().split('= ')[1];
            self.projdir         = inputfilestream.readline().strip().split('= ')[1];
            self.datadir         = inputfilestream.readline().strip().split('= ')[1];
            self.loaddir         = inputfilestream.readline().strip().split('= ')[1];
            self.outdir          = inputfilestream.readline().strip().split('= ')[1];
            self.targetspath     = inputfilestream.readline().strip().split('= ')[1];
            self.targetfiletype  = inputfilestream.readline().strip().split('= ')[1];
            if (inputtype == "train"):
                self.readTrainingInputfile(inputfilestream);
            elif (inputtype == "detect"):
                self.readDetectInputfile(inputfilestream);
            inputfilestream.close();
        except:
            print("Using no input file (blank initialization).")
    def printInputs(self):
        attrs = vars(self);
        print('\n');
        print("********************* INPUTS *********************")
        print('\n'.join("%s: %s" % item for item in attrs.items()))
        print("**************************************************")
        print('\n');
    def readTrainingInputfile(self,inputfilestream):
        self.traindir        = inputfilestream.readline().strip().split('= ')[1];
        self.epochs          = int(inputfilestream.readline().strip().split('= ')[1]);
        self.epochstart      = int(inputfilestream.readline().strip().split('= ')[1]);
        self.batchsize       = int(inputfilestream.readline().strip().split('= ')[1]);
        self.networkcfg      = inputfilestream.readline().strip().split('= ')[1];
        self.imgsize         = int(inputfilestream.readline().strip().split('= ')[1]);
        resume               = inputfilestream.readline().strip().split('= ')[1];
        self.resume          = ((resume == "True") | (resume == "true"));
        invalid_class_list   = inputfilestream.readline().strip().split('= ')[1]
        self.invalid_class_list = np.array( invalid_class_list.split(',') , dtype='int' )
    def readDetectInputfile(self,inputfilestream):
        self.imagepath       = inputfilestream.readline().strip().split('= ')[1];
        plotflag             = inputfilestream.readline().strip().split('= ')[1];
        self.plot_flag       = ((plotflag == "True") | (plotflag == "true"));
        secondary_classifier       = inputfilestream.readline().strip().split('= ')[1];
        self.secondary_classifier  = ((secondary_classifier == "True") | (secondary_classifier == "true"));
        self.networkcfg      = inputfilestream.readline().strip().split('= ')[1];
        self.class_path      = inputfilestream.readline().strip().split('= ')[1];
        self.conf_thres      = float(inputfilestream.readline().strip().split('= ')[1]);
        self.nms_thres       = float(inputfilestream.readline().strip().split('= ')[1]);
        self.batch_size      = int(inputfilestream.readline().strip().split('= ')[1]);
        self.img_size        = int(inputfilestream.readline().strip().split('= ')[1]);
