import numpy as np
import pandas as pd
import glob
import re
import os.path
import math

#Variables globales
fingerprint_history_folder = './dataset/hst/set_1/'                                                 #Ruta donde se encuentran los históricos originales
fingerprint_history_train_file = './files/fingerprint_history_train.csv'                                  #Salida del csv de entrenamiento
fingerprint_history_test_file = './files/fingerprint_history_test.csv'                                    #Salida del csv de tests
test_data_rate = .2                                                                                 #Porcentaje de filas por posicion a volcar en el archivo de test
sensors_list = ['10','11','12','20','21','22','30','31','32','40', '41', '42']                      #Listado de ids de sensores segun su posición
sensors_mac = []                                                                                    #Extraido de los ficheros
regex_file_position = r"(\d+\.\d+_\d+\.\d+_\d+\.\d+)"                                               #regex para extraer la posición del sensor del nombre del fichero
sensors_header = ['timestamp', 'mac_sensor', 'mac_beacon', 'rssi']                                  #cabeceras de los archivos de los sensores
sensors_dtype = {'timestamp': np.float64, 'mac_sensor': str, 'mac_beacon': str, 'rssi': np.int32}   #tipo de datos en los archivos de los sensores

#Vamos a agrupar las mediciones de todos los sensores por zona de medición, extraemos para ello todos los ficheros del primer sensor, a partir de él leemos el resto
first_sensor_files = glob.glob(fingerprint_history_folder+'sensor'+sensors_list[0]+'*.mbd')
for first_sensor_file in first_sensor_files:
    #Leemos el contenido del fichero
    #print(first_sensor_file)
    data = pd.read_csv(first_sensor_file, sep=',', names=sensors_header, dtype=sensors_dtype)

    #Extraemos la zona del nombre del fichero vemos de cargar el resto de sensores
    zone = re.search(regex_file_position, first_sensor_file).group(1)
    for i in range(1, len(sensors_list)):
        sensor = sensors_list[i]
        sensor_file = fingerprint_history_folder+'sensor'+sensor+'_'+zone+'.mbd'
        #print(sensor_file)
        data = pd.concat([data, pd.read_csv(sensor_file, sep=',', names=sensors_header, dtype=sensors_dtype)])
    
    if(len(sensors_mac) == 0):
        sensors_mac = data['mac_sensor'].unique()

    #Redondeamos el timestamp a 0 decimales
    data['timestamp'] = data['timestamp'].round(0) #TODO probar a redondear a 1 decimal o 2
    #Agrupamos por timestamp y mac_sensor, si hay mas de un resultado de mac_sensor, nos quedamos con el valor medio de rssi
    data = data.groupby(['timestamp', 'mac_sensor']).mean(numeric_only=True).reset_index()

    ##Ya tenemos un conjunto de datos con un rssi por sensor y timestamp. Ahora necesitamos rellenar un dataframe con los datos en donde aparezca un sensor por columna
    #De la zona extraemos las posiciones x, y y z
    pos_x, pos_y, pos_z = zone.split('_')
    #Creamos un dataframe con todos los timestamps
    timestamps = data['timestamp'].unique()
    data_position_list = []
    for timestamp in timestamps:
        data_position_row = {'timestamp': timestamp, 'pos_x': pos_x, 'pos_y': pos_y, 'pos_z': pos_z}
        for sensor_mac in sensors_mac:
            rssi = data[(data['timestamp'] == timestamp) & (data['mac_sensor'] == sensor_mac)]['rssi']
            if(len(rssi) > 0):
                data_position_row[sensor_mac] = round(rssi.iloc[0], 0)
            else:
                data_position_row[sensor_mac] = -200
        data_position_list.append(data_position_row)    
    data_position = pd.DataFrame(data_position_list)

    #determinamos el punto de corte en base al ratio de test
    train_test_index = math.floor(len(data_position)*test_data_rate)

    #Escribimos en el csv de salida
    data_position[:-train_test_index].to_csv(fingerprint_history_train_file, mode='a', header=not os.path.exists(fingerprint_history_train_file), index=False)
    data_position[-train_test_index:].to_csv(fingerprint_history_test_file , mode='a', header=not os.path.exists(fingerprint_history_test_file), index=False)