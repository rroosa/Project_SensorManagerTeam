import request

open('file.txt','wb')
with open ('file.txt','rb') as payload:
	headers = {'content-type':'application/x-www-form-urlencoded'}
	r = request.post('http://localhost:5001/postObject', data=payload,headers=headers)
	print r