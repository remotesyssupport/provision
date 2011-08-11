# http://www.it-slav.net/blogs/2009/02/05/install-and-configure-snmp-on-ubuntu/
apt-get -y install snmpd
mv /etc/snmp/snmpd.conf /etc/snmp/snmpd.conf.orig
echo "rocommunity public" >> /etc/snmp/snmpd.conf
cp /etc/default/snmpd /etc/default/snmpd.orig
sed s/SNMPDOPTS/#SNMPDOPTS/ < /etc/default/snmpd.orig > /etc/default/snmpd
eth1=`ifconfig eth1 | grep -o -E 'inet addr:[0-9.]+' | awk -F: '{print $2}'`
echo -e "\nSNMPDOPTS='-Lsd -Lf /dev/null -u snmp -I -smux -p /var/run/snmpd.pid $eth1'" >> /etc/default/snmpd
/etc/init.d/snmpd restart
