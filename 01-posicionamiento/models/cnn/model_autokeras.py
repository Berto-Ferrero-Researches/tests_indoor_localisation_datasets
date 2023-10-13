import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib.pyplot as plt
import math
import os.path
import pickle
import random
import autokeras as ak
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Flatten, Dense, Dropout
from sklearn.model_selection import train_test_split
import sys
script_dir = os.path.dirname(os.path.abspath(__file__)) #Referencia al directorio actual, por si ejecutamos el python en otro directorio
root_dir = script_dir+'/../../../'                                                                        #Referencia al directorio raiz del proyecto
sys.path.insert(1, root_dir)
from lib.trainingcommon import plot_learning_curves
from lib.trainingcommon import load_training_data
from lib.trainingcommon import descale_pos_x
from lib.trainingcommon import descale_dataframe
from lib.trainingcommon import load_data, save_model

#Variables globales
modelname = 'model1'
windowsettings_suffix = '1_4_100_median'
data_file = root_dir+'preprocessed_inputs/paper1/fingerprint_history_window_'+windowsettings_suffix+'.csv'
scaler_file = script_dir+'/files/paper1/'+modelname+'/scaler_'+windowsettings_suffix+'.pkl'
model_file = script_dir+'/files/paper1/'+modelname+'/model_'+windowsettings_suffix+'.tf'
model_image_file = script_dir+'/files/paper1/'+modelname+'/model_plot.png'
random_seed = 42
scale_y = True

#Autokeras config
max_trials = 50
overwrite = True
autokeras_project_name = 'cnn_model_1'
auokeras_folder = root_dir+'/tmp/autokeras_training/'

#Cargamos la semilla de los generadores aleatorios
np.random.seed(random_seed)
random.seed(random_seed)

#Cargamos los ficheros
print("Cargando datos")
X, y = load_data(data_file, scaler_file, train_scaler_file=True, include_pos_z=False, scale_y=scale_y, remove_not_full_rows=False)

#Cambiamos dimensionalidad para que sea compatible con CNN1D
X = X.values.reshape(X.shape[0], X.shape[1], 1)
#X = np.expand_dims(X, axis=2) #Otra forma de hacerlo

#Creamos el modelo
input = ak.Input()
hiddenLayers = ak.ConvBlock(kernel_size=3, separable=False, max_pooling=False, filters=32, num_blocks=1, num_layers=2)(input)
hiddenLayers = ak.ConvBlock(kernel_size=3, separable=False, max_pooling=False, filters=32, num_blocks=1, num_layers=1)(hiddenLayers)
hiddenLayers = ak.ConvBlock(kernel_size=3, separable=False, max_pooling=False, filters=64, num_blocks=1, num_layers=1)(hiddenLayers)
hiddenLayers = ak.ConvBlock(kernel_size=3, separable=False, max_pooling=False, filters=32, num_blocks=1, num_layers=2)(hiddenLayers)
hiddenLayers = ak.DenseBlock(use_batchnorm=False, num_layers=1, num_units=16)(hiddenLayers)
hiddenLayers = ak.DenseBlock(use_batchnorm=False, num_layers=1, num_units=512)(hiddenLayers)
output = ak.RegressionHead(output_dim=y.shape[1], metrics=['mse', 'accuracy'])(hiddenLayers)

model = ak.AutoModel(
  inputs=input,
  outputs=output,
  overwrite=overwrite,
  #objective = 'val_output_d1_accuracy',
  seed=random_seed,
  max_trials=max_trials, project_name=autokeras_project_name, directory=auokeras_folder
)

#Entrenamos
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
callback = tf.keras.callbacks.EarlyStopping(monitor='val_loss', min_delta=0.0001, patience=2, restore_best_weights=True)
history = model.fit(X_train, y_train, validation_data=(X_test, y_test),
                     verbose=2, callbacks=[callback])

# Evaluamos usando el test set
score = model.evaluate(X_test, y_test, verbose=0)

'''
#Intentamos estimar los puntos de test
X_test_sample = X_train#[:5000]
y_test_sample = y_train#[:5000]
prediction = model.predict(X_test_sample)
y_pred = pd.DataFrame(prediction, columns=['pos_x', 'pos_y'])
#Desescalamos
y_test_sample = descale_dataframe(y_test_sample)
y_pred = descale_dataframe(y_pred)

plt.plot(y_test_sample['pos_y'].values, y_test_sample['pos_x'].values, 'go-', label='Real', linewidth=1)
#plt.plot(y_pred['pos_y'].values, y_pred['pos_x'].values, 'ro-', label='Calculada', linewidth=1)
plt.show()
'''

#Guardamos el modelo
model = model.export_model()
save_model(model, model_file)

#Sacamos valoraciones
print("-- Resumen del modelo:")
print(model.summary())

# print("-- Evaluación cruzada")
# print("Puntuaciones de validación cruzada:", cross_val_scores)
# print("Puntuación media:", cross_val_scores.mean())
# print("Desviación estándar:", cross_val_scores.std())

print("-- Entrenamiento final")
print('Test loss: {:0.4f}'.format(score[0]))
print('Val loss: {:0.4f}'.format(score[1]))
print('Val accuracy: {:0.4f}'.format(score[2]))


#Guardamos la imagen resumen
tf.keras.utils.plot_model(model, to_file=model_image_file, show_shapes=True, show_layer_names=False, show_dtype=False, show_layer_activations=False)

#plot_learning_curves(history)
#print(score)
