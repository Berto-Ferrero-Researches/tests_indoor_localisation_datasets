import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib.pyplot as plt
import math
import os.path
import autokeras as ak
import pickle
import random
import sys
script_dir = os.path.dirname(os.path.abspath(__file__)) #Referencia al directorio actual, por si ejecutamos el python en otro directorio
root_dir = script_dir+'/../'
sys.path.insert(1, root_dir)
from lib.trainingcommon import load_real_track_data
from lib.trainingcommon import descale_pos_x
from lib.trainingcommon import descale_pos_y
from lib.trainingcommon import posXYList_to_dinamic_grid
from lib.trainingcommon import dinamic_gridList_to_posXY

#Configuración
input_file_name = 'track_straight_01_all_sensors.mbd_window_median'#'track_1_rssi'#'track_straight_01_all_sensors.mbd_window_median'
synthtetic_track = False#True#False
model = 'clasificacion2_rejilla_dinamica'
remove_not_full_rows = True

#Variables globales
track_file = root_dir+'/preprocessed_inputs/'+("synthetic_tracks/" if synthtetic_track is True else "")+input_file_name+'.csv'
output_file = script_dir+'/prediction_output/'+("synthetic_tracks/" if synthtetic_track is True else "")+model+'_'+input_file_name+'.csv'
model_dir = script_dir+'/models/'+model
scaler_file = model_dir+'/files/scaler_autokeras.pkl'
model_file = model_dir+'/files/model_autokeras'
dim_x = 20.660138018121128
dim_y = 17.64103475472807
random_seed = 42
cell_amount_x = 3
cell_amount_y = 3
zoom_level = 2

#Cargamos la semilla de los generadores aleatorios
np.random.seed(random_seed)
random.seed(random_seed)

#Preparamos los datos
input_data, output_data = load_real_track_data(track_file, scaler_file, False, False, True)
output_data = output_data.to_numpy()
output_data_grid = posXYList_to_dinamic_grid(output_data, zoom_level, cell_amount_x, cell_amount_y)


#Cargamos el modelo
model = tf.keras.models.load_model(model_file, custom_objects=ak.CUSTOM_OBJECTS)

#Predecimos
#tf.compat.v1.keras.backend.get_session().run(tf.compat.v1.tables_initializer(name='init_all_tables'))
predictions = model.predict(input_data)
predictions = np.argmax(predictions, axis=-1)
predictions = np.column_stack(predictions)

#Convertimos a posiciones
predictions_positions = dinamic_gridList_to_posXY(predictions, cell_amount_x=cell_amount_x, cell_amount_y=cell_amount_y)


# print("-Predicciones-")
# print("Real:")
# print(output_data)
# print("Estimado:")
# print(predictions)

#Desescalamos
#with open(scaler_output_file, 'rb') as scalerFile:
#  scaler = pickle.load(scalerFile)
#  scalerFile.close()
#predictions = scaler.inverse_transform(predictions)

#Componemos la salida
output_list = []
for index in range(0, len(predictions)):
  listrow = {
    'real_x': output_data[index][0],
    'real_y': output_data[index][1],
    'real_grid_dim_1': output_data_grid[index][0],
    'real_grid_dim_2': output_data_grid[index][1],
    'predicted_x': predictions_positions[index][0],
    'predicted_y': predictions_positions[index][1],
    'predicted_grid_dim_1': predictions[index][0],
    'predicted_grid_dim_2': predictions[index][1],
  }
  output_list.append(listrow)
output_data = pd.DataFrame(output_list)

#Preparamos cálculos
output_data['deviation_x'] = (output_data['predicted_x'] - output_data['real_x']).abs()
output_data['deviation_y'] = (output_data['predicted_y'] - output_data['real_y']).abs()
output_data['eclidean_distance'] = np.sqrt(np.power(output_data['deviation_x'], 2) + np.power(output_data['deviation_y'], 2))


#Imprimimos la desviacion máxima minima y media de X e Y
print("- Desviaciones en predicciones -")
print("Desviación máxima X: "+str(output_data['deviation_x'].max()))
print("Desviación mínima X: "+str(output_data['deviation_x'].min()))
print("Desviación media X: "+str(output_data['deviation_x'].mean()))
print("Desviación X cuartil 25%: "+str(output_data['deviation_x'].quantile(0.25)))
print("Desviación X cuartil 50%: "+str(output_data['deviation_x'].quantile(0.50)))
print("Desviación X cuartil 75%: "+str(output_data['deviation_x'].quantile(0.75)))

print("Desviación máxima Y: "+str(output_data['deviation_y'].max()))
print("Desviación mínima Y: "+str(output_data['deviation_y'].min()))
print("Desviación media Y: "+str(output_data['deviation_y'].mean()))
print("Desviación Y cuartil 25%: "+str(output_data['deviation_y'].quantile(0.25)))
print("Desviación Y cuartil 50%: "+str(output_data['deviation_y'].quantile(0.50)))
print("Desviación Y cuartil 75%: "+str(output_data['deviation_y'].quantile(0.75)))

print("Distancia euclídea máxima: "+str(output_data['eclidean_distance'].max()))
print("Distancia euclídea mínima: "+str(output_data['eclidean_distance'].min()))
print("Distancia euclídea media: "+str(output_data['eclidean_distance'].mean()))
print("Desviación euclídea cuartil 25%: "+str(output_data['eclidean_distance'].quantile(0.25)))
print("Desviación euclídea cuartil 50%: "+str(output_data['eclidean_distance'].quantile(0.50)))
print("Desviación euclídea cuartil 75%: "+str(output_data['eclidean_distance'].quantile(0.75)))


#Hacemos la salida
output_data.to_csv(output_file, index=False)

#Mostramos el grafico
plt.plot([0, 0, dim_x, dim_x, 0], [0, dim_y,  dim_y, 0, 0], 'go-', label='Real', linewidth=1)
plt.plot(output_data['real_x'].values, output_data['real_y'].values, 'ro-', label='Real', linewidth=1)
plt.plot(output_data['predicted_x'].values, output_data['predicted_y'].values, 'mo-', label='Calculada', linewidth=1)
plt.show()