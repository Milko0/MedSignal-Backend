#!/bin/sh
# Run ONCE from VM1 after the mongo containers are up on all three VMs.
# usage: ./init-replica-lab.sh VM1_IP VM2_IP VM3_IP
docker compose -f docker-compose.node.yml exec -T mongo mongosh --quiet --eval "rs.initiate({_id:'rs0',members:[{_id:0,host:'$1:27017',priority:2},{_id:1,host:'$2:27017'},{_id:2,host:'$3:27017'}]})"
