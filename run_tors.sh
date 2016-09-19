#!/bin/bash
base_socks_port=9052
#base_http_port=3129 # leave 3128 for HAProxy
base_control_port=8118

# Create data directory if it doesn't exist
if [ ! -d "data" ]; then
	mkdir "data"
fi

#for i in {0..10}
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
	# Take into account that authentication for the control port is disabled. Must be used in secure and controlled environments

	echo "Running: tor --RunAsDaemon 1 --CookieAuthentication 0 --HashedControlPassword \"\" --ControlPort $control_port --PidFile tor$i.pid --SocksPort $socks_port --DataDirectory data/tor$i"

	tor  --RunAsDaemon 1 --CookieAuthentication 0 --HashedControlPassword "16:694F2421A51640E760D36519215CF6FAA8F778648D22E2D28536DF0E85" --ControlPort $control_port --PidFile tor$i.pid --SocksPort $socks_port --DataDirectory data/tor$i

#	echo 	"Running: ./delegate/src/delegated -P$http_port SERVER=http SOCKS=localhost:$socks_port"

#	./delegate/src/delegated -P$http_port SERVER=http SOCKS=localhost:$socks_port
done

haproxy -f rotating.cfg -q -db
