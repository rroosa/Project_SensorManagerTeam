import os
import json
from colorama import Fore, Back, Style
from decimal import Decimal, InvalidOperation
import glob

def allowed_file_type(filename, extension):
	#print( f" Check extention of file ...")

	if extension in filename and  filename.rsplit(extension,1)[1].lower() == '':
		print(f"ok extension [{filename}] - [{extension}]  ")
		return True
	else:
		print(f"Error extension [{filename}] - [{extension}]  ")
		return False

def check_folders( folders ):
		print(f"Checking if folders [{folders}] exist ...")

		if not os.path.isdir(folders):
			print(f" Not exist, create new folders {folders} ")
			os.makedirs(folders)
		else:
			print(f"Folders {folders} already exist")

def check_add_format_file(filename, type_file):

	#---------------TEXT --> .txt -------------

	if type_file == 'csv':
		if "." not in filename:
			filename = filename+'.csv'
			return filename

		elif ".csv" in filename and object_name.rsplit('.csv',1)[1] == '':
			print( "Ok extension (.csv)")
			return filename
		else:
			filename = filename+'.csv'
			return filename

def save_file_into_server( path_file, destination, filename):

	check_folders(destination)

	path_file_to_server = os.path.join(destination, filename)

	print(f"Save file [{filename}] into folder [{destination}]")
	path_file.save(path_file_to_server)

def deleteFile_from_server(folder, filename, prev = None ):

	if prev is True:
		#elimina il contenuto
		filesD = glob.glob(folder+'/*')
		#print("fileHHH",filesD)
		
		for f in filesD:
			try:
				os.remove(f)
			except OSError as e:
				print("Error: %s : %s" % (f, e.strerror))
		print(Fore.GREEN +"Success Delete files from folder"+Fore.RESET)

	else:
		print("Delete file from local folder ...")
		path_file = os.path.join(folder,filename)

		if os.path.isfile(path_file):
			try:
				os.remove(path_file)
			except OSError as e:
				print("Error: %s : %s" % (path_file, e.strerror))
			else:
				print(f"Success delete file [{filename}] from [{folder}]")

def dataField_vs_template(local_path, list_keys_template):

	list_all_field_data = []

	with open(local_path) as file_data:
		data = None
		try:
			data = json.load(file_data)
		except json.JSONDecodeError as e:
			return False , f"Error convert to dictionary: {e} ", 808 
		
		else:
			if len(data) > 0:
				obj = data[0]
				#print ("primo oggetto",obj)
				#print(type(obj))
				list_all_field_data = list(obj.keys())
			
	print(Fore.BLUE + "Fields of template" + Fore.RESET)
	print(list_keys_template)
	print(Fore.BLUE + "Fields of the measurements file" + Fore.RESET )
	print(list_all_field_data)

	for el in list_all_field_data:
		if el not in list_keys_template:
			return False, "Error. The fields of the measurements file do not correspond to the template.", 707

	return True, "Success. The fields of the measurements file correspond to the template.", 200

def map_OP_Comparison(key):

	op_comparison = {
		"EQ": "=",
		"NE": "<>",
		"IN": 'in',
		"LE": '<=',
		"LT": '<',
		"GE": '>=',
		"GT": '>',
		"BETWEEN": 'between',
		"NOT_NULL": 'not_null',
		'NULL': 'null',
		'CONTAINS': 'contains',
		'NOT_CONTAINS': 'not_contains',
		'BEGINS_WITH': 'begins_with'
	}

	return op_comparison.get(key)

def is_decimal(d):
	try:
		Decimal(d)
		return True
	except InvalidOperation:
		return False

def prepare_Cond_Att(list_clause_key,list_op_conditional, list_clause_filter, list_op_conditional_filter):
	print("QUERY")
	keyConditionExpression = ""
	filterExpression = ""

	expressionAttributeValues = {} # dict {att:value}

	list_values = []
	list_attribute = []

	i = 1

	# keyConditionExpression

	for count, clause in enumerate (list_clause_key, start = 1 ):

		keyConditionExpression = keyConditionExpression 

		clause_values = clause.get('values')

		comparison = map_OP_Comparison( clause.get('op_comparison'))

		if 'between' == comparison and len(clause_values) == 2: # BETWEEN  :attr_{i} AND :attr_{i+1}
			
			keyConditionExpression = keyConditionExpression + " " + clause.get('attribute') + " " + 'between'
			keyConditionExpression = keyConditionExpression + " " + f":attr_{i}" + " and"
			list_attribute.append(f":attr_{i}")
			i = i + 1
			keyConditionExpression = keyConditionExpression + " " + f":attr_{i}"

			list_attribute.append(f":attr_{i}")
			i = i + 1
			if is_decimal(clause_values[0]):
				clause_values[0] = Decimal(clause_values[0])
			if is_decimal(clause_values[1]):
				clause_values[1] = Decimal(clause_values[0])
			list_values.append(clause_values[0])
			list_values.append(clause_values[1])

		#elif ('begins_with' == comparison or 'contains' == comparison or 'not_contains' == comparison ) and len(clause_values) == 1:
		elif('begins_with' == comparison) and len(clause_values) == 1:
			keyConditionExpression = keyConditionExpression + f" {comparison} ( {clause.get('attribute')} , :attr_{i})"
			list_attribute.append(f":attr_{i}")
			i = i + 1
			if is_decimal(clause_values[0]):
				clause_values[0] = Decimal(clause_values[0])
			list_values.append(clause_values[0])

		elif('contains' == comparison or 'not_contains' == comparison) and len(clause_values) == 1:
			keyConditionExpression = keyConditionExpression + f" {comparison} ( {clause.get('attribute')} , :attr_{i})"
			list_attribute.append(f":attr_{i}")
			i = i + 1
			#if is_decimal(clause_values[0]):
			#	clause_values[0] = Decimal(clause_values[0])
			list_values.append(clause_values[0])


		elif 'in' == comparison and len(clause_values) == 1: 
			string_list = clause_values[0]
			print(string_list)
			string_list = string_list.replace(" ","")
			print(string_list)
			list_value = string_list.split(",")
			print(list_value)
			for i, el in enumerate(list_value):
				if is_decimal(el):
					list_value[i] = Decimal(el)
			print(list_value) # lista di valori

			content = ""
			for j, el in enumerate(list_value):
				if j == 0:
					content = content + f":attr_{i}"
				else:
					content = content + ", " + f":attr_{i}"
				list_attribute.append(f":attr_{i}")
				i = i + 1
				list_values.append(el)

			filterExpression = filterExpression + f" {clause.get('attribute')} {comparison} ( {content} )"



		elif len(clause_values) == 1:
			keyConditionExpression = keyConditionExpression + " " + clause.get('attribute') + " " + comparison 
			keyConditionExpression = keyConditionExpression + " " + f":attr_{i}"
			list_attribute.append(f":attr_{i}")
			i = i + 1
			if is_decimal(clause_values[0]):
				clause_values[0] = Decimal(clause_values[0])
			list_values.append(clause_values[0])

		if count <= len(list_op_conditional):
			keyConditionExpression = keyConditionExpression + " " + list_op_conditional[count - 1] 

	# filterExpression
	for count, clause in enumerate (list_clause_filter, start = 1 ):

		filterExpression = filterExpression 

		clause_values = clause.get('values')

		comparison = map_OP_Comparison( clause.get('op_comparison'))

		if 'between' == comparison and len(clause_values) == 2: # BETWEEN  :attr_{i} AND :attr_{i+1}
			
			filterExpression = filterExpression + " " + clause.get('attribute') + " " + 'between'
			filterExpression = filterExpression + " " + f":attr_{i}" + " and"
			list_attribute.append(f":attr_{i}")
			i = i + 1
			filterExpression = filterExpression + " " + f":attr_{i}"

			list_attribute.append(f":attr_{i}")
			i = i + 1
			if is_decimal(clause_values[0]):
				clause_values[0] = Decimal(clause_values[0])
			if is_decimal(clause_values[1]):
				clause_values[1] = Decimal(clause_values[0])

			list_values.append(clause_values[0])
			list_values.append(clause_values[1])

		#elif ('begins_with' == comparison or 'contains' == comparison or 'not_contains'== comparison ) and len(clause_values) == 1:
		elif 'begins_with' == comparison and len(clause_values) == 1:
			filterExpression = filterExpression + f" {comparison} ( {clause.get('attribute')} , :attr_{i})"
			list_attribute.append(f":attr_{i}")
			i = i + 1
			if is_decimal(clause_values[0]):
				clause_values[0] = Decimal(clause_values[0])
			list_values.append(clause_values[0])

		elif('contains' == comparison or 'not_contains'== comparison ) and len(clause_values) == 1:
			filterExpression = filterExpression + f" {comparison} ( {clause.get('attribute')} , :attr_{i})"
			list_attribute.append(f":attr_{i}")
			i = i + 1
			#if is_decimal(clause_values[0]):
			#	clause_values[0] = Decimal(clause_values[0])
			list_values.append(clause_values[0])


		elif 'in' == comparison and len(clause_values) == 1: 
			string_list = clause_values[0]
			print(string_list)
			string_list = string_list.replace(" ","")
			print(string_list)
			list_value = string_list.split(",")
			print(list_value)
			for i, el in enumerate(list_value):
				if is_decimal(el):
					list_value[i] = Decimal(el)
			print(list_value) # lista di valori

			content = ""
			for j, el in enumerate(list_value):
				if j == 0:
					content = content + f":attr_{i}"
				else:
					content = content + ", " + f":attr_{i}"
				list_attribute.append(f":attr_{i}")
				i = i + 1
				list_values.append(el)

			filterExpression = filterExpression + f" {clause.get('attribute')} {comparison} ( {content} )"



		elif len(clause_values) == 1:
			filterExpression = filterExpression + " " + clause.get('attribute') + " " + comparison 
			filterExpression = filterExpression + " " + f":attr_{i}"
			list_attribute.append(f":attr_{i}")
			i = i + 1
			if is_decimal(clause_values[0]):
				clause_values[0] = Decimal(clause_values[0])
			list_values.append(clause_values[0])

		if count <= len(list_op_conditional_filter):
			filterExpression = filterExpression + " " + list_op_conditional_filter[count - 1] 


	expressionAttributeValues = dict(zip(list_attribute, list_values))

	print(f"Clause key condition : {keyConditionExpression}")

	print(f"Clause filter: {filterExpression}")

	print(f"AttValue: {expressionAttributeValues}")

	return keyConditionExpression, filterExpression, expressionAttributeValues



def prepare_Filter_Att_Expression( list_clause_filter,list_op_conditional_filter ):
	
	filterExpression = ""
	expressionAttributeValues = {} # dict {att:value}
	list_values = []
	list_attribute = []

	i = 1

		# filterExpression
	for count, clause in enumerate (list_clause_filter, start = 1 ):

		filterExpression = filterExpression 

		clause_values = clause.get('values')

		comparison = map_OP_Comparison( clause.get('op_comparison'))

		if 'between' == comparison and len(clause_values) == 2: # BETWEEN  :attr_{i} AND :attr_{i+1}
			
			filterExpression = filterExpression + " " + clause.get('attribute') + " " + 'between'
			filterExpression = filterExpression + " " + f":attr_{i}" + " and"
			list_attribute.append(f":attr_{i}")
			i = i + 1
			filterExpression = filterExpression + " " + f":attr_{i}"

			list_attribute.append(f":attr_{i}")
			i = i + 1
			if is_decimal(clause_values[0]):
				clause_values[0] = Decimal(clause_values[0])
			if is_decimal(clause_values[1]):
				clause_values[1] = Decimal(clause_values[0])

			list_values.append(clause_values[0])
			list_values.append(clause_values[1])

		#elif ('begins_with' == comparison or 'contains' == comparison or 'not_contains' == comparison ) and len(clause_values) == 1:
		elif 'begins_with' == comparison and len(clause_values) == 1:
			filterExpression = filterExpression + f" {comparison} ( {clause.get('attribute')} , :attr_{i})"
			list_attribute.append(f":attr_{i}")
			i = i + 1
			if is_decimal(clause_values[0]):
				clause_values[0] = Decimal(clause_values[0])
			list_values.append(clause_values[0])

		elif('contains' == comparison or 'not_contains'== comparison ) and len(clause_values) == 1:
			filterExpression = filterExpression + f" {comparison} ( {clause.get('attribute')} , :attr_{i})"
			list_attribute.append(f":attr_{i}")
			i = i + 1
			#if is_decimal(clause_values[0]):
			#	clause_values[0] = Decimal(clause_values[0])
			list_values.append(clause_values[0])


		elif 'in' == comparison and len(clause_values) == 1: 
			string_list = clause_values[0]
			print(string_list)
			string_list = string_list.replace(" ","")
			print(string_list)
			list_value = string_list.split(",")
			print(list_value)
			for i, el in enumerate(list_value):
				if is_decimal(el):
					list_value[i] = Decimal(el)
			print(list_value) # lista di valori

			content = ""
			for j, el in enumerate(list_value):
				if j == 0:
					content = content + f":attr_{i}"
				else:
					content = content + ", " + f":attr_{i}"
				list_attribute.append(f":attr_{i}")
				i = i + 1
				list_values.append(el)

			filterExpression = filterExpression + f" {clause.get('attribute')} {comparison} ( {content} )"



		elif len(clause_values) == 1:
			filterExpression = filterExpression + " " + clause.get('attribute') + " " + comparison 
			filterExpression = filterExpression + " " + f":attr_{i}"
			list_attribute.append(f":attr_{i}")
			i = i + 1
			if is_decimal(clause_values[0]):
				clause_values[0] = Decimal(clause_values[0])
			list_values.append(clause_values[0])

		if count <= len(list_op_conditional_filter):
			filterExpression = filterExpression + " " + list_op_conditional_filter[count - 1] 


	expressionAttributeValues = dict(zip(list_attribute, list_values))
	print(f"Clause filter: {filterExpression}")
	print(f"AttValue: {expressionAttributeValues}")

	return filterExpression, expressionAttributeValues














