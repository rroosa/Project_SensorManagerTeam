import boto3
import json, string, random
import sys, getopt
import logging
from botocore.exceptions import ClientError
import csv
from policy import *
from environment_config import *
from colorama import Fore, Back, Style, init
import sys
import os
import time

init(convert=True)

class BotoObj:
	__instance = None

	def __init__(self):

		if BotoObj.__instance != None:
			raise Exception("Class singleton")
		else:
			BotoObj.__instance = self

		self.iam_client = boto3.client('iam')
		self.iam_resource = boto3.resource("iam")
		self.S3_client = boto3.client('s3')
		#self.organization_client = boto3.client('organizations')
		self.S3_client_location = None
		self.logger = logging.getLogger(__name__)

		self.directory_access_key = "Access_keys_users"
		self.id_Account = os.environ["ID_ACCOUNT_AWS"]
		self.prefix_policy_bucket = "policy_bucket-"
		self.prefix_policy_dynamoDB = "policy_dynamoDB-"
		self.prefix_policy_group = "policy_assumeRole-"
		self.prefix_role_assume = "role_assumeRoleUsers-"
		self.user = "user-"

	@staticmethod
	def getInstance():
		if BotoObj.__instance == None:
			BotoObj()
		return BotoObj.__instance

	def progress_bar(self, seconds):
	#Shows a simple progress bar in the command window.
	    for _ in range(seconds):
	    	time.sleep(1)
	    	print(".", end="")
	    	sys.stdout.flush()
	    print()

	"""
	#-----------------------------
	# CREAZIONE DEL BUCKET
	#-----------------------------
	"""
	def createBucket(self, bucket_name, region=None):

		try:
			if region is None:
				print(Fore.RED + f"Creating Bucket: [ {bucket_name}] in region:[ eu-west-3 ] ..."+ Fore.RESET)
				response = self.S3_client.create_bucket(
					Bucket = bucket_name,
					CreateBucketConfiguration = {'LocationConstraint':'eu-west-3'})
				print(response)
			else:
				print(Fore.RED + f"Create Bucket: [{bucket_name}] in region: [ {region}]" + Fore.RESET)
				#self.S3_client_location = boto3.client('s3',region_name = region)
				#location = {'LocationConstraint':region}
				response = self.S3_client.create_bucket(
					Bucket = bucket_name,
					CreateBucketConfiguration = {'LocationConstraint':region} ) 
				print(response)
		except ClientError as error:
			if error.response['Error']['Code'] == 'BucketAlreadyExists':
				#self.logger.exception("Bucket Already Exists")
				print("Bucket already exists ...")

				
			elif error.response['Error']['Code'] ==  'BucketAlreadyOwnedByYou':
				#self.logger.exception("Bucket Already Owned By You")
				print("Bucket Already Owned By You ...")
				
			else:
				print(error)
			return False

		else:
			return True

	"""
	#-----------------------------------------
	# CREAZIONE POLICY R/W relativa al BUCKET
	#-----------------------------------------
	"""
	def createPolicy_Bucket_R_W(self,group_name):

		print(Fore.RED + 'Creating Policy Bucket ...' + Fore.RESET )
		bucket_policy_string = bucket_policy_R_W()

		try:
			policy = self.iam_resource.create_policy(
				PolicyName= self.prefix_policy_bucket + group_name,
				PolicyDocument = bucket_policy_string
				)
			print(f"Create Policy Bucket [ {policy.policy_name} ] -> Success")
			
		except ClientError as error:
			if error.response['Error']['Code'] == 'EntityAlreadyExists':
				print( "Policy already exists...")
				policy_arn = f'arn:aws:iam::{self.id_Account}:policy/'+ self.prefix_policy_bucket + group_name
				return policy_arn
			else:
				self.logger.exception(f"{error.response['Error']['Message']}")
				sys.exit(1)
		else:
			return policy.arn

	"""
	#-------------------------------------------
	#	CREAZIONE POLICY relativa a DYNAMODB
	#-------------------------------------------
	"""
	def createPolicy_DynamoDB(self, group_name):
		print(Fore.RED + 'Creating Policy DynamoDB ...' + Fore.RESET)
		dynamoDB_policy_string = policyDynamoDB()

		try:
			policy = self.iam_resource.create_policy(
				PolicyName = self.prefix_policy_dynamoDB + group_name,
				PolicyDocument = dynamoDB_policy_string
				)
			print(f"Create Policy DynamoDB [ {policy.policy_name} ] -> Success")

		except ClientError as error:
			if error.response['Error']['Code'] == 'EntityAlreadyExists':
				print( "Policy already exists...")
				policy_arn = f'arn:aws:iam::{self.id_Account}:policy/'+ self.prefix_policy_dynamoDB + group_name
				return policy_arn
			else:
				self.logger.exception(f"{error.response['Error']['Message']}")
				sys.exit(1)
		else:
			return policy.arn

	"""
	#------------------------------------------------------------------------------------------------------------
	# CREAZIONE GRUPPO e creazione del Document Policy per la gestione dei buckets e 
	#    			   e creazione del Document Policy per la gestione di DynamoDB
	#------------------------------------------------------------------------------------------------------
	"""
	def createGroup(self,group_name):

		print(Fore.RED + 'Creating Group ...' + Fore.RESET)
		try:
			create_group_response = self.iam_client.create_group(GroupName = group_name)
			print(f" Crate Group [ {group_name} ] -> Success")

		except ClientError as error:
			if error.response['Error']['Code']== 'EntityAlreadyExists':
				print(f'Group [ {group_name} ] already exists... Use the same group')
			else:
				print('Unexpected error occured while creating group... exiting from here',error)
				sys.exit(1)
		else:

			print(Fore.RED + 'Creation of bucket policy managed by the group ' + Fore.RESET)
			#creazione della policy relativa ai buckets (ma non attaccare esplicitamente al bucket)
			policy_s3_arn = self.createPolicy_Bucket_R_W(group_name)
			print(f"s3 Policy arn: [ {policy_s3_arn} ]")

			print(Fore.RED + 'Creation of dynamoDB policy managed by the group ' + Fore.RESET)
			policy_DB_arn = self.createPolicy_DynamoDB(group_name)
			print(f"DB Policy arn: [ {policy_DB_arn} ]")



	"""
	#------------------------------------------------
	#	CREATE DIRECTORY
	#-----------------------------------------------
	"""
	def create_directory(self, path, directory):
		path = path + directory
		if not os.path.exists(path):
			os.mkdir(path)
			print(f"Create directory [ {directory}])")

	"""
	#-----------------------------------------------
	# CREAZIONE CHIAVI DI ACCESSO
	#----------------------------------------------
	"""
	def writeFilecsv(self,user_name, accessKey, path, directory):
		print( Fore.RED + 'Writing file .csv ...' + Fore.RESET)

		header = ['Access key ID','Secret access key']
		data = [accessKey['AccessKeyId'], accessKey['SecretAccessKey']]

		namefile= user_name+'_accessKeys.csv'
		percorso = path+directory+'/'+namefile
		print(percorso)
		with open(percorso, 'w', encoding='UTF8',newline='') as f:
			writer = csv.writer(f)
			writer.writerow(header)
			writer.writerow(data)

		print(f"Wait for write file [ {namefile} ]", end="")
		self.progress_bar(5)

	"""
	#------------------------------------------------
	# CREAZIONE UTENTE
	#------------------------------------------------
	"""
	def createUser(self,user_name):
		"""
			di default un utente ha le chiavi di accesso
		"""
		print( Fore.RED + f'Creating User ...' + Fore.RESET)
		try:
			
			create_user_response = self.iam_resource.create_user(UserName = user_name )
			print(f" Create User [ {user_name} ] -> Success")
			#self.logger.info("Create user %s.", create_user_response.name)
			#print(create_user_response)
		except ClientError as error:
			if error.response['Error']['Code'] == 'EntityAlreadyExists':
				#self.logger.exception("Couldn't create user %s.",user_name)
				print('User already exists... Use other name for user')
				#raise
			else:
				print('Unexpected error occured while creating user... exiting from here')
			
			sys.exit(1) # uscita
		else:

			print(f"Wait for user to be ready.", end="")
			self.progress_bar(10)


		print( Fore.RED + 'Creating Acess Key ...'+ Fore.RESET)
		try:
			user_key = self.iam_client.create_access_key(UserName = user_name)
			print(f"Created access key pair for user [ {user_name} ] -> Success")

		except ClientError as error:
			print(
				f"Couldn't create access keys for user {user.name}. Here's why: "
	            f"{error.response['Error']['Message']}"
	        )
		else:
			self.create_directory( "./", self.directory_access_key )
			self.writeFilecsv(user_name,user_key['AccessKey'], "./", self.directory_access_key  )

			return create_user_response

	"""
	#---------------------------------------------------------
	# OTTENERE UN RUOLO
	#---------------------------------------------------------
	"""
	def getRoleAssumeRoleUser(self,group_name):

		print( Fore.RED + ' Getting role ...' + Fore.RESET)
		try:
			role_name = self.prefix_role_assume + group_name
			response = self.iam_client.get_role(RoleName= role_name)
		except ClientError as error:
			if error.response['Error']['Code'] == 'NoSuchEntity':
				print(f"Role [{role_name}] not exists")
			return False
		else:
			return response

	"""
	#---------------------------------------------------------------
	#	OTTENERE LA LISTA DEGLI ARN delle POLICY attaccate al RUOLO
	#-------------------------------------------------------------
	"""
	def getList_Policy_Arn_of_Role(self, role_name):

		print(Fore.RED + 'Getting list of Policy Arn that are attached to the Role'+Fore.RESET)
		try:
			response = self.iam_client.list_attached_role_policies(
				RoleName = role_name
			)
		except ClientError as error:
			message = error.response['Error']['Message']
			code = error.response['Error']['Code']
			print(f"Error:{message}, Code: {code}")
			return False
		else:
			list_arn = []
			list_attached_policy = response['AttachedPolicies']
			for policy in list_attached_policy:
				list_arn.append(policy['PolicyArn'])

			return list_arn


	"""
	#------------------------------------------------------
	# CREAZIONE RUOLO ASSUME ROLE Users
	#------------------------------------------------------
	"""
	def createRole_AssumeRoleUsers(self, group_name, user_name):

		user_arn = f"arn:aws:iam::{self.id_Account}:user/{user_name}"
		role_name = self.prefix_role_assume + group_name

		policy = assume_role_PolicyDocument(user_arn)
		print( Fore.RED + ' Creating role ...'+ Fore.RESET)
		try:
			role = self.iam_resource.create_role(
				RoleName=role_name,
				AssumeRolePolicyDocument=policy
			)
			print(f"Create role {role.name} -> Success")
		except ClientError as error:
			print(
				f"Couldn't create a role {role_name}. Here's why: "
				f"{error.response['Error']['Message']}"
			)
			sys.exit(1)
		else:
			return role
	"""
	#------------------------------------------------------------
	#	REMOVE ROLE
	#-------------------------------------------------------------
	"""
	def remove_role(self,role_name):
		print(Fore.RED + f"Remove role ..."+Fore.RESET)
		try:
			response = self.iam_client.delete_role(
				RoleName = role_name
			)
			print(f"Remove role {role_name} -> Success")
		except ClientError as error:
			message = error.response['Error']['Message']
			code = error.response['Error']['Code']
			print(f"Couldn't remove role [{role_name}]")
			print(f"Message: {message}, Code:{code}")
			sys.exit(1)




	"""
	#------------------------------------------------------
	#  IS PRESENT GROUP
	#------------------------------------------------------
	"""
	def isPresentGroup(self,group_name):
		print(Fore.RED + 'Check if group exists ...'+ Fore.RESET)
		try:
			group_response = self.iam_client.get_group(
				GroupName = group_name
				)
			print( f"Group [ {group_name} ] exists")
			return True
		except ClientError as error:
			if error.response['Error']['Code'] == 'NoSuchEntity':
				print( f"Group [ {group_name} ] not exists")
			else:
				print("Error...")
			return False

	"""
	#--------------------------------------------------------
	#	ADD bucket permission to Policy
	#--------------------------------------------------------
	"""
	def add_bucket_in_Policy(self,group_name,bucket_name):
		modify = False
		modify_1 = False
		print(Fore.RED +f"Checking if group exists ..."+Fore.RESET)
		try:
			g_response = self.iam_client.get_group(
				GroupName = group_name
				)
			print( f"Group: [{group_name}] is present")

		except ClientError as error:
			print( f"Group [{group_name}] not is exists, ", error)
			sys.exit(1)

		print(f"Checking if bucket exists ...")
		try:
			b_response =self.S3_client.list_buckets()
			buckets = []
			for bucket in b_response['Buckets']:
				buckets.append(bucket['Name'])

			if bucket_name in buckets:
				print( f"Bucket: [{bucket_name}] is present")
			else:
				print( f"Bucket: [{bucket_name}] not is present")
				sys.exit(1)


		except ClientError as error:
			print( "Error", error)
			sys.exit(1)



		policy_name = self.prefix_policy_bucket+group_name
		policy_arn = f"arn:aws:iam::{self.id_Account}:policy/{policy_name}"
		print(Fore.RED + f' Getting policy [{policy_name}] ...'+ Fore.RESET)
		try:
			policy = self.iam_client.get_policy(
				PolicyArn = policy_arn
				)
			#print(policy)
			policyId = policy['Policy']['PolicyId']
			print("Policy Id: ", policyId)
			versionId = policy['Policy']['DefaultVersionId']
			print("Version Id: ", versionId)

			policy_v = self.iam_client.get_policy_version(
				PolicyArn = policy_arn,
				VersionId = versionId
				)
			content_string = json.dumps(policy_v['PolicyVersion']['Document'])
			#print("String")
			#print(type(content_string))
			#print(content_string)

			content_json = policy_v['PolicyVersion']['Document']
			#print("JSON")
			print("Policy Document:")
			print(content_json)
			#policy_Json = policy.default_version.document
			resourse = content_json['Statement'][0]["Resource"]
			effect = content_json['Statement'][0]["Effect"]
			if effect == "Deny":
				content_json['Statement'][0]["Effect"]="Allow"
				content_json['Statement'][0]["Resource"] = [f"arn:aws:s3:::{bucket_name}"]
				modify = True

			else:
				lista = content_json['Statement'][0]["Resource"]
				arn_resourse = f"arn:aws:s3:::{bucket_name}"
				if arn_resourse not in lista:
					lista.append(arn_resourse)
					content_json['Statement'][0]["Resource"]= lista
					modify = True

			resourse_1 = content_json['Statement'][1]["Resource"]
			effect_1 = content_json['Statement'][1]["Effect"]
			if effect_1 == "Deny":
				content_json['Statement'][1]["Effect"]="Allow"
				content_json['Statement'][1]["Resource"] = [f"arn:aws:s3:::{bucket_name}/*"]
				modify_1 = True

			else:
				lista_1 = content_json['Statement'][1]["Resource"]
				arn_resourse_1 = f"arn:aws:s3:::{bucket_name}/*"
				if arn_resourse_1 not in lista_1:
					lista_1.append(arn_resourse_1)
					content_json['Statement'][1]["Resource"]= lista_1
					modify_1 = True
			
			#print("TIPO JSON ")
			#print(type(content_json))
			if modify is True or modify_1 is True:
				print(f"Modify Policy, manage bucket [{bucket_name}] ...")
			
				response = self.iam_client.create_policy_version(
					PolicyArn = policy_arn,
					PolicyDocument = json.dumps(content_json),
					SetAsDefault = True
					)
			
				print(f"Wait to create new version of policy", end="")
				self.progress_bar(10)

				r = self.iam_client.delete_policy_version(
					PolicyArn = policy_arn,
					VersionId = versionId
					)

				print(f"Wait to delete previous version of policy", end="")
				self.progress_bar(10)

				policy_new = self.iam_client.get_policy(
					PolicyArn = policy_arn
				)

				print("Getting the updated Document Policy ...")
				policyId = policy_new['Policy']['PolicyId']
				print("Policy Id:", policyId)
				versionId = policy_new['Policy']['DefaultVersionId']
				print("Version Id", versionId)

				policy_new_v = self.iam_client.get_policy_version(
					PolicyArn = policy_arn,
					VersionId = versionId
				)
				content_string = json.dumps(policy_new_v['PolicyVersion']['Document'])
				print("Document Policy:")
				print(content_string)

			else:
				print(Fore.RED + f" Document Policy already allows to manage the bucket [{bucket_name}]"+ Fore.RESET)



		except ClientError as error:
			print("Error", error)

	"""
	#-------------------------------------------------------------
	#  DETACH BUCKET dal GRUPPO
	#-------------------------------------------------------------
	"""
	def detach_bucket_from_Policy(self,group_name, bucket_name):
		detach = False
		detach_1 = False

		print(f"Checking if group exists ...")
		try:
			g_response = self.iam_client.get_group(
				GroupName = group_name
				)
			print( f"Group: [{group_name}] is present")

		except ClientError as error:
			print( f"Group [{group_name}] not is exists, ", error)
			sys.exit(1)


		print(f"Checking if bucket exists ...")
		try:
			b_response =self.S3_client.list_buckets()
			buckets = []
			for bucket in b_response['Buckets']:
				buckets.append(bucket['Name'])

			if bucket_name in buckets:
				print( f"Bucket: [{bucket_name}] is present")
			else:
				print( f"Bucket: [{bucket_name}] not is present")
				sys.exit(1)


		except ClientError as error:
			print( "Error", error)
			sys.exit(1)

		policy_name = self.prefix_policy_bucket+group_name
		policy_arn = f"arn:aws:iam::{self.id_Account}:policy/{policy_name}"
		print(Fore.RED + f' Getting policy [{policy_name}] ...'+ Fore.RESET)
		try:
			policy = self.iam_client.get_policy(
				PolicyArn = policy_arn
				)
			#print(policy)
			policyId = policy['Policy']['PolicyId']
			print("Policy Id: ", policyId)
			versionId = policy['Policy']['DefaultVersionId']
			print("Version Id: ", versionId)

			policy_v = self.iam_client.get_policy_version(
				PolicyArn = policy_arn,
				VersionId = versionId
				)
			content_string = json.dumps(policy_v['PolicyVersion']['Document'])

			content_json = policy_v['PolicyVersion']['Document']
			print("Policy Document: ")
			print(content_json)

			resourse_list = content_json['Statement'][0]["Resource"]
			resourse_1_list = content_json['Statement'][1]["Resource"]

			arn_resourse = f"arn:aws:s3:::{bucket_name}"
			arn_resourse_1 = f"arn:aws:s3:::{bucket_name}/*"

			if arn_resourse in resourse_list:
				resourse_list.remove(arn_resourse)
				content_json['Statement'][0]["Resource"] = resourse_list
				detach = True

			if arn_resourse_1 in resourse_1_list:
				resourse_1_list.remove(arn_resourse_1)
				content_json['Statement'][1]["Resource"] = resourse_1_list
				detach_1 = True

			if detach is True or detach_1 is True:
				print(f"Modify Policy, detach bucket [{bucket_name}] ...")
			
				response = self.iam_client.create_policy_version(
					PolicyArn = policy_arn,
					PolicyDocument = json.dumps(content_json),
					SetAsDefault = True
					)

				print(f"Wait to create new version of policy", end="")
				self.progress_bar(10)

				r = self.iam_client.delete_policy_version(
					PolicyArn = policy_arn,
					VersionId = versionId
					)

				print(f"Wait to delete previous version of policy", end="")
				self.progress_bar(10)

				policy_new = self.iam_client.get_policy(
					PolicyArn = policy_arn
				)

				print("Getting the updated Document Policy ...")
				policyId = policy_new['Policy']['PolicyId']
				print("Policy Id:", policyId)
				versionId = policy_new['Policy']['DefaultVersionId']
				print("Version Id", versionId)

				policy_new_v = self.iam_client.get_policy_version(
					PolicyArn = policy_arn,
					VersionId = versionId
				)
				content_string = json.dumps(policy_new_v['PolicyVersion']['Document'])
				print("Document Policy:")
				print(content_string)

			else:
				print(Fore.RED + f" Document Policy already denies to manage the bucket [{bucket_name}]"+ Fore.RESET)



		except ClientError as error:
			print("Error", error)


	"""
	#------------------------------------------------------
	# AGGIUNGERE UTENTE AL GRUPPO
	#------------------------------------------------------
	"""
	def addUserToGroup(self, user_name, group_name ):
		print( Fore.RED + ' Adding User to Group ...'+ Fore.RESET)
		try:
			response = self.iam_client.add_user_to_group(
					GroupName = group_name,
					UserName = user_name
				)
			print(f" Wait add user to group", end="")
			self.progress_bar(5)
			print( f" Add user [{user_name}] to group [{group_name}] -> Success")

		except ClientError as error:
			print(f" An arror occured in add user to group")
			print(error)
			sys.exit(1)

		


		"""
			response_get_role = self.getRole(self.prefix_role + "assumeRoleUsers")
			if response_get_role is False:

				user_arn = f"arn:aws:iam::{self.id_Account}:user/{user_name}"
				role_name = self.prefix_role+"assumeRoleUsers"
				
				role = self.createRole(role_name, user_arn)

				# attaccare il ruolo alla policy relativa al bucket gestito dal gruppo
				if group_name == "SensorManagerTeam":
		"""
	"""
	#------------------------------------------------------
	# RIMUOVERE UTENTE DAL GRUPPO
	#------------------------------------------------------
	"""
	def removeUserFromGroup(self, user_name, group_name):
		print( Fore.RED + ' Removing User from Group ...' + Fore.RESET)
		try:
			response = self.iam_client.remove_user_from_group(
					GroupName = group_name,
					UserName = user_name
				)
			print(f" Wait remove user from group", end="")
			self.progress_bar(4)
			print( f" Remove user [{user_name}] from group [{group_name}] -> Success")

		except ClientError as error:
			print(f" An arror occured in remove user from group")
			print(error)
			sys.exit(1)


	#-----------------------------------------------
	# ADD PRINCIPAL IN ROLEASSUME
	#-----------------------------------------------
	
	def add_principal_in_AssumeRoleUsers(self,response_role, group_name, user_name):

		role_name = self.prefix_role_assume + group_name
		user_arn = f"arn:aws:iam::{self.id_Account}:user/{user_name}"

		trust_policy = response_role['Role']['AssumeRolePolicyDocument']
		print(trust_policy)
		array = trust_policy['Statement'][0]['Principal']['AWS']
		print(array)
		print(type(array))
		if isinstance(array, str):
			lista = [array]
			lista.append(user_arn)
		else:
			lista = array
			lista.append(user_arn)

		trust_policy['Statement'][0]['Principal']['AWS'] = lista
		#print("MOFIFICA")
		#print(trust_policy)

		response_update = self.iam_client.update_assume_role_policy(
			RoleName= role_name,
			PolicyDocument= json.dumps(trust_policy)
			)

		print(f"Wait update Role.", end="")
		self.progress_bar(10)

		response2 = self.iam_client.get_role(RoleName= role_name)
		trust_policy2 = response2['Role']['AssumeRolePolicyDocument']

		print("Role updates")
		print(trust_policy2)

	#-----------------------------------------------
	# REMOVE PRINCIPAL IN ROLEASSUME
	#-----------------------------------------------
	
	def remove_principal_in_AssumeRoleUsers(self,response_role, group_name, user_name):

		role_name = self.prefix_role_assume + group_name
		user_arn = f"arn:aws:iam::{self.id_Account}:user/{user_name}"

		trust_policy = response_role['Role']['AssumeRolePolicyDocument']
		print(trust_policy)
		array = trust_policy['Statement'][0]['Principal']['AWS']
		print(array)
		print(type(array))

		if isinstance(array, str):
			# significa che è rimasto un solo utente,
			# controllare se l'arn presente corrisponde a quello dell'user da rimuovere
			if array == user_arn:
				# si si vuol dire che questo utente va rimosso,
				#pertanto verrà rimosso tutto il ruolo
				
				print("There is no user in the group")
				print(" Detach policies from the role")
				# è neccessario prima staccare le due policy: bucket e dynamodb
				# quindi recuperare la lista di policy_arn attacati al ruolo,
				# in modo da staccare le policy per arn

				list_policy_arn = self.getList_Policy_Arn_of_Role(role_name)

				if list_policy_arn is not False:

					for policy_arn in list_policy_arn: 
						self.detach_policy_from_role(role_name, policy_arn)

					#una volta che le policy sono state distaccate, è possibile rimuovere il ruolo
					self.remove_role(role_name)

		elif isinstance(array, list):
			lista_users = array
			lista_users.remove(user_arn)

			print("Update assume role policy")
			# altrimenti, dopo aver rimosso arn_user dalla lista, ci sono ancora altri users
			# allora aggiornare il ruolo
			trust_policy['Statement'][0]['Principal']['AWS'] = lista_users
			response_update = self.iam_client.update_assume_role_policy(
				RoleName= role_name,
				PolicyDocument= json.dumps(trust_policy)
				)
			print(f"Wait update Role.", end="")
			self.progress_bar(10)

			response2 = self.iam_client.get_role(RoleName= role_name)
			trust_policy2 = response2['Role']['AssumeRolePolicyDocument']

			print("Role updates")
			print(trust_policy2)






	"""
	#------------------------------------
	#   GET ARN POLICY
	#------------------------------
	"""
	def getArnPolicy(self, resourse, group_name):
		policy_name = ""
		if resourse == "bucket":
			policy_name = self.prefix_policy_bucket + group_name 
			
		elif resourse == "assumeRole":
			policy_name = self.prefix_role_assume + group_name

		elif resourse == "dynamoDB":
			policy_name = self.prefix_policy_dynamoDB + group_name
		
		policy_arn =  f"arn:aws:iam::{self.id_Account}:policy/{policy_name}"

		try:
			policy = self.iam_client.get_policy(
				PolicyArn = policy_arn
				)
			print(f"Policy {policy_arn} exists ")
			return policy_arn

		except ClientError as Error:
			print(f"Policy {policy_arn} not exists")
			return False
	""""
	#----------------------------------------
	#   ATTACH POLICY TO ROLE
	#-----------------------------------------
	"""
	def attach_policy_to_role(self, role, policy_arn):
		try:
			role.attach_policy(PolicyArn = policy_arn)
			print(f" Attach Policy to the role.")
		except ClientError as error:
			print(f"Couldn't  attach policy to role", Error)

		""""
	#----------------------------------------
	#   DETACH POLICY TO ROLE
	#-----------------------------------------
	"""
	def detach_policy_from_role(self, role_name, policy_arn):
		try:
			self.iam_client.detach_role_policy(
				RoleName = role_name,
				PolicyArn = policy_arn
			)
			print(f" Detach Policy [{policy_arn}] from the role.")
		except ClientError as error:
			print(f"Couldn't  detach policy to role", Error)

	#--------------------------------------------
	#	CREATE POLICY ASSUME ROLE TO GROUP
	#--------------------------------------------
	def createPolicyAssumeRole_to_Group(self,group_name,role_arn):
		policy_string = policyAssumeRole(role_arn)
		policy_name = self.prefix_policy_group+group_name

		try:
			group_response = self.iam_client.get_group(
					GroupName= group_name
				)
			group_resource = self.iam_resource.Group(group_name)
		except ClientError as Error:
			print(f"Group not exists", error)
			sys.exit(1)
		
		
		print(Fore.RED + " Creating policy inline to for group that lets the user assume ..." + Fore.RESET)	
		try:
			group_resource.create_policy(
				PolicyName = policy_name,
				PolicyDocument = policy_string
				)
		except ClientError as error:
			print(
				f"Couldn't create an inline policy for group. Here's why: "
				f"{error.response['Error']['Message']}"
				)
			raise
		else:
			print(" Give AWS time to propagate these new resources and connections.", end="")
			self.progress_bar(5)

	#-------------------------------------------------------------
	#	LIST GROUPS
	#--------------------------------------------------------------
	def listGroups(self):
		response = self.iam_client.list_groups()
		list_nameGroup = []

		for group in response['Groups']:
			#group_details = iam.get_group(GroupName = group['GroupName'])
			list_nameGroup.append(group['GroupName'])
		return list_nameGroup

	#---------------------------------------------------------------
	#	LIST USER in Group
	#----------------------------------------------------------------
	def listUsers(self, group):
		if group is None:
			#print all user in all groups
			dizionario = {}
			response = self.iam_client.list_groups()
			
			for group in response['Groups']:
				group_details = self.iam_client.get_group(GroupName = group['GroupName'])
				list_user = []
				for user in group_details['Users']:
					list_user.append(user['UserName'])
				dizionario[group['GroupName']]= list_user

			return dizionario
		else:
			try:
				dizionario = {}
				group_details = self.iam_client.get_group(GroupName = group)
				list_user = []
				for user in group_details['Users']:
					list_user.append(user['UserName'])
				dizionario[group]= list_user
				return dizionario
			except ClientError as error:
				if error.response['Error']['Code'] == 'NoSuchEntity':
					print(f"Group [{group}] does not exist")
				return dizionario

	#------------------------------------------------------------------
	#	LIST ALL USERS 
	#------------------------------------------------------------------
	def listUsersAll(self):
		""" elnca gli utenti nel corrente account"""
		list_name_user = []
		try:
			users = list(self.iam_resource.users.all())
			# lista di risorse user
			for u in users:
				list_name_user.append(u.name)
			self.logger.info("Got %s users.", len(users))
		except ClientError as error:
			self.logger.exception("Couldn't get users.")
			raise
		else:
			return list_name_user

	#-----------------------------------------------------------------
	#	LIST ALL BUCKET 
	#-----------------------------------------------------------------
	def listBuckets(self):
		try:
			b_response =self.S3_client.list_buckets()
			buckets = []
			for bucket in b_response['Buckets']:
				buckets.append(bucket['Name'])
			return buckets
		except ClientError as error:
			print( "Error", error)
		

























