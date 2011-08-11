import unittest

import provision.config as config
import provision.nodelib as nodelib

class Test(unittest.TestCase):

    def setUp(self):

        self.submap = {'ci_user_host': 'testuser@testhost',}

        self.format_string_script = '''# provision-template-type: format-string
scp -pr -o StrictHostKeyChecking=no {ci_user_host}:pkg/libcloud .
'''
        self.template_string_script = '''# provision-template-type: template-string
scp -pr -o StrictHostKeyChecking=no ${ci_user_host}:pkg/libcloud .
'''
        self.template_string_script_simple = ''' # provision-template-type: template-string
scp -pr -o StrictHostKeyChecking=no $ci_user_host:pkg/libcloud .'''

        self.template_script_unsupported_type = '''# provision-template-type: mako
scp -pr -o StrictHostKeyChecking=no ${ci_user_host}:pkg/libcloud .
'''
        self.non_template_script = '''apt-get -y install python-setuptools python-dev gcc
'''
        # don't do this
        self.multiple_specifiers_one_line = '''
# provision-template-type: format-string provision-template-type: template-string
apt-get -y install python-setuptools python-dev gcc
'''
        # or this
        self.multiple_specifiers_multiple_lines = '''
# provision-template-type: format-string
# provision-template-type: template-string
apt-get -y install python-setuptools python-dev gcc
'''
        self.bash_function = '''# provision-template-type: template-string
download_file() {
  echo wget -q -O $DOWNLOAD_DIR/$1 $2
  wget -q -O $DOWNLOAD_DIR/$1 $2
  http_rc=$?
  if [[ "$http_rc" != "0" ]]; then
    echo "Download of $1 failed, return code was $http_rc"
    exit 1
  fi
  if [ ! -f $DOWNLOAD_DIR/$1 ]; then
    echo "Downloaded file $1 not found"
    exit 1
  fi
}
'''
        self.awk_function = '''# provision-template-type: template-string
eth1=`ifconfig eth1 | grep -o -E 'inet addr:[0-9.]+' | awk -F: '{print $2}'`'''


    def test_format_strings_detection(self):
        assert 'format-string' == \
            config.TEMPLATE_RE.search(self.format_string_script).groupdict()['type']

    def test_template_strings_detection(self):
        assert 'template-string' == \
            config.TEMPLATE_RE.search(self.template_string_script).groupdict()['type']

    def test_multiple_specifiers_one_line(self):
        assert 'template-string' == \
            config.TEMPLATE_RE.search(self.multiple_specifiers_one_line).groupdict()['type']

    def test_multiple_specifiers_multiple_lines(self):
        assert 'format-string' == \
            config.TEMPLATE_RE.search(self.multiple_specifiers_multiple_lines).groupdict()['type']

    def test_bash_function_unchanged(self):
        assert self.bash_function == nodelib.substitute(
            self.bash_function, self.submap)

    def test_awk_function_unchanged(self):
        assert self.awk_function == nodelib.substitute(
            self.awk_function, self.submap)

    def test_format_string_substitution(self):
        assert nodelib.substitute(self.format_string_script, self.submap).find(
            self.submap['ci_user_host']) > 0

    def test_template_string_substitution(self):
        assert nodelib.substitute(self.template_string_script, self.submap).find(
            self.submap['ci_user_host']) > 0

    def test_template_string_simple_substitution(self):
        assert nodelib.substitute(self.template_string_script_simple, self.submap).find(
            self.submap['ci_user_host']) > 0

    def test_template_script_unsupported_type(self):
        try:
            nodelib.substitute(self.template_script_unsupported_type, self.submap)
            self.fail()
        except KeyError:
            pass
