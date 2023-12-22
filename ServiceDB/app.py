import json
from flask import Flask, request, jsonify, flash, redirect, Response, send_from_directory, send_file, make_response
from werkzeug.utils import secure_filename
from utility_functions import *
from dynamo_botoObj import DynamoBotoObj
from colorama import Fore, Back, Style
import os

app = Flask(__name__)

app.config['TEMPLATE_DEVICE_FOLDER'] = 'static/template_device' #use
app.config['DATASET_DEVICE_FOLDER'] = 'static/dataset_device' #use
app.config['DOWNLOAD_FOLDER'] = 'static/download' # save csv or excel file, of query result 


@app.route('/', methods=['GET'])
def home():
	print("Microservice for managed DynamoDB")
	return jsonify({"home":f"Microservice for DynamoDB"})


#TESTATO OK
# richiesta relativa alla registrazione di un dispositivo -> comporta la creazione della tabella
@app.route('/createTable', methods=['POST'])
def createTable():
	message1=""
	message2=""
	message3=""
	message4=""

	if request.files and request.files.get('template_json') is not None:
		print(request.files['template_json'])
		path_file = request.files['template_json']
		print("File name", path_file.filename)
		message1 = path_file.filename

	else:
		path_file = None
		message1 = "Required <template_json>"

	args = request.values
	id_device = args.get("id_device")

	if id_device is None or id_device == "":
		message2 = "Required <id_device>"
		id_device = None
	else:
		message2 = id_device

	if id_device is None or path_file is None:
		data = jsonify({"Response":{"template_json": message1, "id_device": message2}})
		response = make_response(data, 707)
		return response

	# entrambi i campi sono dati

	# 1) ---controllare l'estensione del file (.json) e controlla i campi -------------
	
	print(Fore.MAGENTA + f"STEP-1/6 -> Check extension of file template_json" + Fore.RESET)
	if path_file and allowed_file_type(path_file.filename, ".json"):
		#message3 = "Correct extension of Template file"

		#------------------------------------------------------------------------------
		print(Fore.MAGENTA + f"STEP-2/6 -> Save file template_json to local folder" + Fore.RESET)

		#----   save file in server flask (static/template_device)  ---------------------
		destination = os.path.join(app.root_path, app.config['TEMPLATE_DEVICE_FOLDER'])
		secure_file_name = secure_filename(path_file.filename)
		save_file_into_server(path_file, destination, secure_file_name)

		#-----  parse json ------------------------------------------
		print(Fore.MAGENTA + f"STEP-3/6 -> Parse file template_json" + Fore.RESET)

		response_bool, message_response, code = db_botoObj.parseJsonTemplate(  secure_file_name, id_device )
		

		if response_bool is False:
			print(Fore.RED + f"Error parse file: {message_response}, Code: {code}"+ Fore.RESET)

					#----- elimina il template dal server flask
			print(Fore.MAGENTA + f"STEP-4/6 -> Delete file template_json from local folder" + Fore.RESET)
			deleteFile_from_server(destination, secure_file_name )

			print(Fore.MAGENTA + f"STEP-5/6 -> Pass on next step")

			print(Fore.MAGENTA + f"STEP-6/6 -> Send Response to Gategay" + Fore.RESET)
			

			data = jsonify({"Response": message_response})
			response = make_response(data, code)
			response.headers["Content-Type"] = 'application/json'
			return response

			#return jsonify({"template_json": message1, "id_device": message2, "Response- extension": message3, "Response - parse file":message4, "Result":message_response})

		else:
			#message4 = "Success"
			print(Fore.GREEN + f"Success parse file: {message_response}, Code: {code}"+ Fore.RESET)

			#print("Device", id_device)
					#----- elimina il template dal server flask
			print(Fore.MAGENTA + f"STEP-4/6 -> Delete file template_json from local folder" + Fore.RESET)

			deleteFile_from_server(destination, secure_file_name )

			# ------- creazione della TABELLA ------------------------------
			print(Fore.MAGENTA + f"STEP-5/6 -> Create Table in DynamoDB" + Fore.RESET)
			message = ""
			code = ""
			try:
				message, code = db_botoObj.createTable(id_device)
			except SystemExit as error:
				code = error.args[1]
				message = error.args[0]

			if code == 200:
				print(Fore.GREEN + f"Success in creating table [{id_device}]" + Fore.RESET)
			else:
				print(Fore.RED + f"Failure to create table [{id_device}]" + Fore.RESET) # verificato

			print(Fore.MAGENTA + f"STEP-6/6 -> Send Response to Gateway" + Fore.RESET)

			data = jsonify({"Response": message})
			response = make_response( data,code)
			response.headers["Content-Type"]= "application/json"
			return response
			#return jsonify({"template_json": message1, "id_device": message2, "Response- extension": message3, "Response - parse file":message4, "Result":message_response, "Result create table": messa_create})

	else:

		message = "Error extension file. Choose file (.json)"
		print(Fore.RED + f"Falled: {message}, Code: 707"+ Fore.RESET)

		print(Fore.MAGENTA + f"STEP-4/6 -> Delete file template_json from local folder" + Fore.RESET)
		deleteFile_from_server(destination, secure_file_name )

		print(Fore.MAGENTA + f" STEP-5/6 -> Pass on next STEP-6" + Fore.RESET)

		print(Fore.MAGENTA + f"STEP-6/6 -> Send Response to Gategay" + Fore.RESET)
		data = jsonify({"Response": message})
		response = make_response( data,707)
		response.headers["Content-Type"]= "application/json"
			
		return response

		#return jsonify({"template_json": message1, "id_device": message2, "Response": message3})

# richiesta
@app.route('/write_Data', methods=['POST'])
def write_Data():
	print('write_Data')
	message_file = ""
	message_dev = ""
	message_list = ""

	print(Fore.MAGENTA + f"STEP-1/6 -> Check the form values" + Fore.RESET)

	if request.files and request.files.get('data_json') is not None:
		print(request.files['data_json'])
		path_file = request.files['data_json']
		print("File name", path_file.filename)
		message_file = path_file.filename

	else:
		path_file = None
		message_file = "Required <data_json>"

	args = request.values
	id_device = args.get("id_device")
	string_list_keys_template = args.get("list_keys_template")

	if id_device is None or id_device == "":
		message_dev = "Required <id_device>"
		id_device = None
	else:
		message_dev = id_device

	if string_list_keys_template is None or string_list_keys_template == "":
		message_list = "Required <list_keys_template>"
		string_list_keys_template = None
	else:
		message_list = string_list_keys_template



	if id_device is None or path_file is None or string_list_keys_template is None:
		print(Fore.RED +"Form is not filled out correctly")
		data = jsonify({"Response":{"data_json": message_file, "id_device": message_dev, "list_keys_template" : message_list}})
		response = make_response(data, 707)
		response.headers['Content-Type'] = 'application/json'
		return response

	
	# 1) ---controllare l'estensione del file (.json)  -------------
	
	print(Fore.MAGENTA + f"STEP-2/6 -> Check extension of file template_json" + Fore.RESET)
	if path_file and allowed_file_type(path_file.filename, ".json"):
		#message3 = "Correct extension of Template file"

		#------------------------------------------------------------------------------
		print(Fore.MAGENTA + f"STEP-3/6 -> Save file dataset_device.json to local folder" + Fore.RESET)

		#----   save file in server flask ------------------------ ---------------------
		destination = os.path.join(app.root_path, app.config['DATASET_DEVICE_FOLDER'])
		secure_file_name = secure_filename(path_file.filename)
		save_file_into_server(path_file, destination, secure_file_name)

		#-----  parse json ------------------------------------------
		
		# convert string in list "a,b,c" -> ["a","b","c"]
		list_keys_template = list(string_list_keys_template.split(','))


		print(Fore.MAGENTA + f"STEP-4/6 -> Check if the measurement fields match the template" + Fore.RESET)
		print("List of template fields:")
		print(list_keys_template)
		local_path = os.path.join(app.root_path, app.config['DATASET_DEVICE_FOLDER'],secure_file_name)

		bool_match, message_match, code = dataField_vs_template(local_path, list_keys_template)

		if bool_match is False:
			print(Fore.RED + "Error. The measurement fields do not match the template fields"+ Fore.RESET)
			print(Fore.MAGENTA + f"STEP-5/6 -> Skip on next STEP-6" + Fore.RESET)
			print(Fore.MAGENTA + f"STEP-6/6 -> Send Error Response to Gateway" + Fore.RESET)

			data = jsonify({"Response": message_match})
			response = make_response(data, 808)
			response.headers['Content-Type'] = 'application/json'
			return response

		print(Fore.GREEN + "Correct. The measurement fields match the template fields"+ Fore.RESET)



		#----   write data in Table ------------------------------------------------
		print(Fore.MAGENTA + f"STEP-5/6 -> Write data on Table [{id_device}]" + Fore.RESET)

		path_dataset = os.path.join(destination,secure_file_name)
		code = ""
		resp = ""
		try:
			resp, code = db_botoObj.writeData(id_device, path_dataset)
		except SystemExit as error:
			code = error.args[1]
			resp = error.args[0]

		#--  elimina il file dal folder dataset_device --------
		deleteFile_from_server(destination, secure_file_name )
		#------------------------------
		print(Fore.MAGENTA + f"STEP-6/6 -> Send Response to Gateway" + Fore.RESET)
		data = jsonify({"Response":resp})
		response = make_response(data, code)
		response.headers['Content-Type'] = 'application/json'
		return response


### NUOVO - TESTATO 
@app.route('/delete_Table', methods=['DELETE'])
def delete_Table():
	message1 = ""
	args = request.values
	print(Fore.MAGENTA + f"STEP-1/3 -> Check form value"+ Fore.RESET)
	table_name = args.get('table_name')

	if table_name is None or table_name =="":
		message1 = "Required <table_name>"
		print(Fore.RED + f"Error: {message1}"+ Fore.RESET)
		data = jsonify({"Response": message1})
		response = make_response(data, 707)
		return response
	else:
		print(Fore.GREEN + f"Correct compile form: table_name [{table_name}]"+ Fore.RESET)

		## ---------- delete table  ----------------------------
		print(Fore.MAGENTA + f"STEP-2/3 -> Delete table"+ Fore.RESET)
		code = ""
		resp = ""
		try:
			resp, code = db_botoObj.deleteTable(table_name)
		except SystemExit as error:
			code = error.args[1]
			resp = error.args[0]

		if code == 200:
			print(Fore.GREEN+ f"Success Delete Table [{table_name}]"+Fore.RESET)
		else:
			print(Fore.RED+ f"Falled in Delete Table [{table_name}]. Error [{resp}]"+Fore.RESET)

		print(Fore.MAGENTA + f"STEP-3/3 -> Send Response to Gateway"+ Fore.RESET)
		data =  jsonify({"Response": resp})
		response = make_response( data, code)
		response.headers['Content-Type'] = 'application/json'
		return response

@app.route('/exec_Query', methods=['GET'])
def exec_Query():
	print(exec_Query)
	id_device = None
	list_clause_key = []
	list_clause_filter = []
	list_op_conditional = []
	list_op_conditional_filter = []
	select = ""
	format_file = None
	#filename_csv = None

	deleteFile_from_server(os.path.join(app.root_path,app.config['DOWNLOAD_FOLDER']),None, True)

	print(Fore.MAGENTA + f"STEP-1/4 -> Check forms value" + Fore.RESET)

	#data = json.loads(request.data)
	if request.is_json:
		print(type(request.json)) # dict!

		dict_content = request.json
		id_device = dict_content.get('id_device')
		list_clause_key = dict_content.get('list_clause_key')
		list_op_conditional = dict_content.get('list_op_conditional')

		list_clause_filter = dict_content.get('list_clause_filter')
		list_op_conditional_filter = dict_content.get('list_op_conditional_filter')
		select = dict_content.get('select')
		format_file = dict_content.get('format_file')
		

	print(f"id_device: {id_device}")
	print(f"list_clause_key: {list_clause_key}")
	print(f"list_op_conditional: {list_op_conditional}")
	print(f"list_clause_filter: {list_clause_filter}")
	print(f"list_op_conditional_filter: {list_op_conditional_filter}")
	print(f"select: {select}")
	print(f"format_file: {format_file}")

	filename = ""
	mimetype = ""
	
	if format_file == "csv":
		filename = "result_query.csv"
		mimetype = 'text/csv'

	elif format_file == "excel":
		filename = "result_query.xlsx"
		mimetype = "application/vnd.ms-excel"

	
	destination_folder_local = os.path.join(app.root_path, app.config['DOWNLOAD_FOLDER'])
	filename = secure_filename(filename)
	destination_local =os.path.join(destination_folder_local, filename)

	df_or_mess = ""
	code = ""
	print(Fore.MAGENTA+f"STEP-2/4 -> Prepare and exec QUERY" + Fore.RESET)

	try: 

		df_or_mess, code = db_botoObj.prepare_send_Query(id_device, list_clause_key, list_op_conditional, list_clause_filter, list_op_conditional_filter, select)

	except SystemExit as error:
		df_or_mess = error.args[0] 
		code = error.args[1] #606


	if code == 200:
		# successo, il risultato si trova in un file in destination_local
		# manda il file
		print(Fore.MAGENTA +f"STEP-3/4 -> Save FILE of the QUERY RESULT in local folder"+Fore.RESET)
		check_folders(destination_folder_local)
		# convert [dataframe] -- in --> [csv]
		if format_file == "csv":
			df_or_mess.to_csv(destination_local, sep =',', index = False)
		else:
			df_or_mess.to_excel(destination_local, index = False)



		print(Fore.MAGENTA + f"STEP-4/4 -> Send FILE of the QUERY RESULT to GATEWAY "+ Fore.RESET)
		# AGGIUNGERE as_attachment=True se si vuole SCARICARE
		response = send_file(destination_local, mimetype= mimetype, download_name=filename)
		response.headers["x-filename"] = filename
		response.headers["Access-Control-Expose-Headers"] = 'x-filename'
		response.headers["Content-Type"] = mimetype
		return response 

	else:
		print(Fore.MAGENTA + f"STEP-3/4 -> Skip on next STEP-4"+Fore.RESET)
		print(Fore.MAGENTA + f"STEP-4/4 -> Send ERROR RESULT to GATEWAY "+ Fore.RESET)

		data = jsonify({"Response":df_or_mess})
		response = make_response(data, code)
		response.headers['Content-Type'] = 'application/json'
		return response

@app.route('/exec_Scan', methods=['GET'])
def exec_Scan():
	print(exec_Scan)
	id_device = None
	list_clause_filter = []
	list_op_conditional_filter = []
	select = ""
	format_file = None
	
	deleteFile_from_server(os.path.join(app.root_path,app.config['DOWNLOAD_FOLDER']),None,True)

	print(Fore.MAGENTA + f"STEP-1/4 -> Check forms value" + Fore.RESET)

	if request.is_json:
		print(type(request.json)) # dict!

		dict_content = request.json

		id_device = dict_content.get('id_device')
		list_clause_filter = dict_content.get('list_clause_filter')
		list_op_conditional_filter = dict_content.get('list_op_conditional_filter')
		select = dict_content.get('select')
		format_file = dict_content.get('format_file')
		

	print(f"id_device: {id_device}")
	print(f"list_clause_filter: {list_clause_filter}")
	print(f"list_op_conditional_filter: {list_op_conditional_filter}")
	print(f"select: {select}")
	print(f"format_file: {format_file}")

	filename = ""
	mimetype = ""

	if format_file == "csv":
		filename = "result_query.csv"
		mimetype = 'text/csv'

	elif format_file == "excel":
		filename = "result_query.xlsx"
		mimetype = "application/vnd.ms-excel"

	
	destination_folder_local = os.path.join(app.root_path, app.config['DOWNLOAD_FOLDER'])
	filename = secure_filename(filename)
	destination_local =os.path.join(destination_folder_local, filename)

	df_or_mess = ""
	code = ""
	print(Fore.MAGENTA+f"STEP-2/4 -> Prepare and exec SCAN" + Fore.RESET)
	try: 

		df_or_mess, code = db_botoObj.prepare_send_Scan(id_device, list_clause_filter, list_op_conditional_filter, select)

	except SystemExit as error:
		df_or_mess = error.args[0] 
		code = error.args[1] #606



	if code == 200:
		# successo, il risultato si trova in un file in destination_local
		# manda il file
		print(Fore.MAGENTA +f"STEP-3/4 ->Save FILE of the SCAN RESULT in local folder"+Fore.RESET)
		check_folders(destination_folder_local)
		# convert [dataframe] -- in --> [csv]
		if format_file == "csv":
			df_or_mess.to_csv(destination_local, sep =',', index = False)
		else:
			df_or_mess.to_excel(destination_local, index = False)



		print(Fore.MAGENTA + f"STEP-4/4 -> Send FILE of the SCAN RESULT to GATEWAY "+ Fore.RESET)
		# AGGIUNGERE as_attachment=True se si vuole SCARICARE
		response = send_file(destination_local, mimetype= mimetype, download_name=filename)
		response.headers["x-filename"] = filename
		response.headers["Access-Control-Expose-Headers"] = 'x-filename'
		response.headers["Content-Type"] = mimetype
		return response 

	else:
		print(Fore.MAGENTA + f"STEP-3/4 -> Skip on next STEP-4"+Fore.RESET)
		print(Fore.MAGENTA + f"STEP-4/4 -> Send ERROR RESULT to GATEWAY "+ Fore.RESET)

		data = jsonify({"Response":df_or_mess})
		response = make_response(data, code)
		response.headers['Content-Type'] = 'application/json'
		return response




if __name__ == '__main__':
	print("Microservice for DynamoDB")

	db_botoObj = DynamoBotoObj.getInstance()
	db_botoObj.setAssume_Role_Arn(os.environ['ASSUME_ROLE_ARN'])
	db_botoObj.setRoleSessionName(os.environ['SESSION_NAME'])
	db_botoObj.setTemplateFolder(app.config['TEMPLATE_DEVICE_FOLDER'])
	db_botoObj.setDatasetFolder(app.config['DATASET_DEVICE_FOLDER'] )
	db_botoObj.sessionWithRefresh()



	app.run(host='0.0.0.0', port=5003, debug=True)
