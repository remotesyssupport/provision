# Install libcloud and deps in virtual env
apt-get install -y python2.6-dev gcc
apt-get install -y python-virtualenv
virtualenv env
source ./env/bin/activate && easy_install nose
source ./env/bin/activate && easy_install pycrypto
source ./env/bin/activate && easy_install paramiko
source ./env/bin/activate && mkdir -p ~/pkg && cd ~/pkg && wget http://www.ibiblio.org/pub/mirrors/apache//incubator/libcloud/apache-libcloud-incubating-0.4.1.tar.bz2 && tar jxf apache-libcloud-incubating-0.4.0.tar.bz2 && cd apache-libcloud-0.4.0 && python setup.py install