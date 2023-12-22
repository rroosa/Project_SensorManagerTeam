import boto3
import json, string, random
import sys, getopt
import logging
import botocore
from botocore.exceptions import ClientError
import csv
from environment_config import *
from colorama import Fore, Back, Style
import sys
import os
import time
import glob
import datetime

from boto3 import Session
from botocore.credentials import RefreshableCredentials
from botocore.session import get_session


class UserBotoObj:
	__instance = None

	def __init__(self):

		if UserBotoObj.__instance != None:
			raise Exception("Class singleton")
		else:
			UserBotoObj.__instance = self
			self.assume_role_arn = None
			self.session_name = None
			self.temp_credentials = None

			self.STS_client = boto3.client('sts')
			self.S3_client = boto3.client('s3')

			self.id_Account = os.environ["ID_ACCOUNT_AWS"]
			self.logger = logging.getLogger(__name__)
			self.root_path = None
			self.folder_StaticUpload = None # cartella dove caricare prima i file da essere poi inviati a AWS S3
			self.folder_StaticDownload = None # cartella dove caricare i file che vengono scaricati da AWS S3
			#self.APP_ROOT = os.path.dirname(os.path.abspath(__file__))
			#self.target = os.path.join(self.APP_ROOT, 'static/upload')
			self.extension = None
			


	@staticmethod
	def getInstance():
		if UserBotoObj.__instance == None:
			UserBotoObj()
		return UserBotoObj.__instance

	def setAssume_Role_Arn(self, assume_role_arn):
		self.assume_role_arn = assume_role_arn

	def setRoleSessionName(self, session_name):
		self.session_name = session_name


	def assumeRolewithResourse(self):
		try:
			response = self.STS_client.assume_role(
				RoleArn=self.assume_role_arn, RoleSessionName=self.session_name
			)
			self.temp_credentials = response["Credentials"]
			print(self.temp_credentials)
			print(f"Assumed role {self.assume_role_arn} and got temporary credentials.")
		except ClientError as error:
			print(
				f"Couldn't assume role {self.assume_role_arn}. Here's why: "
				f"{error.response['Error']['Message']}"
				)
			raise

		self.S3_resourse = boto3.resource(
				"s3",
				aws_access_key_id = self.temp_credentials["AccessKeyId"],
				aws_secret_access_key = self.temp_credentials["SecretAccessKey"],
				aws_session_token = self.temp_credentials["SessionToken"],
			)
	def assumeRolewithClient(self):
		try:
			response = self.STS_client.assume_role(
				RoleArn=self.assume_role_arn, RoleSessionName=self.session_name
			)
			self.temp_credentials = response["Credentials"]
			print(self.temp_credentials)
			print(f"Assumed role {self.assume_role_arn} and got temporary credentials.")
		except ClientError as error:
			print(
				f"Couldn't assume role {self.assume_role_arn}. Here's why: "
				f"{error.response['Error']['Message']}"
				)
			raise

		self.S3_client = boto3.client(
				"s3",
				aws_access_key_id = self.temp_credentials["AccessKeyId"],
				aws_secret_access_key = self.temp_credentials["SecretAccessKey"],
				aws_session_token = self.temp_credentials["SessionToken"],
			)
	#-----------------------------------------------
	def session_AssumeRole(self):
		#session = boto3.Session(profile_name ='user2')
		session = boto3.Session()
		self.STS_client = session.client("sts")
		response = self.STS_client.assume_role(
			RoleArn = self.assume_role_arn, RoleSessionName = self.session_name, DurationSeconds= 3000 #DurationSeconds ()
			)
		new_session = boto3.Session(
			aws_access_key_id = response['Credentials']['AccessKeyId'],
			aws_secret_access_key = response['Credentials']['SecretAccessKey'],
			aws_session_token = response['Credentials']['SessionToken']
			)

		self.S3_client = new_session.client('s3')

	#---------------------------------------------

	def sessionWithRefresh(self):

		#session = Session(profile_name = 'user2')
		session = Session()

		def refresh():
			self.STS_client = session.client('sts')
			credentials = self.STS_client.assume_role(
				RoleArn = self.assume_role_arn,
				RoleSessionName= self.session_name,
				DurationSeconds = 3000
				)['Credentials']

			return dict(
					access_key = credentials['AccessKeyId'],
					secret_key = credentials['SecretAccessKey'],
					token = credentials['SessionToken'],
					expiry_time = credentials['Expiration'].isoformat()
				)

		session_credential = RefreshableCredentials.create_from_metadata(
				metadata = refresh(),
				refresh_using = refresh,
				method = 'sts-assume-role'
			)

		s = get_session()
		s._credentials = session_credential
		region = session._session.get_config_variable('region')
		s.set_config_variable('region',region)

		self.S3_client = Session(botocore_session=s).client('s3')











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

	def check_folders(self, folders ):
		print(f"Check if folders [{folders}] exist ...")

		if not os.path.isdir(folders):
			print(f"[ Not exist, create new folders ]")
			os.makedirs(folders)
		else:
			print(f"[ Folders exist ]")

	def allowed_obj_type(self, object_name, type_file):

		#---------------TEXT --> .txt -------------

		if type_file == 'text':
			if "." not in object_name:
				object_name = object_name+'.txt'
				return object_name

			elif ".txt" in object_name and object_name.rsplit('.txt',1)[1] == '':
				print( "Ok extension")
				return object_name
			else:
				return None

		#--------------- WORD --> .docx -----------
		if type_file == 'word':
			if "." not in object_name:
				object_name = object_name +'.docx'
				return object_name

			elif ".docx" in object_name and object_name.rsplit('.docx',1)[1] == '':
				print( "Ok extension")
				return object_name
			else:
				return None

		#------------- PDF --> .pdf  ----------------

		elif type_file == 'pdf':
			if "." not in object_name:
				object_name = object_name + '.pdf'
				return object_name
			elif ".pdf" in object_name and object_name.rsplit('.pdf',1)[1] == '':
				print('Ok extension')
				return object_name
			else:
				return None
		else: 
			return False
	 

	def allowed_obj(self, object_name):
		ALLOWED_EXTS = ['docx',"pdf", "txt"]

		return  "." in object_name and object_name.rsplit('.',1)[1].lower() in ALLOWED_EXTS


	def allowed_file(self, file_name, ext=None):
		#file_name è il nome del file con estensione
		ALLOWED_EXTS = ['docx',"pdf", "txt"]
		
		if "." in file_name and file_name.rsplit('.',1)[1].lower() in ALLOWED_EXTS:
			extension = file_name.rsplit('.',1)[1].lower()
			print("Extract extension ",file_name.rsplit('.',1)[1].lower()) # da file.text.docx -> ottengo [docx]
			if ext is not None:
				# si tratta di file
				self.setExt("."+extension)
				print( self.getExt())
				return True
			else:
				# si tratta di Obj
				if "."+extension == self.getExt():
					return True
				else:
					return False
		else:

			return False

	def allowed_file_type(self, name, ext):
		#file_name è il nome del file con estensione
		#ALLOWED_EXTS = ['docx',"pdf", "txt"]
		# controllare se il file è di tipo pdf o text
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









		"""
			extension = file_name.rsplit('.',1)[1].lower()
			print("Extract extension ",file_name.rsplit('.',1)[1].lower()) # da file.text.docx -> ottengo [docx]
			if ext is not None:
				# si tratta di file
				self.setExt("."+extension)
				print( self.getExt())
				return True
			else:
				# si tratta di Obj
				if "."+extension == self.getExt():
					return True
				else:
					return False
		else:

			return False
		"""


		#return "." in file_name and file_name.rsplit('.',1)[1].lower() in ALLOWED_EXTS

	"""
	def upload_file_in_application(self, path_file, object_name):

		if not os.path.isdir(self.target):
			os.mkdir(self.target)
		else:
			print("Elimina file dalla cartella".format(self.target))
			
			filesD = glob.glob(self.target+'/*')
			for f in filesD:
				try:
					os.remove(f)
				except OSError as e:
					print("Error: %s : %s" % (f, e.strerror))
			
			destination = "/".join([self.target, object_name])
			print ("Accept incoming file: ", object_name)
			print ("Save it to:", destination)
			path_file.save(destination)
    
	"""
	


	def checkValidityCredential(self):
		print(f" Checking the validity of credential....")
		try:
			response = self.STS_client.get_caller_identity()
			print(Fore.GREEN + f"  Credential are valid:"+ Fore.RESET+f"{response}")
		except ClientError as error:
			print(Fore.RED + f"Credential are not valid" + Fore.RESET )

			self.sessionWithRefresh()


	def upload_file_in_S3(self, bucket, file_name_local, object_name, folder = None ):
		#percorso per salvare prima il file nel server Flask
		self.check_folders(os.path.join(self.root_path, self.folder_StaticUpload))
		#timestamp = str(datetime.datetime.now())

		from_path_flask = os.path.join(self.root_path, self.folder_StaticUpload, file_name_local)
		
		print( f" Upload Object [{object_name}] in bucket [{bucket}] S3 ... ")

		self.checkValidityCredential()

		key = ""

		if folder is not None:
			key = f"{folder}/{object_name}"
		else:
			key = object_name

		#print("Key!!!!!!!!!!!",key)

		try:
			response = self.S3_client.upload_file(from_path_flask, bucket, key, ExtraArgs={'ContentType':"application/json"})
			
		except ClientError as error:

			message = error.response['Error']['Message']
			code = error.response['Error']['Code']
			print(Fore.RED + f"Falled upload_file: {message}, Code:{code}"+ Fore.RESET)
			message = f"Un internal error occurent."
			raise SystemExit(message,606)

		except ParamValidationError as error:
			message = "The parameters you provider are incorrect: {}".format(error)
			code = 400
			print(Fore.RED + f"Falled upload_file: {message}, Code:{code}"+ Fore.RESET)
			return message, code
		else:
			message = f"Success: upload_file {key} in bucket {bucket}"
			code = 200
			print(Fore.GREEN + f"{message}, Code:{code}"+ Fore.RESET)

			return message, code

	def download_file_from_S3(self, bucket, folder, object_name):
		#percorso per salvare prima il file nel server flask

		self.check_folders(os.path.join(self.root_path, self.folder_StaticDownload))
		local_dir = os.path.join(self.root_path, self.folder_StaticDownload)
		#timestamp = str(datetime.datetime.now())

		to_path_flask = os.path.join(self.root_path, self.folder_StaticDownload, object_name)
		
		print(f" -> Check validity Credential")

		self.checkValidityCredential()

		key = ""
		if folder is not None:
			key = f"{folder}/{object_name}"
		else:
			key = object_name

		#print(Fore.BLUE +f" Download Object [{key}] from bucket [{bucket}] S3 ..."+ Fore.RESET)


		try:
			self.S3_client.download_file(bucket, key, to_path_flask)
			
			#with open(to_path_flask, 'wb') as f:
			#	self.S3_client.download_fileobj(bucket, object_name,f)

		except ClientError as error:
			print(Fore.RED+f"Download file from bucket S3:", error.response['Error']['Code'],error.response['Error']['Message']+ Fore.RESET)
			mess = error.response['Error']['Message'] # Not Found
			code = error.response['Error']['Code'] # 404
			return (False, mess, code)
		else:
			print(Fore.GREEN + f" Success download file from bucket S3"+ Fore.RESET)	

			return (True , "Success", 200)

	def delete_file_from_s3(self, bucket, object_name):

		self.checkValidityCredential()

		print(f" Delete object {object_name} from bucket {bucket}")
		try:
			
			self.S3_client.delete_object(
					Bucket = bucket,
					Key= object_name
					)
		except ClientError as error:
			print( f" Error delete object from bucket S3 ", error )
			mess = error.response['Error']['Message']
			code = error.response['Error']['Code']
			return mess, code
		except botocore.exceptions.ParamValidationError as error:
			message = f"The parameters you provider are incorrect: {error}".format(error) 
			code = 606
			return message, code
		else:
			return f"Success Delete Object [{object_name}]", 200

	def exampleListObject_in_Bucket(self):
		my_bucket = self.S3_resourse.Bucket('sensor-data-sheet')
		for my_bucket_obj in my_bucket.objects.all():
			print(my_bucket_obj.key)

	def exampleListObject_in_Bucket_with_Session(self):
		bucket = os.environ['BUCKET_DATA_SHEET']
		response = self.S3_client.list_objects_v2(Bucket = bucket)
		lista = response.get('Contents')
		bucket_name = []
		print(f" LIST OF OBJECT in bucket [{bucket}]")
		if lista is not None:
			for element in lista:
				bucket_name.append(element['Key'])
			
			for key in bucket_name:
				print(f" - {key}" )

	def exampleListFolder_in_Bucket_with_Session(self):
		"""
		buckets_list = self.S3_client.list_buckets()
		lista = buckets_list['Buckets']
		for b in lista:
			name = b['Name']
			print(f"{name}")
		"""

		bucket = os.environ['BUCKET_DATA_SHEET']

		folders = self.S3_client.list_objects_v2(Bucket = bucket, Delimiter='/' )
		#print(folders)
		#foldes = bucket.list('','/')
		folder_name = []
		pref = folders.get('CommonPrefixes')
		print(f" LIST of CATEGORY in bucket [{bucket}]")
		if pref is not None:
			for element in folders.get('CommonPrefixes'):
				el = element.get('Prefix')
				el = el.replace("/","")
				folder_name.append(el)
			
			for key in folder_name:
				print(f" - {key}" )




	def exampleListBuckets(self):
		try:
			lista = []
			for bucket in self.S3_resourse.buckets.all():
				print(bucket.name)
				lista.append(bucket.name)
			return lista

		except ClientError as error:
			print(
				f"Couldn't list buckets for the account. Here's why: "
				f"{error.response['Error']['Message']}"
			)
			return False

	#--------------------------------------------
	#	LIST of CATEGORY (subfolders) into bucket
	#---------------------------------------------

	def getListCategories(self, bucket):
		listCategories = []

		try:
			result = self.S3_client.list_objects_v2( Bucket = bucket , Delimiter = '/' )
			#print("RISULTATO RISPOSTA",result)
			#print("COMMON PREFIXES")
			#print("type", type(result.get('CommonPrefixes') ))
			#print(result.get('CommonPrefixes'))
			
			if result.get('CommonPrefixes') is not None:
				
				for categ in result.get('CommonPrefixes'):
					if categ.get('Prefix') is not None:
						listCategories.append(categ.get('Prefix'))
					else:
						return (False, "-")

		except ClientError as error:
			message = error.response['Error']['Message']
			code = error.response['Error']['Code']
			print(Fore.RED + f"Error: {message}. Code [{code}]" + Fore.RESET)
			return (False, message)
		else:
			print(Fore.GREEN + f"Success execution list_categories" + Fore.RESET)
			return (True, listCategories)

	#-------------------------------------------------
	#	LIST of OBJECT into specific Category
	#-------------------------------------------------

	def getObjectIntoCategory( self, bucket, category):
		
		prefix = ""
		if category is not None:
			prefix = f"{category}/"

		listObjects = []

		try:
			result = self.S3_client.list_objects_v2(Bucket = bucket, Delimiter = '/', Prefix = prefix )
			#print(result)
			elements = result.get("Contents") #array
			if elements is not None:
				print(Fore.GREEN +"Any objects exist in bucket " +Fore.RESET)

				for element in elements:
					key = element['Key'] # prefix/object_name
					listObjects.append( key.replace(prefix, ""))
			else:
				print(Fore.RED +"Nothing object exists in bucket" +Fore.RESET)
				return (False, f"Object does not exist")


		except ClientError as error:
			mess = error.response['Errore']['Message']
			code = error.response['Error']['Code']
			print(Fore.RED +f" Error: {mess}, Code: {code}" +Fore.RESET)
			return (code, mess)

		else:
			return (True, listObjects)










		#if object_name is None:
		#	object_name = os.path.basename(path_file)

		#print(f" object_name [{object_name}] ")

		#self.upload_file_in_application(path_file,object_name)
		#return True , f"Success"

		"""
		print(Fore.RED +f" Check if file [{path_file}] exists... ")
		if not os.path.exists(path_file):
			print(f"Couldn't find file")
			return False , f"Couldn't find file"

		else:
		"""
		"""
		try:
			print(f"Upload Object [{object_name}] in bucket [{bucket}] ")
			response = self.S3_client.upload_file(path_file, bucket, object_name)
		except ClientError as error:
			self.logger.error(error)
			return False, f"Error upload_file"
		else:
			return True, f"Success upload_file"
		"""







	
