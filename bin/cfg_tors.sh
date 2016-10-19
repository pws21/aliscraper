#!/bin/bash
base_socks_port=9052
base_control_port=8118


for i in {0..9}
do
        j=$((i+1))
        socks_port=$((base_socks_port+i))
        control_port=$((base_control_port+i))
        echo "Write cfg for tor$i"
        i=$i socks_port=$socks_port control_port=$control_port envsubst < "tpl.cfg" > /etc/tor/tor$i.cfg
        touch /var/run/tor/tor$i.pid
        chmod 644 /var/run/tor/tor$i.pid
        chown debian-tor:debian-tor  /var/run/tor/tor$i.pid
done

cd /etc/init.d
wget -O tor https://gist.githubusercontent.com/7adietri/9122199/raw/4ed71b894eddbdfb0e241fa06bb583a19f0ccc89/tor
chmod +x tor

