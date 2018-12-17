import unittest
import numpy as np
import torch
import sys,os
import matplotlib.pyplot as plt
import cv2
import json
sys.path.append('../')
from utils.datasets import *
from src.InputFile import *
from utils.utils import plot_rgb_image
from utils.datasetProcessing import *
from src.targets.Target import *
from src.targets.fcn_sigma_rejection import *
from src.targets.per_class_stats import *
import warnings

class GPUtests(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore",category=ResourceWarning)
        warnings.filterwarnings("ignore",category=DeprecationWarning)
        
    def test_cuda_available(self):
        print("test if cuda is available")
        cudaavail = torch.cuda.is_available()
        print("cuda available: " + str(cudaavail))
        self.assertTrue(cudaavail);
    def test_cuda_version(self):
        print("test if cuda version is > 9")
        cudarelease = torch.version.cuda
        print("cuda version: " + str(cudarelease))
        self.assertTrue(int(cudarelease[0]) >= 9);
    def test_gpu_avail(self):
        print("test if GPUs are available")
        numGPU = torch.cuda.device_count()
        print("gpus available: " + str(numGPU));
        for i in range(numGPU):
            namegpu = torch.cuda.get_device_name(i)
            print("gpu " + str(i+1) + ": " + namegpu);
        self.assertTrue(numGPU >= 1);


        
class DataProcessingTests(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore",category=ResourceWarning)
        warnings.filterwarnings("ignore",category=DeprecationWarning)
        args                    = lambda:0
        args.inputfilename      = './input_test.dat'
        self.inputs             = InputFile(args)
        self.ndata              = 9
        self.nobject            = 11158

    def test_get_labels_geojson(self):
        print('test loading of geojson formatted data')
        coords,chips,classes    = get_labels_geojson(self.inputs.datadir + 'xview/labels/jsontest.json')
        self.assertTrue(coords.shape == (self.nobject, 4))
        self.assertTrue(chips.size   == self.nobject)
        self.assertTrue(classes.size == self.nobject)

    def test_get_dataset_filenames(self):
        print('test loading dataset filenames')
        files  = get_dataset_filenames(self.inputs.traindir,'.tif')
        self.assertTrue(len(files) == self.ndata)

    def test_get_dataset_height_width_channels(self):
        print('test loading sizes of dataset images')
        extension  = '.tif'
        files, HWC = get_dataset_height_width_channels(self.inputs.traindir,extension)
        self.assertTrue(HWC.shape == (self.ndata,3))
        self.assertTrue(files[0]  == ('train_images_2316' + extension))
        self.assertTrue(np.all(HWC[0] == np.array([3197, 3475, 3])))

    def test_strip_image_number_from_filename(self):
        print('test strip image number from image filename')
        imgname  = 'train_images_2316.tif'
        imgname2 = '2316.tif'
        num      = strip_image_number_from_filename(imgname,'_')
        num2     = strip_image_number_from_filename(imgname2,'_')
        self.assertTrue(num  == 2316)
        self.assertTrue(num2 == 2316)
        

        
class DatasetTests(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore",category=ResourceWarning)
        warnings.filterwarnings("ignore",category=DeprecationWarning)
        args                    = lambda:0
        args.inputfilename      = './input_test.dat'
        self.inputs             = InputFile(args);
        self.filetypes          = ['matlab', 'pickle']
        self.filetypeAppend     = ['.mat', '.pkl']
        self.basetargetpath     = self.inputs.targetspath[0:-4];
        self.nclass             = 60
        self.nobjects           = 11057
        self.ndata              = 9
        self.expectedTargetKeys = {'__header__', '__version__', '__globals__', 'class_cov', 'class_mu', 'class_sigma', 'id', 'image_numbers', 'image_weights', 'targets', 'wh'}
    
    def test_load_targets(self):
        print('test training data loading functionality')        
        for i in range(len(self.filetypes)):
            self.inputs.targetfiletype = self.filetypes[i]
            self.inputs.targetspath    = self.basetargetpath + self.filetypeAppend[i];
            sys.stdout = open(os.devnull, 'w')
            dataloader                 = ListDataset(self.inputs)
            sys.stdout = sys.__stdout__
            self.assertTrue(dataloader.mat.keys() == self.expectedTargetKeys)
            self.assertTrue(dataloader.mat['class_cov'].shape   == (self.nclass,4,4))
            self.assertTrue(dataloader.mat['class_mu'].shape    == (self.nclass,4))
            self.assertTrue(dataloader.mat['class_sigma'].shape == (self.nclass,4))
            self.assertTrue(dataloader.mat['id'].size              == self.nobjects)
            self.assertTrue(dataloader.mat['image_numbers'].shape  == (self.ndata,1))
            self.assertTrue(dataloader.mat['image_weights'].shape  == (self.ndata,1))
            self.assertTrue(dataloader.mat['targets'].shape        == (self.nobjects,5))
            self.assertTrue(dataloader.mat['wh'].shape             == (self.nobjects,2))
            
    def test_show_targets(self):
        print('test training data labeling')
        self.inputs.targetfiletype = self.filetypes[0]
        self.inputs.targetspath    = self.basetargetpath + self.filetypeAppend[0];
        sys.stdout = open(os.devnull, 'w')
        dataloader                 = ListDataset(self.inputs)
        sys.stdout = sys.__stdout__
        for i, (imgs, targets) in enumerate(dataloader):
            try:
                obj     = targets[0][:,1:].numpy()
                obj    *= self.inputs.imgsize
            except:
                obj     = []
            img     = np.transpose(imgs[0].numpy(),(1,2,0))
            plot_rgb_image(img,dataloader.rgb_mean.squeeze(),dataloader.rgb_std.squeeze(),obj)



class TargetTests(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore",category=ResourceWarning)
        warnings.filterwarnings("ignore",category=DeprecationWarning)
        args                    = lambda:0
        args.inputfilename      = './input_test.dat'
        self.inputs             = InputFile(args);
        self.inputs.targetfile  = '/'.join(self.inputs.targetspath.split('/')[0:-1]) + '/jsontest.json'
        self.inputs.targetfiletype = 'json'
        self.nclass             = 41
        self.nobjects           = 11158
        self.ndata              = 9
        self.targetdata         = Target(self.inputs);
        
    def test_load_target_file(self):
        print('test target loading functionality (.json file)')
        self.assertTrue( vars(self.targetdata)['_Target__chips'].size   == self.nobjects )
        self.assertTrue( vars(self.targetdata)['_Target__coords'].shape == (self.nobjects,4) )
        self.assertTrue( vars(self.targetdata)['_Target__classes'].size == self.nobjects )
        self.assertTrue( len(vars(self.targetdata)['_Target__files'])   == self.ndata )
        self.assertTrue( len(vars(self.targetdata)['_Target__class_labels'])   == self.nclass )

    def test_xy_coords(self):
        print('test target coordinate parsing function')
        coords          = np.zeros([5,4]);
        coords[:,0] = 1; coords[:,1] = 2; coords[:,2] = 3; coords[:,3] = 4;
        x1,y1,x2,y2     = parse_xy_coords(coords)
        self.assertTrue(np.all(x1 == 1))
        self.assertTrue(np.all(y1 == 2))
        self.assertTrue(np.all(x2 == 3))
        self.assertTrue(np.all(y2 == 4))

    def test_compute_width_height_area(self):
        print('test target coordinate area function')
        coords          = np.zeros([5,4]);
        coords[:,0] = 1; coords[:,1] = 2; coords[:,2] = 3; coords[:,3] = 4;
        x1,y1,x2,y2     = parse_xy_coords(coords)
        w,h,area        = compute_width_height_area(x1,y1,x2,y2)
        self.assertTrue(np.all(w == coords[:,2] - coords[:,0]))
        self.assertTrue(np.all(h == coords[:,3] - coords[:,1]))
        self.assertTrue(np.all(area == w*h))

    def test_compute_cropped_data(self):
        print('test target cropping method')
        self.targetdata.compute_cropped_data()
        w = vars(self.targetdata)['_Target__filtered_w']
        h = vars(self.targetdata)['_Target__filtered_h']
        self.assertTrue( np.min(w) == 0 )
        self.assertTrue( np.max(w) == 738 )
        self.assertTrue( np.min(h) == 0 )
        self.assertTrue( np.max(h) == 1028 )
        
    def test_fcn_sigma_rejection(self):
        print('test fcn_sigma_rejection function')
        arr         = np.array([[1,2,3],[4,5000,6],[7,8,9],[1000,11,12],[13,14,15]])
        arr2        = arr.ravel()
        x,inliers   = fcn_sigma_rejection(arr,3,3)  # 2D array test
        x2,inliers2 = fcn_sigma_rejection(arr2,3,3) # 1D vector test
        x_expected  = arr.ravel()
        x_expected  = np.delete(x_expected,[4,9])
        inliers_expected = np.ones_like(arr)
        inliers_expected[3,0] = 0
        inliers_expected[1,1] = 0
        self.assertTrue(np.all(x == x_expected))
        self.assertTrue(np.all(inliers == inliers_expected))
        self.assertTrue(np.all(x2 == x_expected))
        self.assertTrue(np.all(inliers2 == inliers_expected.ravel()))

    def test_sigma_rejection_indices(self):
        print('test sigma rejection method')
        self.targetdata.compute_cropped_data()
        i1       = self.targetdata.sigma_rejection_indices(vars(self.targetdata)['_Target__filtered_area']);
        i2       = self.targetdata.sigma_rejection_indices(vars(self.targetdata)['_Target__filtered_w']);
        i3       = self.targetdata.sigma_rejection_indices(vars(self.targetdata)['_Target__filtered_h']);
        self.assertTrue( (i1.size == self.nobjects) & (i2.size == self.nobjects) & (i3.size == self.nobjects) )

    def test_manual_dimension_requirements(self):
        print('test manual dimension requirements method')
        self.targetdata.compute_cropped_data()
        area_lim = 20; w_lim = 4; h_lim = 4; AR_lim = 15;
        idx = self.targetdata.manual_dimension_requirements(area_lim,w_lim,h_lim,AR_lim)
        test = np.all(  (vars(self.targetdata)['_Target__filtered_area'][idx] >= area_lim) & \
                        (vars(self.targetdata)['_Target__w'][idx]        > w_lim) & \
                        (vars(self.targetdata)['_Target__h'][idx]        > h_lim) & \
                        (vars(self.targetdata)['_Target__filtered_AR'][idx]   < AR_lim) )
        self.assertTrue(test)

    def test_edge_requirements(self):
        print('test edge requirements method')
        self.targetdata.compute_cropped_data()
        w_lim = 10; h_lim = 10; x2_lim = 10; y2_lim = 10;
        idx = self.targetdata.edge_requirements(w_lim,h_lim,x2_lim,y2_lim)
        test = np.all(  (vars(self.targetdata)['_Target__x1'][idx] < vars(self.targetdata)['_Target__image_w'][idx]-w_lim) & \
                        (vars(self.targetdata)['_Target__y1'][idx] <  vars(self.targetdata)['_Target__image_h'][idx]-h_lim) & \
                        (vars(self.targetdata)['_Target__x2'][idx] > x2_lim) & \
                        (vars(self.targetdata)['_Target__y2'][idx] > y2_lim) )
        self.assertTrue(test)

    def test_area_requirements(self):
        print('test area requirements method')
        area       = np.array([0.2,1.3,2.4])
        new_area   = area * np.array([0.9, 11.0,0.2])
        area_ratio = np.array([1,10,0.1]);
        idx        = area_requirement(new_area,area,area_ratio)
        self.assertTrue( np.all( idx == [False, True, True] ) )

    def test_nan_inf_size_requirements(self):
        print('test nan/inf/size requirements method')
        image_h = np.array([1 ,2,30,4 ,0,0,90]).astype(float); image_h[4] = np.nan; image_h[5] = np.inf;
        image_w = np.array([50,0,70,80,9,0,100]).astype(float); image_w[1] = np.inf;
        size    = 10
        idx     = nan_inf_size_requirements(image_h,image_w,size)
        self.assertTrue(np.all( idx == [False,False,True,False,False,False,True] ) )

    def test_invalid_class_requirement(self):
        print('test invalid class requirement method')
        input1 = self.inputs.invalid_class_list
        input2 = vars(self.targetdata)['_Target__classes']
        input3 = vars(self.targetdata)['_Target__coords']
        idx    = invalid_class_requirement(input1,input2)
        test   = (input2[idx] == input1[:,None])
        invalidID = np.where(idx == 0)[0]
        self.assertTrue( np.all(input2[invalidID] == input1[0]) | np.all(input2[invalidID] == input1[1]) )

    def test_apply_mask_to_filtered_data(self):
        print('test mask application to filtered data method')
        self.targetdata.compute_filtered_data_mask()
        mask = vars(self.targetdata)['_Target__mask'] 
        self.assertTrue( np.where(mask == 1)[0].size == 11047 )

    def test_per_class_stats(self):
        print('test per_class_stats function')
        classes = np.array([ 3,5,2,5,3,5,7,7,4,3,2,4,5,6,7,8,0,1,4,2,2,4,6,7,8,0,0,8,6,4,3,1,4,6,9,6,9,0] ).astype(int)
        w       = np.array([ 5,2,6,9,7,5,3,2,1,2,4,7,9,7,1,8,6,4,2,3,3,5,7,8,7,7,8,7,5,3,2,3,4,5,8,3,8,9] ).astype(float)
        h       = np.array([ 1,7,2,6,4,9,7,6,4,2,5,6,4,2,5,7,8,1,9,3,6,3,3,2,1,6,8,5,3,5,7,3,2,2,2,6,5,1] ).astype(float)
        class_mu,class_sigma,class_cov = per_class_stats(classes,w,h)
        self.assertTrue( np.all(class_mu.shape  == (10,4)) & \
                         np.all(class_sigma.shape == (10,4)) & \
                         np.all(class_cov.shape == (10,4,4)) )
        self.assertTrue( np.linalg.norm(class_mu[0] - np.array([2.0036,1.4877,3.4912,0.51592])) < 0.001 )
        self.assertTrue( np.linalg.norm(class_sigma[0] - np.array([0.1512,0.86689,0.76245,0.98357])) < 0.001 )
        self.assertTrue( np.linalg.norm(class_cov[0][0] - np.array([0.030482,-0.12869,-0.098209,0.15917])) < 0.001)

    def test_compute_image_weights_with_filtered_data(self):
        print('test class weight computation method')
        self.targetdata.compute_cropped_data()
        self.targetdata.compute_filtered_data_mask()
        self.targetdata.apply_mask_to_filtered_data()
        self.targetdata.compute_image_weights_with_filtered_data()
        class_freq    = vars(self.targetdata)['_Target__filtered_class_freq']
        class_weights = vars(self.targetdata)['_Target__filtered_class_weights']
        self.assertTrue( np.all(class_freq[0:5] == np.array([10,25,10,9,2900])) )

    def test_compute_bounding_box_clusters_using_kmeans(self):
        print('test bounding box cluster computation method')
        self.targetdata.process_target_data()
        clusters_wh       = vars(self.targetdata)['_Target__clusters_wh']
        clusters_expected = np.array([[13.098,9.7326],[11.681,17.44],[21.13,15.55]])
        plt.plot(clusters_wh[:,0], clusters_wh[:,1], 'bo')
        plt.show()
        self.assertTrue( np.linalg.norm(clusters_wh[0:3] - clusters_expected) < 0.001)
        
    
        
if __name__ == '__main__':
    unittest.main();