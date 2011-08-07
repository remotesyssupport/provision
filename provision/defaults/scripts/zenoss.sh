echo "deb http://dev.zenoss.org/deb main stable" > /etc/apt/sources.list.d/zenoss.list
apt-get update
apt-get -y --force-yes install zenoss-stack
/etc/init.d/zenoss-stack start
