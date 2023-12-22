import os
import json
import logging
import glob
from colorama import Fore, Back, Style
from werkzeug.utils import secure_filename

class UtilityFunction:
	__instance = None

	def __init__(self):

		if UtilityFunction.__instance != None:
			raise Exception("Class singleton")
		else:
			UtilityFunction.__instance = self
			self.extension = None
			self.root_path = None
			self.folder_StaticUpload = app.config['UPLOAD_FOLDER'] # cartella dove caricare prima i file da essere poi inviati a AWS S3
			self.folder_StaticDownload = app.config['DOWNLOAD_FOLDER']

			############################################
			###			service S3							####
			#self.url_S3 = f"http://localhost:5002"
			self.url_S3 = app.config['CONNECT_S3']
			self.url_uploadObjectInBucket = '/uploadObjectInBucket'
			self.url_registerDevice = '/registerDevice'
			self.url_getObject = '/get_Object'
			self.url_deleteObject = '/delete_Object'
			self.url_listFields = '/get_ListFields'
			self.url_listObjects = '/listObjects'
			self.url_listCategories = '/listCategories'
			self.url_listObjects_in_Folder = '/listObjects'



			######################################
			### 		service DB           #####
			self.url_DB = f"http://localhost:5003"
			self.url_DB = app.config['CONNECT_DB']
			self.url_createTable = '/createTable'
			self.url_deleteTable = '/delete_Table'
			self.url_writeData = '/write_Data'
			self.url_execQuery = '/exec_Query'
			self.url_execScan = '/exec_Scan'


	@staticmethod
	def getInstance():
		if UtilityFunction.__instance == None:
			UtilityFunction()
		return UtilityFunction.__instance

	def getExt(self):
		return self.extension

	def setExt(self, extension):
		self.extension = extension

	def setUploadFolder(self, upload_folder):

		self.folder_StaticUpload = upload_folder

	def setDownloadFolder(self, download_folder):

		self.folder_StaticDownload = download_folder

	def setRootPath(self, root_path):
		self.root_path = root_path

	def getUrl_UploadObject_S3(self):
		return self.url_uploadObjectInBucket

	def getUrl_RegisterDevice(self):
		return self.url_registerDevice

	def getUrl_Check_to_CreateTable(self):
		return self.url_check_to_createTable

	def getUrl_CreateTable(self):
		return self.url_createTable


	def getUrl_DeleteObject_S3(self):
		return self.url_deleteObject

	def getUrl_GetObject_S3(self):
		return self.url_getObject

	def getUrl_GetListFieldsTemplate_S3(self):
		return self.url_listFields

	def getUrl_ListObject_S3(self):
		return self.url_listObjects

	def getUrl_ListCategories_S3(self):
		return self.url_listCategories

	def getUrl_List_Objects_in_Folder_S3(self):
		return self.url_listObjects_in_Folder


	def getUrl_DeleteTable_DB(self):
		return self.url_deleteTable

	def getUrl_writeData_DB(self):
		return self.url_writeData

	def getUrl_ExecQuery_DB(self):
		return self.url_execQuery

	def getUrl_ExecSCAN_DB(self):
		return self.url_execScan


	def getUrl_Connect_S3(self):
		return self.url_S3

	def getUrl_Connect_DB(self):
		return self.url_DB








	def check_file_format(self,filename, extension):
		print( f" Check extention of file ...")

		if extension in filename and  filename.rsplit(extension,1)[1].lower() == '':
			print(Fore.GREEN + f"Ok extension [{filename}] - [{extension}] " + Fore.RESET)
			return True
		else:
			print(Fore.RED + f"Error extension [{filename}] - [{extension}] " + Fore.RESET)
			return False

	def check_folders(self, folders ):
		print(f"Checking if folders [{folders}] exist ...")

		if not os.path.isdir(folders):
			print(f" Not exist, create new folders {folders} ")
			os.makedirs(folders)
		else:
			print(f"Folders {folders} already exist")

	def save_file_into_server(self, path_file, destination, filename):

		self.check_folders(destination)

		path_file_to_server = os.path.join(destination, filename)

		print(f"Save file [{filename}] into folder [{destination}]")
		path_file.save(path_file_to_server)

	def deleteFile_from_server(self, folder, filename, prev=None ):
		if prev is True:
			#elimina il contenuto
			filesD = glob.glob(folder+'/*')
		
			for f in filesD:
				try:
					os.remove(f)
				except OSError as e:
					print("Error: %s : %s" % (f, e.strerror))
			print(Fore.GREEN +"Success Delete files from folder"+Fore.RESET)

		else:
			print(f"Delete file from folder. ..")
			path_file = os.path.join(folder,filename)

			if os.path.isfile(path_file):
				try:
					os.remove(path_file)
				except OSError as e:
					print("Error: %s : %s" % (path_file, e.strerror))
				else:
					print(f"Delete file [{filename}] from server Flask's folder [{folder}]")



	def allowed_file_type(self, name, ext):
		#file_name è il nome del file con estensione
		#ALLOWED_EXTS = ['docx',"pdf", "txt"]
		# controllare se il file è di tipo pdf o text
		print("Checking the file format ...")
		if ext == 'check_file':
	
			if ".txt" in name and name.rsplit('.txt',1)[1].lower() == '':
				print("ok extension (.txt)")
				self.setExt(".txt")
				return True

			elif ".docx" in name and name.rsplit('.docx',1)[1] == '':
				print("ok extension")
				self.setExt(".docx")
				return True

			elif ".pdf" in name and name.rsplit('.pdf',1)[1] == '':
				print("ok extension")
				self.setExt(".pdf")
				return True

			else:
				return False

		elif ext == 'check_obj':
			if "." not in name:
				name = name+self.getExt()
				return name
			else:
				if self.getExt() == ".txt":

					if ".txt" in name and name.rsplit('.txt',1)[1].lower() == '':
						return name
					else:
						return False

				if self.getExt() == ".docx":

					if ".docx" in name and name.rsplit('.docx',1)[1].lower() == '':
						return name
					else:
						return False
				
				elif self.getExt() == ".pdf":

					if ".pdf" in name and name.rsplit('.pdf',1)[1] == '':
						return name
					else:
						return False

	def allowed_obj_type(self, object_name, type_file):

		#---------------TEXT --> .txt -------------

		if type_file == 'text':
			if "." not in object_name:
				object_name = object_name+'.txt'
				return object_name

			elif ".txt" in object_name and object_name.rsplit('.txt',1)[1] == '':
				print( "Ok extension (.txt)")
				return object_name
			else:
				return None

		#--------------- WORD --> .docx -----------
		elif type_file == 'word':
			if "." not in object_name:
				object_name = object_name +'.docx'
				return object_name

			elif ".docx" in object_name and object_name.rsplit('.docx',1)[1] == '':
				print( "Ok extension (.docx)")
				return object_name
			else:
				return None

		#------------- PDF --> .pdf  ----------------

		elif type_file == 'pdf':
			if "." not in object_name:
				object_name = object_name + '.pdf'
				return object_name
			elif ".pdf" in object_name and object_name.rsplit('.pdf',1)[1] == '':
				print('Ok extension (.pdf)')
				return object_name
			else:
				return None

		#------------ JSON --> .json  ----------------

		elif type_file == 'json':
			if "." not in object_name:
				object_name = object_name + '.json'
				return object_name
			elif ".json" in object_name and object_name.rsplit('.json', 1)[1] == '':
				print('Ok extention (.json)')
				return object_name
			else:
				return None
		else: 
			return False



	def handlerResponse(self, response_incoming, source, message_success, message_error):
		colore = ""
		if source == "Microservice S3":
			color = Fore.CYAN
		elif source == "Microservice DB":
			color = Fore.MAGENTA

		 

		code = response_incoming.status_code
		headers = response_incoming.headers

		content_type = headers.get('Content-Type')
		content_json = None

		if content_type == "application/json":

			content_json = response_incoming.json()

			if response_incoming.status_code == 200:
				content = content_json.get("Response")
				print(color+f" Response from {source}:"+ Fore.RESET)
				print(Fore.GREEN + f"{content}" + Fore.RESET)

				message_to_utent = message_success

			elif response_incoming.status_code == 707:
				c_json = response_incoming.json()
				content = c_json.get("Response")
				message_to_utent = content
				print(color+f"Response from {source}:"+ Fore.RESET)
				print(Fore.RED + f"{content}" + Fore.RESET)

				#return jsonify({"Response": message_to_utent })

			elif response_incoming.status_code == 808 or response_incoming.status_code == 606 :
				content_json = response_incoming.json()
				content = content_json.get("Response")
				print(color+f"Response from {source}:"+ Fore.RESET)
				print(Fore.RED + f"{content}" + Fore.RESET)
				
				message_to_utent = content

				#return jsonify({"Response": message_to_utent })

			else:
				content = content_json.get("Response")
				print(color+f" Response from {source}:"+ Fore.RESET)
				print(Fore.RED + f"{content}" + Fore.RESET)

				message_to_utent = message_error

			return message_to_utent

		return "No message."

		# non usato
	def dataField_vs_template(self, filepath_local_data, filepath_local_template):

		list_all_field_data = []
		list_all_field_template = []

		# parse FILE TEMPLATE 
		
		print(f" Parse file template")

		with open(filepath_local_template, 'r') as file_template:
			# returns JSON object as a dictionary
			template = None
			try:
				template = json.load(file_template)
			except json.JSONDecodeError as e:
				#print("Error convert to dictionary ")
				return False , f"Error convert to dictionary: {e} ", 808 
			else:
				#--- controlla se il campo "keys_measures" è presente ed estrai il valore sotto "field"
				
				if 'keys_measures' in template:
					list_keys_obj = template.get('keys_measures')

					for obj in list_keys_obj:
						list_all_field_template.append(obj.get('field'))

				if 'other_measures' in template:
					list_keys_obj = template.get('other_measures')

					for obj in list_keys_obj:
						list_all_field_template.append(obj.get('field'))

		# parse FILE MEASURES 
		
		print(f" Parse file of measures")

		with open(filepath_local_data, 'r') as file_data:
			data = None
			try:
				data = json.load(file_data)
			except json.load(file_template) as e:
				return False , f"Error convert to dictionary: {e} ", 808 
			else:
				obj = data[0]
				#print ("primo oggetto",obj)
				#print(type(obj))
				list_all_field_data = list(obj.keys())

		print(Fore.BLUE + "Fields of template" + Fore.RESET)
		print(list_all_field_template)
		print(Fore.BLUE + "Fields of the measurements file" + Fore.RESET )
		print(list_all_field_data)

		for el in list_all_field_data:
			if el not in list_all_field_template:
				return False, "Error. The fields of the measurements file do not correspond to the template.", 707

		return True, "Success. The fields of the measurements file correspond to the template.", 200















