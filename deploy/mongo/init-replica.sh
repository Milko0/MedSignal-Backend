#!/bin/sh
# Initiates the 3-member replica set once; mongo1 gets priority 2 so it is the usual primary.
until mongosh --host mongo1 --quiet --eval "db.adminCommand('ping')" >/dev/null 2>&1; do sleep 2; done
mongosh --host mongo1 --quiet --eval '
try { rs.status(); print("replica set already initiated") }
catch (e) {
  rs.initiate({ _id: "rs0", members: [
    { _id: 0, host: "mongo1:27017", priority: 2 },
    { _id: 1, host: "mongo2:27017" },
    { _id: 2, host: "mongo3:27017" } ] });
  print("replica set initiated")
}'
