#!/bin/bash
base_socks_port=9052
base_control_port=8118

# Create data directory if it doesn't exist
if [ ! -d "data" ]; then
	mkdir "data"
fi

for i in {0..9}

do
	j=$((i+1))
	socks_port=$((base_socks_port+i))
	control_port=$((base_control_port+i))
#	http_port=$((base_http_port+i))
	if [ ! -d "data/tor$i" ]; then
		echo "Creating directory data/tor$i"
		mkdir "data/tor$i"
	fi

	echo "Running: tor --RunAsDaemon 1 --CookieAuthentication 0 --HashedControlPassword \"\" --ControlPort $control_port --PidFile tor$i.pid --SocksPort $socks_port --DataDirectory data/tor$i"

	tor --MaxCircuitDirtiness 120 --RunAsDaemon 1 --CookieAuthentication 0 --HashedControlPassword "16:694F2421A51640E760D36519215CF6FAA8F778648D22E2D28536DF0E85" --ControlPort $control_port --PidFile tor$i.pid --SocksPort $socks_port --DataDirectory data/tor$i

done

#haproxy -f rotating.cfg -q -db
