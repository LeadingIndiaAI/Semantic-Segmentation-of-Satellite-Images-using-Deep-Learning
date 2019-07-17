import PIL
from PIL import Image
import matplotlib.pyplot as plt
from libtiff import TIFF
from libtiff import TIFFfile, TIFFimage
from scipy.misc import imresize
import numpy as np
import math
import glob
import cv2
import os
from pspnet import PSPNet
import skimage.io as io
import skimage.transform as trans
from keras.models import *
from keras.layers import *
from keras.optimizers import *
from keras.callbacks import ModelCheckpoint, LearningRateScheduler
from keras.preprocessing.image import ImageDataGenerator
from keras import backend as keras
#%matplotlib inline

# To read the images in numerical order
import re
numbers = re.compile(r'(\d+)')
def numericalSort(value):
    parts = numbers.split(value)
    parts[1::2] = map(int, parts[1::2])
    return parts

# List of file names of actual Satellite images for traininig 
filelist_trainx = sorted(glob.glob('Inter-IIT-CSRE/The-Eye-in-the-Sky-dataset/sat/*.tif'), key=numericalSort)
# List of file names of classified images for traininig 
filelist_trainy = sorted(glob.glob('Inter-IIT-CSRE/The-Eye-in-the-Sky-dataset/gt/*.tif'), key=numericalSort)

# List of file names of actual Satellite images for testing 
filelist_testx = sorted(glob.glob('Inter-IIT-CSRE/The-Eye-in-the-Sky-test-data/sat_test/*.tif'), key=numericalSort)
                                        


# Not useful, messes up with the 4 dimentions of sat images

# Resizing the image to nearest dimensions multipls of 'stride'

def resize(img, stride, n_h, n_w):
    #h,l,_ = img.shape
    ne_h = (n_h*stride) + stride
    ne_w = (n_w*stride) + stride
    
    img_resized = imresize(img, (ne_h,ne_w))
    return img_resized

# Padding at the bottem and at the left of images to be able to crop them into 128*128 images for training

def padding(img, w, h, c, crop_size, stride, n_h, n_w):
    
    w_extra = w - ((n_w-1)*stride)
    w_toadd = crop_size - w_extra
    
    h_extra = h - ((n_h-1)*stride)
    h_toadd = crop_size - h_extra
    
    img_pad = np.zeros(((h+h_toadd), (w+w_toadd), c))
    #img_pad[:h, :w,:] = img
    #img_pad = img_pad+img
    img_pad = np.pad(img, [(0, h_toadd), (0, w_toadd), (0,0)], mode='constant')
    
    return img_pad
    


# Adding pixels to make the image with shape in multiples of stride

def add_pixals(img, h, w, c, n_h, n_w, crop_size, stride):
        
    w_extra = w - ((n_w-1)*stride)
    w_toadd = crop_size - w_extra

    h_extra = h - ((n_h-1)*stride)
    h_toadd = crop_size - h_extra

    img_add = np.zeros(((h+h_toadd), (w+w_toadd), c))
        
    img_add[:h, :w,:] = img
    img_add[h:, :w,:] = img[:h_toadd,:, :]
    img_add[:h,w:,:] = img[:,:w_toadd,:]
    img_add[h:,w:,:] = img[h-h_toadd:h,w-w_toadd:w,:]
            
    return img_add    



# Adding pixels to make the image with shape in multiples of stride

def add_pixals(img, h, w, c, n_h, n_w, crop_size, stride):
    
    w_extra = w - ((n_w-1)*stride)
    w_toadd = crop_size - w_extra
    
    h_extra = h - ((n_h-1)*stride)
    h_toadd = crop_size - h_extra
    
    img_add = np.zeros(((h+h_toadd), (w+w_toadd), c))
    
    img_add[:h, :w,:] = img
    img_add[h:, :w,:] = img[:h_toadd,:, :]
    img_add[:h,w:,:] = img[:,:w_toadd,:]
    img_add[h:,w:,:] = img[h-h_toadd:h,w-w_toadd:w,:]
    
    return img_add    


# Slicing the image into crop_size*crop_size crops with a stride of crop_size/2 and makking list out of them

def crops(a, crop_size = 128):
    
    #stride = int(crop_size/2)
    stride = 32

    croped_images = []
    h, w, c = a.shape
    
    n_h = int(int(h/stride))
    n_w = int(int(w/stride))
    
    # Padding using the padding function we wrote
    a = add_pixals(a, h, w, c, n_h, n_w, crop_size, stride)
    
    # Resizing as required
    ##a = resize(a, stride, n_h, n_w)
    
    # Adding pixals as required
    #a = add_pixals(a, h, w, c, n_h, n_w, crop_size, stride)
    
    # Slicing the image into 128*128 crops with a stride of 64
    for i in range(n_h-1):
        for j in range(n_w-1):
            crop_x = a[(i*stride):((i*stride)+crop_size), (j*stride):((j*stride)+crop_size), :]
            croped_images.append(crop_x)
    return croped_images


# Another type of cropping

def new_crops(img, crop_size = 512):
    stride = crop_size 
    
    croped_images = []
    h, w, c = img.shape
    
    n_h = math.ceil(h/stride)
    n_w = math.ceil(w/stride)
    
    for i in range(n_h):
        
        if (h - i*crop_size) >= crop_size:
            stride = crop_size
        elif (h - i*crop_size) <= crop_size:
            stride = (crop_size - (w - i*crop_size))
        for j in range(n_w):
            if (w - i*crop_size) >= crop_size:
                stride = crop_size
            elif (w - i*crop_size) <= crop_size:
                stride = (crop_size - (w - i*crop_size))
                
            crop_x = img[(i*stride):((i*stride)+crop_size), (j*stride):((j*stride)+crop_size), :]
            croped_images.append(crop_x)
    return croped_images


# Reading, padding, cropping and making array of all the cropped images of all the trainig sat images
trainx_list = []

for fname in filelist_trainx[:13]:
    
    # Reading the image
    tif = TIFF.open(fname)
    image = tif.read_image()
    
    # Padding as required and cropping
    crops_list = crops(image)
    #print(len(crops_list))
    trainx_list = trainx_list + crops_list
    
# Array of all the cropped Training sat Images    
trainx = np.asarray(trainx_list)


# Reading, padding, cropping and making array of all the cropped images of all the trainig gt images
trainy_list = []

for fname in filelist_trainy[:13]:
    
    # Reading the image
    tif = TIFF.open(fname)
    image = tif.read_image()
    
    # Padding as required and cropping
    crops_list = crops(image)
    
    trainy_list = trainy_list + crops_list
    
# Array of all the cropped Training gt Images    
trainy = np.asarray(trainy_list)


# Reading, padding, cropping and making array of all the cropped images of all the testing sat images
testx_list = []

#for fname in filelist_trainx[13]:
    
    # Reading the image
tif = TIFF.open(filelist_trainx[13])
image = tif.read_image()
    
# Padding as required and cropping
crops_list = crops(image)
    
testx_list = testx_list + crops_list
    
# Array of all the cropped Testing sat Images  
testx = np.asarray(testx_list)


# Reading, padding, cropping and making array of all the cropped images of all the testing sat images
testy_list = []

#for fname in filelist_trainx[13]:
    
# Reading the image
tif = TIFF.open(filelist_trainy[13])
image = tif.read_image()
    
# Padding as required and cropping
crops_list = crops(image)
    
testy_list = testy_list + crops_list
    
# Array of all the cropped Testing sat Images  
testy = np.asarray(testy_list)

# Making array of all the training sat images as it is without any cropping

xtrain_list = []

for fname in filelist_trainx:
    
    # Reading the image
    tif = TIFF.open(fname)
    image = tif.read_image()
    
    crop_size = 128
    
    stride = 64
    
    h, w, c = image.shape
    
    n_h = int(int(h/stride))
    n_w = int(int(w/stride))
    
    
    image = padding(image, w, h, c, crop_size, stride, n_h, n_w)
    
    xtrain_list.append(image)

x_train = np.asarray(xtrain_list)
tif = TIFF.open('Inter-IIT-CSRE/The-Eye-in-the-Sky-dataset/sat/14.tif')
image = tif.read_image()
crop_size = 128
    
stride = 64
h, w, c = image.shape
    
n_h = int(int(h/stride))
n_w = int(int(w/stride))
    
    
image = padding(image, w, h, c, crop_size, stride, n_h, n_w)
x_train = image
# Making array of all the training gt images as it is without any cropping

ytrain_list = []

for fname in filelist_trainy:
    
    # Reading the image
    tif = TIFF.open(fname)
    image = tif.read_image()
    
    crop_size = 128
    
    stride = 64
    
    h, w, c = image.shape
    
    n_h = int(int(h/stride))
    n_w = int(int(w/stride))
    
    
    image = padding(image, w, h, c, crop_size, stride, n_h, n_w)
    
    ytrain_list.append(image)

y_train = np.asarray(ytrain_list)


tif = TIFF.open('Inter-IIT-CSRE/The-Eye-in-the-Sky-dataset/gt/14.tif')
image = tif.read_image()
crop_size = 128
    
stride = 64
    
h, w, c = image.shape
    
n_h = int(int(h/stride))
n_w = int(int(w/stride))
    
    
image = padding(image, w, h, c, crop_size, stride, n_h, n_w)
y_train = image

'''def unet(shape = (None,None,4)):
    
    # Left side of the U-Net
    inputs = Input(shape)
    in_shape = inputs.shape
    print(in_shape)
    conv1 = Conv2D(64, 3, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(inputs)
    conv1 = Conv2D(64, 3, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(conv1)
    conv1 = BatchNormalization()(conv1)
    pool1 = MaxPooling2D(pool_size=(2, 2))(conv1)
    conv2 = Conv2D(128, 3, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(pool1)
    conv2 = Conv2D(128, 3, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(conv2)
    conv2 = BatchNormalization()(conv2)
    pool2 = MaxPooling2D(pool_size=(2, 2))(conv2)
    conv3 = Conv2D(256, 3, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(pool2)
    conv3 = Conv2D(256, 3, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(conv3)
    conv3 = BatchNormalization()(conv3)
    pool3 = MaxPooling2D(pool_size=(2, 2))(conv3)
    conv4 = Conv2D(512, 3, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(pool3)
    conv4 = Conv2D(512, 3, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(conv4)
    conv4 = BatchNormalization()(conv4)
    drop4 = Dropout(0.5)(conv4)
    pool4 = MaxPooling2D(pool_size=(2, 2))(drop4)
    
    # Bottom of the U-Net
    conv5 = Conv2D(1024, 3, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(pool4)
    conv5 = Conv2D(1024, 3, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(conv5)
    conv5 = BatchNormalization()(conv5)
    drop5 = Dropout(0.5)(conv5)
    
    # Upsampling Starts, right side of the U-Net
    up6 = Conv2D(512, 2, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(UpSampling2D(size = (2,2))(drop5))
    merge6 = concatenate([drop4,up6], axis = 3)
    conv6 = Conv2D(512, 3, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(merge6)
    conv6 = Conv2D(512, 3, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(conv6)
    conv6 = BatchNormalization()(conv6)

    up7 = Conv2D(256, 2, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(UpSampling2D(size = (2,2))(conv6))
    merge7 = concatenate([conv3,up7], axis = 3)
    conv7 = Conv2D(256, 3, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(merge7)
    conv7 = Conv2D(256, 3, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(conv7)
    conv7 = BatchNormalization()(conv7)

    up8 = Conv2D(128, 2, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(UpSampling2D(size = (2,2))(conv7))
    merge8 = concatenate([conv2,up8], axis = 3)
    conv8 = Conv2D(128, 3, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(merge8)
    conv8 = Conv2D(128, 3, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(conv8)
    conv8 = BatchNormalization()(conv8)

    up9 = Conv2D(64, 2, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(UpSampling2D(size = (2,2))(conv8))
    merge9 = concatenate([conv1,up9], axis = 3)
    conv9 = Conv2D(64, 3, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(merge9)
    conv9 = Conv2D(64, 3, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(conv9)
    conv9 = Conv2D(16, 3, activation = 'relu', padding = 'same', kernel_initializer = 'random_normal')(conv9)
    conv9 = BatchNormalization()(conv9)

    # Output layer of the U-Net with a softmax activation
    conv10 = Conv2D(3, 1, activation = 'softmax')(conv9)

    model = Model(input = inputs, output = conv10)

    model.compile(optimizer = Adam(lr = 0.000009), loss = 'categorical_crossentropy', metrics = ['accuracy'])
    
    model.summary()
    
    filelist_modelweights = sorted(glob.glob('*.h5'), key=numericalSort)
    
    if 'model_nocropping.h5' in filelist_modelweights:
        model.load_weights('model_nocropping.h5')
    return model
'''

model = PSPNet()


# Data Augmentation

datagen_args = dict(rotation_range=0.2,
                    width_shift_range=0.05,
                    height_shift_range=0.05,
                    shear_range=0.05,
                    zoom_range=0.05,
                    horizontal_flip=True,
                    fill_mode='nearest')


#x_datagen = ImageDataGenerator(**datagen_args)
#y_datagen = ImageDataGenerator(**datagen_args)

#seed = 1

#x_datagen.fit(trainx, augment=True, seed = seed)
#y_datagen.fit(trainy, augment=True, seed = seed)

#x_generator = x_datagen.flow(trainx, seed=seed)

#y_generator = y_datagen.flow(trainy, seed=seed)

#train_generator = zip(x_generator, y_generator)



#model.fit_generator(train_generator, epochs = 10, steps_per_epoch=117)
#model.save("model_augment.h5")

trainx = trainx/np.max(trainx)
trainy = trainy/np.max(trainy)

testx = testx/np.max(testx)
testy = testy/np.max(testy)

hist = model.fit(trainx, trainy, epochs=5, validation_data = (testx, testy),batch_size=64, verbose=1)
model.save("model_psp.h5")


#epochs = 20
#for e in range(epochs):
#        print("epoch %d" % e)
#        #for X_train, Y_train in zip(x_train, y_train): # these are chunks of ~10k pictures
#        h,w,c = x_train.shape
#        X_train = np.reshape(x_train,(1,h,w,c))
#        h,w,c = y_train.shape
#        Y_train = np.reshape(y_train,(1,h,w,c))
#        model.fit(X_train, Y_train, batch_size=1, nb_epoch=1)
	
#        model.save("model_nocropping.h5")        
#print(X_train.shape, Y_train.shape)


#model.save("model_nocropping.h5")

#epochs = 10
#for e in range(epochs):
#	print("epoch %d" % e)
#	for X_train, Y_train in zip(x_train, y_train): # these are chunks of ~10k pictures
#		h,w,c = X_train.shape
#		X_train = np.reshape(X_train,(1,h,w,c))
#		h,w,c = Y_train.shape
#		Y_train = np.reshape(Y_train,(1,h,w,c))
#		model.fit(X_train, Y_train, batch_size=1, nb_epoch=1)
        #print(X_train.shape, Y_train.shape)


#model.save("model_nocropping.h5")

#accuracy = model.evaluate(x=x_test,y=y_test,batch_size=16)
#print("Accuracy: ",accuracy[1])

