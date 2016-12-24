'''
Created on Dec 23, 2016

@author: devdatta
'''
import logging
import json
import prettytable
import os
import sys

from cliff.command import Command

import common
import deployment as dp


class ServiceDeploy(Command):
    "Deploy a service"

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(ServiceDeploy, self).get_parser(prog_name)
        return parser
    
    def _read_service_setup_script(self, service_info):
        for serv_type, serv in service_info.iteritems():
            setup_script_path = serv['service']['setup_script']
            if not os.path.exists(setup_script_path):
                logging.error("Setup script path %s does not exist." % setup_script_path)
                sys.exit(0)
            setup_script_fp = open(setup_script_path, "r")
            setup_script_content = setup_script_fp.read()
            serv['service']['setup_script_content'] = setup_script_content
    
    def take_action(self, parsed_args):
        self.log.info('Deploying service')
        
        service_info = common.read_service_info()
        
        self._read_service_setup_script(service_info)
        
        cloud_info = common.read_cloud_info()
        
        self.dep_track_url = dp.Deployment().create_service_instance(service_info, cloud_info)
        self.log.debug("Service deployment tracking url:%s" % self.dep_track_url)

        l = self.dep_track_url.rfind("/")
        dep_id = self.dep_track_url[l+1:]

        x = prettytable.PrettyTable()
        x.field_names = ["Service Name", "Deploy ID", "Cloud"]

        cloud = cloud_info['type']
        for serv in service_info.itervalues():
            service_name = serv['service']['type']
            x.add_row([service_name, dep_id, cloud])
            self.app.stdout.write("%s\n" % x)
            self.log.debug(x)