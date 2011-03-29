echo "deb http://hudson.gotdns.com/debian binary/" >> /etc/apt/sources.list
wget -O - http://hudson-ci.org/debian/hudson-ci.org.key | apt-key add -
apt-get update
apt-get install -y hudson
/etc/init.d/hudson stop
echo 'HUDSON_ARGS=$HUDSON_ARGS" --prefix=/hudson --httpListenAddress=localhost"' >> /etc/default/hudson
/etc/init.d/hudson restart
