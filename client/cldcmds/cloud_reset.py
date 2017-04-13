'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com> January 23, 2017

@author: devdatta
'''

from cliff.command import Command

import common

class CloudReset(Command):
    "Reset cloud setup in FirstMile sandbox"

    def get_parser(self, prog_name):
        parser = super(CloudReset, self).get_parser(prog_name)
        parser.add_argument('--cloud',
                                 dest='cloud',
                                 help="Name of the cloud (google, aws)")
        return parser

    def _reset_google(self):
        common.reset_google()

    def _reset_aws(self):
        common.reset_aws()

    def take_action(self, parsed_args):
        dest = parsed_args.cloud
        if dest:
            dest = dest.lower()
            self.log.debug("Destination:%s" % dest)
        else:
            dest = raw_input("Please enter Cloud deployment target>")
            dest = dest.rstrip().lstrip().lower()

        common.verify_cloud(dest)

        if parsed_args.cloud == 'google':
            self._reset_google()
        if parsed_args.cloud == 'aws':
            self._reset_aws()
        if dest == 'local-docker':
            print("No reset required for local-docker")
            exit()
