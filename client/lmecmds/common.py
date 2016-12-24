'''
Created on Dec 23, 2016

@author: devdatta
'''

import os
import sys
import yaml

def read_app_info():
    cwd = os.getcwd()
    lmefile = cwd + "/lme.yaml"
    if not os.path.exists(lmefile):
        print("lme.yaml not present. Please create it and then try again.")
        sys.exit(0)

    app_info = {}

    fp = open(lmefile, "r")
    lme_obj = yaml.load(fp.read())
    #print(lme_obj)
    application_obj = lme_obj['application']
    app_type = application_obj['type']
    entry_point = application_obj['entry_point']

    app_info['app_type'] = app_type
    app_info['entry_point'] = entry_point

    if application_obj['env_variables']:
        env_var_obj = application_obj['env_variables']
        app_info['env_variables'] = env_var_obj

    return app_info

def read_service_info():
    cwd = os.getcwd()
    lmefile = cwd + "/lme.yaml"
    if not os.path.exists(lmefile):
        print("lme.yaml not present. Please create it and then try again.")
        sys.exit(0)

    service_info = {}
    fp = open(lmefile, "r")
    lme_obj = yaml.load(fp.read())
    services_list = lme_obj['services']
    for service_obj in services_list:
        service_info[service_obj['service']['type']] = service_obj

    return service_info

def read_cloud_info():
    cwd = os.getcwd()
    lmefile = cwd + "/lme.yaml"
    if not os.path.exists(lmefile):
        print("lme.yaml not present. Please create it and then try again.")
        sys.exit(0)

    cloud_info = {}
    fp = open(lmefile, "r")
    lme_obj = yaml.load(fp.read())
    cloud_obj = lme_obj['cloud']

    cloud_info['type'] = cloud_obj['type']
    if cloud_obj['type'] == 'local':
        app_port = '5000'
        if cloud_obj['port']:
            app_port = cloud_obj['port']
            cloud_info['app_port'] = app_port
    if cloud_obj['type'] == 'google':
        if not cloud_obj['project_id']:
            print("project_id required for cloud %s" % cloud_obj['type'])
            sys.exit(0)
        else:
            project_id = cloud_obj['project_id']
            cloud_info['project_id'] = project_id
        if not cloud_obj['user_email']:
            print("user_email required for cloud %s" % cloud_obj['type'])
            sys.exit(0)
        else:
            user_email = cloud_obj['user_email']
            cloud_info['user_email'] = user_email

    return cloud_info