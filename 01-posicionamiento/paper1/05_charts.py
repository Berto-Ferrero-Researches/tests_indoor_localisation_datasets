import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import os
import os.path
# Referencia al directorio actual, por si ejecutamos el python en otro directorio
script_dir = os.path.dirname(os.path.abspath(__file__))

# Definimos el listado de modelos a diseñar
models = [
    'T1',
    'M1',
    'M2',
    'M3',
    'M4',
    'M5',
    'M6',
    'M7',
    'M8'
]

# Definimos el valor del paper baseline para comparar
baselineMean = 3.064
baselineMedian = 2.223

# Dataset a emplear
datasets = [
    {
        'name': 'minsensors_10',
        'public_name': 'Empty Values Dataset',
        'values': {}
    },
    {
        'name': 'minsensors_12',
        'public_name': 'Non-empty Values Dataset',
        'values': {}
    }
]

# Configuración general
models_dir = os.path.join(script_dir, 'models')
output_dir = os.path.join(script_dir, 'charts')
predictions_file_pattern = os.path.join(
    models_dir, '__model_name__/__dataset_name__/output_prediction/predictions.csv')


max_value = 0
# Recorremos cada dataset
for dataset in datasets:
    # Recorremos cada modelo y recogemos sus medidas en distancia euclidiana
    dataset_values = {}
    for modelName in models:
        predictions_file = predictions_file_pattern.replace(
            '__model_name__', modelName).replace('__dataset_name__', dataset['name'])
        df = pd.read_csv(predictions_file)
        euc_distance = df['eclidean_distance']
        dataset_values[modelName] = euc_distance

    # Acumulamos los valores, de esta forma podemos definir valores como el máximo en la escala
    dataset['values'] = dataset_values

    max_dataset_value = np.max([value for row in dataset_values.values() for value in row])
    if(max_dataset_value > max_value):
        max_value = max_dataset_value

# Recorremos cada dataset una vez mas para ya plasmar los resultados
for dataset in datasets:
    fig, ax = plt.subplots()
    # Baseline
    plt.axhline(y=baselineMean, color='red', linestyle='-.', label='Baseline Mean', linewidth=1.5)
    plt.axhline(y=baselineMedian, color='blue', linestyle='-.', label='Baseline Median', linewidth=1.5)

    # Recorremos cada modelo y plasmamos los resultados
    ax.boxplot(dataset['values'].values(), meanline=True, showmeans=True, notch=True, showfliers=True)
    ax.set_xticklabels(dataset['values'].keys())
    ax.yaxis.grid(True)  # Agregar líneas de guía horizontales
    ax.set_ylim([0, max_dataset_value+2.5])
    plt.xlabel('Models')
    plt.ylabel('Euclidian distance error (m)')
    plt.title('Testing results - '+dataset['public_name'])
    
    plt.savefig(os.path.join(output_dir, dataset['name']+'-boxplot.png'))
    plt.savefig(os.path.join(output_dir, dataset['name']+'-boxplot.eps'))
