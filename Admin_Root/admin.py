import argparse
import time
import os
from botoObj import BotoObj
from environment_config import *
from colorama import Fore, Back, Style, init

init(convert=True)

botoObj = None
id_Account = os.environ["ID_ACCOUNT_AWS"]
role_assume = "role-assumeRoleUsers"

# 1)
def createBucket(nameBucket, region, prefix,auto):
    print('Task create Bucket')
    
    if nameBucket is not None:
        nameBucket = nameBucket
    elif prefix is not None:
        print(f"Generate bucket_name with prefix {prefix} ")
        nameBucket = prefix+f"-{time.time_ns()}"
    else:
        
        print("Generate bucket_name automatic")
        nameBucket = f"sensor-data-sheet-{time.time_ns()}"

    if region is not None:
        print("Region",region)
    
    response_bool = botoObj.createBucket(nameBucket, region)
    print(f" Bucket [{nameBucket} ] created -> {response_bool}" )


# 2-3)
def createIAM(group, user):
    print('Task createIAM')
    if group != None:
        print('Group: ',group)
        botoObj.createGroup(group)

    if user != None:
        print('User: ',user)
        user_obj = botoObj.createUser(user)


# 4)
def active( group):

    boolean = botoObj.isPresentGroup(group)
    if boolean is True:
        os.environ["ACTIVE_GROUP"] = group
        print ("Set Active Group ->" + os.environ["ACTIVE_GROUP"])
# 5)
def manageBucket(group, bucket):

    botoObj.add_bucket_in_Policy(group,bucket)

def detachBucket(group, bucket):

    botoObj.detach_bucket_from_Policy(group, bucket)

# 6)
def add( user, group):
    print('Task add user in group')
    print('Group:', group)
    print('User:', user)
    #aggiungere utente al gruppo
    botoObj.addUserToGroup(user,group)
    #ottenere il Ruolo assumeRoleUser
    response_role = botoObj.getRoleAssumeRoleUser(group)
    if response_role is False:
        # create new role assumeRoleUser
        role = botoObj.createRole_AssumeRoleUsers(group, user)
        # ---------------------------------------------------------
        #----attacca la policy del bucket al ruolo ----------------
        policy_bucket_arn = botoObj.getArnPolicy("bucket",group)

        if policy_bucket_arn is not False:

            botoObj.attach_policy_to_role(role, policy_bucket_arn)
        else:
            print("Error - policy bucket not present")
            sys.exit(1)
        #------------------------------------------------------------
        #------ attacca la policy del dynamoDB al ruolo -------------
        policy_dynamoDB_arn = botoObj.getArnPolicy("dynamoDB", group)

        if policy_dynamoDB_arn is not False:

            botoObj.attach_policy_to_role(role, policy_dynamoDB_arn)
        else:
            print("Error - policy dynamoDB not present")
            sys.exit(1)


        # creare la policy inline AssumeRole attaccando al gruppo
        botoObj.createPolicyAssumeRole_to_Group(group, role.arn)


    else:
         
        botoObj.add_principal_in_AssumeRoleUsers(response_role, group, user)

# 6.2)
def remove( user, group):
    print('Task remove user from group')
    print('Group:', group)
    print('User:', user)
    #rimuovere utente dal gruppo
    botoObj.removeUserFromGroup(user,group)

    #ottenere il Ruolo assumeRoleUser
    response_role = botoObj.getRoleAssumeRoleUser(group)

    if response_role is not False:
        # eliminare l'arn_user dal campo Principal-> AWS relativo al RUOLO
        botoObj.remove_principal_in_AssumeRoleUsers(response_role, group, user)



# 7)

def listGroups():
    list_response = botoObj.listGroups()
    print("Groups:")
    for g in list_response:
        print(g)

# 8)
def listUsers(all, group, split ):
    #print(all, group, split)

    if group is not None:

        dizionario = botoObj.listUsers(group)
        for group, users in dizionario.items():
            print(f"Group: {group}")
            for u in users:
                print(f"- {u}")
    elif split is None:

        dizionario = botoObj.listUsers(None)
        for group, users in dizionario.items():
            print(f"Group: {group}")
            for u in users:
                print(f"- {u}")
    else:
        list_all_users=botoObj.listUsersAll()
        print("All Users")
        for u in list_all_users:
            print(f"- {u}")

#9)
def listBuckets():
    lista = botoObj.listBuckets()
    print("Existing buckets:")
    for bucket in lista:
        print(f"[{bucket}]")



if __name__ == '__main__':

    botoObj = BotoObj.getInstance()

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='subparser')

    """
    #------------------------------------------------------------------------------------
    1) BUCKET - creare bucket 
    #  createBucket (--name <name> | --prefix <prefix> | --auto )  [--region <region> ]
    #-------------------------------------------------------------------------------------
    """
    parser_bucket = subparsers.add_parser('createBucket')

    group = parser_bucket.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-n','--name', dest = 'nameBucket', help='name bucket'
        )
    group.add_argument(
        '-p','--prefix',dest= 'prefix',  help ='prefix for name Bucket'
        )
    group.add_argument(
        '-a', '--auto', dest='auto',action='store', default= 'UNSPECIFIED', nargs='?'
       )

    parser_bucket.add_argument(
        '-r','--region', dest= 'region', default = None, help='location for bucket es. eu-west-3')


    """
    #--------------------------------------------------------------------------------------------
    2-3) GROUP e/o USER -  creare un gruppo e/o utente
    #  createIAM (--group <name>) (--user <name>)
    #---------------------------------------------------------------------------------------------
    """
    parser_a = subparsers.add_parser('createIAM')
    parser_a.add_argument(
        '-g', '--group', dest='group', default=None,  help='group')

    parser_a.add_argument(
        '-u', '--user', dest='user', default=None, help='user of group') 

    """
    #---------------------------------------------------------------------
    4) ACTIVE group 
    #  active --group <name>
    #--------------------------------------------------------------------
    """
    parser_active = subparsers.add_parser('active')
    parser_active.add_argument(
        '-g', '--group', dest='group', help='group_name to activate', required=True)

    """
    #------------------------------------------------------------------
    5) MANAGE BUCKET BY GROUP
    #  manageBucket --bucket <bucket_name> --group <group_name>
    #------------------------------------------------------------------
    """
    parser_manager = subparsers.add_parser('manageBucket')
    parser_manager.add_argument(
        '-g', '--group', dest='group', help='group_name ', required=True)
    parser_manager.add_argument(
        '-b', '--bucket', dest='bucket', help='bucket_name to be managed by group', required=True)

    """
    #------------------------------------------------------------------
    5.1) detach BUCKET from GROUP
    #  manageBucket --bucket <bucket_name> --group <group_name>
    #------------------------------------------------------------------
    """
    parser_detach = subparsers.add_parser('detachBucket')
    parser_detach.add_argument(
        '-g', '--group', dest='group', help='group_name ', required=True)
    parser_detach.add_argument(
        '-b', '--bucket', dest='bucket', help='bucket_name to be detach from the group', required=True)

    """
    #-----------------------------------------------------------------------
    6) ADD user to Group
    #  add --user <name> --group <group>
    #----------------------------------------------------------------------
    """
    parser_add = subparsers.add_parser('add')
    parser_add.add_argument(
        '-g', '--group', dest='group', help='name group for add user', required = True)
    parser_add.add_argument(
        '-u', '--user', dest='user',  help='name user to add to a group', required = True)
    """

        #-----------------------------------------------------------------------
    6.2) REMOVE user to Group
    #  remove --user <name> --group <group>
    #----------------------------------------------------------------------
    """
    parser_add = subparsers.add_parser('remove')
    parser_add.add_argument(
        '-g', '--group', dest='group', help='name group for add user', required = True)
    parser_add.add_argument(
        '-u', '--user', dest='user',  help='name user to add to a group', required = True)
    """


    #------------------ 
    7)  LIST GROUP 
    #----------------
    """
    parser_g = subparsers.add_parser('listGroups')
    """
    #----------------------
    8) LIST USERS 
    #----------------------
    """
    parser_u = subparsers.add_parser('listUsers')
    group_op = parser_u.add_mutually_exclusive_group(required=True)

    group_op.add_argument(
        '-g', '--group', dest='group', default=None,  help='name group of users')
    group_op.add_argument(
        '-a', '--all', dest='all',action='store', default= 'UNSPECIFIED', nargs='?', help = 'list all users'
        )
    group_op.add_argument(
        '-s', '--split', dest='split',action='store', default= 'UNSPECIFIED', nargs='?', help = 'list all users splited into gropus'
        )
    """
    #---------------------------- 
    9)LIST BUCKET 
    #--------------------------
    """
    parser_list_bucket = subparsers.add_parser('listBuckets')

    kwargs = vars(parser.parse_args())
    globals()[kwargs.pop('subparser')](**kwargs)


 


