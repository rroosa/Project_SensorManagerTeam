import json
from flask import Flask, request, jsonify, redirect, Response, make_response, send_from_directory, send_file
from werkzeug.utils import secure_filename
import os
import http.client
import requests
from utility_functions import UtilityFunction
from environment_config import *
from colorama import Fore, Back, Style
import re
import decimal

app = Flask(__name__)


if app.config["ENV"] == "production":
	app.config.from_object("config.ProductionConfig")

elif app.config["ENV"] == "testing":
	app.config.from_object("config.TestingConfig")

elif app.config["ENV"] == "development":
	app.config.from_object("config.DevelopmentConfig")


#app.config['UPLOAD_FOLDER']= 'static/upload'
#c = 'static/download'

#connection_s3 = http.client.HTTPConnection('localhost', 5002)
#connect_s3 = f"http://localhost:5002"
#connect_DB = f"http://localhost:5003"
connect_s3 = app.config['CONNECT_S3']
connect_DB = app.config['CONNECT_DB']


@app.route('/', methods=['GET'])
def home():
	print("Microservice Gateway")
	return jsonify({"home":f"Microservice Gataway"})

@app.route('/hello/from/s3', methods=['GET'])
def hello_http():

	header = {'ACCEPT': 'application/json'}

	with connection_s3 as connection:
		connection.request("GET", "/")
		response = connection.getresponse()
		reason = response.reason
		response_bytes = response.read() # leggi il contenuto della risposta come bytes


	print(f"Status_code: {response.status} ")
	print(f"Reason: {response.reason} ")

	return jsonify({"Response": response.status})

@app.route('/hello/s3', methods=['GET'])
def hello_requests():
	header = {'ACCEPT': 'application/json'}
	resp = requests.get(connect_s3, headers = header)
	resp_dict = resp.json()

	return jsonify(resp_dict)



#-------- ENDPOINT to regiter DEVICE ----------
# TESTATO - OK
@app.route('/register_Device', methods=['POST'])
def register_Device():
	#print("Send to S3: device_template  and device_sensor_name")
	message_d=""
	message_t=""
	section_register = False
	bucket = app.config['BUCKET_TEMPLATE']

	# manage request from client-utent
	print(Fore.BLUE + f" STEP-1/7 -> Check forms value" + Fore.RESET)
	args = request.values
	device_sensor_name = args.get("sensorDevice_model")
	device_template = None

	if device_sensor_name is None or device_sensor_name == "":
		message_d = "Required <sensorDevice_model>"
		device_sensor_name = None
	else:
		message_d = device_sensor_name

	
	if request.files and request.files.get('device_template') is not None:
		message_t = request.files['device_template'].filename
		device_template = request.files['device_template']
		# controlla l'estensione del file
		if message_t != "":
			resp_bool = utility_Obj.check_file_format(message_t,".json")
			if resp_bool is False:
				message_t = "Error: Uncorrect extension file, choose file (.json)"

				data = jsonify({"Response": message_t} )
				response = make_response(data, 707)
				response.headers['Content-Type']= 'application/json'
				return response
		else:
			message_t = "Required pathfile in format (.json) in <device_template>" 
			device_template = None
	
	else:
		message_t = "Required <device_template>"

	if device_template is not None: # è presente
		if device_sensor_name is None: # non presente
			return jsonify({"device_template": message_t, "device_sensor_name": message_d } )
		else:
			section_register = True  # è presente
			
	else:
		
		return jsonify({"device_template": message_t, "device_sensor_name": message_d } )
		

	if section_register is True:
		print(Fore.GREEN + f"Correct compile form" + Fore.RESET)

		print(Fore.BLUE + f" STEP-2/7 -> Section REGISTER DEVICE" + Fore.RESET)

		##########    prepare request to send to microservice S3 and DB  ###############
		
		
		#----   save file in server flask (static/upload)  -
		destination = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
		secure_file_name = secure_filename(device_template.filename)
		utility_Obj.save_file_into_server(device_template, destination, secure_file_name)

		pathfile_local = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'],secure_file_name)
		print("Local path: ",pathfile_local)

		#---- send request POST to Microservice DB -----------------
		print(Fore.BLUE + f" STEP-3/7 -> send Request POST to Microservice DB" + Fore.RESET)

		f = open(pathfile_local, 'rb')
		files = {'template_json': f }
		data = {"id_device": device_sensor_name }
		header = {'ACCEPT': 'application/json'}
		url_destination = utility_Obj.getUrl_Connect_DB() + utility_Obj.getUrl_CreateTable()
		response_from_DB = requests.post(url_destination, files = files, data = data, headers= header)
		f.close()

		message_to_utent = ""

		print(Fore.BLUE + f" STEP-4/7 -> Manage Response obtained from Microservice DB" + Fore.RESET)


		if response_from_DB.status_code == 200:
			content_json = response_from_DB.json()
			print("content_json",content_json)
			content = content_json.get("Response")
			print(Fore.MAGENTA+f"Response from Microservice DB:"+ Fore.RESET)
			print(Fore.GREEN + f"[{content}]" + Fore.RESET)
			#print("Success register device")
			#message_to_utent = "Success Register Device"
		elif response_from_DB.status_code == 707:
			c_json = response_from_DB.json()
			content_json = c_json.get("Response")
			message_to_utent = content_json
			print(Fore.MAGENTA+f"Response from Microservice DB:"+ Fore.RESET)
			print(Fore.RED + f"[{message_to_utent}]" + Fore.RESET)

			message_to_utent = re.sub("Table","Device", content, flags=re.IGNORECASE)
			print(Fore.BLUE + f" STEP-5/7 -> Skip on next STEP-7" + Fore.RESET)
			print(Fore.BLUE + f" STEP-7/7 -> Response to client-utent" + Fore.RESET)


			return jsonify({"Response": message_to_utent })


		elif response_from_DB.status_code == 808 or response_from_DB.status_code == 606 :
			content_json = response_from_DB.json()
			content = content_json.get("Response")
			print(Fore.MAGENTA+f"Response from Microservice DB:"+ Fore.RESET)
			print(Fore.RED + f"[{content}]" + Fore.RESET)
			
			message_to_utent = re.sub("Table","Device", content, flags=re.IGNORECASE)
			print(Fore.BLUE + f" STEP-5/7 -> Skip on next STEP-7" + Fore.RESET)
			print(Fore.BLUE + f" STEP-7/7 -> Response to client-utent" + Fore.RESET)


			return jsonify({"Response": message_to_utent })

		else:
			content_json = response_from_DB.json()
			content = content_json.get("Response")
			print(Fore.MAGENTA+f"Response from Microservice DB:"+ Fore.RESET)
			print(Fore.RED + f"[{content}]" + Fore.RESET)

			message_to_utent = re.sub("Table","Device", content, flags=re.IGNORECASE)
			print(Fore.BLUE + f" STEP-5/7 -> Skip on next STEP-7" + Fore.RESET)
			print(Fore.BLUE + f" STEP-7/7 -> Response to client-utent" + Fore.RESET)

			return jsonify({"Response": message_to_utent })




		#----  send requests POST to Microservice S3----------------
		print(Fore.BLUE + f" STEP-5/7 -> send Request POST to Microservice S3" + Fore.RESET)

		f = open(pathfile_local,'rb')
		files = {'device_template': f }
		header = {'ACCEPT': 'application/json'}
		data = {'device_sensor_name': device_sensor_name, "bucket": bucket, "type_file":"json" }

		url_destination = utility_Obj.getUrl_Connect_S3() + utility_Obj.getUrl_RegisterDevice()

		response_incoming_S3 = requests.post(url_destination, files = files, data = data, headers= header)
		f.close()

		code = response_incoming_S3.status_code
		headers = response_incoming_S3.headers
		content_type = headers.get('Content-Type')
		content_json = None
		message_to_utent = ""

		print(Fore.BLUE + f"STEP-6/7 ->  Manage Response obtained Microservice S3" + Fore.RESET)

		if content_type == "application/json":

			content_json = response_incoming_S3.json()

			if response_incoming_S3.status_code == 200:
				content = content_json.get("Response")
				print(Fore.CYAN+f" Response from Microservice S3:"+ Fore.RESET)
				print(Fore.GREEN + f"[{content}]" + Fore.RESET)

				message_to_utent = "Success Register Device"

			elif response_incoming_S3.status_code == 707:
				c_json = response_incoming_S3.json()
				content_json = c_json.get("Response")
				message_to_utent = content_json
				print(Fore.CYAN+f"Response from Microservice S3:"+ Fore.RESET)
				print(Fore.RED + f"[{message_to_utent}]" + Fore.RESET)

				#return jsonify({"Response": message_to_utent })

			elif response_incoming_S3.status_code == 808 or response_incoming_S3.status_code == 606 :
				content_json = response_incoming_S3.json()
				content = content_json.get("Response")
				print(Fore.CYAN+f"Response from Microservice S3:"+ Fore.RESET)
				print(Fore.RED + f"[{content}]" + Fore.RESET)
				
				message_to_utent = content

				#return jsonify({"Response": message_to_utent })

			else:
				content = content_json.get("Response")
				print(Fore.CYAN+f" Response from Microservice S3:"+ Fore.RESET)
				print(Fore.RED + f"[{content}]" + Fore.RESET)

				message_to_utent = "Falled Register Device"


			if response_incoming_S3.status_code != 200:
				print(Fore.YELLOW+ "STEP_extra-1/2 -> Send Request DELETE to Microservice DB"+ Fore.RESET)
				#elimina la tabella creata
				#---- send request POST to Microservice DB -----------------
				header = {'ACCEPT': 'application/json'}
				data = {"table_name": device_sensor_name }
				url_destination = utility_Obj.getUrl_Connect_DB() + utility_Obj.getUrl_DeleteTable()
				response_from_DB = requests.delete(url_destination, data = data, headers= header)

				code_db = response_from_DB.status_code
				headers = response_from_DB.headers
				content_type = headers.get('Content-Type')

				print(Fore.YELLOW + f" STEP_extra-2/2 -> Manage Response obtained from Microservice DB" + Fore.RESET)

				if content_type is not None and content_type == 'application/json':
					content_json = response_from_DB.json()
					content = content_json.get("Response")
					print(Fore.MAGENTA+f"Response from Microservice DB:"+ Fore.RESET)
					if code_db != 200:
						print(Fore.RED + f"[{content}]" + Fore.RESET)
					else:
						print(Fore.GREEN + f"[{content}]" + Fore.RESET)


		utility_Obj.deleteFile_from_server(destination,secure_file_name)
		
		print(Fore.BLUE + f" STEP-7/7 -> Response to client-utent" + Fore.RESET)

		return jsonify({"Response": message_to_utent , "Code": code})




# --- TESTATO
@app.route('/store_SensorDataSheet', methods=['POST']) #---> call postObject of S3
def store_SensorDataSheet():
	print("store_SensorDataSheet")
	message1 = ""
	message2 = ""
	message3 = ""
	args = request.values

	#-----------------------------------------------------
	#bucket = args.get("bucket")
	#print("Bucket ", bucket)
	bucket = app.config['BUCKET_DATA_SHEET']

	category = args.get("category")
	object_name = args.get("dataSheet_name")
	path_file = None

	print(Fore.BLUE + f" STEP-1/6 -> Check the form values" + Fore.RESET)


	if request.files and request.files.get('path_file') is not None:
		print(request.files['path_file'])
		path_file = request.files['path_file']
		print("File name", path_file.filename)
		if path_file.filename == "":
			path_file = None
			message1 = "Required pathfile in format (.txt || .pdf || .docx) in <path_file>"
		else:
			message1 = path_file.filename

	else:
		message1 = "Required <path_file>"

		#path_file = args.get('bucket')
		#print("path_file", path_file)

	if bucket is None or bucket == "":
		bucket = None
		message2 = "Required <bucket>"
	else:
		message2 = bucket

	if category is None or category == "":
		category = None
		message3 = "Required <category>"

	else:
		message3 = category

	if (path_file is None) or (bucket is None) or (category is None):

		print(Fore.RED + f"Uncorrect compile form" + Fore.RESET)
		return jsonify({"Path_file": message1, "Category": message3})

		#object_name = args.get('object_name') # nome dell'oggetto (con estensione)

	print(Fore.BLUE + f"Check the file format" + Fore.RESET)

	if path_file and utility_Obj.allowed_file_type(path_file.filename, "check_file"):
		# estensione del file è corretto 
		print( Fore.GREEN + f" File format is correct" + Fore.RESET)

		print("Nome file: ", path_file.filename )
		secure_file_name = secure_filename(path_file.filename)
		print("Security file: ",secure_file_name)
		if object_name is None:
			object_name = secure_file_name
		#  se object name è presente, controlla se rispetta le estensioni compatibile con il file
		else:
			response_type = utility_Obj.allowed_file_type(object_name,"check_obj" )
			if response_type is False:
				response = ""
				if utility_Obj.getExt() == '.pdf':
					response = "Uncorrect extension of sensor_data_sheet name. Replace in (.pdf)"
					#return jsonify({"filename":message1,"Object_name": object_name, "category": category,"Bucket": message2, "Response": "Uncorrect extension object (.pdf)"})
				
				elif utility_Obj.getExt() == '.txt':
					response = "Uncorrect extension of sensor_data_sheet name. Replace in (.txt)"
					#return jsonify({"filename":message1,"Object_name": object_name, "category": category,"Bucket": message2, "Response": "Uncorrect extension object (.txt)"})


				elif utility_Obj.getExt() == '.docx':
					response = "Uncorrect extension of sensor_data_sheet name. Replace in (.docx)"
					#return jsonify({"filename":message1,"Object_name": object_name, "category": category,"Bucket": message2, "Response": "Uncorrect extension object (.docx)"})
				print( Fore.RED+ f"{response}" + Fore.RESET)
				return jsonify({"Response": response})
			else:
				object_name = response_type
		#-----------------------------
		#	TEST CORRECT compile POST
		#return jsonify({"filename":message1,"Object_name": object_name, "Bucket": message2, "Response": "Correct POST"})
		#
		#-------------------------
		print( Fore.GREEN+ f"Correct compile form" + Fore.RESET)

		print(Fore.BLUE + f"STEP-2/6 -> Save file to local folder"+ Fore.RESET)

		destination = os.path.join(app.root_path,app.config['UPLOAD_FOLDER'])
		secure_file_name = secure_filename(path_file.filename)
		utility_Obj.save_file_into_server(path_file, destination, secure_file_name)
		
		pathfile_local = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'],secure_file_name)
		
		##########    prepare request to send microservice S3  ###############

		print(Fore.BLUE + f"STEP-3/6 -> Send Request POST to Microservice S3"+ Fore.RESET)
		f = open(pathfile_local,'rb')
		header = {'ACCEPT': 'application/json'}
		files = {'path_file': f}
		data = {'object_name': object_name, "bucket": bucket, "folder": category }
		
		url_destination = utility_Obj.getUrl_Connect_S3() + utility_Obj.getUrl_UploadObject_S3()

		response_from_S3 = requests.post(url_destination, files = files, data = data, headers= header)
		f.close()
		print(Fore.BLUE + f"STEP-4/6 -> Manage Response obtained from Microservice S3"+ Fore.RESET)
		message_success = f"Upload Success of file {secure_file_name}"
		message_error = "Upload Falled"
		source = "Microservice S3"


		message_to_client = utility_Obj.handlerResponse( response_from_S3, source, message_success, message_error)

		print(Fore.BLUE + f"STEP-5/6 -> Delete file from local folder"+ Fore.RESET)

		utility_Obj.deleteFile_from_server(destination, secure_file_name )

		print(Fore.BLUE + f"STEP-6/6 -> Response to client-utent"+ Fore.RESET)

		return jsonify({"Response": message_to_client})

	else:
		print( Fore.RED + f" Error. File format not is correct" + Fore.RESET)
		
		message = f"Error. File format not is correct. Choose file type with extension [text (.txt) ||  word (.docx ) || pdf (.pdf )]" 

		print(Fore.BLUE + f"STEP-2/6 -> Skip on next STEP-6"+ Fore.RESET)
		print(Fore.BLUE + f"STEP-6/6 -> Response to client-utent"+ Fore.RESET)

		return jsonify({"Response": message})
		#return jsonify({"filename":message1,"Object_name": object_name, "Bucket": message2, "Response": "Choose file type with extension [text (.txt) ||  word (.docx ) || pdf (.pdf )]"})

## TESTATO
#### DELETE TEMPLATE from BUCKET and DELETE TABLE from DB
@app.route('/delete_Device', methods=['DELETE']) #---> invoca delete_Object di S3 & delete_Table di DB
def delete_Device():
	print("delete_Device")
	message1 = ""
	args = request.values
	sensorDevice_model = args.get('sensorDevice_model') # nome del dispositivo da eliminare
	bucket = app.config['BUCKET_TEMPLATE']

	print(Fore.BLUE + f" STEP-1/7 -> Check forms value" + Fore.RESET)

	if sensorDevice_model is None or sensorDevice_model =="":
		sensorDevice_model = None
		message1 = "Required <sensorDevice_model>"

		return jsonify({"Response": message1})


	######### prepare request to send ServiceS3 ############
	print(Fore.BLUE +f" STEP-2/7 -> Prepare Request to send Microservice S3" +Fore.RESET)
	key = f"template-{sensorDevice_model}.json"
	header = {'ACCEPT': 'application/json'}
	data = {'bucket': bucket, "key": key }

	url_destination_S3 = utility_Obj.getUrl_Connect_S3() + utility_Obj.getUrl_DeleteObject_S3()

	response_incoming_S3 = requests.delete(url_destination_S3,  data = data, headers= header)

	print(Fore.BLUE + f" STEP-3/7 -> Manage Response obtained from Microservice S3" + Fore.RESET)


	code = response_incoming_S3.status_code
	headers = response_incoming_S3.headers
	content_type = headers.get('Content-Type')
	content_json = None
	response_to_client_user = ""
	
	if content_type == "application/json":
		content_json = response_incoming_S3.json()
		content = content_json.get("Response")

		if code == 200:
			print(Fore.CYAN+f"Response from Microservice S3:"+ Fore.RESET)
			print(Fore.GREEN + f"[{content}]" + Fore.RESET)
			#response_to_client_user = content

		elif code == 707 or code == 606:
			print(Fore.CYAN+f"Response from Microservice S3:"+ Fore.RESET)
			print(Fore.RED + f"[{content}]" + Fore.RESET)
			response_to_client_user = content
		else:
			print(Fore.CYAN+f"Response from Microservice S3:"+ Fore.RESET)
			print(Fore.RED + f"[{content}]" + Fore.RESET)

			response_to_client_user = f"Error Delete Device {sensorDevice_model}"
	"""
	if code != 200:
		print(Fore.BLUE + f" STEP-4/6 -> Pass on next step" + Fore.RESET)
		print(Fore.BLUE + f" STEP-5/6 -> Pass on next step" + Fore.RESET)
		print(Fore.BLUE + f" STEP-6/6 -> Response to client-utent" + Fore.RESET)

		return jsonify({"Response": response_to_client_user})
	"""


	######## prepare request to send ServiceDB    ############
	print(Fore.BLUE + f" STEP-4/6 -> Prepare Request to Microservice DB" + Fore.RESET)

	data = {'table_name': sensorDevice_model } 
	
	url_destination_DB = utility_Obj.getUrl_Connect_DB() + utility_Obj.getUrl_DeleteTable_DB()
	
	response_from_DB = requests.delete(url_destination_DB,  data = data, headers= header)


	#########----  handler response
	print(Fore.BLUE + f" STEP-5/6 -> Manage Response obtained from Microservice DB" + Fore.RESET)

	code = response_from_DB.status_code
	headers = response_from_DB.headers
	content_type = headers.get('Content-Type')
	content_json = None
	response_to_client_user = ""

	if content_type == "application/json":
		content_json = response_from_DB.json()
		if code == 200:
			content = content_json.get("Response")
			print(Fore.MAGENTA+f" Response from Microservice DB:"+ Fore.RESET)
			print(Fore.GREEN + f"[{content}]" + Fore.RESET)

			response_to_client_user = "Success Delete Device"

		elif code == 707 or code == 606:
			content = content_json.get("Response")
			print(Fore.MAGENTA+f" Response from Microservice DB:"+ Fore.RESET)
			print(Fore.RED + f"[{content}]" + Fore.RESET)



			response_to_client_user = re.sub("Resource","Device",content, flags= re.IGNORECASE)

		else:
			content = content_json.get("Response")
			print(Fore.MAGENTA+f" Response from Microservice DB:"+ Fore.RESET)
			print(Fore.RED + f"[{content}]" + Fore.RESET)

			response_to_client_user = f"Error Delete Device {sensorDevice_model}"
	
	print(Fore.BLUE + f" STEP-6/6 -> Response to client-utent" + Fore.RESET)

	return jsonify({"Response": response_to_client_user})




## TESTATO
@app.route('/delete_SensorDataSheet', methods=['DELETE']) #---> call delete_Object of S3
def delete_SensorDataSheet():
	print("delete_SensorDataSheet")
	
	message_n = ""
	message_t = ""
	message_c = ""
	message_b = ""

	args = request.values
	dataSheet_name = args.get('dataSheet_name')
	dataSheet_fileType = args.get('dataSheet_fileType')
	dataSheet_category = args.get('dataSheet_category')

	bucket = app.config['BUCKET_DATA_SHEET']

	#print(dataSheet_name,dataSheet_fileType,dataSheet_category)
	print(Fore.BLUE + f" STEP-1/4 -> Check forms value" + Fore.RESET)



	if dataSheet_name is None or dataSheet_name == "":
		dataSheet_name = None
		message_n = "Required <dataSheet_name>"
	else:
		message_n = dataSheet_name

	if dataSheet_fileType is None or dataSheet_fileType == "":
		dataSheet_fileType = None
		message_t = "Required <dataSheet_fileType>"
	else:
		message_t = dataSheet_fileType

	if dataSheet_category is None or dataSheet_category == "":
		dataSheet_category = None
		message_c = "Required <dataSheet_category>"
	else:
		message_c = dataSheet_category


	if bucket is None or dataSheet_fileType is None or dataSheet_name is None or dataSheet_category is None:
		print(Fore.RED + f"Error compile form" + Fore.RESET)
		print(Fore.BLUE + f" STEP-2/4 -> Skip on next STEP-4" + Fore.RESET)
		print(Fore.BLUE + f" STEP-4/4 -> Send Error Response to client-utent" + Fore.RESET)
		data = jsonify({"Response":{"dataSheet_category": message_c, "dataSheet_name":message_n, "dataSheet_fileType": message_t}})
		response = make_response(data, 707)
		response.headers['Content-Type']= 'application/json'
		return response

	else:
		# tutti i campi sono presenti
		#print(Fore.GREEN + f"Correct compile files form" + Fore.RESET)
		message_n = None

		if dataSheet_fileType == 'text':
			utility_Obj.setExt(".txt")
			response_object_name = utility_Obj.allowed_file_type(dataSheet_name, "check_obj")
			if response_object_name is False:
				message_n = "Uncorrect extension dataSheet_name, it must be (.txt)"

				#return jsonify({"Action":"Delete","from_bucket": bucket,"Category": message_c, "DataSheet_name":message_n, "dataSheet_fileType": message_t})
			else:
				#message_n = response_object_name
				dataSheet_name = response_object_name

		elif dataSheet_fileType == 'word':

			utility_Obj.setExt(".docx")
			response_object_name = utility_Obj.allowed_file_type(dataSheet_name, "check_obj")
			if response_object_name is False:
				message_n = "Uncorrect extension dataSheet_name, it must be (.docx)"
				#return jsonify({"Action":"Delete","from_bucket": bucket, "Category": message_c, "DataSheet_name":message_n, "dataSheet_fileType": message_t})

			else:
				#message_n = response_object_name
				dataSheet_name = response_object_name

		elif dataSheet_fileType == 'pdf':
			utility_Obj.setExt(".pdf")
			response_object_name = utility_Obj.allowed_file_type(dataSheet_name, "check_obj")
			if response_object_name is False:
				message_n = "Uncorrect extension dataSheet_name, it must be (.pdf)"
				#return jsonify({"Action":"Delete","from_bucket": bucket, "Category": message_c, "DataSheet_name":message_n, "dataSheet_fileType": message_t})

			else:
				#message_n = response_object_name
				dataSheet_name = response_object_name
		else:
			message_n = "Incorrect type, Choose (text || pdf || docx)"

		if message_n is not None:
			print(Fore.RED + f"{message_n}"+ Fore.RESET)
			print(Fore.BLUE + f" STEP-2/4 -> Skip on next STEP-4" + Fore.RESET)
			print(Fore.BLUE + f" STEP-4/4 -> Send Error Response to client-utent" + Fore.RESET)
			data = jsonify({"Response":message_n})
			response = make_response(data, 707)
			response.headers['Content-Type']= 'application/json'
			return response

			#return jsonify({"Action":"Delete","from_bucket": bucket, "Category": message_c, "DataSheet_name":message_n, "dataSheet_fileType": message_t})
		print(Fore.GREEN + f"The form field are correct" + Fore.RESET)
	########## prepare request to send ServiceS3 ############
	print(Fore.BLUE + f" STEP-2/4 -> Send Request DELETE to Microservice S3" + Fore.RESET)

	url_destination_S3 = utility_Obj.getUrl_Connect_S3() + utility_Obj.getUrl_DeleteObject_S3()
	data = {'bucket': bucket, 'folder': dataSheet_category, 'key': dataSheet_name } 
	header = {'ACCEPT': 'application/json'}
	response_from_S3 = requests.delete(url_destination_S3,  data = data, headers= header)
	#########----  handler responses
	print(Fore.BLUE + f" STEP-3/4 -> Manage Response obtained from Microservice S3" + Fore.RESET)
	source = "Microservice S3"
	message_success = f"File [{dataSheet_name}] was successfully deleted."
	message_error = f"Error. File [{dataSheet_name}] was not deleted."
	
	message_response = utility_Obj.handlerResponse(response_from_S3, source, message_success, message_error)
	
	print(Fore.BLUE + f" STEP-4/4 -> Send Response to client-utent" + Fore.RESET)

	data = jsonify({"Response":message_response})
	response = make_response(data)
	response.headers['Content-Type']='application/json'
	return response
	




## TESTATO - OK
@app.route('/get_SensorDataSheet', methods=['GET']) #---> call get_Object of S3
def get_SensorDataSheet():
	print("get_SensorDataSheet")
	
	message_n = ""
	message_t = ""
	message_c = ""
	message_b = ""

	args = request.args
	dataSheet_name = args.get('dataSheet_name')
	dataSheet_fileType = args.get('dataSheet_fileType')
	dataSheet_category = args.get('dataSheet_category')
	bucket = app.config['BUCKET_DATA_SHEET']
	
	utility_Obj.deleteFile_from_server(os.path.join(app.root_path,app.config['DOWNLOAD_FOLDER']),None,True)

	print(Fore.BLUE + f" STEP-1/4 -> Check forms value" + Fore.RESET)
		
	if dataSheet_name is None or dataSheet_name == "":
		dataSheet_name = None
		message_n = "Required <sensor_dataSheet_name>"
	else:
		message_n = dataSheet_name

	if dataSheet_fileType is None or dataSheet_fileType == "":
		dataSheet_fileType = None
		message_t = "Required <dataSheet_fileType>"
	else:
		message_t = dataSheet_fileType

	if dataSheet_category is None or dataSheet_category == "":
		dataSheet_category = None
		message_c = "Required <dataSheet_category>"
	else:
		message_c = dataSheet_category


	if bucket is None or dataSheet_fileType is None or dataSheet_name is None or dataSheet_category is None:
		print(Fore.RED + f"Uncorrect compile form" + Fore.RESET)
		
		return jsonify({"Category": message_c, "DataSheet_name":message_n, "dataSheet_fileType": message_t})
	
	# tutti i campi sono presenti

	# verifica la compatibilità dei tipi
	# if type == text -> estensione <nome_file>.txt
	# if type == pdf -> estensione <nome_file>.pdf
	# if type == word -> estensione <nome_file>.docx
	response_type = None
	if dataSheet_fileType == 'text':
		response_type = utility_Obj.allowed_obj_type(dataSheet_name, 'text')

	elif dataSheet_fileType == 'word':
		response_type = utility_Obj.allowed_obj_type(dataSheet_name, 'word')

	elif dataSheet_fileType == 'pdf':
		response_type = utility_Obj.allowed_obj_type(dataSheet_name, 'pdf')

	else:
		response_type = False

	if response_type is False:
		message = "Uncorrect TYPE. Choose ( text || word || pdf)"
		print(Fore.RED +f"{message}"+ Fore.RESET)
		return jsonify({"Response":message})
		#return jsonify({"Bucket":message_b, "Category": message_c, "dataSheet_name": message_n, "dataSheet_fileType": message_t, "Response": "Uncorrect TYPE ( text || word || pdf)"})

	if response_type is None:
		message = ""
		if type_file == 'pdf':
			message = "Uncorrect extension, it must be ( .pdf)"
			#return jsonify({"Bucket":message_b, "Category": message_c, "dataSheet_name": mmessage_n, "dataSheet_fileType": message_t, "Response": "Uncorrect extension, it must be ( .pdf)"})
		
		elif type_file == 'text':
			message = "Uncorrect extension, it must be ( .txt)"
			#return jsonify({"Bucket":message_b, "Category": message_c, "dataSheet_name": message_n, "dataSheet_fileType": message_t, "Response": "Uncorrect extension, it must be ( .txt)"})
		
		elif type_file == 'word':
			message = "Uncorrect extension, it must be ( .docx)"
			#return jsonify({"Bucket":message1, "Category": message4, "Object_name": message2, "Type_file": message3, "Response": "Uncorrect extension, it must be ( .docx)"})
		else:
			message = "Uncorrect extension. choose ( .pdf || .txt || .docx)"
		print(Fore.RED+ f"{message}" + Fore.RESET)
		return jsonify({"Response":message})

	else:
		dataSheet_name = response_type
		print("New dataSheet_name: ", dataSheet_name )

	####------------------------
	# FORM is correct compiles
	####------------------------
	print(Fore.GREEN + f"Correct compile form"+ Fore.RESET)
	########## prepare request to send ServiceS3 ############

	mimetype = ""

	if dataSheet_fileType == 'text':
		mimetype = 'text/plain'

	if dataSheet_fileType == 'word':
		mimetype = 'application/msword'

	elif dataSheet_fileType == 'pdf':
		mimetype = 'application/pdf'	


	url_destination_S3 = utility_Obj.getUrl_Connect_S3() + utility_Obj.getUrl_GetObject_S3()
	data = {'bucket': bucket, 'folder': dataSheet_category, 'object_name': dataSheet_name , 'type_file':dataSheet_fileType} 
	#header = {'ACCEPT': mimetype}
	header = {
	'Accept':"multipart/form-data",
	'Content-Type':mimetype
	}
	#print("Send requests to Microservice S3", data)
	
	

	local_folder_destination  = os.path.join(app.root_path, app.config['DOWNLOAD_FOLDER'])
	utility_Obj.check_folders(local_folder_destination)
	path_file = os.path.join(app.root_path, app.config['DOWNLOAD_FOLDER'],dataSheet_name)
	###############################################################################
	print(Fore.BLUE + f" STEP-2/4 -> Send Request GET to Microservice S3" + Fore.RESET)

	response_incoming = requests.get(url_destination_S3,  params = data, headers= header)
	####################################################################################

	##---- handler response
	print(Fore.BLUE + f" STEP-3/4 -> Manage Response obtained from Microservice S3" + Fore.RESET)
	
	if response_incoming.status_code == 200:
		print(Fore.GREEN + f"Success in download file, save il local folder"+ Fore.RESET)
		with open(path_file, 'wb') as file:
			file.write(response_incoming.content)

		print(Fore.BLUE + f" STEP-4/4 -> Send File to client-utent" + Fore.RESET)

		response = send_file(path_file, mimetype=mimetype, download_name=dataSheet_name)
		response.headers["x-filename"] = dataSheet_name
		response.headers["Access-Control-Expose-Headers"] = 'x-filename'
		return response


	else:
		print(Fore.RED + f"Falled in download file"+ Fore.RESET)
		print(Fore.BLUE + f" STEP-4/4 -> Send Error Response to client-utent" + Fore.RESET)
		headers = response_incoming.headers
		content_type = headers.get('Content-Type')
		if content_type == "application/json":
			print("Content-Type is: json" )
			content_json = response_incoming.json()
			print(f"{content_json}")
			response_message = content_json.get("Response")
			code = response_incoming.status_code
			if response_message is not None:
				return jsonify({"Response": response_message, "Code": code})
			else:
				return jsonify({"Response": "Request failed", "Code": code})

		else:
			return jsonify({"Response":"Response not understood"})



## TESTATO OK
@app.route('/get_TemplateDevice', methods=['GET']) #---> call get_Object of S3
def get_TemplateDevice():

	print("get_TemplateDevice")
	#print("Send request to microservice S3 to obtain  device_template  by [device_sensor_name]")
	message_d=""
	message_t=""
	bucket = app.config['BUCKET_TEMPLATE']

	utility_Obj.deleteFile_from_server(os.path.join(app.root_path,app.config['DOWNLOAD_FOLDER']),None,True)


	# manage request from client-jax
	print(Fore.BLUE + f" STEP-1/5 -> Check forms value" + Fore.RESET)

	args = request.args
	device_sensor_name = args.get("sensorDevice_model")
	template_fileType = args.get("template_fileType")
	

	if device_sensor_name is None or device_sensor_name == "":
		message_d = "Required <sensorDevice_model>"
		device_sensor_name = None
	else:
		message_d = device_sensor_name

	if template_fileType is None or template_fileType == "":
		template_fileType = None
		message_t = "Required <template_fileType>"
	else:
		message_t = template_fileType

	if device_sensor_name is None or template_fileType is None:

		print(Fore.RED +f"Form filled out incorrectly"+ Fore.RESET)
		print(Fore.BLUE + f" STEP-2/5 -> Skip on step STEP-5" + Fore.RESET)
		print(Fore.BLUE + f" STEP-5/5 -> Send Error Response to client" + Fore.RESET)

		data =  jsonify({"Response":{"sensorDevice_model":message_d ,"template_fileType": message_t}})
		response = make_response(data, 707)
		response.headers['Content-Type'] = 'application/json'
		return response

	response_type = False
	if template_fileType == 'json':
		response_type = utility_Obj.allowed_obj_type(device_sensor_name, 'json')

	if response_type is False:
		print(Fore.RED +f"Form filled out incorrectly"+ Fore.RESET)
		print(Fore.BLUE + f" STEP-2/5 -> Skip on step STEP-5" + Fore.RESET)
		print(Fore.BLUE + f" STEP-5/5 -> Send Error Response to client" + Fore.RESET)

		data = jsonify({"Response": "Uncorrect TYPE: choose ( json)"})
		response = make_response(data, 707)
		response.headers['Content-Type'] = 'application/json'
		return response

	if response_type is None:
		print(Fore.RED +f"Form filled out incorrectly"+ Fore.RESET)
		print(Fore.BLUE + f" STEP-2/5 -> Skip on step STEP-4" + Fore.RESET)
		print(Fore.BLUE + f" STEP-4/5 -> Send Error Response to client" + Fore.RESET)

		data = jsonify({"Response": "Uncorrect nome of sensorDevice_model: insert only name or name with extension ( .json)"})
		response = make_response(data, 707)
		response.headers['Content-Type'] = 'application/json'
		return response

	device_sensor_name = response_type # nome con estensione (sensorDevice_model.json)

	print(Fore.GREEN +f"Form filled out correctly"+ Fore.RESET)

	##### prepare request to send Microservice S3 ####################
	device_sensor_name = f"template-{device_sensor_name}"	 # presenta l'estensione
	
	local_folder_destination  = os.path.join(app.root_path, app.config['DOWNLOAD_FOLDER'])
	utility_Obj.check_folders(local_folder_destination)
	path_file = os.path.join(app.root_path, app.config['DOWNLOAD_FOLDER'],device_sensor_name)
	
	
	print(Fore.BLUE+ f"STEP-2/5 -> Send Request to Microservice S3"+ Fore.RESET)

	url_destination_S3 = utility_Obj.getUrl_Connect_S3() + utility_Obj.getUrl_GetObject_S3()
	data = {'bucket': bucket, 'object_name': device_sensor_name , 'type_file': template_fileType} 
	header = {
	'Accept':"multipart/form-data",
	'Content-Type':"application/json"
	}

	response_incoming = requests.get(url_destination_S3,  params = data, headers= header)
	
	print(Fore.BLUE+ f"STEP-3/5 -> Manage Response obtained from Microservice S3 "+ Fore.RESET)


	if response_incoming.status_code == 200:
		print(Fore.GREEN + f" Success. Incoming file. " + Fore.RESET)
		print(Fore.BLUE+ f"STEP-4/5 -> Save file in local folder "+ Fore.RESET)

		with open(path_file, 'wb') as file:
			file.write(response_incoming.content)

		print(Fore.BLUE+ f"STEP-5/5 -> Send file template to client "+ Fore.RESET)

		response_to_client = send_file(path_file, mimetype='application/json', download_name=device_sensor_name)
		response_to_client.headers["x-filename"] = device_sensor_name
		response_to_client.headers["Access-Control-Expose-Headers"] = 'x-filename'
		return response_to_client
		"""
		data = jsonify({"Response": "Success: Save device_template"})
		response = make_response( data, 200)
		response.headers["Content-Type"]= "application/json"
		return response
		"""
	
	else:
		message_resp = ""
		code_resp = ""
		print(Fore.BLUE+ f"STEP-4/5 -> Skip on next STEP-5 "+ Fore.RESET)
		print(Fore.BLUE+ f"STEP-5/5 -> Send Response to client "+ Fore.RESET)

		print(Fore.RED +" Error in Request file."+ Fore.RESET)
		list_headers = response_incoming.headers
		content_type = list_headers.get('Content-Type')
		if content_type == "application/json":
			#print("Content-Type is: json" )
			content_json = response_incoming.json()
			#print(f"{content_json}")
			response_message = content_json.get("Response")
			code = response_incoming.status_code
			print(Fore.CYAN + f"{response_message}"+ Fore.RESET)
			if response_message is not None:
				message_resp = jsonify({"Response": response_message})
				code_resp = code
			else:
				message_resp = jsonify({"response": "Request Failed"})
				code_resp = code

		else:
			print(Fore.CYAN + f"Response not understand "+ Fore.RESET)
			message_resp = jsonify({"Response":"not understand"})
			code_resp = 404

		response = make_response(message_resp, code_resp)
		response.headers['Content-Type'] = 'application/json'
		return response



# NUOVO
@app.route('/store_DataDevice', methods=['POST']) #---> call get_Object of S3
def store_DataDevice():
	print('/store_DataDevice')

	message_d=""
	message_file=""
	bucket = app.config['BUCKET_TEMPLATE']

	
	print(Fore.BLUE + f" STEP-1/8 -> Check forms value" + Fore.RESET)
	
	args = request.values
	sensorDevice_model = args.get("sensorDevice_model")
	sensorDevice_data = None
	

	if sensorDevice_model is None or sensorDevice_model == "":
		message_d = "Required <sensorDevice_model>"
		sensorDevice_model = None
	else:
		message_d = sensorDevice_model

	if request.files and request.files.get('sensorDevice_data') is not None:
		message_file = request.files['sensorDevice_data'].filename
		sensorDevice_data = request.files['sensorDevice_data']
		# controlla l'estensione del file
		if message_file != "":
			resp_bool = utility_Obj.check_file_format(message_file,".json")
			if resp_bool is False:
				message_file = "Error: Uncorrect extension file, choose file (.json)"

				data = jsonify({"Response": {"sensorDevice_model":message_d,"sensorDevice_data":message_file}} )
				response = make_response(data, 707)
				response.headers['Content-Type']= 'application/json'
				return response
		else:
			sensorDevice_data = None
			message_file = "Required file in format (.json) in <sensorDevice_data>"

	
	else:
		message_file = "Required <sensorDevice_data>"


	if sensorDevice_data is None or sensorDevice_model is None:
		print(Fore.RED +f"Form is filled out incorrectly"+ Fore.RESET)
		print(Fore.BLUE + f" STEP-2/8 -> Skip on step STEP-8" + Fore.RESET)
		print(Fore.BLUE + f" STEP-8/8 -> Send Error Response to client" + Fore.RESET)

		data =  jsonify({"Response":{"sensorDevice_model":message_d ,"sensorDevice_data": message_file}})
		response = make_response(data, 707)
		response.headers['Content-Type'] = 'application/json'
		return response


	print(Fore.GREEN +f"Form is filled out correctly"+ Fore.RESET)


	print(Fore.BLUE + f" STEP-2/8 -> Send Request to Microservice S3 to obtain list of fields of Device Template" + Fore.RESET)

	object_name = f"template-{sensorDevice_model}.json"
	bucket = app.config['BUCKET_TEMPLATE']

	url_destination_S3 = utility_Obj.getUrl_Connect_S3() + utility_Obj.getUrl_GetListFieldsTemplate_S3()

	data = {'bucket': bucket, 'object_name': object_name , 'type_file': "json"} 
	header = {
	'Accept':"multipart/form-data",
	'Content-Type':"application/json"
	}
	response = requests.get(url_destination_S3,  params = data, headers= header)
	
	print(Fore.BLUE+ f"STEP-3/8 -> Manage Response obtained from Microservice S3 "+ Fore.RESET)


	content_json = response.json()
	content = content_json.get("Response")
	list_keys_template = content.get("list_all_field_template")
	code = response.status_code
	

	if code != 200:
		
		print(Fore.BLUE+ f"STEP-4/8 -> Skip on next STEP-8" + Fore.RESET)
		print(Fore.BLUE+ f"STEP-5/8 -> Send Error Response to client" + Fore.RESET)
		data =  jsonify({"Response":f"Device [{sensorDevice_model}] is not registered. Please register Device first."})
		response = make_response(data, code)
		response.headers['Content-Type'] = 'application/json'
		return response

	# il dispositivo è registrato
	print(Fore.GREEN +f" Device [{sensorDevice_model}] is registered"+Fore.RESET)
	print(f"List Keys Template: {list_keys_template} " )
	print(type(list_keys_template))
	
	
	print(Fore.BLUE + f" STEP-4/8 -> Save file of sensorDevice_data in local folder" + Fore.RESET)

	destination = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
	secure_file_name = secure_filename(sensorDevice_data.filename)
	utility_Obj.save_file_into_server(sensorDevice_data, destination, secure_file_name)

	pathfile_local = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'],secure_file_name)
	print("Local path: ",pathfile_local)

	#-----------prepare request to MICROSERVICE DB ----------------- 
	print(Fore.BLUE + f" STEP-5/8 -> Send Request POST to Microservice DB (file sensorDevice_data and list_keys_template)" + Fore.RESET)

	# convert list in string -> [a,b,c] -> "a,b,c"
	string_list_keys_template = ",".join(list_keys_template)
	#print(string_list_keys_template)
	f = open(pathfile_local,'rb')
	data = {"list_keys_template": string_list_keys_template , "id_device":sensorDevice_model}
	files = {"data_json": f}
	header = {'ACCEPT': 'application/json'}

	url_destination = utility_Obj.getUrl_Connect_DB() + utility_Obj.getUrl_writeData_DB()

	response_from_DB = requests.post(url_destination, files = files, data = data, headers= header)
	f.close()
	print(Fore.BLUE + f"STEP-6/8 -> Manage Response obtained from Microservice DB"+ Fore.RESET)
	message_success = f"The measurement data was saved correctly"
	message_error = "Error saving measurement data"
	source = "Microservice DB"


	message_to_client = utility_Obj.handlerResponse( response_from_DB, source, message_success, message_error)

	print(Fore.BLUE + f"STEP-7/8 -> Delete file from local folder"+ Fore.RESET)

	utility_Obj.deleteFile_from_server(destination, secure_file_name )

	print(Fore.BLUE + f"STEP-8/8 -> Response to client-utent"+ Fore.RESET)

	return jsonify({"Response": message_to_client})


	
@app.route('/show_DataDevice', methods = ['GET'])
def show_DataDevice():
	print('show_DataDevice')
	#print("Send request to microservice S3 to obtain  device_template  by [device_sensor_name]")
	message_d=""
	message_t=""
	filename = ""
	mimetype = ""
	format_file = "excel"

	args = request.args

	# elimina dal folder tutti i file

	utility_Obj.deleteFile_from_server(os.path.join(app.root_path,app.config['DOWNLOAD_FOLDER']),None,True)
	
	# manage request from client-jax
	print(Fore.BLUE + f"STEP-1/4 -> Check forms value" + Fore.RESET)

	sensorDevice_model = args.get("sensorDevice_model")

	if sensorDevice_model is None or sensorDevice_model =="":
		message_d = "Required <sensorDevice_model>"
		data = jsonify({"Response":message_d})
		return make_response(data, 707)

	attr_1 = args.get("attr_1")
	op_comparison_1 = args.get("op_comparison_1")
	value_1 = args.get("value_1")

	op_conditional = args.get("op_conditional")

	attr_2 = args.get("attr_2")
	op_comparison_2 = args.get("op_comparison_2")
	value_2 = args.get("value_2")
	value_3 = args.get("value_3")


	attr_3 = args.get("attr_3")
	op_comparison_3 = args.get("op_comparison_3")
	value_4 = args.get("value_4")

	op_conditional_2_F = args.get("op_conditional_2_F")

	# clausola 4
	attr_4 = args.get("attr_4")
	op_comparison_4 = args.get("op_comparison_4")
	value_5 = args.get("value_5")
	op_conditional_3_4 = args.get("op_conditional_3_4")



	select = args.get("select")

	filename_csv = args.get("filename_csv")

	format_file = args.get("format_file", default=format_file)

	clause_1 = None
	clause_2 = None
	clause_3 = None
	clause_4 = None


	if attr_1 is not None and op_comparison_1 is not None and value_1 is not None:

		clause_1 = {
		"attribute" : attr_1,
		"op_comparison" : op_comparison_1,
		"values" : [value_1]
		}

	if attr_2 is not None and op_comparison_2 is not None and value_2 is not None and value_3 is not None:

		clause_2 = {
		"attribute" : attr_2,
		"op_comparison" : op_comparison_2,
		"values" : [value_2, value_3]
		}

	if attr_2 is not None and op_comparison_2 is not None and value_2 is not None and value_3 is None:
		clause_2 = {
		"attribute" : attr_2,
		"op_comparison" : op_comparison_2,
		"values" : [value_2]
		}

	if attr_3 is not None and op_comparison_3 is not None and value_4 is not None:
		#print(type(value_4)) # string
		clause_3 = {
		"attribute" : attr_3,
		"op_comparison" : op_comparison_3,
		"values" : [value_4]
		}

	if attr_4 is not None and op_comparison_4 is not None and value_5 is not None:
		#print(type(value_4)) # string
		clause_4 = {
		"attribute" : attr_4,
		"op_comparison" : op_comparison_4,
		"values" : [value_5]
		}




	list_clause_key = []
	list_op_conditional = [] # (lega clausola 1 e 2) # caso QUERY

	list_clause_filter = []
	list_op_conditional_filter = [] # # caso scan (lega clausola 2 con 3)
									# # caso query (lega clausole di altri attributi)

	if clause_1 is not None: # caso QUERY
		list_clause_key.append(clause_1)

		if clause_2 is not None:
			list_clause_key.append(clause_2)

			if op_conditional is not None: # lega 1 e 2
				list_op_conditional.append(op_conditional)
			else:
				list_op_conditional.append("AND")

	else: # caso SCAN
		# HASH non presente usare SCAN,  con filter
		if clause_2 is not None:
			list_clause_filter.append(clause_2)

			if clause_3 is not None:
				if op_conditional_2_F is not None: # lega clausola 2 con 3, # caso SCAN
					list_op_conditional_filter.append(op_conditional_2_F)
				else:
					list_op_conditional_filter.append("AND")

	# indipendentemente se si tratta di query o scan, clausola 3 e 4 va in filter
	if clause_3 is not None:
		list_clause_filter.append(clause_3)

	if clause_4 is not None:
		list_clause_filter.append(clause_4)
		if op_conditional_3_4 is not None:
			list_op_conditional_filter.append(op_conditional_3_4)
		else:
			list_op_conditional_filter.append("AND")



	if select is None:
		select = "" 

	param = None
	url_destination = ""

	if clause_1 is not None: # caso QUERY

		param = {
			"id_device": sensorDevice_model,
			"list_clause_key": list_clause_key,
			"list_op_conditional": list_op_conditional,
			"list_clause_filter": list_clause_filter,
			"list_op_conditional_filter": list_op_conditional_filter, # se si mettono più clausole di altri attributi
			"select": select, # stringa con elementi separati da virgola 
			"format_file":format_file
		}

		print(Fore.BLUE + f"STEP-2/4 -> Send Request to Microservice DB to Exec QUERY" + Fore.RESET)


		url_destination = utility_Obj.getUrl_Connect_DB() + utility_Obj.getUrl_ExecQuery_DB()

	else: # caso SCAN
		param = {
			"id_device": sensorDevice_model,
			#"list_clause_where": list_clause_where,
			#"list_op_conditional": list_op_conditional,
			"list_clause_filter": list_clause_filter,
			"list_op_conditional_filter": list_op_conditional_filter,
			"select": select, # stringa con elementi separati da virgola 
			"format_file":format_file
		}
		print(Fore.BLUE + f"STEP-2/4 -> Send Request to Microservice DB to Exec SCAN" + Fore.RESET)

		url_destination = utility_Obj.getUrl_Connect_DB() + utility_Obj.getUrl_ExecSCAN_DB()


	#------------ SEND REQUEST -------------------
	headers = {'Content-Type':'application/json'}

	response_incoming = requests.get( url= url_destination, json = param, headers = headers)

	#print(response.status_code)
	#print(response.json())

	#content = response.json()
	print(Fore.BLUE + f"STEP-3/4 -> Manage Response obtained from Microservice DB" + Fore.RESET)

	if response_incoming.status_code == 200:

		if format_file == "excel":
			print(Fore.MAGENTA + f"The EXCEL FILE of the QUERY RESULT has been received. Save it."+ Fore.RESET)
			filename = f"result_query_{sensorDevice_model}.xlsx"
			mimetype='application/vnd.ms-excel'

		elif format_file == "csv":
			print(Fore.MAGENTA + f"The CSV FILE of the QUERY RESULT has been received. Save it."+ Fore.RESET)
			filename = f"result_query_{sensorDevice_model}.csv"
			mimetype = 'text/csv'
 
		destination_folder_local = os.path.join(app.root_path, app.config['DOWNLOAD_FOLDER'])
		filename = secure_filename(filename)
		destination_local = os.path.join(destination_folder_local,filename)

		with open(destination_local, 'wb') as file:
			file.write(response_incoming.content)

		print(Fore.BLUE + f"STEP-4/4 -> Send File to client-utent" + Fore.RESET)

		response = send_file(destination_local, mimetype= mimetype, download_name=filename)
		response.headers["x-filename"] = filename
		response.headers["Access-Control-Expose-Headers"] = 'x-filename'
		return response



	else:
		headers = response_incoming.headers
		content_type = headers.get('Content-Type')
		if content_type == "application/json":
			content_json = response_incoming.json()
			response_message = content_json.get("Response")
			print(Fore.MAGENTA + f"Response from Microcervice DB" + Fore.RESET)
			print(Fore.RED + f"{response_message}" + Fore.RESET)

			print(Fore.BLUE + f"STEP-4/4 -> Send Error Response to client-utent" + Fore.RESET)
			response_message = re.sub("resource","Device", response_message, flags=re.IGNORECASE)
			code = response_incoming.status_code
			data = jsonify({"Response": response_message})
			response = make_response(data, code)
			response.headers['Content-Type'] = 'application/json'
			return response
		else:
			return jsonify({"Response":"Error processing the request"})



@app.route('/getFields/<sensorDevice_model>', methods=['GET'])
def getFields(sensorDevice_model):

	sensorDevice_model = sensorDevice_model

	print(Fore.BLUE + f"STEP-1/3 -> Send Request to Microservice S3 to obtain dict of keys_attributes field"+Fore.RESET)

	bucket = app.config['BUCKET_TEMPLATE']
	object_name = f"template-{sensorDevice_model}.json"

	url_destination_S3 = utility_Obj.getUrl_Connect_S3() + utility_Obj.getUrl_GetListFieldsTemplate_S3()

	data = {'bucket': bucket, 'object_name': object_name , 'type_file': "json"} 
	header = {
	'Accept':"multipart/form-data",
	'Content-Type':"application/json"
	}
	response = requests.get(url_destination_S3,  params = data, headers= header)
	
	print(Fore.BLUE+ f"STEP-2/3 -> Manage Response obtained from Microservice S3 "+ Fore.RESET)


	code = response.status_code
	headers = response.headers
	content_type = headers.get('Content-Type')

	if code == 200 and content_type == "application/json":
		content_json = response.json()
		content = content_json.get("Response")
		dict_attributes = content.get("dict_attributes")
		code = response.status_code

		key_partition = dict_attributes.get("key_partition")
		key_sort = dict_attributes.get("key_sort")
		attributes = dict_attributes.get("attributes")

		if key_partition is not None:
			print(f"key_partition: {key_partition}")

		if key_sort is not None:
			print(f"key_sort: {key_sort}")

		if attributes is not None:
			print(f"attributes: {attributes}")

		data = jsonify({"Response": dict_attributes})
		response_to_html = make_response(data, 200)
		response_to_html.headers['Content-Type'] = 'application/json'
		return response_to_html

	else:
		content_json = response.json()
		content = content_json.get("Response")
		data = jsonify({"Response": content})
		response_to_html = make_response(data, code)
		return response_to_html



@app.route('/get_ListDevices', methods=['GET'])
def get_ListDevices():
	print("get_ListDevices")

	print(Fore.BLUE+f"STEP-1/3 -> Send Request to Microservice S3"+ Fore.RESET)

	url_destination = utility_Obj.getUrl_Connect_S3() + utility_Obj.getUrl_ListObject_S3()

	bucket = app.config['BUCKET_TEMPLATE']
	data = {"bucket": bucket, "name_model":"True" }
	header = {'Content-Type':"application/json"}

	response = requests.get( url = url_destination , params = data, headers = header )

	print(Fore.BLUE+f"STEP-2/3 -> Manage Response from Microservice S3"+ Fore.RESET)

	headers = response.headers
	content_type = headers.get('Content-Type')
	code = response.status_code

	list_devices = None
	message =""
	if code == 200 and content_type == "application/json":
		content_json = response.json()
		content = content_json.get("Response")
		if content is not None:
			print(Fore.GREEN + "Success in processing of request" + Fore.RESET )
			list_devices = content
			message = list_devices

			if isinstance(list_devices,list):
				print("LIST of registered Sensor DEVICE Models")
				for el in list_devices:
					print(f" - {el}")

	elif content_type == "application/json":
		content_json = response.json()
		content = content_json.get("Response")
		if content is not None:
			print(Fore.RED + f"Obtain from S3 an error response" + Fore.RESET )
			print(Fore.CYAN + f"{content}"+ Fore.RESET)
			message = f"{content}"

	else:
		print(Fore.RED + f"Response not is understand" + Fore.RESET )
		message = f"Response not is understand"

	print(Fore.BLUE+f"STEP-3/3 -> Send Response to client"+ Fore.RESET)

	data = jsonify({"Response": message})
	response_to_html = make_response(data,code)
	response_to_html.headers['Content-Type'] = 'application/json'
	return response_to_html


@app.route('/get_listSensorCategories', methods=['GET'])
def get_listSensorCategories():
	print("get_listSensorCategories")

	print(Fore.BLUE+f"STEP-1/3 -> Send Request to Microservice S3"+ Fore.RESET)

	url_destination = utility_Obj.getUrl_Connect_S3() + utility_Obj.getUrl_ListCategories_S3()

	bucket = app.config['BUCKET_DATA_SHEET']
	data = {"bucket": bucket}
	header = {'Content-Type':"application/json"}

	response = requests.get( url = url_destination , params = data, headers = header )

	print(Fore.BLUE+f"STEP-2/3 -> Manage Response from Microservice S3"+ Fore.RESET)

	headers = response.headers
	content_type = headers.get('Content-Type')
	code = response.status_code

	list_devices = None
	message =""
	if code == 200 and content_type == "application/json":
		content_json = response.json()
		content = content_json.get("Response")
		if content is not None:
			print(Fore.GREEN + "Success in processing of request" + Fore.RESET )
			list_devices = content
			message = list_devices

			if isinstance(list_devices,list):
				print("LIST of registered Sensor DEVICE Models")
				for el in list_devices:
					print(f" - {el}")

	elif content_type == "application/json":
		content_json = response.json()
		content = content_json.get("Response")
		if content is not None:
			print(Fore.RED + f"Obtain from S3 an error response" + Fore.RESET )
			print(Fore.CYAN + f"{content}"+ Fore.RESET)
			message = f"{content}"

	else:
		print(Fore.RED + f"Response not is understand" + Fore.RESET )
		message = f"Response not is understand"

	print(Fore.BLUE+f"STEP-3/3 -> Send Response to client"+ Fore.RESET)

	data = jsonify({"Response": message})
	response_to_html = make_response(data,code)
	response_to_html.headers['Content-Type'] = 'application/json'
	return response_to_html



@app.route('/get_listDataSheets_of_Category', methods=['GET'])
def get_listDataSheets_of_Category():
	print("get_listDataSheets_of_Category")

	message_c = ""
	args = request.args

	category = args.get("category")
	bucket = app.config['BUCKET_DATA_SHEET'] 

	print(Fore.BLUE + f"STEP-1/3 -> Check forms value" + Fore.RESET)

	if category is None or category == "":
		message_c = "Required <category>"
		print(Fore.RED + "Form is filled out incorrectly" + Fore.RESET)
		data = jsonify({"Response":message_c})
		response = make_response(data, 707)
		response.headers['Content-Type'] = 'application/json'
		return response

	print(Fore.GREEN + "Form is filled out correctly" + Fore.RESET)

	print(Fore.BLUE+f"STEP-2/3 -> Send Request to Microservice S3"+ Fore.RESET)

	url_destination = utility_Obj.getUrl_Connect_S3() + utility_Obj.getUrl_List_Objects_in_Folder_S3()

	bucket = app.config['BUCKET_DATA_SHEET']
	data = {"bucket": bucket, "category":category}
	header = {'Content-Type':"application/json"}

	response = requests.get( url = url_destination , params = data, headers = header )

	print(Fore.BLUE+f"STEP-3/3 -> Manage Response from Microservice S3"+ Fore.RESET)

	headers = response.headers
	content_type = headers.get('Content-Type')
	code = response.status_code

	list_data_sheet = None
	message =""
	if code == 200 and content_type == "application/json":
		content_json = response.json()
		content = content_json.get("Response")
		if content is not None:
			print(Fore.GREEN + "Success in processing of request" + Fore.RESET )
			list_data_sheet = content
			message = list_data_sheet

			if isinstance(list_data_sheet,list):
				print(f"LIST of DataSheets of Category [{category}] ")
				for el in list_data_sheet:
					print(f" - {el}")

	elif content_type == "application/json":
		content_json = response.json()
		content = content_json.get("Response")
		if content is not None:
			print(Fore.RED + f"Obtain from S3 an error response" + Fore.RESET )
			print(Fore.CYAN + f"{content}"+ Fore.RESET)
			message = f"{content}"

	else:
		print(Fore.RED + f"Response not is understand" + Fore.RESET )
		message = f"Response not is understand"

	print(Fore.BLUE+f"STEP-3/3 -> Send Response to client"+ Fore.RESET)

	data = jsonify({"Response": message})
	response_to_client = make_response(data,code)
	response_to_client.headers['Content-Type'] = 'application/json'
	return response_to_client













	




if __name__ == '__main__':
	print("Microservice Gateway")

	print(f"Flask ENV is {app.config['ENV']}")


	utility_Obj = UtilityFunction.getInstance()
	utility_Obj.setRootPath(app.root_path)
	#utility_Obj.setUploadFolder(app.config['UPLOAD_FOLDER'])
	#utility_Obj.setDownloadFolder(app.config['DOWNLOAD_FOLDER'])

	app.run(host='0.0.0.0', port=5001, debug=True)