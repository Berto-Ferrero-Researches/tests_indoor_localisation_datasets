import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib.pyplot as plt
import math
import os.path
import pickle
import random
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import KFold
from scikeras.wrappers import KerasRegressor
from sklearn.model_selection import train_test_split
import keras
import sys
script_dir = os.path.dirname(os.path.abspath(__file__)) #Referencia al directorio actual, por si ejecutamos el python en otro directorio
root_dir = script_dir+'/../../../'                                                                        #Referencia al directorio raiz del proyecto
sys.path.insert(1, root_dir)
from lib.trainingcommon import plot_learning_curves
from lib.trainingcommon import load_training_data
from lib.trainingcommon import descale_pos_x
from lib.trainingcommon import descale_dataframe
from lib.trainingcommon import load_data, save_model, save_history

# Variables globales y configuración
modelname = 'M1-model1_paper'
random_seed = 42
# Keras config
use_gpu = False
loss='mse'
#optimizer='adam'
learning_rate=0.001

windowsettings_suffix = '1_4_100_median'

batch_sizes = [16, 32, 64, 128, 256, 512, 1024]

# -- END Configuración -- #

# Cargamos la semilla de los generadores aleatorios
np.random.seed(random_seed)
random.seed(random_seed)

#Si no usamos GPU forzamos a usar CPU
if not use_gpu:
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"    

# ---- Entrenamiento del modelo ---- #

for batch_size in batch_sizes:

  batch_size_str = str(batch_size)
  print("---- Entrenamiento del modelo ----")
  print("Batch size: "+batch_size_str)

  #Variables globales
  data_file = root_dir+'preprocessed_inputs/paper1/fingerprint_history_window_'+windowsettings_suffix+'.csv'
  scaler_file = script_dir+'/files/batch_size_search/'+modelname+'/scaler_'+windowsettings_suffix+'_bs'+batch_size_str+'.pkl'
  model_file = script_dir+'/files/batch_size_search/'+modelname+'/model_'+windowsettings_suffix+'_bs'+batch_size_str+'.tf'
  history_file = script_dir+'/files/batch_size_search/'+modelname+'/history_'+windowsettings_suffix+'_bs'+batch_size_str
  model_image_file = script_dir+'/files/batch_size_search/'+modelname+'/model_plot.png'
  autokeras_project_name = modelname
  auokeras_folder = root_dir+'/tmp/autokeras_training/'

  # ---- Construcción del modelo ---- #

  #Cargamos los ficheros
  X, y = load_training_data(data_file, scaler_file, include_pos_z=False, scale_y=True, remove_not_full_rows=False)


  #Construimos el modelo
  #Nos basamos en el diseño descrito en el paper "Indoor Localization using RSSI and Artificial Neural Network"
  inputlength = X.shape[1]
  outputlength = y.shape[1]
  hiddenLayerLength = round(inputlength*2/3+outputlength, 0)
  print("Tamaño de la entrada: "+str(inputlength))
  print("Tamaño de la salida: "+str(outputlength))
  print("Tamaño de la capa oculta: "+str(hiddenLayerLength))

  input = tf.keras.layers.Input(shape=inputlength)
  hiddenLayer = tf.keras.layers.Dense(hiddenLayerLength, activation='relu')(input)
  output = tf.keras.layers.Dense(outputlength, activation='linear')(hiddenLayer)
  model = tf.keras.models.Model(inputs=input, outputs=output)

  
  optimizer = keras.optimizers.Adam(learning_rate=learning_rate)
  model.compile(loss=loss, optimizer=optimizer, metrics=[loss, 'accuracy']) 

  #Entrenamos
  X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
  callback = tf.keras.callbacks.EarlyStopping(monitor='val_loss', min_delta=0.0001, patience=10, restore_best_weights=True)
  history = model.fit(X_train, y_train, validation_data=(X_test, y_test),
                      verbose=2, callbacks=[callback], batch_size=batch_size,  epochs=1000)

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
  save_model(model, model_file)
  save_history(history, history_file)

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