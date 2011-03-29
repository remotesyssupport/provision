DEBIAN_FRONTEND="noninteractive" apt-get -y install python-pip python-virtualenv python-argparse
pip install virtualenvwrapper
export WORKON_HOME=~/envs && mkdir -p $WORKON_HOME
echo 'export WORKON_HOME=~/envs' >> ~/.bashrc
echo 'source /usr/local/bin/virtualenvwrapper.sh' >> ~/.bashrc
