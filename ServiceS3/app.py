import json
from flask import Flask, request, jsonify, flash, redirect, Response, send_from_directory, send_file, make_response
from werkzeug.utils import secure_filename
from user_botoObj import UserBotoObj
from utility_function import *
import os
from colorama import Fore, Back, Style
import requests


app = Flask(__name__)

app.config['UPLOAD_FOLDER']= 'static/upload'
app.config['DOWNLOAD_FOLDER'] = 'static/download'
#app.config['ASSUME_ROLE_ARN'] = "arn:aws:iam::130680778050:role/demo-role-ab55cf51-1317-48eb-a6ce-2f2ab7530813"
#app.config['SESSION_NAME'] = "AssumeRoleDemoSession"
#app.secret_key = "My Secret key"

@app.route('/', methods=['GET'])
def home():
	print("Microservice for managed S3")
	return jsonify({"home":f"Microservice for managed S3"})

@app.route('/listCategories', methods=['GET'])
def listCategories():
	print("Get list of categories")
	args = request.args
	bucket = args.get('bucket')

	print(Fore.CYAN + f"STEP-1/3 -> Check form values"+Fore.RESET)

	if bucket is None or bucket == "":
		bucket = None
		message1 = "Required <bucket>"

		data = jsonify({"Response":message1})
		response = make_response(data, 707)
		response.headers['Content-Type'] = 'application/json'
		return response

	else:
		message1 = bucket
	print(Fore.CYAN + f"STEP-2/3 -> Obtain list of Categories of Bucket"+Fore.RESET)
	bool_response, resp = user_botoObj.getListCategories( bucket = bucket) # ["sensore pressione/", "sensore temperatura/"]
	
	if bool_response is False:
		#print("Errore bucket ")
		print(Fore.CYAN + f"STEP-3/3 -> Send Error Response to Gateway"+Fore.RESET)
		data = jsonify({"Response": resp})
		response = make_response(data, 606)
		response.headers['Content-Type'] = 'application/json'
		return response

		#return jsonify({"Bucket": message1, "List of categories": "-", "Response": listaFolder_error}) # error

	listaCategories = []
	print(Fore.CYAN + f"STEP-3/3 -> Send Response to Gateway"+Fore.RESET)
	for folder in resp:
		listaCategories.append(folder.replace("/", "")) # ["sensore pressione", "sensore temperatura"]

	data = jsonify({"Response":listaCategories})
	response = make_response(data, 200)
	response.headers['Content-Type'] = 'application/json'
	return response


	#return jsonify({"Bucket": message1, "List of categories": listaCategories})

@app.route('/listObjects', methods=['GET'])
def listObjects():
	print("List Objects in Bucket or in a specific category")
	print(Fore.CYAN + f"STEP-1/3 -> Check form values"+Fore.RESET)
	args = request.args
	category = args.get('category')
	bucket = args.get('bucket')
	name_model = args.get('name_model')

	if category is None or category == "":
		category = None
		message1 = "Category not is present"
	else:
		message1 = category

	if bucket is None or bucket == "":
		bucket = None
		message2 = "Required <bucket>"
	else:
		message2 = bucket

	if  bucket is None:
		print(Fore.RED+ f"Form is not filled out correctly"+Fore.RESET)
		print(Fore.CYAN + f"STEP-2/3 -> Skip on next STEP-3"+Fore.RESET)
		print(Fore.CYAN + f"STEP-3/3 -> Send error Response"+Fore.RESET)

		data = jsonify({"Response":{"bucket":message2,"category": message1}})
		response = make_response(data, 707)
		response.headers["Content-Type"] = "application/json"
		return response 
		#return jsonify({"Bucket": message2, "category": message1})

	print(Fore.CYAN + f"STEP-2/3 -> Obtain list of Objects in Bucket"+Fore.RESET)
	response_bool, listaObject = user_botoObj.getObjectIntoCategory( bucket, category)
	print(Fore.CYAN + f"STEP-3/3 -> Send Response to Gateway"+Fore.RESET)
	if response_bool is True:
		if name_model is not None and name_model == "True":
			list_name_model = []
			for el in listaObject:
				name = el.replace("template-","")
				name = name.replace(".json","")
				list_name_model.append(name)

			listaObject = list_name_model

		
		data = jsonify({"Response": listaObject})
		response = make_response( data ,200 )
		response.headers["Content-Type"] = "application/json"
		return response

	elif response_bool is False:
		#print("Sezione False")
		data = jsonify({"Response": listaObject})
		response = make_response(
				data,606 #" listaObject =" Object is not exist"
			)
		response.headers["Content-Type"] = "application/json"
		return response

		#return jsonify({"Bucket":message2, "category": message1, "Response": listaObject}) # error
	"""
	else:
		data = jsonify({"Response": listaObject})
		response = make_response( data ,response_bool )
		response.headers["Content-Type"] = "application/json"
		return response
	"""

		#return jsonify({"Bucket":message2, "category": message1, "list Objects": listaObject})




@app.route('/getObject', methods=['GET'])
def getObject():
	print("getObject")
	print(os.path.join(app.root_path,app.config['DOWNLOAD_FOLDER']))

	deleteFile(os.path.join(app.root_path,app.config['DOWNLOAD_FOLDER']),True)
	args = request.args
	bucket = args.get('bucket') # nome backet 
	object_name = args.get("object_name") # name object stores in bucket
	type_file = args.get('type') # type of file ( text || pdf  || word)
	category = args.get('category')


	if bucket is None or bucket == "":
		bucket = None
		message1 = "Required <bucket>"
	else:
		message1 = bucket

	if object_name is None or object_name == "":
		object_name = None
		message2 = "Required <object_name>"
	else:
		message2 = object_name

	if type_file is None or type_file == "":
		type_file = None
		message3 = "Required <type_file>"
	else:
		message3 = type_file

	if category is None or category == "":
		category = None
		message4 = "Required <category>"
	else:
		message4 = category

	if bucket is None or object_name is None or type_file is None or category is None:
		return jsonify({"Bucket":message1,"Object_name": message2, "Type_file": message3, "Category":message4})

	# --- tutti e quattro argomenti sono presenti

	# verifica la compatibilità dei tipi
	# if type == text -> estensione <nome_file>.txt
	# if type == pdf -> estensione <nome_file>.pdf
	# if type == word -> estensione <nome_file>.docx
	response_type = None
	if type_file == 'text':
		response_type = user_botoObj.allowed_obj_type(object_name, 'text')

	elif type_file == 'word':
		response_type = user_botoObj.allowed_obj_type(object_name, 'word')

	elif type_file == 'pdf':
		response_type = user_botoObj.allowed_obj_type(object_name, 'pdf')

	else:
		response_type = False

	if response_type is False:
		return jsonify({"Bucket":message1, "Category": message4, "Object_name": message2, "Type_file": message3, "Response": "Uncorrect TYPE ( text || word || pdf)"})

	if response_type is None:
		if type_file == 'pdf':
			return jsonify({"Bucket":message1, "Category": message4, "Object_name": message2, "Type_file": message3, "Response": "Uncorrect extension, it must be( .pdf)"})
		
		elif type_file == 'text':
			return jsonify({"Bucket":message1, "Category": message4, "Object_name": message2, "Type_file": message3, "Response": "Uncorrect extension, it must be ( .txt)"})
		
		elif type_file == 'word':
			return jsonify({"Bucket":message1, "Category": message4, "Object_name": message2, "Type_file": message3, "Response": "Uncorrect extension, it must be ( .docx)"})

	else:
		object_name = response_type
		print("New object_name: ", object_name )
	
	#----------------------------------
	# TEST  CORRECT compile GET
	#return jsonify({"Bucket":message1,"Object_name": message2, "Type_file": message3, "New object_name: ": object_name})
	#-----------------------------

	response_bool, response_mess, local_path_or_None = user_botoObj.download_file_from_S3(bucket, category, object_name)
	print("LOCAL DIR or None:",local_path_or_None)
	print("Message: ",response_mess)
	if response_bool is True:
		#---------------------no----------
		#with open(path_local,'r', encoding = 'utf-8') as f:
		#	lines = f.readlines()
		#	print(lines)

		#return Response(
		#	print(open(path_local).read()),
		#	mimetype = 'application/pdf',
		#	headers = {"Content-Disposition": "attachment:filename={}".format(object_name)}
		#	)
		#----------------------------------
		mimetype = ""
		if type_file == 'text':
			mimetype = 'text/plain'

		if type_file == 'word':
			mimetype = 'application/msword'

		elif type_file == 'pdf':
			mimetype = 'application/pdf'
		#return jsonify({"action":"get","from": bucket,"object_name":object_name, "Response": "Success"})
		#'application/msword'
		
		workingdir = os.path.abspath(os.getcwd())
		filepath = workingdir + '/static/download/'
		#return send_file(filepath+object_name, mimetype='application/msword',as_attachment=True, download_name="output.doc")
		#return send_file("static/download/word1.txt.docx", as_attachment = True)
		
		#-------
		#return send_from_directory(filepath, object_name, as_attachment = False)

		#deleteFile(os.path.join(app.root_path,app.config['DOWNLOAD_FOLDER'],object_name))
		#--------------
		# AGGIUNGERE as_attachment=True se si vuole SCARICARE
		response = send_file(filepath+object_name, mimetype=mimetype, download_name=object_name)
		response.headers["x-filename"] = object_name
		response.headers["Access-Control-Expose-Headers"] = 'x-filename'
		response.headers['Content-Type'] = mimetype
		return response



		#return jsonify({"action":"get","from": bucket,"object_name":object_name, "Response": "Success"})

	else:

		return jsonify({"action":"Get","from": bucket,"object_name":object_name, "Response": f"Falled [{response_mess}]"})

# NUOVO - TESTATO -OK
@app.route('/get_Object', methods=['GET'])
def get_Object():
	print("get_Object")

	print(Fore.CYAN + f" STEP-1/3 -> Check forms value" + Fore.RESET)
		

	deleteFile(os.path.join(app.root_path,app.config['DOWNLOAD_FOLDER']),True)
	args = request.args
	bucket = args.get('bucket') # nome backet 
	object_name = args.get("object_name") # name object stores in bucket
	type_file = args.get('type_file') # type of file ( text || pdf  || word)
	folder = args.get('folder')
	only_pull = args.get('only_pull')
	
	if bucket is None or bucket == "":
		bucket = None
		message1 = "Required <bucket>"
	else:
		message1 = bucket

	if object_name is None or object_name == "":
		object_name = None
		message2 = "Required <object_name>"
	else:
		message2 = object_name

	if type_file is None or type_file == "":
		type_file = None
		message3 = "Required <type_file>"
	else:
		message3 = type_file

	if folder is None or folder == "":
		folder = None
		message4 = "Not present <folder>"
	else:
		message4 = folder

	if bucket is None or object_name is None or type_file is None:
		print(Fore.RED+ f"Uncorrect fields of form"+Fore.RESET)

		print(Fore.CYAN + f" STEP-2/3 -> Skip on next STEP-3" + Fore.RESET)
		print(Fore.CYAN + f" STEP-3/3 -> Send Response to Gateway" + Fore.RESET)
		data = jsonify({"Response":{"Bucket":message1,"Object_name": message2, "Type_file": message3, "Folder":message4}})
		response = make_response( data, 707)
		response.headers['Content-Type'] = 'application/json'
		return response
	# --- tutti e quattro argomenti sono presenti
	##------ CONNECT with AWS S3 to DOWLOAD object in local_path (static/dowload)  ---------------------
	print(Fore.GREEN+ f"Correct fields of form"+Fore.RESET)

	print(Fore.CYAN + f" STEP-2/3 -> Dowload file from Bucket S3 AWS" + Fore.RESET)

	response_bool, response_mess, code = user_botoObj.download_file_from_S3(bucket, folder, object_name)
	print(response_bool,response_mess,code)
	if response_bool is True:

		mimetype = ""
		if type_file == 'text':
			mimetype = 'text/plain'

		if type_file == 'word':
			mimetype = 'application/msword'

		elif type_file == 'pdf':
			mimetype = 'application/pdf'

		elif type_file == 'json':
			mimetype = 'application/json'

		# get file from local_path and return as response to Gateway 
		
		workingdir = os.path.abspath(os.getcwd())
		filepath = workingdir + '/static/download/'

		if only_pull is not None:
			if only_pull is True:
				print(Fore.GREEN + f"Success Dowload file in local from Bucket"+ Fore.RESET)

				data = jsonify({"Response":True})
				response = make_response(data, 200)
				response.headers['Content-Type'] = 'application/json'
				return response




		print(Fore.CYAN + f"STEP-3/3 -> Send OBJECT to GATEWAY as RESPONSE "+ Fore.RESET)
		# AGGIUNGERE as_attachment=True se si vuole SCARICARE
		response = send_file(filepath+object_name, mimetype=mimetype, download_name=object_name)
		response.headers["x-filename"] = object_name
		response.headers["Access-Control-Expose-Headers"] = 'x-filename'
		response.headers["Content-Type"] = 'mimetype'
		return response
	
	else:

		#print(Fore.CYAN + f"STEP-3/3 -> Send ERROR RESPONSE "+ Fore.RESET)

		data = jsonify({"Response": f"File download failed. {response_mess}"})
		response = make_response( data, code)
		response.headers["Content-Type"]= "application/json"
			
		return response





# TESTATO OK
@app.route('/registerDevice', methods=['POST'])
def registerDevice():
	message_t = ""
	message_d = ""
	message_b = ""
	message_type = ""
	device_template = None
	device_sensor_name = None
	bucket = None
	type_file = None
	args = request.values
	

	#--------- SEZIONE REGISTRAZIONE DEL DEVICE ----------
	# Richiesto: [template] (file.json)
	#			 [device_sensor_name] (nome del dispsitivo)
	#-----------------------------------------------------
	#template = args.get('template')
	bucket = args.get('bucket')
	type_file = args.get('type_file')
	device_sensor_name = args.get('device_sensor_name')

	print(Fore.CYAN + f" STEP-1/7 -> Checking the values in the form" + Fore.RESET)


	if device_sensor_name is None or device_sensor_name == "":
		message_d = "Required <device_sensor_name>"
		device_sensor_name = None

	else:
		message_d = device_sensor_name 

	if bucket is None or bucket =="":
		message_b = "Required <bucket>"
		bucket = None
	else:
		message_b = bucket

	if type_file is None or type_file =="":
		message_type = "Required <type_file>"
		type_file = None
	else:
		message_type = type_file



	
	if request.files and request.files.get('device_template') is not None:
		message_t = request.files['device_template'].filename
		device_template = request.files['device_template']
	else:
		message_t = "Required <device_template>"

	if device_template is None or bucket is None or device_sensor_name is None or type_file is None:
		
		print(Fore.RED + f" Error filling out the form" + Fore.RESET)
		
		data = jsonify({"Response":{"device_template": message_t, "device_sensor_name": message_d, "bucket":message_b, "type_file": message_type }})
		response = make_response(data, 707)
		response.headers['Content-Type']= 'application/json'
		return response

	#return jsonify({"Response from": "S3","template_file": message_d, "device_sensor_name": message_t } )

	# -- controlla se è di tipo .json
	print(Fore.CYAN + f"STEP-2/7 -> Check extension of file device_template" + Fore.RESET)

	resp_bool = ckeck_extension(message_t,".json")
	if resp_bool is False:
		print(Fore.RED + f" Error: Uncorrect extension file" + Fore.RESET)

		data = jsonify({"Response":{"device_template":"Uncorrect extension file, choose file (.json)"}})
		response = make_response(data, 707)
		response.headers['Content-Type'] = 'application/json'
		return response
		
		#return jsonify({"device_template": message_t, "device_sensor_name": message_d } )
	
	else:
		# -- save file in server Flask in static/upload
		print(Fore.CYAN + f" STEP-3/7 -> Save file device_template in local folder" + Fore.RESET)

		secure_file_name = secure_filename(device_template.filename)
		print("Security file: ",secure_file_name)
		user_botoObj.check_folders(os.path.join(app.root_path,app.config['UPLOAD_FOLDER']))
		
		local_path = os.path.join(app.root_path,app.config['UPLOAD_FOLDER'],secure_file_name)
		
		device_template.save(local_path)
	
		print(Fore.GREEN+ f"Upload file in Flask [{device_template.filename}] -> Success" + Fore.RESET)

		# -- controlla se nel file json sono presenti tutte le chiavi
		print(Fore.CYAN + f" STEP-4/7 -> Parse JSON file device_template " + Fore.RESET)

		keys = ["sensorDevice_model", "keys" ,"keys_measures", "other_measures"]
		bool_check = check_keys(local_path, keys)
		if bool_check is False:

			print(Fore.RED + f" Error: The fields in the file [{device_template}] do not conform to the device_template " + Fore.RESET)
			
			print(Fore.CYAN + f" STEP-5/7 -> Delete file device_template from local folder" + Fore.RESET)

			deleteFile(os.path.join(app.root_path,app.config['UPLOAD_FOLDER'],secure_file_name))

			print(Fore.CYAN + f" STEP-6/7 -> Skip on next step" + Fore.RESET)

			print(Fore.CYAN + f" STEP-7/7 -> Send Response to Gateway" + Fore.RESET)

			message1 = f" Error: The fields in the file [{device_template}] do not conform to the device_template "
			data = jsonify({"Response":message1})
			response = make_response(data, 808)
			return response
			#return jsonify({"action":"post","in_bucket": bucket,"object_name":device_sensor_name, "Response": "Template does not have the required keys"})


		# -- controlla se device_sensor_name coincide con il valore della chiave "sensorDevice_model" presente nel file
		bool_check, mess = check_field(local_path, "sensorDevice_model", device_sensor_name)
		object_name = ""
		if type_file == "json":
			object_name = f"template-{device_sensor_name}.json"
		
		if bool_check is True:
			print(Fore.GREEN + f"Parse JSON File {device_sensor_name}.json is Correct"+ Fore.RESET)
			
			#-- upload file [template-device_sensore_name] in bucket
			print(Fore.CYAN + f" STEP-5/7 -> UPLOAD Object device_template into Bucket" + Fore.RESET)

			
			mess, code  = user_botoObj.upload_file_in_S3(bucket, secure_file_name, object_name, None )

			print(Fore.CYAN + f" STEP-6/7 -> Delete file device_template from local folder" + Fore.RESET)

			deleteFile(os.path.join(app.root_path,app.config['UPLOAD_FOLDER'],secure_file_name))

			print(Fore.CYAN + f" STEP-7/7 -> Send response to Gateway" + Fore.RESET)


			data = jsonify({"Response": mess})
			response = make_response( data, code)
			response.headers["Content-Type"] = 'application/json'
			return response

		else:
			print(Fore.RED + f"Error parse JSON File {device_sensor_name}.json. {mess}"+ Fore.RESET)
			message = f"Error parse JSON File {device_sensor_name}.json. {mess}"

			print(Fore.CYAN + f" STEP-5/7 -> Delete file device_template from local folder" + Fore.RESET)
			deleteFile(os.path.join(app.root_path,app.config['UPLOAD_FOLDER'],secure_file_name))
			
			print(Fore.CYAN + f" STEP-6/7 -> Skip on next step" + Fore.RESET)

			print(Fore.CYAN + f" STEP-7/7 -> Send response to Gateway" + Fore.RESET)

			data = jsonify({"Response": message})
			response = make_response( data, 808)
			response.headers['Content-Type'] = 'application/json'

			return response


			#return jsonify({"filename":secure_file_name,"Object_name": object_name, "Bucket": bucket, "Response": mess})
			


@app.route('/postObject', methods=['POST'])
def putObject():
	print("postObject")
	message1 = ""
	message2 = ""
	message3 = ""

	args = request.values

	#-----------------------------------------------------

	bucket = args.get("bucket")
	print("Bucket ", bucket)

	category = args.get("category")
	path_file = None
	#print(request.files)#MultiDict



	if request.files and request.files.get('path_file') is not None:
		print(request.files['path_file'])
		path_file = request.files['path_file']
		print("File name", path_file.filename)

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

		return jsonify({"Message <path_file>": message1, "Message <bucket>":message2, "Message <category>": messag3})

	
		#redirect(request.url, 302, Response(jsonify({"Message": message})))
		#---------------------------------------

	object_name = args.get('object_name') # nome dell'oggetto (con estensione)

	if path_file and user_botoObj.allowed_file_type(path_file.filename, "check_file"):
		# estensione del file è corretto 

		print("Nome file: ", path_file.filename )
		secure_file_name = secure_filename(path_file.filename)
		print("Security file: ",secure_file_name)
		if object_name is None:
			object_name = secure_file_name
		#  se object name è presente, controlla se rispetta le estensioni compatibile con il file
		else:
			response_type = user_botoObj.allowed_file_type(object_name,"check_obj" )
			if response_type is False:
				if user_botoObj.getExt() == '.pdf':
					return jsonify({"filename":message1,"Object_name": object_name, "category": category,"Bucket": message2, "Response": "Uncorrect extension object (.pdf)"})
				
				elif user_botoObj.getExt() == '.txt':
					return jsonify({"filename":message1,"Object_name": object_name, "category": category,"Bucket": message2, "Response": "Uncorrect extension object (.txt)"})


				elif user_botoObj.getExt() == '.docx':
					return jsonify({"filename":message1,"Object_name": object_name, "category": category,"Bucket": message2, "Response": "Uncorrect extension object (.docx)"})

			else:
				object_name = response_type
		#-----------------------------
		#	TEST CORRECT compile POST
		#return jsonify({"filename":message1,"Object_name": object_name, "Bucket": message2, "Response": "Correct POST"})
		#
		#-------------------------
		user_botoObj.check_folders(os.path.join(app.root_path,app.config['UPLOAD_FOLDER']))
		
		path_file.save(os.path.join(app.root_path,app.config['UPLOAD_FOLDER'],secure_file_name))
		
		print(f"Upload file in Flask [{path_file.filename}] -> Success")


		mess, code  = user_botoObj.upload_file_in_S3(bucket, secure_file_name, object_name, category )

		deleteFile(os.path.join(app.root_path,app.config['UPLOAD_FOLDER'],secure_file_name))

		data = jsonify({"Response", mess})
		response = make_response( data, code)
		response.headers["Content-Type"]= 'application/json'
		return response

	else:

		 
		return jsonify({"filename":message1,"Object_name": object_name, "Bucket": message2, "Response": "Choose file type with extension [text (.txt) ||  word (.docx ) || pdf (.pdf )]"})
		

		#print(f"Upload file [{path_file.filename}] -> Falled")
		#return jsonify({"action":"post","file_name":path_file.filename, "Response": "EXTENSION file not is allow"})



@app.route('/deleteObject', methods=['DELETE'])
def deleteObject():
	print("deleteObject")
	args = request.values
	bucket = args.get('bucket')
	object_name = args.get('object_name')
	object_type = args.get('object_type')
	category = args.get('category')

	if bucket is None or bucket == "":
		bucket =None
		message1 = "Required <bucket>"
	else:
		message1 = bucket

	if object_name is None or object_name == "":
		object_name = None
		message2 = "Required <object_name>"
	else:
		message2 = object_name

	if object_type is None or object_type == "":
		object_type = None
		message3 = "Required <object_type>"
	else:
		message3 = object_type

	if category is None or category == "":
		category = None
		message4 = "Required <category>"
	else:
		message4 = category

	if bucket is None or object_name is None or object_type is None or category is None:

		return jsonify({"action":"delete","from_bucket": message1, "category": message4, "object_name":message2, "object_type": message3})
	else:
		# tutti i campi sono presenti
		if object_type == 'text':
			user_botoObj.setExt(".txt")
			response_object_name = user_botoObj.allowed_file_type(object_name, "check_obj")
			if response_object_name is False:
				message2 = "Uncorrect extension object_name, it must be (.txt)"
				return jsonify({"action":"delete","from_bucket": message1,"category": message4, "object_name":message2, "object_type": message3})

			else:
				message2 = response_object_name
				object_name = response_object_name

		elif object_type == 'word':
			user_botoObj.setExt(".docx")
			response_object_name = user_botoObj.allowed_file_type(object_name, "check_obj")
			if response_object_name is False:
				message2 = "Uncorrect extension object_name, it must be (.docx)"
				return jsonify({"action":"delete","from_bucket": message1, "category": message4, "object_name":message2, "object_type": message3})

			else:
				message2 = response_object_name
				object_name = response_object_name
		
		elif object_type == 'pdf':
			user_botoObj.setExt(".pdf")
			response_object_name = user_botoObj.allowed_file_type(object_name, "check_obj")
			if response_object_name is False:
				message2 = "Uncorrect extension object_name, it must be (.pdf)"
				return jsonify({"action":"delete","from_bucket": message1, "category": message4, "object_name":message2, "object_type": message3})

			else:
				message2 = response_object_name
				object_name = response_object_name

		else:
			message3 = "Incorrect type, Choose (text || pdf || docx)"
			return jsonify({"action":"delete","from_bucket": message1, "category": message4, "object_name":message2, "object_type": message3})

		#--------------------------------
		# 		TEST
		#return jsonify({"action":"Delete","from_bucket": message1, "object_name":message2, "object_type": message3})
		#--------------------------------
		key = f"{category}/{object_name}"
		print(key)

		response_s3, code = user_botoObj.delete_file_from_s3(bucket, key)

		
		return make_response(
			jsonify(
				{"action":"Delete","from_bucket": message1, "category":message4, "object_name":message2, "object_type": message3, "Response": response_s3, "Code": code}))

		#else:
		#	return jsonify({"action":"Delete","from_bucket": message1, "category":message4, "object_name":message2, "object_type": message3, "Response": f"Falled -> {response_s3}"})

# NUOVO ----  TESTATO OK
@app.route('/delete_Object',methods=['DELETE'])
def delete_Object():
	print("delete Object")
	message1 = ""
	message2 = ""

	args = request.values
	bucket = args.get('bucket')
	key = args.get('key')
	folder = args.get('folder')
	print(Fore.CYAN + f"STEP-1/4 -> Check form value"+ Fore.RESET)
	if bucket is None or bucket == "":
		bucket = None
		message1 = "Bucket <Required>"
	else:
		message1 = bucket

	if key is None or key == "":
		key = None
		message2 = "Key <Required>"
	else:
		message2 = key

	if folder is None or folder == "":
		folder = None
		message3 = "Folder not present"
	else:
		message3 = folder

	if bucket is None or key is None:
		print(Fore.RED + f"Error: {message1}, {message2}, {message3}"+ Fore.RESET)
		print(Fore.CYAN + f"STEP-2/4 -> Skip on next STEP-4"+ Fore.RESET)
		print(Fore.CYAN + f"STEP-4/4 -> Send Error Response to Gateway"+ Fore.RESET)

		data = jsonify({"Response":{"Key": message2,"Bucket": message1}})
		response = make_response(data, 707)
		response.headers['Content-Type'] = 'application/json'
		return response  # verificato
		
	print(Fore.GREEN + f"Correct compile form: bucket [{bucket}], Key [{key}]"+ Fore.RESET)



	
	#-------------------------------------------
	# verifica se l'oggetto è presente
	#
	#-------------------------------------------
	# prendi tutti gli oggetti nella lista
	print(Fore.CYAN + f"STEP-2/4 -> Check if Object is present into Bucket"+ Fore.RESET)

	response_bool_or_code, message_or_list = user_botoObj.getObjectIntoCategory(bucket, folder)

	if response_bool_or_code is True:
		lista = message_or_list
		# controlla se l'oggetto è presente il lista
		if key in lista:
			print(Fore.GREEN + f"Object [{key}] is present"+ Fore.RESET)
			# prosegui all'eliminazione dell'oggetto
		else:
			print(Fore.RED + f"Object [{key}] not is present"+ Fore.RESET)
			data = jsonify({"Response":f"Object {key}, not is present"})
			print(Fore.CYAN + f"STEP-3/4 -> Skip on next STEP-4"+ Fore.RESET)
			print(Fore.CYAN + f"STEP-4/4 -> Send  Response to Gateway"+ Fore.RESET)

			response = make_response(data, 606)
			response.headers['Content-Type'] = 'application/json'
			return response

	elif response_bool_or_code is False:
		print(Fore.RED + f"Object [{key}] not is present"+ Fore.RESET)
		data = jsonify({"Response":f"Object {key}, not is present"})
		print(Fore.CYAN + f"STEP-3/4 -> Skip on next STEP-4"+ Fore.RESET)
		print(Fore.CYAN + f"STEP-4/4 -> Send Response to Gateway"+ Fore.RESET)
		
		data = jsonify({"Response": message_or_list})
		response = make_response(data, 606)
		response.headers["Content-Type"] = "application/json"
		return response
	else:
		print(Fore.RED + f"Object [{key}] not is present"+ Fore.RESET)
		data = jsonify({"Response":f"Object {key}, not is present"})
		print(Fore.CYAN + f"STEP-3/4 -> Skip on next STEP-4"+ Fore.RESET)
		print(Fore.CYAN + f"STEP-4/4 -> Send Response to Gateway"+ Fore.RESET)
		data = jsonify({"Response": message_or_list})
		response = make_response(data, response_bool_or_code)
		response.headers["Content-Type"] = "application/json"
		return response


	#--- se i campi richiesti sono presenti
	if folder is not None:
		key = f"{folder}/{key}"

	#--- DELETE OBJECT from BUCKET 
	print(Fore.CYAN + f"STEP-3/4 -> Delete Object from Bucket"+ Fore.RESET)

	response_s3, code = user_botoObj.delete_file_from_s3(bucket, key)

	if code == 200:
		print(Fore.GREEN+ f"Success Delete Object [{key}] from bucket [{bucket}]"+Fore.RESET)
	else:
		print(Fore.RED+ f"Falled in Delete Object [{key}] from bucket [{bucket}]"+Fore.RESET)

	print(Fore.CYAN + f"STEP-4/4 -> Send Response to Gateway"+ Fore.RESET)

	data =  jsonify({"Response": response_s3})
	response = make_response( data, code)
	response.headers['Content-Type'] = 'application/json'
	return response



# NUOVO TESTATO ok
@app.route('/uploadObjectInBucket', methods=['POST'])
def uploadObjectInBucket():
	message1 = ""
	message2 = ""
	message3 = ""
	message4 = ""

	args = request.values

	#-----------------------------------------------------
	bucket = args.get("bucket")
	object_name = args.get('object_name')
	folder = args.get('folder')
	path_file = None

	print(Fore.CYAN + f"STEP-1/5 -> Check the form values" + Fore.RESET)


	if request.files and request.files.get('path_file') is not None:
		#print(request.files['path_file'])
		path_file = request.files['path_file']
		#print("File name", path_file.filename)
		message1 = path_file.filename

	else:
		message1 = "Required <path_file>"

	if bucket is None or bucket == "":
		bucket = None
		message2 = "Required <bucket>"
	else:
		message2 = bucket

	if object_name is None or object_name == "":
		object_name = None
		message3 = "Required <object_name>"
	else:
		message3 = object_name

	if folder is None or folder == "":
		folder = None
		message4 = "Folder is not preset"
	else:
		message4 = folder



	if (path_file is None) or (bucket is None) or (object_name is None):
		
		print(Fore.RED + f"Uncorrect the fields of form" + Fore.RESET)
		print(Fore.CYAN + f"STEP-2/5 -> Skip on STEP-5"+ Fore.RESET)
		print(Fore.CYAN + f"STEP-5/5 -> Send Respone to Gateway"+ Fore.RESET)

		message = jsonify({"Response":{"path_file": message1, "bucket":message2, "object_name": message3, "folder": message4}})
		response = make_response(message,707)
		response.headers["Content-Type"]='application/json'
		return response
	else:

		print(Fore.GREEN + f"Correct the fields of form" + Fore.RESET)

		######--------------------------------------------
		###    gestire il file da caricare nel bucket
		###################################################
		# 1) salvare il file nel server Flask in locale
		print(Fore.CYAN + f"STEP-2/5 -> Save file to local folder"+ Fore.RESET)

		secure_file_name = secure_filename(path_file.filename)
		print("Security file: ",secure_file_name)
		user_botoObj.check_folders(os.path.join(app.root_path,app.config['UPLOAD_FOLDER']))
		path_file.save(os.path.join(app.root_path,app.config['UPLOAD_FOLDER'],secure_file_name))
		print(f"Upload file in Flask [{path_file.filename}] -> Success")

		print(Fore.CYAN + f"STEP-3/5 -> Upload File object into Bucket"+ Fore.RESET)

		# 2) caricare l'oggetto nel bucket
		code =""
		mess =""
		try:
			mess, code  = user_botoObj.upload_file_in_S3(bucket, secure_file_name, object_name, folder )
		except SystemExit as error:
			code = error.args[1]
			mess = error.args[0]

		# 2) eliminare l'oggetto dal server Flask 

		print(Fore.CYAN + f"STEP-4/5 -> Delete file from local folder"+ Fore.RESET)

		deleteFile(os.path.join(app.root_path,app.config['UPLOAD_FOLDER'],secure_file_name))

		print(Fore.CYAN + f"STEP-5/5 -> Send Respone to Gateway"+ Fore.RESET)

		data = jsonify({"Response": mess})
		response = make_response( data, code)
		response.headers["Content-Type"]= 'application/json'
		return response
		

		
@app.route('/get_ListFields', methods=['GET'])
def get_ListFields():
	print("get_ListFields")

	#print(Fore.CYAN + f" STEP-1/3 -> Check forms value" + Fore.RESET)
	args = request.args
	bucket = args.get('bucket') # nome backet 
	object_name = args.get("object_name") # name object stores in bucket
	type_file = args.get('type_file') # type of file ( text || pdf  || word || json)
	folder = args.get('folder')
	only_pull = True

	parameters = {'bucket': bucket, 'object_name': object_name , 'type_file': type_file,'folder': folder, 'only_pull':only_pull} 
	header = {
	'Accept':"multipart/form-data",
	'Content-Type':"application/json"
	}
	response_incoming = requests.get( "http://localhost:5002/get_Object", parameters)

	if response_incoming.status_code != 200:
		message_gateway = "" 
		code_g = ""
		#print(Fore.CYAN + f" STEP-3/4 -> Skip on next STEP-4" + Fore.RESET)
		print(Fore.CYAN + f" STEP-3/3 -> Send Error Response to Gateway" + Fore.RESET)
		headers = response_incoming.headers
		content_type = headers.get('Content-Type')
		if content_type == "application/json":
			print("Content-Type is: json" )
			content_json = response_incoming.json()
			#print(f"{content_json}")
			response_message = content_json.get("Response")
			code = response_incoming.status_code
			if response_message is not None:
				message_gateway = jsonify({"Response": response_message})
				code_g = code
			else:
				code_g = code
				message_gateway = jsonify({"Response": "Request failed"})

		else:
			message_gateway = jsonify({"Response":"Response not understood"})
			code_g = code

		response = make_response(message_gateway, code_g)
		response.headers['Content-Type'] = 'application/json'
		return response

	elif response_incoming.status_code == 200:
		print(Fore.CYAN + f" STEP-3/4 -> Read file and collects field values" + Fore.RESET)

		local_path = os.path.join(app.root_path,app.config['DOWNLOAD_FOLDER'],object_name)

		list_keys = ["keys", "other_measures"]
		resp_bool, list_all_field_template, dict_attributes = collect_FieldValues(local_path, list_keys)

		message = ""
		code = ""
		if resp_bool is True:
			print(Fore.GREEN + "Success parse file"+ Fore.RESET)
			message = {"list_all_field_template":list_all_field_template, "dict_attributes":dict_attributes}
			code = 200
		else:
			print(Fore.RED + "Error parse file" + Fore.RESET)
			message = "Error parse template"
			code = 808

		print(Fore.CYAN + f" STEP-4/4-> Send Response" + Fore.RESET)

		data = jsonify({"Response": message})
		response = make_response(data, code)
		response.headers['Content-Type'] = 'application/json'
		return response











	if bucket is None or object_name is None or type_file is None:
		print(Fore.RED+ f"Uncorrect fields of form"+Fore.RESET)

		print(Fore.CYAN + f" STEP-2/3 -> Skip on next STEP-3" + Fore.RESET)
		print(Fore.CYAN + f" STEP-3/3 -> Send Response to Gateway" + Fore.RESET)
		data = jsonify({"Response":{"Bucket":message1,"Object_name": message2, "Type_file": message3, "Folder":message4}})
		response = make_response( data, 707)
		response.headers['Content-Type'] = 'application/json'
		return response
	# --- tutti e quattro argomenti sono presenti







if __name__ == '__main__':
	print("Microservice for managed S3")

	user_botoObj = UserBotoObj.getInstance()
	user_botoObj.setRootPath(app.root_path)
	user_botoObj.setUploadFolder(app.config['UPLOAD_FOLDER'])
	user_botoObj.setDownloadFolder(app.config['DOWNLOAD_FOLDER'])
	user_botoObj.setAssume_Role_Arn(os.environ['ASSUME_ROLE_ARN'])
	user_botoObj.setRoleSessionName(os.environ['SESSION_NAME'])
	#------------------------------------
	"""
	#------RESOURSE
	user_botoObj.assumeRolewithResourse()
	user_botoObj.exampleListObject_in_Bucket()
	#------------------------------------
	#-----CLIENT
	user_botoObj.assumeRolewithClient()
	"""
	#-------------------
	#----- SESSIONE ASSUME ROLE CLIENT ----- --------- 
	#user_botoObj.session_AssumeRole()
	#user_botoObj.exampleListObject_in_Bucket_with_Session()
	#------------------------------------------------------------

	##-------SESSIONE ASSUME ROLE CON REFRASH
	user_botoObj.sessionWithRefresh()
	user_botoObj.exampleListObject_in_Bucket_with_Session()
	user_botoObj.exampleListFolder_in_Bucket_with_Session()


	#user_botoObj.assumeRolewithClient()
	"""
	lista = user_botoObj.exampleListBuckets() # NELLA POLICY VEDERE LA LISTA DI TUTTI I BUCKET NON è PERMESSO
	
	if lista is False:
		print ("Errore assume role")
	else:
		print("Existing buckets:")
		for bucket in lista:
			print(f"[{bucket}]")
	
	"""


	app.run(host='0.0.0.0', port=5002, debug=True)
