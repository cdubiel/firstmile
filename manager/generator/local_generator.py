'''
Created on Oct 26, 2016

@author: devdatta
'''
import logging


class LocalGenerator(object):

    def __init__(self, task_def):
        self.task_def = task_def
        if self.task_def.app_data:
            self.app_type = task_def.app_data['app_type']
            self.app_dir = task_def.app_data['app_location']
            self.app_name = task_def.app_data['app_name']

    def _generate_for_service(self):
        pass

    def _generate_for_python_app(self, service_ip_dict):
        
        DB = ''
        db_name = ''
        USER = ''
        PASSWORD = ''
        HOST = ''
        host = ''
        
        if bool(service_ip_dict):
            serv = self.task_def.service_data[0]
            service_name = serv['service_name']

            DB = serv['service_details']['db_var']
            db_name = serv['service_details']['db_name']
            USER = serv['service_details']['user_var']
            PASSWORD = serv['service_details']['password_var']
            HOST = serv['service_details']['host_var']

            for k, v in service_ip_dict.items():
                if k == service_name:
                    host = v

        entry_point = self.task_def.app_data['entry_point']

        df = ''
        if bool(service_ip_dict):
            df = ("FROM ubuntu:14.04\n"
                  "RUN apt-get update -y\n"
                  "RUN apt-get install -y python-setuptools python-pip\n"
                  "ADD requirements.txt /src/requirements.txt\n"
                  "RUN cd /src; pip install -r requirements.txt\n"
                  "ADD . /src\n"
                  "EXPOSE 5000\n"
                  "ENV {DB} {db_name}\n"
                  "ENV {USER} lmeuser\n"
                  "ENV {PASSWORD} lmeuserpass\n"
                  "ENV {HOST} {host}\n"
                  "CMD [\"python\", \"/src/application.py\"]"
                  "").format(DB=DB, db_name=db_name, USER=USER,
                             PASSWORD=PASSWORD, HOST=HOST, host=host, run_cmd=entry_point)
        else:
            df = ("FROM ubuntu:14.04\n"
                  "RUN apt-get update -y\n"
                  "RUN apt-get install -y python-setuptools python-pip\n"
                  "ADD requirements.txt /src/requirements.txt\n"
                  "RUN cd /src; pip install -r requirements.txt\n"
                  "ADD . /src\n"
                  "EXPOSE 5000\n"
                  )

            env_var_obj = self.task_def.app_data['env_variables']
            env_vars = ''
            if env_var_obj:
                for key, value in env_var_obj.iteritems():
                    env_vars = env_vars + ("ENV {key} {value}\n").format(key=key, value=value)
                df = df + env_vars

            df = df +  ("CMD [\"python\", \"/src/{entry_point}\"]").format(entry_point=entry_point)

        logging.debug("App dir: %s" % self.app_dir)
        docker_file_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir, 
                                                          app_name=self.app_name)
        logging.debug("Dockerfile dir:%s" % docker_file_dir)
        docker_file = open(docker_file_dir + "/Dockerfile", "w")
        docker_file.write(df)
        docker_file.close()

    def generate(self, generate_type, service_ip_dict):
        if generate_type == 'service':
            self._generate_for_service()
        elif generate_type == 'app':
            logging.debug("Local generator called for app %s" %
                          self.task_def.app_data['app_name'])
            if self.app_type == 'python':
                self._generate_for_python_app(service_ip_dict)
            else:
                print("Application of type %s not supported." % self.app_type)
        return 0