import json
from environment_config import *

def bucket_policy_R_W():

	policy = {

	    "Version": "2012-10-17",
	    "Statement": [
	        {
	            "Effect": "Deny",
	            "Action": [
	                "s3:ListAllMyBuckets",
	                "s3:GetBucketLocation"
	            ],
	            "Resource": [f"arn:aws:s3:::*"]
	        },
	        {
	            "Effect": "Deny",
	            "Action": [
	                "s3:PutObject",
	                "s3:GetObject",
	                "s3:DeleteObject"
	            ],
	            "Resource": 
	                [f"arn:aws:s3:::*/*"]
	            
	        }
	    ]
	}

	policy_string = json.dumps(policy)
	return policy_string

def assume_role_PolicyDocument(user_arn):

	policy = {

        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": [user_arn]},
                "Action": "sts:AssumeRole",
            }
        ],
        }
	policy_string = json.dumps(policy)
	return policy_string

def policyAssumeRole(role_arn):

	policy ={
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Resource": role_arn,
            }
        ],
	}
	policy_string = json.dumps(policy)
	return policy_string

def policyDynamoDB():
	id_account = os.environ["ID_ACCOUNT_AWS"]
	arn = f"arn:aws:dynamodb:eu-west-3:{id_account}:table/*"

	policy = {
		"Version":"2012-10-17",
		"Statement": [
			{
				"Effect": "Allow",
				"Action": "dynamodb:*",
				"Resource":[
				arn
				]
			}				
		]
	}
	policy_string = json.dumps(policy)
	return policy_string

