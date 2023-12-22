import boto3
import json, string
from botocore.exceptions import ClientError
import sys
import os
import botocore
from environment_config import *
from boto3 import Session
from botocore.credentials import RefreshableCredentials
from botocore.session import get_session
from decimal import Decimal
from colorama import Fore, Back, Style
from werkzeug.utils import secure_filename
from utility_functions import *
import pandas as pd


class DynamoBotoObj:
	__instance = None

	def __init__(self):

		if DynamoBotoObj.__instance != None:
			raise Exception("Class singleton")
		else:
			DynamoBotoObj.__instance = self
			self.assume_role_arn = None
			self.session_name = None
			self.temp_credentials = None

			self.folder_template = None
			self.folder_dataset = None

			self.STS_client = boto3.client('sts')
			self.DB_client = boto3.client('dynamodb')
			self.DB_resource = boto3.resource('dynamodb')

			self.id_Account = os.environ["ID_ACCOUNT_AWS"]

			self.list_AttributeDefinitions = None
			self.list_KeySchema = None 


	@staticmethod
	def getInstance():
		if DynamoBotoObj.__instance == None:
			DynamoBotoObj()
		return DynamoBotoObj.__instance

	def setTemplateFolder(self, folder):
		self.folder_template = folder

	def setDatasetFolder(self, folder):
		self.folder_dataset = folder

	def setAssume_Role_Arn(self, assume_role_arn):
		self.assume_role_arn = assume_role_arn

	def setRoleSessionName(self, session_name):
		self.session_name = session_name



	def sessionWithRefresh(self):

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

		self.DB_client = Session(botocore_session=s).client('dynamodb')
		self.DB_resource = Session(botocore_session=s).resource('dynamodb')



	def parseJsonTemplate( self, file_template, id_device ):

		list_AttributeDefinitions = []
		list_KeySchema = []
		

		list_measures = None
		list_keys = None

		path_file = os.path.join(self.folder_template,file_template)

		with open(path_file) as f:
			# returns JSON object as a dictionary
			data = None
			try:
				data = json.load(f)
			except json.JSONDecodeError as e:
				#print("Error convert to dictionary ")
				return False , f"Error convert to dictionary: {e} ", 808 # verificato
			else:

				#--- controlla se il campo sensorDeviceModel matcha con id_device
				if 'sensorDevice_model' in data:
					print(f"The field [sensorDeviceModel] is present")
					sensorDeviceModel = data.get('sensorDevice_model')
					
					if sensorDeviceModel != id_device:
						message = f"The value in the field [sensorDeviceModel] does not match with [{id_device}]"
						return False, message, 808
				else:
					message = f"The field [sensorDeviceModel] not is present"
					return False, message, 808
				

				#--- controlla se nella sezione di measures e keys, i valori delle chiavi 'field' sono gli stessi
				if 'keys_measures' in data and 'keys' in data:
					list_item = data.get('keys_measures')
					list_attribute = []
					for item in list_item:
						list_attribute.append(item.get('field'))

					list_item2 = data.get('keys')
					list_attribute2 = []
					for item in list_item2:
						list_attribute2.append(item.get('field'))

					if len(list_attribute) == len(list_attribute2):

						for e in list_attribute:
							if e not in list_attribute2:
								return False, f"Error, the items in the fields ('keys') and ('keys_measures') does not match", 808 #verificato
					else:
						return False, f"Error, the number of items in the fields ('keys') and ('keys_measures') does not match ", 808 # verificato


				#--- section MEASURES -> ATTRIBUTE_DEFINITIONS
				if 'keys_measures' in data:
					list_measures = data['keys_measures']
					for obj in list_measures: #{'field': '<name_field>', 'type':' string | number'}
						if 'field' in obj and 'type' in obj:
							Name = obj['field']
							Type = ""
							t = obj['type']
							if t == 'string':
								Type = 'S'
							elif t == 'number':
								Type = 'N'

							if Name != "" and Type != "":

								obj_dict = {'AttributeName': Name, 'AttributeType': Type}
								list_AttributeDefinitions.append(obj_dict)

				#--- section KEYS -> KEY_SCHEMA 
				if 'keys' in data:
					list_keys = data['keys']
					if len(list_keys) == 2:
						# 1- elemento deve essere di tipo partition, il secondo di tipo sort
						first_obj = None
						second_obj = None
						el_first = None
						el_second = None
						if list_keys[0].get('type') == 'partition':
							el_first = 0
							if list_keys[1].get('type') == 'sort':
								el_second = 1
						elif list_keys[1].get('type') == 'partition':
							el_first = 1
							if list_keys[0].get('type') == 'sort':
								el_second = 0
						else:
							return False, f"Error in key type definition, choose ( partition || sort )", 808 #verificato

						if el_first is not None and el_second is not None:

							first_obj = {'AttributeName': list_keys[el_first].get('field'), 'KeyType':'HASH'}
							second_obj = {'AttributeName': list_keys[el_second].get('field'), 'KeyType':'RANGE'}
							list_KeySchema.append(first_obj)
							list_KeySchema.append(second_obj)

						else:
							return False, f"Error in key type definition, choose ( partition || sort )", 808 # verificato

					elif len(list_keys) == 1:

						if list_keys[0].get('type') == 'partition':
							obj = {'AttributeName': list_keys[0].get('field'), 'KeyType':'HASH'}
							list_KeySchema.append(obj)
						else:
							return False, f"Error in key type definition, choose ( partition )",808 # verificato

				if len(list_AttributeDefinitions) != 0 and len(list_KeySchema) !=0:

					print("List_AttributeDefinitions:")
					print(list_AttributeDefinitions)

					print("list_KeySchema")
					print(list_KeySchema)

					self.list_AttributeDefinitions = list_AttributeDefinitions
					self.list_KeySchema = list_KeySchema 

					return True, f"Correct compile template", 200 # verificato

				else:
					return False , f"Uncorrect compile template, the required fields are not present, insert (sensorDevice_model, keys, keys_measures)", 808 #verificato

	#------------------------------------------------------
	##             Create Table
	#--------------------------------------------------------
	def createTable( self, id_device):
		table = None
		#print(f"Creating table {id_device}...")
		try:
			table = self.DB_resource.create_table(

				TableName = id_device,
				KeySchema = self.list_KeySchema,
				AttributeDefinitions = self.list_AttributeDefinitions,
				ProvisionedThroughput = {
					'ReadCapacityUnits': 20, # lettura 1 unita -> 4KB
					'WriteCapacityUnits': 20 # scrittura 1 unita -> 1KB
				}
			)
		except botocore.exceptions.ClientError as error:
			self.list_AttributeDefinitions = None
			self.list_KeySchema = None
			#print(f" Error", error.response['Error']['Message'])
			message = error.response['Error']['Message']
			code = error.response['Error']['Code']
			raise SystemExit(message, 606)
			
		except botocore.exceptions.ParamValidationError as error:

			self.list_AttributeDefinitions = None
			self.list_KeySchema = None
			#print(f" Error", error)
			message = f"The parameters you provider are incorrect: {error}".format(error) # verificato
			code = 606
			return message, code
		except ValueError as e:
			print(Fore.RED+ f"Error in create Table. {e}"+Fore.RESET)
			return "Error in register Table. The name not is correct.",606
		else:
			print(f" Waiting create table {id_device}....")
			table.wait_until_exists() # attendere finchè la tabella non esista
			self.list_AttributeDefinitions = None
			self.list_KeySchema = None
			return f"Success to create table", 200 # verificato


	#--------------------------------------------------------------
	##   		WRITE DATA into TABLE
	#--------------------------------------------------------------
	def writeData(self, id_device, path_dataset_json):

		dataset_item = None
		try:
			with open(path_dataset_json) as file:
				dataset_item = json.load( file, parse_float=Decimal)
		except FileNotFoundError as e:

			mess = f"File [{path_dataset_json.filename}] with data set not found "
			return mess,707

		else:
			dim = len(dataset_item)
			print(f" Write: num [{dim}] data into table [{id_device}] ... ")

			try:
				with self.DB_resource.Table(id_device).batch_writer() as writer:
					for item in dataset_item:
						writer.put_item(Item = item)

			except ClientError as error:
				print(Fore.RED +f" Falled, Couldn't load data into table [{id_device}]"+Fore.RESET)
				mess = error.response['Error']['Message']
				code = error.response['Error']['Code']
				raise SystemExit(mess,606)
				
			else:
				mess = f" Success. Load data into Table [{id_device}]"
				print(Fore.GREEN+f"{mess}"+Fore.RESET)

				return  mess, 200 

	#----------------------------------------------------------------
	## 			DELETE TABLE
	#-----------------------------------------------------------------
	def deleteTable(self, table_name):
		print(f"Delete table [{table_name}] from DynamoDB")
		try:
			resp = self.DB_client.delete_table(
				TableName = table_name
				)
			#print(f"Delete Table [{table_name}] ->  Success")
		except ClientError as error:
			#print(f"Error delete table [{table_name}], {error.response['Error']['Message']}")
			mess = error.response['Error']['Message']
			code = error.response['Error']['Code']
			raise SystemExit(f"Resource [{table_name}] Not found",606)
			#return "Resource Table Not found", code
		except botocore.exceptions.ParamValidationError as error:

			message = f"The parameters you provider are incorrect: {error}".format(error) 
			code = 606
			return message, code
		except ResourceNotFoundException:
			message = f"Error. Resource Not Found"
			code = 606
		else:
			return "Success Delete Table", 200

	#------------------------------------------------------------
	##
	#-----------------------------------------------------------
	def prepare_send_Query(self, id_device, list_clause_where, list_op_conditional, list_clause_filter,list_op_conditional_filter,select):


		keyConditionExpression, filterExpression, expressionAttruibuteValues = prepare_Cond_Att(list_clause_where,list_op_conditional,list_clause_filter,list_op_conditional_filter )
		#print(keyConditionExpression)
		response = None 
		table = None
		consumedCapacity = 0

		try:
			table = self.DB_resource.Table(id_device)
		except ValueError as e:
			print( Fore.RED + f"Error.{e}" + Fore.RESET)
			return f"Error. Table name not is correct. {e}",606
		
		try:
			print(" Query execution ...")
			if filterExpression =="" and select =="":
				response = table.query(
					KeyConditionExpression = keyConditionExpression,
					ExpressionAttributeValues = expressionAttruibuteValues,
					ReturnConsumedCapacity='TOTAL'
					
				)
			elif filterExpression =="" and select !="":
				response = table.query(
					KeyConditionExpression = keyConditionExpression,
					ExpressionAttributeValues = expressionAttruibuteValues,
					ProjectionExpression = select,
					ReturnConsumedCapacity='TOTAL'
					)
			elif select =="":
				response = table.query(
					KeyConditionExpression = keyConditionExpression,
					ExpressionAttributeValues = expressionAttruibuteValues,
					FilterExpression = filterExpression,
					ReturnConsumedCapacity='TOTAL'
					)
			else:
				response = table.query(
					KeyConditionExpression = keyConditionExpression,
					ExpressionAttributeValues = expressionAttruibuteValues,
					FilterExpression = filterExpression,
					ProjectionExpression = select,
					ReturnConsumedCapacity='TOTAL'
					)


		except ClientError as error:
			#print(f"Error delete table [{table_name}], {error.response['Error']['Message']}")
			mess = error.response['Error']['Message']
			code = error.response['Error']['Code']
			print(Fore.RED + f"{mess}, {code}"+ Fore.RESET)
			raise SystemExit(f" Error: in execution of query. {mess}",606)
			#return "Resource Table Not found", code
		except botocore.exceptions.ParamValidationError as error:

			message = f"The parameters you provider are incorrect: {error}".format(error) 
			code = 606
			print(Fore.RED+f"Error.{message}"+Fore.RESET)
			return message, code

		except ValueError as e :
			print(Fore.RED+f" Error set Parameter in Query"+Fore.RESET)
			return  f"Error in processing Query",606

		else:
			print(Fore.GREEN+ f" Success in execution of Query"+ Fore.RESET)
			print(response)
			#print(json.dumps(response.get('Items')))
			print(Fore.YELLOW+ f" Number of elements: {response.get('Count')}"+ Fore.RESET)

			#print(type(json.dumps(response.get('Items'))))

			# convert [dict] -- in --> [dataframe]
			consumedCapacity = response.get('ConsumedCapacity').get('CapacityUnits')

			item_dataFrame = pd.DataFrame.from_dict(response.get('Items') )

			while 'LastEvaluatedKey' in response:

				if filterExpression =="" and select =="":
					response = table.query(
						KeyConditionExpression = keyConditionExpression,
						ExpressionAttributeValues = expressionAttruibuteValues,
						ReturnConsumedCapacity='TOTAL'
						
					)
				elif filterExpression =="" and select !="":
					response = table.query(
						KeyConditionExpression = keyConditionExpression,
						ExpressionAttributeValues = expressionAttruibuteValues,
						ProjectionExpression = select,
						ReturnConsumedCapacity='TOTAL'
						)
				elif select =="":
					response = table.query(
						KeyConditionExpression = keyConditionExpression,
						ExpressionAttributeValues = expressionAttruibuteValues,
						FilterExpression = filterExpression,
						ReturnConsumedCapacity='TOTAL'
						)
				else:
					response = table.query(
						KeyConditionExpression = keyConditionExpression,
						ExpressionAttributeValues = expressionAttruibuteValues,
						FilterExpression = filterExpression,
						ProjectionExpression = select,
						ReturnConsumedCapacity='TOTAL'
						)

				consumedCapacity = consumedCapacity + response.get('ConsumedCapacity').get('CapacityUnits')
				item_dataFrame_2 = pd.DataFrame.from_dict(response.get('Items') )
				try:
					item_dataFrame = pd.concat([item_dataFrame,item_dataFrame_2],ignore_index = True)
					item_dataFrame.reset_index()
				except ValueError as e:
					print(Fore.RED+f"Error: {e}")
					return f" Error: {e}",606


			if select != "":
				select = select.replace(" ","")
				print(select.split(","))
				lista = select.split(",")
				item_dataFrame = item_dataFrame.reindex(columns = lista)
			

			#item_dataFrame.reset_index(drop=True, inplace= True)
			print(Fore.YELLOW + f" DataFrame of itemes" + Fore.RESET)
			print(item_dataFrame)

			# convert [dataframe] -- in --> [json]
			#item_json = item_dataFrame.to_json(orient = 'records')
			#print(item_json)

			# oppure 
			print(Fore.YELLOW + f" TOTAL Consumed Capacity: {consumedCapacity}"+ Fore.RESET)
		
			return item_dataFrame, 200

	def prepare_send_Scan(self, id_device, list_clause_filter, list_op_conditional_filter, select):

		filterExpression, expressionAttruibuteValues = prepare_Filter_Att_Expression( list_clause_filter,list_op_conditional_filter)
		table = None
		response = None 
		consumedCapacity = 0
		try:
			table = self.DB_resource.Table(id_device)
		except ValueError as e:
			print(Fore.RED + f"Error.{e}"+Fore.RESET)
			return f" Error. Table name not is correct. {e}",606
		try:
			print(" SCAN execution ...")
			if filterExpression == "" and select =="":
				response = table.scan(ReturnConsumedCapacity='TOTAL'),


			elif filterExpression == "" and select !="":
				response = table.scan(
					ProjectionExpression = select,
					ReturnConsumedCapacity='TOTAL'
				)
			elif filterExpression != "" and select =="":
				response = table.scan(
					FilterExpression = filterExpression,
					ExpressionAttributeValues = expressionAttruibuteValues,
					ReturnConsumedCapacity='TOTAL'
				)
			else:
				response = table.scan(
					FilterExpression = filterExpression,
					ExpressionAttributeValues = expressionAttruibuteValues,
					ProjectionExpression = select,
					ReturnConsumedCapacity='TOTAL'
				)


		except ClientError as error:
			#print(f"Error delete table [{table_name}], {error.response['Error']['Message']}")
			mess = error.response['Error']['Message']
			code = error.response['Error']['Code']
			print(Fore.RED + f"{mess}, {code}"+ Fore.RESET)
			raise SystemExit(f" Error: in execution of SCAN. {mess}",606)
			#return "Resource Table Not found", code
		except botocore.exceptions.ParamValidationError as error:

			message = f"The parameters you provider are incorrect: {error}".format(error) 
			code = 606
			print(Fore.RED+f" Error.{message}"+Fore.RESET)
			return message, code
		except ValueError as e:
			print(Fore.RED + f" Error in set parameter in Scan.{e}"+Fore.RESET)
			return f"Error in processing Query",606

		else:
			print(Fore.GREEN + f" Success in execution of Scan"+ Fore.RESET)
			print(response)
			#print(json.dumps(response.get('Items')))
			print(Fore.YELLOW + f" Number of elements: {response.get('Count')}"+Fore.RESET)

			#print(type(json.dumps(response.get('Items'))))

			# convert [dict] -- in --> [dataframe]
			consumedCapacity = response.get('ConsumedCapacity').get('CapacityUnits')
			item_dataFrame = pd.DataFrame.from_dict(response.get('Items') )

			while 'LastEvaluatedKey' in response:

				if filterExpression == "" and select =="":
					response = table.scan(
						ExclusiveStartKey = response['LastEvaluatedKey'],
						ReturnConsumedCapacity='TOTAL'
						)

				elif filterExpression == "" and select !="":
					response = table.scan(
						ProjectionExpression = select,
						ExclusiveStartKey = response['LastEvaluatedKey'],
						ReturnConsumedCapacity='TOTAL'
					)
				elif filterExpression != "" and select =="":
					response = table.scan(
						FilterExpression = filterExpression,
						ExpressionAttributeValues = expressionAttruibuteValues,
						ExclusiveStartKey = response['LastEvaluatedKey'],
						ReturnConsumedCapacity='TOTAL'
					)
				else:
					response = table.scan(
						FilterExpression = filterExpression,
						ExpressionAttributeValues = expressionAttruibuteValues,
						ProjectionExpression = select,
						ExclusiveStartKey = response['LastEvaluatedKey'],
						ReturnConsumedCapacity='TOTAL'
					)

				consumedCapacity = consumedCapacity + response.get('ConsumedCapacity').get('CapacityUnits')
				item_dataFrame_2 = pd.DataFrame.from_dict(response.get('Items') )
				try:
					item_dataFrame = pd.concat([item_dataFrame,item_dataFrame_2],ignore_index = True)
					item_dataFrame.reset_index()
				except ValueError as e:
					print(Fore.RED+f"Error: {e}")
					return f"Error: {e}",606




			if select != "":
				select = select.replace(" ","")
				print(select.split(","))
				lista = select.split(",")
				item_dataFrame = item_dataFrame.reindex(columns = lista)
			
			#item_dataFrame.reset_index(drop=True, inplace= True)
			print(item_dataFrame)

			# convert [dataframe] -- in --> [json]
			item_json = item_dataFrame.to_json(orient = 'records')
			print(item_json)

			print(Fore.YELLOW + f" TOTAL Consumed Capacity: {consumedCapacity}" + Fore.RESET)
			return item_dataFrame, 200




































