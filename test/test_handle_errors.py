import unittest

import libcloud.types

import provision.config as config

class Test(unittest.TestCase):

    def setUp(self):
        self.devnull = open('/dev/null', 'w')

    def tearDown(self):
        self.devnull.close()

    def test_handle_errors_simple_success(self):
        assert config.handle_errors(lambda: 0) == 0

    def test_handle_errors_parsed_success(self):
        assert config.handle_errors(lambda parsed: 0, object()) == 0

    def test_handle_errors_simple_fail(self):
        assert config.handle_errors(lambda: 1) == 1

    def test_handle_errors_generic_exception(self):
        def raises():
             raise Exception()
        assert config.handle_errors(raises, out=self.devnull) == config.EXCEPTION

    def test_handle_errors_service_unavailable(self):
        def raises():
             raise libcloud.types.MalformedResponseError(
                 "Failed to parse XML", body='Service Unavailable', driver=object())
        assert config.handle_errors(raises, out=self.devnull) == config.SERVICE_UNAVAILABLE

    def test_handle_errors_malformed_response(self):
        def raises():
             raise libcloud.types.MalformedResponseError(
                 "Failed to parse XML", body='A bad response', driver=object())
        assert config.handle_errors(raises, out=self.devnull) == config.MALFORMED_RESPONSE

    def test_handle_errors_timeout(self):
        def raises():
            try:
                None.open_sftp_client
            except AttributeError as e:
                raise libcloud.types.DeploymentError(object(), e)
        assert config.handle_errors(raises, out=self.devnull) == config.TIMEOUT

    def test_handle_errors_deployment_error(self):
        def raises():
            try:
                None.foo
            except AttributeError as e:
                raise libcloud.types.DeploymentError(object(), e)
        assert config.handle_errors(raises, out=self.devnull) == config.DEPLOYMENT_ERROR
