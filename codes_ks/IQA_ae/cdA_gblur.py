import os
import utils
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
plt.switch_backend('agg')

from keras import backend as K
import keras.backend.tensorflow_backend as KTF
KTF.set_session(utils.get_session())

from keras.datasets import cifar10
(x_train, _), (x_test, _) = cifar10.load_data()

################### Processing the data ##################
x_train.shape, x_test.shape

x_train = x_train.astype('float32') / 255.
x_test = x_test.astype('float32') / 255.
x_train = np.reshape(x_train, (len(x_train), 32, 32, 3))  # adapt this if using `channels_first` image data format
x_test = np.reshape(x_test, (len(x_test), 32, 32, 3))  # adapt this if using `channels_first` image data format

# Adding GBLUR
x_train, x_train_noisy = utils.cifar10_gblur(x_train)
x_test, x_test_noisy = utils.cifar10_gblur(x_test)
x_train.shape, x_train_noisy.shape, x_test.shape, x_test_noisy.shape

# Displaying noisy images
n = 10
plt.figure(figsize=(20, 4))
for i in range(1, n):
    # display original
    ax = plt.subplot(2, n, i)
    plt.imshow(x_train[i].reshape(32, 32, 3))
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)

    # display reconstruction
    ax = plt.subplot(2, n, i + n)
    plt.imshow(x_train_noisy[i].reshape(32, 32, 3))
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
plt.show()
plt.savefig('saves/cdA_gblur_noisy_vis.png')

"""Constructing the Model"""
import keras
from keras import losses
from keras.models import Model
from keras.layers import Input, Dense, Conv2D, MaxPooling2D, UpSampling2D, concatenate

L = 5
F = [16, 32, 64, 128, 256] # Number of filters at each layer
# Encoder
inp = Input(shape = (None, None, 3))
enc = Conv2D(F[0], (3, 3), activation='relu', padding='same', strides=(2, 2))(inp)
for convs in range(1, L):
    filters = F[convs]
    enc = Conv2D(filters, (3, 3), activation='relu', padding='same', strides=(2, 2))(enc)
encoder = Model(inputs=[inp], outputs=[enc])
encoder.compile(optimizer='adadelta', loss='mean_squared_error')

# Decoder
h = Input(shape = (None, None, F[L-1]))
dec = UpSampling2D((2, 2))(h)
dec = Conv2D(F[L-1], (3, 3), activation='relu', padding='same')(dec)
for deconvs in range(1, L):
    if deconvs == L-1:
        filters = 3
    else:
        filters = F[::-1][deconvs]
    dec = UpSampling2D((2, 2))(dec)
    dec = Conv2D(filters, (3, 3), activation='relu', padding='same')(dec)
decoder = Model(inputs=[h], outputs=[dec])
decoder.compile(optimizer='adadelta', loss='mean_squared_error')

# Reconstruction of the input
inp = Input(shape=(None, None, 3))
inp_recon = decoder(encoder(inp))

ae = Model(inputs = [inp], outputs = [inp_recon])
ae.compile(optimizer='adadelta', loss='mean_squared_error')

######################### Model Flow Diagram ###########################
from keras.utils import plot_model
plot_model(ae, to_file='my_models/cdA_gblur_model.png', show_shapes=True)

########################## Training the model ##########################
from keras.callbacks import TensorBoard
import sys

ae.fit([x_train_noisy],
       [x_train_noisy],
       epochs=100,
       batch_size=128,
       shuffle=True,
       validation_data=([x_test_noisy], 
                        [x_test_noisy]),
       callbacks=[TensorBoard(log_dir='tmp/ae', histogram_freq=0, 
                              write_graph=True, write_images=True)])

from keras.models import load_model
ae.save('my_models/cdA_gblur.h5')

######################### Testing the model ############################
decoded_imgs = ae.predict([x_test_noisy])

vis_inp = utils.visualize(x_test, [32, 32], [1, 1], [5, 5], color=1)
vis_inp_recon = utils.visualize(decoded_imgs, [32, 32], [1, 1], [5, 5], color=1)

plt.figure(figsize=(15, 15))
plt.subplot(1, 2, 1), plt.imshow(vis_inp)
plt.subplot(1, 2, 2), plt.imshow(vis_inp_recon)
plt.show()
plt.savefig('saves/cdA_gblur_recon_vis.png')
