import numpy as np
import pandas as pd
import glob
import re
import os.path
import math

#Variables globales
script_dir = os.path.dirname(os.path.abspath(__file__))                                                                  #Referencia al directorio actual, por si ejecutamos el python en otro directorio
fingerprint_track_folder = script_dir+'/dataset/trk/'                                                                    #Ruta donde se encuentran los históricos originales
fingerprint_track_file = 'straight_01_all_sensors.mbd'                                                                   #Fichero a extraer
fingerprint_track_output = script_dir+'/dataset_processed_csv/track_'+fingerprint_track_file+'_window.csv'                   #Salida del csv de entrenamiento
time_grouping_timestamp_difference = 0.02                                                                                #Al comprobar la diferencia de tiempos, en cuanto haya una diferencia de mas de este valor se cerrará el grupo anterior
sensors_mac = []                                                                                                         #Extraido de los ficheros
#cabeceras de los archivos de los sensores
sensors_header = ['timestamp', 'mac_sensor', 'mac_beacon', 'rssi', 'pos_x', 'pos_y', 'pos_z', 'aruco_pos_1', 'aruco_pos_2', 'aruco_pos_3', 'aruco_pos_4', 'aruco_pos_5', 'aruco_pos_6', 'aruco_pos_7', 'aruco_pos_8', 'aruco_pos_9'] 
#tipo de datos en los archivos de los sensores
sensors_dtype = {'timestamp': np.float64, 'mac_sensor': str, 'mac_beacon': str, 'rssi': np.int32, 'pos_x': np.float64, 'pos_y': np.float64, 'pos_z': np.float64, 'pos_z': np.float64, 'aruco_pos_1': np.float64, 'aruco_pos_2': np.float64, 'aruco_pos_3': np.float64, 'aruco_pos_4': np.float64, 'aruco_pos_5': np.float64, 'aruco_pos_6': np.float64, 'aruco_pos_7': np.float64, 'aruco_pos_8': np.float64, 'aruco_pos_9': np.float64}   
#Configuración de agrupador
min_window_size = 0.5                                                                                 #Tamaño mínimo de la ventana de agrupación
max_window_size = 1.5                                                                                 #Tamaño máximo de la ventana de agrupación
min_entries_per_sensor = 3                                                                            #Número mínimo de entradas por sensor para que el sensor se considere valido
min_valid_sensors = 12                                                                                #Número mínimo de sensores validos para que la ventana se considere valida 
invalid_sensor_value = -150                                                                           #Valor que se asigna a los sensores invalidos
sensor_filtering_tipe = 'median'                                                                      #Tipo de filtrado a aplicar a los sensores validos. Valores posibles: 'mean', 'median', 'mode', 'max', 'min'


#Cargamos el fichero
data = pd.read_csv(fingerprint_track_folder+fingerprint_track_file, sep=',', names=sensors_header, dtype=sensors_dtype)
#Retenemos el listado de macs
sensors_mac = data['mac_sensor'].unique()

##
## Proceso de agrupado por ventana de tiempo y filtrado
##
registries_pool = []
fingerprint_data = []
for index, row in data.iterrows():
    #ACUMULACIÓN DE REGISTROS
    #Retenemos la hora actual
    current_time = row['timestamp']
    #Añadimos registro al pool
    registries_pool.append(row)
    #Limpiamos caducados
    while len(registries_pool) > 0 and current_time - registries_pool[0]['timestamp'] > max_window_size:
        registries_pool.pop(0)

    #COMPROBACIÓN DE VENTANA VÁLIDA
    #Comprobamos si la ventana cumple con la antiguedad minima
    if not(len(registries_pool) > 0 and current_time - registries_pool[0]['timestamp'] >= min_window_size):
        continue
    #Comprobamos cuantos sensores válidos hay en el pool. Para ello debemos anotar cuantos sensores tienen al menos x entradas (segun configuración)
    valid_sensors = 0
    for sensor_mac in sensors_mac:
        if len(list(filter(lambda x: x['mac_sensor'] == sensor_mac, registries_pool))) >= min_entries_per_sensor:
            valid_sensors += 1
    #Si no hay suficientes sensores validos, continuamos
    if valid_sensors < min_valid_sensors:
        continue

    #FILTRADO DE REGISTROS
    subdata = {}
    for sensor_mac in sensors_mac:
        #Obtenemos los registros del sensor
        sensor_registries = list(filter(lambda x: x['mac_sensor'] == sensor_mac, registries_pool))
        #Comprobamos si el sensor es valido
        if len(sensor_registries) >= min_entries_per_sensor:
            #Si es valido, aplicamos el filtro
            if sensor_filtering_tipe == 'mean':
                subdata[sensor_mac] = math.floor(np.mean(list(map(lambda x: x['rssi'], sensor_registries))))
            elif sensor_filtering_tipe == 'median':
                subdata[sensor_mac] = math.floor(np.median(list(map(lambda x: x['rssi'], sensor_registries))))
            elif sensor_filtering_tipe == 'mode':
                subdata[sensor_mac] = math.floor(np.mode(list(map(lambda x: x['rssi'], sensor_registries))))
            elif sensor_filtering_tipe == 'max':
                subdata[sensor_mac] = math.floor(np.max(list(map(lambda x: x['rssi'], sensor_registries))))
            elif sensor_filtering_tipe == 'min':
                subdata[sensor_mac] = math.floor(np.min(list(map(lambda x: x['rssi'], sensor_registries))))
            else:
                raise Exception('Invalid filtering type')
        else:
            #Si no es valido, asignamos el valor de invalido
            subdata[sensor_mac] = invalid_sensor_value

    #Vaciamos el pool
    registries_pool = []

    #Añadimos el registro a la lista de registros, en este caso añadimos también la posición
    subdata['timestamp'] = current_time
    subdata['pos_x'] = row['pos_x']
    subdata['pos_y'] = row['pos_y']
    subdata['pos_z'] = row['pos_z']
    fingerprint_data.append(subdata)

#Preparamos el dataframe final
output_dataframe = pd.DataFrame(fingerprint_data)

#TODO esto esta hecho por hacer archivos con el mismo formato que el resto de generadores, si se decide usar este formato hay que quitarlo
#Ponemos pos_x, pos_y y pos_z al principio
output_dataframe = output_dataframe[['timestamp', 'pos_x', 'pos_y', 'pos_z'] + sensors_mac.tolist()]

#Guardamos en csv
output_dataframe.to_csv(fingerprint_track_output, index=False)
