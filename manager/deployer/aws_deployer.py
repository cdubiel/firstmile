import logging
import subprocess
import time
import os

from docker import Client
from common import app
from common import service
from common import utils
from common import docker_lib
from common import constants
from common import fm_logger

from manager.service_handler.mysql import aws_handler as awsh

fmlogging = fm_logger.Logging()

TMP_LOG_FILE = "/tmp/lme-aws-deploy-output.txt"

class AWSDeployer(object):

    def __init__(self, task_def):
        self.task_def = task_def
        #self.logger = logging.getLogger(name=self.__class__.__name__)

        self.services = {}
        self.app_obj = ''

        if self.task_def.app_data:
            self.app_obj = app.App(self.task_def.app_data)
            self.app_dir = task_def.app_data['app_location']
            self.app_name = task_def.app_data['app_name']

        if task_def.service_data:
            self.service_obj = service.Service(task_def.service_data[0])
            if self.service_obj.get_service_type() == 'mysql':
                self.services['mysql'] = awsh.MySQLServiceHandler(self.task_def)

        self.docker_handler = docker_lib.DockerLib()

        self.docker_client = Client(base_url='unix://var/run/docker.sock', version='1.18')

    def _parse_container_id(self, app_cont_name):
        cont_grep_cmd = ("docker ps -a | grep {cont_name} | cut -d ' ' -f 1 ").format(cont_name=app_cont_name)
        fmlogging.debug("Container grep command:%s" % cont_grep_cmd)
        cont_id = subprocess.check_output(cont_grep_cmd, shell=True)
        fmlogging.debug("Container id:%s" % cont_id)
        return cont_id

    def _process_logs(self, cont_id, app_cont_name, app_obj):

        fmlogging.debug("Fetching logs from AWS deployer container")
        logged_status = []

        docker_logs_cmd = ("docker logs {cont_id}").format(cont_id=cont_id)
        fmlogging.debug("Docker logs command:%s" % docker_logs_cmd)
        cname = "1.2.3.4"

        is_env_ok = False
        fmlogging.debug("Parsing statuses from AWS")
        while not is_env_ok:
            log_lines = subprocess.check_output(docker_logs_cmd, shell=True)
            log_lines = log_lines.split("\n")
            for line in log_lines:
                line = line.rstrip().lstrip()
                if line.find("CNAME:") >= 0:
                    stat = line.split(":")
                    cname = stat[1].rstrip().lstrip()
                if line.find("ERROR:") >= 0:
                    stat = line.split(":")
                    error = stat[1].rstrip().lstrip()
                    if error not in logged_status:
                        logged_status.append(error)
                        app_obj.update_app_status(error)
                if line.find("INFO:") >= 0:
                    stat = line.split(":")
                    status = stat[1]
                    if status not in logged_status:
                        logged_status.append(status)
                        a = line.find("INFO:")
                        line = line[a+5:]
                        app_obj.update_app_status(line)
                    if status.lower().find("successfully launched environment") >= 0:
                        is_env_ok = True
            time.sleep(1)

        # Copy out .pem file
        app_dir = self.app_dir + "/" + self.app_name
        fmlogging.debug("AWS - Done reading deploy logs. App dir:%s" % app_dir)
        env_name = utils.read_environment_name(app_dir)
        cont_id = cont_id.rstrip().lstrip()
        cp_cmd = ("docker cp {cont_id}:/src/{env_name}.pem {app_dir}/.").format(cont_id=cont_id,
                                                                                env_name=env_name,
                                                                                app_dir=app_dir)
        os.system(cp_cmd)

        if not cname:
            region = utils.get_aws_region()
            cname = ("http://{env_name}.{region}.elasticbeanstalk.com").format(env_name=env_name, region=region)

        fmlogging.debug("AWS - CNAME:%s" % cname)
        return cname
        
    def _deploy_app_container(self, app_obj):
        app_cont_name = app_obj.get_cont_name()
        
        fmlogging.debug("Deploying app container:%s" % app_cont_name)

        docker_run_cmd = ("docker run -i -t -d {app_container}").format(app_container=app_cont_name)
        cont_id = subprocess.check_output(docker_run_cmd, shell=True)
        cont_id = cont_id.rstrip().lstrip()
        fmlogging.debug("Running container id:%s" % cont_id)

        cname = self._process_logs(cont_id, app_cont_name, app_obj)
        return cname

    def _cleanup(self, app_obj):
        # Remove any temporary container created for service provisioning
        for serv in self.task_def.service_data:
            serv_handler = self.services[serv['service']['type']]
            serv_handler.cleanup()

        # Remove app container
        self.docker_handler.stop_container(app_obj.get_cont_name(),
                                           "container created to deploy application no longer needed.")
        self.docker_handler.remove_container(app_obj.get_cont_name(),
                                             "container created to deploy application no longer needed.")
        self.docker_handler.remove_container_image(app_obj.get_cont_name(),
                                                   "container created to deploy application no longer needed.")
        # Remove app tar file
        app_name = self.app_name
        location = self.app_dir
        utils.delete_tar_file(location, app_name)

    def get_logs(self, info):
        fmlogging.debug("AWS deployer called for getting app logs of app:%s" % info['app_name'])

        app_name = info['app_name']
        app_version = info['app_version']
        app_dir = (constants.APP_STORE_PATH + "/{app_name}/{app_version}/{app_name}").format(app_name=app_name,
                                                                                             app_version=app_version)
        app_version_dir = (constants.APP_STORE_PATH + "/{app_name}/{app_version}").format(app_name=app_name,
                                                                                          app_version=app_version)
        #cwd = os.getcwd()
        #os.chdir(app_dir)

        cont_name = app_name + "-" + app_version + "-retrieve-logs"
        cmd = ("docker run {cont_name}").format(cont_name=cont_name)
        os.system(cmd)

        cmd1 = ("docker ps -a | grep {cont_name} | head -1 | awk '{{print $1}}'").format(cont_name=cont_name)

        cont_id = subprocess.check_output(cmd1, shell=True)
        cont_id = cont_id.rstrip().lstrip()

        # Copy out the log file
        log_file = app_version + constants.RUNTIME_LOG
        cp_cmd = ("docker cp {cont_id}:/src/{log_file} {app_version_dir}/.").format(cont_id=cont_id,
                                                                                    log_file=log_file,
                                                                                    app_version_dir=app_version_dir)

        os.system(cp_cmd)

        self.docker_handler.remove_container(cont_name,
                                             "container created to retrieve app logs no longer needed.")
        self.docker_handler.remove_container_image(cont_name,
                                                   "container created to retrieve app logs no longer needed.")

        ec2_ip_cont = app_name + "-" + app_version + "-getec2-ip"
        self.docker_handler.remove_container_image(ec2_ip_cont,
                                                   "container created to obtain ec2 ip address no longer needed.")

        fmlogging.debug("Retrieving application runtime logs done. Remove intermediate containers.")
        log_cont_name = ("{app_name}-retrieve-logs").format(app_name=cont_name)
        self.docker_handler.remove_container_image(log_cont_name, "Deleting container image created to obtain logs")

        #os.chdir(cwd)

    def deploy_to_secure(self, info):
        fmlogging.debug("AWS deployer called for securing service:%s" % info['service_name'])

        work_dir = ''
        cont_name = ''

        if info['service_name']:
            service_name = info['service_name']
            service_version = info['service_version']
            if not cont_name:
                cont_name = service_name + "-" + service_version + "-status"
            if not work_dir:
                work_dir = (constants.SERVICE_STORE_PATH + "/{service_name}/{service_version}/").format(service_name=service_name,
                                                                                                        service_version=service_version)
        if os.path.exists(work_dir + "/Dockerfile.modify"):
            cmd = ("docker run {cont_name}").format(cont_name=cont_name)
            done = False
            time.sleep(60) # wait for the modification action to kick-in and then check
            while not done:
                err, output = utils.execute_shell_cmd(cmd)
                self.docker_handler.stop_container(cont_name, "Stopping db status check container.")
                self.docker_handler.remove_container(cont_name, "Removing db status check container.")

                lines = output.split("\n")
                print(output)
                for line in lines:
                    instance_available = utils.check_if_available(line)
                    if instance_available:
                        done = True
                        time.sleep(2)
            self.docker_handler.remove_container_image(cont_name, "done modifying RDS instance")

        # update service status to SECURING
        utils.update_service_status(info, constants.SECURING_COMPLETE)

    def deploy_for_delete(self, info):
        work_dir = ''
        cont_name = ''
        artifact_name = ''
        if info['app_name']:
            fmlogging.debug("AWS deployer for called to delete app:%s" % info['app_name'])

            app_name = info['app_name']
            app_version = info['app_version']
            work_dir = (constants.APP_STORE_PATH + "/{app_name}/{app_version}/{app_name}").format(app_name=app_name,
                                                                                                  app_version=app_version)
            cont_name = app_name + "-" + app_version + "-status"
            artifact_name = app_name
        if info['service_name']:
            service_name = info['service_name']
            service_version = info['service_version']
            if not cont_name:
                cont_name = service_name + "-" + service_version + "-status"
            if not work_dir:
                work_dir = (constants.SERVICE_STORE_PATH + "/{service_name}/{service_version}/").format(service_name=service_name,
                                                                                                        service_version=service_version)
        #cwd = os.getcwd()
        #os.chdir(work_dir)

        if os.path.exists(work_dir + "/Dockerfile.status"):
            cmd = ("docker run {cont_name}").format(cont_name=cont_name)
            done = False
            while not done:
                err, output = utils.execute_shell_cmd(cmd)
                self.docker_handler.stop_container(cont_name, "Stopping db status check container.")
                self.docker_handler.remove_container(cont_name, "Removing db status check container.")
                if err.lower().find("not found") >= 0:
                    done = True
                if output.lower().find("not found") >= 0:
                    done = True
                time.sleep(2)
            self.docker_handler.remove_container_image(cont_name, "done deleting database")

        # Deleting the security group by creating container image (and then deleting it)
        if os.path.exists(work_dir + "/Dockerfile.secgroup"):
            delete_sec_group_cont = artifact_name + "-secgroup"
            self.docker_handler.build_container_image(delete_sec_group_cont, work_dir + "/Dockerfile.secgroup", df_context=work_dir)
            self.docker_handler.remove_container_image(delete_sec_group_cont, "deleting security group")
        utils.delete(info)
        #os.chdir(cwd)

    def deploy(self, deploy_type, deploy_name):
        if deploy_type == 'service':
            fmlogging.debug("AWS deployer called for deploying RDS instance")

            service_ip_list = []
            for serv in self.task_def.service_data:
                serv_handler = self.services[serv['service']['type']]
                # Invoke public interface
                utils.update_status(self.service_obj.get_status_file_location(),
                                    constants.DEPLOYING_SERVICE_INSTANCE)
                if self.app_obj:
                    self.app_obj.update_app_status(constants.DEPLOYING_SERVICE_INSTANCE)
                service_ip = serv_handler.provision_and_setup()
                service_ip_list.append(service_ip)
                utils.update_status(self.service_obj.get_status_file_location(),
                                    constants.SERVICE_INSTANCE_DEPLOYMENT_COMPLETE)
                if self.app_obj:
                    self.app_obj.update_app_status(constants.SERVICE_INSTANCE_DEPLOYMENT_COMPLETE)
                utils.save_service_instance_ip(self.service_obj.get_status_file_location(),
                                               service_ip)

            # TODO(devkulkarni): Add support for returning multiple service IPs
            return service_ip_list[0]
        else:
            fmlogging.debug("AWS deployer called for app %s" %
                          self.task_def.app_data['app_name'])
            app_obj = app.App(self.task_def.app_data)
            app_obj.update_app_status(constants.DEPLOYING_APP)
            app_ip_addr = self._deploy_app_container(app_obj)
            app_obj.update_app_status(constants.APP_DEPLOYMENT_COMPLETE)
            app_obj.update_app_ip(app_ip_addr)
            fmlogging.debug("AWS deployment complete.")
            fmlogging.debug("Removing temporary containers created to assist in the deployment.")
            self._cleanup(app_obj)
