'''
Created on Dec 22, 2016

@author: devdatta
'''
import logging
import os
import stat
import subprocess
import time

from common import docker_lib

class MySQLServiceHandler(object):

    def __init__(self, task_def, app_obj):
        self.task_def = task_def

        self.app_dir = task_def.app_data['app_location']
        self.app_name = task_def.app_data['app_name']
        self.app_version = task_def.app_data['app_version']
        self.access_token_cont_name = "google-access-token-cont-" + self.app_name + "-" + self.app_version
        self.create_db_cont_name = "google-create-db-" + self.app_name + "-" + self.app_version
        self.docker_handler = docker_lib.DockerLib()

        if task_def.service_data:
            self.service_details = task_def.service_data[0]['service_details']

    def _deploy_instance(self, access_token, project_id, db_server):
        cmd = ('curl --header "Authorization: Bearer {access_token}" --header '
               '"Content-Type: application/json" --data \'{{"name":"{db_server}",'
               '"region":"us-central", "settings": {{"tier":"db-n1-standard-1", "activationPolicy":"ALWAYS", "ipConfiguration":{{"authorizedNetworks":[{{"value":"0.0.0.0/0"}}]}}}}}}\' '
               ' https://www.googleapis.com/sql/v1beta4/projects/{project_id}/instances -X POST').format(access_token=access_token,
                                                                                                        db_server=db_server,
                                                                                                        project_id=project_id)
        logging.debug("Creating Cloud SQL instance")
        logging.debug(cmd)
        try:
            os.system(cmd)
        except Exception as e:
            print(e)

        self._wait_for_db_instance_to_get_ready(access_token, project_id, db_server)

    def _create_user(self, access_token, project_id, db_server):
        username_val = 'lmeroot'
        password_val = 'lme123'
        cmd = ('curl --header "Authorization: Bearer {access_token}" --header '
               '"Content-Type: application/json" --data \'{{"name":"{username_val}", "password":"{password_val}"}}\''
               ' https://www.googleapis.com/sql/v1beta4/projects/{project_id}/instances/{db_server}/users?host=%25&name={username_val} -X PUT '
               ).format(access_token=access_token, db_server=db_server, project_id=project_id,
                        username_val=username_val, password_val=password_val)
        logging.debug("Setting Cloud SQL credentials")
        logging.debug(cmd)
        try:
            output = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, shell=True).communicate()[0]
        except Exception as e:
            print(e)

        self_link = ''
        for line in output.split("\n"):
            line = line.lstrip().rstrip()
            if line and line.find("selfLink") >= 0:
                parts = line.split(" ")
                self_link = parts[1].rstrip().lstrip()
                self_link = self_link.replace(",","").replace("\"","")
                logging.debug("Link for tracking create user operation:%s" % self_link)

        if self_link:
            user_created = False
            track_usr_cmd = ('curl --header "Authorization: Bearer {access_token}" '
                             ' {track_op} -X GET').format(access_token=access_token, track_op=self_link)
            logging.debug("Track user create operation cmd:%s" % track_usr_cmd)
            logging.debug(track_usr_cmd)

            while not user_created:
                try:
                    output = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE, shell=True).communicate()[0]
                except Exception as e:
                    print(e)
                for line in output.split("\n"):
                    line = line.lstrip().rstrip()
                    if line and line.find("status") >= 0:
                        parts = line.split(" ")
                        is_done = parts[1].rstrip().lstrip()
                        if is_done.find("DONE") >= 0:
                            user_created = True
                time.sleep(2)

            logging.debug("Creating user done.")

    def _wait_for_db_instance_to_get_ready(self, access_token, project_id, db_server):
        cmd = ('curl --header "Authorization: Bearer {access_token}" '
               ' https://www.googleapis.com/sql/v1beta4/projects/{project_id}/instances/{db_server} -X GET'
              ).format(access_token=access_token, project_id=project_id, db_server=db_server)

        db_instance_up = False
        while not db_instance_up:
            try:
                output = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, shell=True).communicate()[0]
            except Exception as e:
                print(e)

            for line in output.split("\n"):
                line = line.lstrip().rstrip()
                if line and line.startswith("\"state\""):
                    components = line.split(":")
                    status = components[1].lstrip().rstrip()
                    if status.find('RUNNABLE') >= 0:
                        db_instance_up = True
            time.sleep(2)

    def _get_ip_address_of_db(self, access_token, project_id, db_server):
        cmd = ('curl --header "Authorization: Bearer {access_token}" '
               ' https://www.googleapis.com/sql/v1beta4/projects/{project_id}/instances/{db_server} -X GET'
              ).format(access_token=access_token, project_id=project_id, db_server=db_server)
        logging.debug("Obtaining IP address of the Cloud SQL instance")
        logging.debug(cmd)
        try:
            output = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, shell=True).communicate()[0]
        except Exception as e:
            print(e)

        for line in output.split("\n"):
            line = line.lstrip().rstrip()
            if line and line.startswith("\"ipAddress\""):
                components = line.split(":")
                ip_address = components[1].lstrip().rstrip()
                ip_address = ip_address.replace("\"",'')
                ip_address = ip_address.replace(",",'')
                logging.debug("*** IP Address:[%s]" % ip_address)
                return ip_address

    def _create_database_prev(self, db_ip, access_token, project_id, db_server):
        db_name = 'greetings'
        cmd = ('curl --header "Authorization: Bearer {access_token}" '
               '"Content-Type: application/json" --data \'{{"instance":"{db_server}", "name":"{db_name}", "project":"{project_id}"}}\''
               ' https://www.googleapis.com/sql/v1beta4/projects/{project_id}/instances/{db_server}/databases -X POST'
              ).format(access_token=access_token, project_id=project_id, db_server=db_server, db_name=db_name)
        logging.debug("Creating database")
        logging.debug(cmd)
        try:
            output = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, shell=True).communicate()[0]
        except Exception as e:
            print(e)

    def _create_database(self, db_ip):
        logging.debug("Creating database")

        app_deploy_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir,
                                                         app_name=self.app_name)

        # Read these values from lme.conf file
        db_user = 'lmeroot'
        db_password = 'lme123'
        cmd = (" echo \" create database {db_name} \" | mysql -h{db_ip} --user={db_user} --password={db_password}  ").format(db_ip=db_ip,
                                                                                                                             db_user=db_user,
                                                                                                                             db_password=db_password,
                                                                                                                             db_name=self.service_details['db_name'])
        fp = open(app_deploy_dir + "/create-db.sh", "w")
        fp.write("#!/bin/sh \n")
        fp.write(cmd)
        fp.close()
        perm = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        os.chmod(app_deploy_dir + "/create-db.sh", perm)

        cwd = os.getcwd()
        os.chdir(app_deploy_dir)

        # Create Dockerfile
        df = ("FROM ubuntu:14.04 \n"
              "RUN apt-get update && apt-get install -y mysql-client-core-5.5\n"
              "COPY create-db.sh . \n"
              "CMD ./create-db.sh"
              )
        fp = open(app_deploy_dir + "/Dockerfile.create-db", "w")
        fp.write(df)
        fp.close()

        docker_build_cmd = ("docker build -t {create_db_cont_name} -f Dockerfile.create-db .").format(create_db_cont_name=self.create_db_cont_name)
        logging.debug("Docker build cmd for database create cont:%s" % docker_build_cmd)
        os.system(docker_build_cmd)

        docker_run_cmd = ("docker run -i -t -d {create_db_cont_name}").format(create_db_cont_name=self.create_db_cont_name)
        logging.debug("Docker run cmd for database create cont:%s" % docker_run_cmd)
        os.system(docker_run_cmd)

        os.chdir(cwd)

    # Public interface
    def provision_and_setup(self, access_token):
        db_server = self.app_name + "-" + self.app_version + "-db-instance"
        project_id = self.task_def.app_data['project_id']
        self._deploy_instance(access_token, project_id, db_server)
        self._create_user(access_token, project_id, db_server)
        service_ip = self._get_ip_address_of_db(access_token, project_id, db_server)
        self._create_database(service_ip)
        return service_ip

    def cleanup(self):
        # Stop and remove container generated for creating the database
        if self.task_def.service_data:
            self.docker_handler.stop_container(self.create_db_cont_name, "container created to create db no longer needed.")
            self.docker_handler.remove_container(self.create_db_cont_name, "container created to create db no longer needed.")
            self.docker_handler.remove_container_image(self.create_db_cont_name, "container created to create db no longer needed.")