import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib.pyplot as plt
import math
import os.path
import numbers
import pickle
import autokeras as ak
from sklearn.model_selection import train_test_split
import random
import sys
script_dir = os.path.dirname(os.path.abspath(__file__)) #Referencia al directorio actual, por si ejecutamos el python en otro directorio
root_dir = script_dir+'/../../'                                                                        #Referencia al directorio raiz del proyecto
sys.path.insert(1, root_dir)
from lib.trainingcommon import set_random_seed_value, load_data, save_history, save_model, descale_pos_x, descale_pos_y
from lib.models import M1

# Objetivos:
# FST1: Nº mínimo de medidas por sensor obligatorias VS error de predicción y número de muestras
# FST2: Nº mínimo de sensores con valor obligatorio VS error de predicción y número de muestras
# FST3: Tipo de filtrado de los sensores VS error de predicción y número de muestras
# FST4: Tamaño máximo de ventana VS error de predicción y número de muestras
# FST5: Tamaño mínimo de ventana VS error de predicción y número de muestras
# -- Configuración -- #

# Configuración por test
test_specific_settings = {
	'FST1': {
		'chart_x_label': 'Minimal required measures per sensor',
		'test_values': [1, 2, 3, 4, 5, 6],
	},
	'FST2': {
		'chart_x_label': 'Minimal required sensors without empty values',
		'test_values': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
	},
	'FST3': {
		'chart_x_label': 'Filter type',
		'test_values': ['max', 'min', 'mean', 'median', 'tss'],
	},
	'FST4': {
		'chart_x_label': 'Max window size (sec.)',
		'test_values': ["1.0", "1.25", "1.5", "1.75", "2.0", "2.25", "2.5", "2.75", "3.0"],
	},
	'FST5': {
		'chart_x_label': 'Min window size (sec.)',
		'test_values': ["0.25", "0.5", "0.75", "1.0", "1.25", "1.5", "1.75"],
	},
}

# Variables globales
random_seed = 42
batch_size = 256
dim_x = 20.660138018121128
dim_y = 17.64103475472807

#Configuración de la prueba
test_name = 'FST1'
output_dir = script_dir+'/output/'+test_name+'/'
output_dir_models = output_dir+'models/'
input_data_dir = root_dir+'preprocessed_inputs/paper1/'
training_data_filename = input_data_dir+test_name+'-fingerprint_-test_variable-.csv'
test_data_filename = input_data_dir+test_name+'-track_-test_variable-.csv'
scaler_filename = output_dir_models+'-test_variable--scaler.pkl'
model_filename = output_dir_models+'-test_variable--model.keras'
history_filename = output_dir_models+'-test_variable--history.pkl'

#Salida de los datos de test
test_output_file = output_dir+'/predictions/'+test_name+'_predictions_-test_variable-.csv'
general_figure_file = output_dir+'results.png'
general_boxfigure_file = output_dir+test_name+'_result.eps'
general_samples_frecuency_file = output_dir+'samples_frecuency.png'
general_results_file = output_dir+'results_data.csv'

# -- END Configuración -- #

# Extreamos la configuración específica de la prueba
chart_x_label = test_specific_settings[test_name]['chart_x_label']
test_values = test_specific_settings[test_name]['test_values']

# Cargamos la semilla de los generadores aleatorios
set_random_seed_value(random_seed)

# Recorremos cada valor de test_values
general_results = []
deviations = []
time_diffs = []
for test_value in test_values:
	#Definimos ficheros
	training_data_filename_execution = training_data_filename.replace('-test_variable-', str(test_value))
	test_data_filename_execution = test_data_filename.replace('-test_variable-', str(test_value))
	scaler_filename_execution = scaler_filename.replace('-test_variable-', str(test_value))
	model_filename_execution = model_filename.replace('-test_variable-', str(test_value))
	history_filename_execution = history_filename.replace('-test_variable-', str(test_value))
	test_output_file_execution = test_output_file.replace('-test_variable-', str(test_value))

	#Comprobamos si hay que entrenar
	training_required = False
	if not os.path.isfile(model_filename_execution) or not os.path.isfile(history_filename_execution) or not os.path.isfile(scaler_filename_execution):
		training_required = True

	#Si hay que entrenar
	if training_required:

		#Borramos ficheros previos para que no chillen
		if os.path.isfile(model_filename_execution):
			os.remove(model_filename_execution)
		if os.path.isfile(history_filename_execution):
			os.remove(history_filename_execution)
		if os.path.isfile(scaler_filename_execution):
			os.remove(scaler_filename_execution)

		#Cargamos los datos
		X_train, y_train = load_data(training_data_filename_execution, scaler_filename_execution, train_scaler_file=True, include_pos_z=False, scale_y=True, remove_not_full_rows=False)

		#Construimos el modelo
		inputlength = X_train.shape[1]
		outputlength = y_train.shape[1]
		model = M1(inputlength=inputlength, outputlength=outputlength).build_model()

		#Entrenamos
		X_train, X_test, y_train, y_test = train_test_split(X_train, y_train, test_size=0.2, random_state=random_seed)
		callback = tf.keras.callbacks.EarlyStopping(monitor='val_loss', min_delta=0.0001, patience=10, restore_best_weights=True)
		history = model.fit(X_train, y_train, epochs=1000, batch_size=batch_size, validation_data=(X_test, y_test), callbacks=[callback], verbose=1)

		#Guardamos el modelo y el histórico
		save_model(model, model_filename_execution)
		save_history(history, history_filename_execution)

	#Procedemos a la evaluación

	#Cargamos los datos de test
	X_test, y_test = load_data(test_data_filename_execution, scaler_filename_execution, train_scaler_file=False, include_pos_z = False, scale_y=True, remove_not_full_rows=False)
	full_data = pd.read_csv(test_data_filename_execution) #Cargamos la tabla completa para calculos adicionales como la diferencia de tiempo entre muestras

	#Cargamos el modelo
	model = tf.keras.models.load_model(model_filename_execution, custom_objects=ak.CUSTOM_OBJECTS)

	#Predecimos
	predictions = model.predict(X_test)

	#Componemos la salida
	y_test = y_test.to_numpy()
	output_list = []
	for index in range(0, len(predictions)):
		listrow = {
			'predicted_x': predictions[index][0],
			'predicted_y': predictions[index][1],
			#'predicted_z': predictions[index][2],
			'real_x': y_test[index][0],
			'real_y': y_test[index][1],
			#'real_z': output_data[index][2],
		}
		output_list.append(listrow)
	output_data = pd.DataFrame(output_list)

	#Desescalamos
	output_data['predicted_x'] = descale_pos_x(output_data['predicted_x'])
	output_data['predicted_y'] = descale_pos_y(output_data['predicted_y'])
	output_data['real_x'] = descale_pos_x(output_data['real_x'])
	output_data['real_y'] = descale_pos_y(output_data['real_y'])

	#Preparamos cálculos
	output_data['deviation_x'] = (output_data['predicted_x'] - output_data['real_x']).abs()
	output_data['deviation_y'] = (output_data['predicted_y'] - output_data['real_y']).abs()
	output_data['eclidean_distance'] = np.sqrt(np.power(output_data['deviation_x'], 2) + np.power(output_data['deviation_y'], 2))

	#Calculamos la diferencia de tiempo de cada fila con la previa
	output_data['time_diff'] = full_data['timestamp'].diff()

	#Hacemos la salida de todos los datos en bruto
	output_data.to_csv(test_output_file_execution, index=False)

	#Acumulamos los datos generales
	time_diff = output_data['time_diff'].dropna()
	general_results.append({
		'test_value': test_value,
		'test_samples_amount': len(output_data),
		'min_time_diff': time_diff.min(),
		'max_time_diff': time_diff.max(),
		'mean_time_diff': time_diff.mean(),
		'q25_time_diff': time_diff.quantile(0.25),
		'q50_time_diff': time_diff.quantile(0.50),
		'q75_time_diff': time_diff.quantile(0.75),
		'min_x': output_data['deviation_x'].min(),
		'max_x': output_data['deviation_x'].max(),
		'mean_x': output_data['deviation_x'].mean(),
		'q25_x': output_data['deviation_x'].quantile(0.25),
		'q50_x': output_data['deviation_x'].quantile(0.50),
		'q75_x': output_data['deviation_x'].quantile(0.75),
		'min_y': output_data['deviation_y'].min(),
		'max_y': output_data['deviation_y'].max(),
		'mean_y': output_data['deviation_y'].mean(),
		'q25_y': output_data['deviation_y'].quantile(0.25),
		'q50_y': output_data['deviation_y'].quantile(0.50),
		'q75_y': output_data['deviation_y'].quantile(0.75),
		'min_euclidean': output_data['eclidean_distance'].min(),
		'max_euclidean': output_data['eclidean_distance'].max(),
		'mean_euclidean': output_data['eclidean_distance'].mean(),
		'q25_euclidean': output_data['eclidean_distance'].quantile(0.25),
		'q50_euclidean': output_data['eclidean_distance'].quantile(0.50),
		'q75_euclidean': output_data['eclidean_distance'].quantile(0.75),
		'standard_deviation_euclidean': output_data['eclidean_distance'].std(),
	})
	deviations.append(output_data['eclidean_distance'])
	time_diffs.append(time_diff)

#Imprimimos a csv los resultados generales

general_results = pd.DataFrame(general_results)
general_results.to_csv(general_results_file, index=False)

# #Imprimimos la gráfica
# # Primer eje con el error medio
# fig, ax1 = plt.subplots()
# ax1.set_xlabel(chart_x_label)
# ax1.set_ylabel('Mean error (m)', color='tab:blue')
# ax1.set_ylim([0, general_results['mean_euclidean'].max()+0.5])
# plot_1 = ax1.plot(general_results['test_value'], general_results['mean_euclidean'], label='Mean error (m)', color='tab:blue', marker='o')
# #ax1.tick_params(axis='y', labelcolor='tab:blue')

# # Segundo eje con la cantidad de muestras
# ax2 = ax1.twinx()
# ax2.set_ylabel('Samples amount', color='tab:red')
# ax2.set_ylim([0, general_results['test_samples_amount'].max()+1])
# plot_2 = ax2.plot(general_results['test_value'], general_results['test_samples_amount'], label='Samples amount', color='tab:red', marker='o')
# #ax2.tick_params(axis='y', labelcolor='tab:red')

# # Tercer eje con la desviación estandar
# ax3 = ax1.twinx()
# ax3.set_yticklabels([])  # Ocultar los valores del eje y, pero mantener las líneas del eje
# ax3.yaxis.set_label_position('left')  # Colocar la etiqueta del eje y a la izquierda
# ax3.yaxis.set_label_coords(-0.1, 0)  # Colocamos la etiqueta del eje y a la izquierda
# ax3.set_ylabel('Standard deviation (m)', color='tab:green')
# ax3.set_ylim([0, general_results['mean_euclidean'].max()+0.5])
# plot_3 = ax3.plot(general_results['test_value'], general_results['standard_deviation_euclidean'], label='Standard deviation (m)', color='tab:green', marker='o')
# #ax3.tick_params(axis='y', labelcolor='tab:green')

# # Leyenda
# # plots = plot_1 + plot_2 + plot_3
# # labels = [l.get_label() for l in plots]
# # ax1.legend(plots, labels, loc='lower left')

# plt.xticks(general_results['test_value'])
# #plt.gca().set_aspect('equal', adjustable='datalim') # Para que los ejes tengan la misma escala
# plt.grid(True, which='both', linestyle='-', linewidth=0.5)
# plt.minorticks_on()
# plt.grid(which='minor', linestyle=':', linewidth='0.5', color='gray')
# plt.savefig(general_figure_file)


##Imprimimos la gráfica de cajas
# Primer eje con el error medio
fig, ax1 = plt.subplots()
ax1.set_xlabel(chart_x_label)
ax1.set_ylabel('Euclidian distance error (m)')
ax1.set_ylim([0, 12])

# Calculate the positions for the boxplots
positions = general_results['test_value']
#si positions no es numérico, tenemos que aplicar unas posiciones generadas
if not isinstance(positions[0], numbers.Number):	
	positions = np.arange(len(general_results['test_value']))
plot_1 = ax1.boxplot(deviations, positions=positions, showfliers=True, widths=0.2, showmeans=True, meanline=True, notch=True)
ax1.set_xticklabels(general_results['test_value'])

# Segundo eje con la cantidad de muestras
ax2 = ax1.twinx()
#ax2.set_ylabel('Samples amount', color='tab:red')
ax2.set_ylim([0, 70])
plot_2 = ax2.plot(general_results['test_value'], general_results['test_samples_amount'], label='Samples amount', color='tab:red', marker='o')
#ax2.tick_params(axis='y', labelcolor='tab:red')
#ax2.set_xticklabels(general_results['test_value'])
ax2.set_yticklabels([]) #Ocultar valores en el eje
ax2.yaxis.grid(False)

# Iterar sobre las posiciones y los números de muestras
for pos, num_samples in zip(positions, general_results['test_samples_amount']):
    # Usar annotate para agregar una anotación en la posición correspondiente
    ax1.annotate(str(num_samples), (pos, 1), xytext=(0, 250), 
                 textcoords='offset points', ha='center', va='bottom', color='tab:red')
ax1.annotate("Samples amount", (0.5, 1), xytext=(0, -20), xycoords='figure fraction', textcoords='offset points', ha='center', va='bottom', color='tab:red')


# Tercer eje con la frecuencia de muestras
ax3 = ax1.twinx()
ax3.set_xticks(positions)
ax3.set_ylabel('Time between samples (sec.)', color='tab:blue')
ax3.set_ylim([0, 3])
plot_3 = ax3.plot(general_results['test_value'], general_results['mean_time_diff'], label='Time between samples (sec.)', color='tab:blue', marker='o')
ax3.tick_params(axis='y', labelcolor='tab:blue')
ax3.set_xticklabels(general_results['test_value'])

plt.xticks(general_results['test_value'])
plt.grid(True)
plt.savefig(general_boxfigure_file)


# ##Tercer gráfico con la frecuencia de muestras
# fig, ax1 = plt.subplots()
# ax1.set_xlabel(chart_x_label)
# ax1.set_ylabel('Time difference between samples (sec.)')
# ax1.set_ylim([0, 6])

# # Calculate the positions for the boxplots
# positions = np.arange(1, len(general_results['test_value'])+1)
# plot_1 = ax1.boxplot(time_diffs, positions=positions, showfliers=True, widths=0.2)
# ax1.set_xticklabels(general_results['test_value'])

# # Segundo eje con la cantidad de muestras
# ax2 = ax1.twinx()
# ax2.set_ylabel('Samples amount', color='tab:red')
# ax2.set_ylim([0, 70])
# plot_2 = ax2.plot(general_results['test_value'], general_results['test_samples_amount'], label='Samples amount', color='tab:red', marker='o')
# ax2.tick_params(axis='y', labelcolor='tab:red')
# ax2.set_xticklabels(general_results['test_value'])

# plt.xticks(general_results['test_value'])
# plt.grid(True)
# plt.savefig(general_samples_frecuency_file)