class LighttpdHackMiddleware(object):
    def __init__(self, app, script_name=''):
        self.app = app
        self.script_name = script_name

    def __call__(self, environ, start_response):
        # overwrite SCRIPT_NAME
        environ['SCRIPT_NAME'] = self.script_name
        return self.app(environ, start_response)
