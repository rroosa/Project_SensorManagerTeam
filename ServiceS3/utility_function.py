import os
import glob
import json
from colorama import Fore, Back, Style

def deleteFile(path_file, prev = None):
	if prev is True:
		#elimina il contenuto
		filesD = glob.glob(path_file+'/*')
		#print("fileHHH",filesD)
		
		for f in filesD:
			try:
				os.remove(f)
			except OSError as e:
				print("Error: %s : %s" % (f, e.strerror))
		print(Fore.GREEN +"Success Delete files from folder"+Fore.RESET)

	else:

		#print(Fore.GREEN +"Delete file from folder"+Fore.RESET)
		if os.path.isfile(path_file):
			try:
				os.remove(path_file)
			except OSError as e:
				print("Error: %s : %s" % (path_file, e.strerror))
			else:
				print(Fore.GREEN+"Success Delete file from local folder"+Fore.RESET)


def ckeck_extension(filename, extension):
	print( f" Check extention of file ...")

	if extension in filename and filename.rsplit(extension,1)[1].lower() == '':
		print(Fore.GREEN + f"Ok extension [{filename}] - [{extension}] " + Fore.RESET)
		return True
	else:
		print(Fore.RED + f"Error extension [{filename}] - [{extension}] " + Fore.RESET)
		return False

def check_field(local_path, key, value):
	print("Cheking the value in the key-field...")
	try:
		with open(local_path) as file:
			content = json.load(file)

			val = content.get(key)
			if val is not None:
				if val == value:
					return True , "Ok check value in the key-field"
				else:
					return False , f"The value in the key-field [{key}] not match"
			else:
				return False , f"The key-field [{key}] is not present"

	except json.JSONDecodeError as e:
		print(f" Error {e}")
		return False ,e
	else:
		return True, "Ok check value in the key-field"

def check_keys(local_path, keys):
	print("Cheking keys...")
	with open(local_path) as file:
		content = json.load(file)
		list_keys = list(content.keys())
		for k in keys:
			if k not in list_keys:
				return False

	return True

def collect_FieldValues(local_path, list_keys): # [keys, other_measures]
	dict_of_attribute = {
	"key_partition":"",
	"key_sort":"",
	"attributes":[]
	}

	list_all_field = []
	print(f" Parse file")

	with open(local_path) as file:
			# returns JSON object as a dictionary
			content = None
			try:
				content = json.load(file)
			except json.JSONDecodeError as e:
				#print("Error convert to dictionary ")
				return False, f"Error convert to dictionary: {e} " 
			else:
				
				for key in list_keys:
					if key in content:
						list_keys = content.get(key)
						for obj in list_keys:
							list_all_field.append(obj.get('field'))
							type_key = obj.get('type')
							if type_key == 'sort':
								dict_of_attribute['key_sort'] = obj.get('field')
							elif type_key == 'partition':
								dict_of_attribute['key_partition'] = obj.get('field')
							else:
								dict_of_attribute['attributes'].append(obj.get('field'))
	
	print(f"List of fieds: {list_all_field}")
	print(f"Dict of keys attributes: {dict_of_attribute}")

	return True, list_all_field, dict_of_attribute

				





	
