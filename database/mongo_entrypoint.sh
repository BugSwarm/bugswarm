#!/bin/bash

nohup mongod --bind_ip ::,0.0.0.0 &
sleep 2
mongorestore /root/bugswarm/database/dump
sed -i 's/<host>/localhost/g' /root/bugswarm/database/database/config.py
sed -i 's/<dbname>/bugswarm/g' /root/bugswarm/database/database/config.py
chmod 444 /root/bugswarm/database/database/config.py
nohup python3 /root/bugswarm/database/run.py &
