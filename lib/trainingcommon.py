import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pickle
import tensorflow as tf
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import MinMaxScaler

#region Carga de datos
def load_training_data(training_file: str, test_file: str, scaler_file: str=None, include_pos_z: bool=True, scale_y: bool=False, group_x_2dmap: bool=False, remove_not_full_rows: bool=False):
    #Cargamos los ficheros
    train_data = pd.read_csv(training_file)
    test_data = pd.read_csv(test_file)

    #Preparamos los datos
    X_train, y_train = prepare_data(train_data, include_pos_z, scale_y, remove_not_full_rows)
    X_test, y_test = prepare_data(test_data, include_pos_z, scale_y, remove_not_full_rows)

    #Escalamos
    if scaler_file is not None:
        scaler = StandardScaler()
        scaler.fit(X_train)
        with open(scaler_file, 'wb') as scalerFile:
            pickle.dump(scaler, scalerFile)
            scalerFile.close()

        X_train_scaled = X_train.copy()        
        X_train_scaled[X_train.columns] = scaler.transform(X_train)
        X_train = X_train_scaled
        X_test_scaled = X_test.copy()        
        X_test_scaled[X_test.columns] = scaler.transform(X_test)
        X_test = X_test_scaled

    #Agrupamos los valores de X en un mapa 2D
    if group_x_2dmap:
        X_train = group_rssi_2dmap(X_train)
        X_test = group_rssi_2dmap(X_test)

    #Devolvemos
    return X_train, y_train, X_test, y_test

def load_real_track_data(track_file: str, scaler_file: str=None, include_pos_z: bool=True, scale_y: bool=False, remove_not_full_rows: bool=False):
    #Cargamos el fichero
    track_data = pd.read_csv(track_file)

    #Preparamos los datos
    X, y = prepare_data(track_data, include_pos_z, scale_y, remove_not_full_rows)

    #Escalamos
    if scaler_file is not None:
        with open(scaler_file, 'rb') as scalerFile:
            scaler = pickle.load(scalerFile)
            scalerFile.close()

        X_scaled = X.copy()        
        X_scaled[X.columns] = scaler.transform(X)
        X = X_scaled   

    #Devolvemos
    return X, y

def prepare_data(data, include_pos_z: bool=True, scale_y: bool=False, remove_not_full_rows: bool=False):
    #Eliminamos las filas que no tienen todos los datos
    
    if remove_not_full_rows:
        #Reemplazamos los -200 en las columnas de rssi (a partir de la cuarta) por NaN
        data.iloc[:, 4:] = data.iloc[:, 4:].replace(-200, np.nan)

    #Extraemos cada parte
    y = data.iloc[:, 1:(4 if include_pos_z else 3)]
    X = data.iloc[:, 4:]
    #Escalamos y
    if scale_y:
        y = scale_dataframe(y)

    #Ordenamos alfabéticamente las columnas de X, asegurandonos de que todos los datasets van en el mismo orden
    X = X.reindex(sorted(X.columns), axis=1)

    #Inputamos los valores de -200 por el modelo
    #YA no es necesario, hay un csv con los datos inputados
    #if remove_not_full_rows:
    #    X = imputing_predict_na_data(X)

    #Convertimos a float32 e in32 para reducir complejidad
    y = y.astype(np.float32)
    X = X.astype(np.int32)

    #Devolvemos
    return X,y

def imputing_predict_na_data(data: pd.DataFrame):
    #Creamos una copia de data para el trabajo
    data_tmp = data.copy()
    #Reemplazamos los -200 por NaN
    data = data.replace(-200, np.nan)
    #Borramos las filas que tengan 3 o mas NaN
    #data_tmp = data_tmp.dropna(thresh=3)
    #Nos aseguramos que en el tmp sea -200
    data_tmp = data_tmp.replace(np.nan, -200)

    #Cargamos el scaler
    scaler = MinMaxScaler()
    scaler.fit([[-100], [0]])
    #Escalamos
    for sensor in data_tmp.columns:
        data_tmp[sensor] = scaler.transform(data_tmp[sensor].values.reshape(-1, 1)).flatten()

    #Cargamos el modelo
    model = tf.keras.models.load_model('dataset_imputing_values/files/model.h5')
    #Predecimos
    data_tmp_output = model.predict(data_tmp.values.reshape(data_tmp.shape[0], data_tmp.shape[1], 1))
    #Desescalamos
    data_tmp_output = scaler.inverse_transform(data_tmp_output.reshape(data_tmp_output.shape[0], data_tmp_output.shape[1]))
    data_tmp_output = pd.DataFrame(data_tmp_output, columns=data_tmp.columns).round()

    #Reemplazamos los -200 por los valores predichos
    for index,row in data.iterrows():
        for sensor in data.columns:
            if np.isnan(row[sensor]):
                data[sensor][index] = data_tmp_output[sensor][index]

    #Devolvemos
    return data


def group_rssi_2dmap(data: pd.DataFrame, default_empty_value: int=-200):
    #Definimos el array de la matriz a extrapolar, sacada de los mapas del dataset
    #  0  12  21  0
    #  11 10  20  22
    #  42 40  30  31
    #  0  41  32  0
    rssi_map = [
        [None, '000000000102', '000000000201', None],
        ['000000000101', 'b827eb4521b4', 'b827eb917e19', '000000000202'],
        ['000000000402', 'b827ebfd7811', 'b827ebf7d096', '000000000301'],
        [None, '000000000401', '000000000302', None]
    ]
    final_data = []
    #Por cada fila del dataset creamos un array con los valores de rssi en el mismo índice que la matriz rssi_map
    for index, row in data.iterrows():
        rssi = np.ndarray((len(rssi_map), len(rssi_map[0])))
        for i in range(len(rssi_map)):
            rssi_map_row = rssi_map[i]
            for j in range(len(rssi_map_row)):
                rssi_map_col = rssi_map_row[j]
                rssi_value = default_empty_value
                if rssi_map_col is not None:
                    rssi_value = row[rssi_map_col]
                rssi[i][j] = rssi_value
        final_data.append(rssi)
    #Devolvemos
    return np.array(final_data)
#endregion

#region escalado de datos

def get_scaler_pos_x():
    """
    Devuelve un scaler para la posición x
    Returns: 
        MinMaxScaler    
    """
    scaler = MinMaxScaler()
    scaler.fit([[0],[20.660138018121128]])
    return scaler

def get_scaler_pos_y():
    """
    Devuelve un scaler para la posición y
    Returns: 
        MinMaxScaler    
    """
    scaler = MinMaxScaler()
    scaler.fit([[0],[17.64103475472807]])
    return scaler

def scale_pos_x(pos_x: pd.Series):
    """
    Escala la posición x
    Args:
        pos_x (pd.Series): posición x
    Returns:
        pd.Series: posición x escalada
    """
    scaler = get_scaler_pos_x()
    return scaler.transform(pos_x.values.reshape(-1, 1)).flatten()

def scale_pos_y(pos_y: pd.Series):
    """
    Escala la posición y
    Args:
        pos_y (pd.Series): posición y
    Returns:
        pd.Series: posición y escalada
    """
    scaler = get_scaler_pos_y()
    return scaler.transform(pos_y.values.reshape(-1, 1)).flatten()

def scale_dataframe(data: pd.DataFrame):
    """
    Escala un dataframe
    Args:
        data (pd.DataFrame): dataframe a escalar
    Returns:
        pd.DataFrame: dataframe escalado
    """
    data_scaled = data.copy()
    data_scaled['pos_x'] = scale_pos_x(data['pos_x'])
    data_scaled['pos_y'] = scale_pos_y(data['pos_y'])
    return data_scaled

def descale_pos_x(pos_x: pd.Series):
    """
    Desescala la posición x
    Args:
        pos_x (pd.Series): posición x
    Returns:
        pd.Series: posición x desescalada
    """
    scaler = get_scaler_pos_x()
    return scaler.inverse_transform(pos_x.values.reshape(-1, 1)).flatten()

def descale_pos_y(pos_y: pd.Series):
    """
    Desescala la posición y
    Args:
        pos_y (pd.Series): posición y
    Returns:
        pd.Series: posición y desescalada
    """
    scaler = get_scaler_pos_y()
    return scaler.inverse_transform(pos_y.values.reshape(-1, 1)).flatten()

def descale_dataframe(data: pd.DataFrame):
    """
    Desescala un dataframe
    Args:
        data (pd.DataFrame): dataframe a desescalar
    Returns:
        pd.DataFrame: dataframe desescalado
    """
    data_scaled = data.copy()
    data_scaled['pos_x'] = descale_pos_x(data['pos_x'])
    data_scaled['pos_y'] = descale_pos_y(data['pos_y'])
    return data_scaled

#endregion


#region dibujado
def plot_learning_curves(hist):
  plt.plot(hist.history['loss'])
  plt.plot(hist.history['val_loss'])
  plt.title('Curvas de aprendizaje')
  plt.ylabel('Loss')
  plt.xlabel('Epoch')  
  plt.legend(['Conjunto de entrenamiento', 'Conjunto de validación'], loc='upper right')
  plt.show()
#endregion