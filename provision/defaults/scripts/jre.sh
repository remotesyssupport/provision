echo "sun-java6-jre shared/accepted-sun-dlj-v1-1 boolean true" | debconf-set-selections
echo "sun-java6-plugin shared/accepted-sun-dlj-v1-1 boolean true" | debconf-set-selections
cp /etc/apt/sources.list /etc/apt/sources.list.backup
sed s/universe/"universe multiverse/" < /etc/apt/sources.list.backup > /etc/apt/sources.list
apt-get update
apt-get -y install sun-java6-jre sun-java6-plugin sun-java6-fonts
