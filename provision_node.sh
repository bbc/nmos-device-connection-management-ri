#!/usr/bin/env bash

# Copyright 2017 British Broadcasting Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install python-pip devscripts apache2 apache2-dev debhelper -y
pip install --upgrade pip

pip install setuptools

cd /home/vagrant

git clone https://github.com/bbc/nmos-common.git
git clone https://github.com/bbc/nmos-reverse-proxy.git

cd /home/vagrant/nmos-common
python setup.py install

cd /home/vagrant/nmos-reverse-proxy
make deb
dpkg -i ../nmos-reverse-proxy_*_all.deb
sudo apt-get -f -y install


cd /vagrant
python setup.py install

cp -r /vagrant/bin/connectionmanagement /usr/bin
cp -r /vagrant/share/ipp-connectionmanagement /usr/share
cp -r /vagrant/etc/apache2/sites-available/*.conf /etc/apache2/sites-available/
cp -r /vagrant/etc/init/nmosconnection.conf /etc/init
cp -r /vagrant/lib/systemd/system/nmosconnection.service /lib/systemd/system
cp -r /vagrant/var/www/connectionManagementDriver /var/www
cp -r /vagrant/var/www/connectionManagementUI /var/www
chmod +x /usr/bin/connectionmanagement

ln -s /lib/init/upstart-job /etc/init.d/nmosconnection
ln -s /lib/systemd/system/nmosconnection.service /etc/systemd/system/multi-user.target.wants/nmosconnection.service

service nmosconnection start
service apache2 restart
a2ensite nmos-ui.conf
service apache2 reload
