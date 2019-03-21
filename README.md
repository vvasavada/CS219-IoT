# CS219-IoT
CS 219 Cloud Computing Course Project - Developing IoT platform with focus on communication security

## Setup
with a clean repo: `sudo python3 setup.py install`

## Usage
Note: Make sure user_configs.yaml and user_configs.yaml.bck is deleted. Do fresh install: sudo python3 setup.py install.

1/ Run MQTT Broker: python3 broker.py

2/ Register new user through device1: python3 client_register.py

3/ Add another device: python3 client_config.py add_device device2 device2

4/ Add one more device: python3 client_config.py add_device device3 device3

5/ Add publish all ACL: python3 client_config.py add_acl publish all vaibhavagg2/test

6/ Add subscribe all ACL: python3 client_config.py add_acl subscribe all vaibhavagg2/test

7/ Let device2 listen to vaibhavagg2/test and vaibhavagg2/device2/test: python3 client_subscribe_dev2.py

8/ Let device3 listen to vaibhavagg2/test and try to listen to vaibhavagg2/device2/test: python3 client_subscribe_dev3.py

9/ Publish message to vaibhavagg2/test so both can receive: python3 client_publish.py vaibhavagg2/test

10/ Publish message to vaibhavagg2/device2/test and only device2 can receive: python3 client_publish.py vaibhavagg2/device2/test
