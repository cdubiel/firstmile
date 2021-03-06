import sys

from cliff.app import App
from cliff.commandmanager import CommandManager


class CLDApp(App):

    def __init__(self):
        super(CLDApp, self).__init__(
            description='Multi-cloud application orchestration and service provisioning CLI.',
            version='1.0.0.rc2',
            command_manager=CommandManager('cld.cmds'),
            deferred_help=True,
            )

    def initialize_app(self, argv):
        self.LOG.debug('initialize_app %s' % argv)

    def prepare_to_run_command(self, cmd):
        self.LOG.debug('prepare_to_run_command %s', cmd.__class__.__name__)

    def clean_up(self, cmd, result, err):
        self.LOG.debug('clean_up %s', cmd.__class__.__name__)
        if err:
            self.LOG.debug('got an error: %s', err)


def main(argv=sys.argv[1:]):
    myapp = CLDApp()
    return myapp.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
