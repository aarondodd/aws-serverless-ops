#!/bin/bash

#positional argument processing
HOST=$1
PORT=$2
USER=$3
PASSWORD=$4
DATABASES=$5
s3_bucket=$6
s3_path=$7

#HOST=serverlessops1.cluster-czpi934xq9hf.us-east-1.rds.amazonaws.com
#USER=admin
#PASSWORD=Password01

db_dir=/tmp/db_backups
date_format=`date +%Y-%m-%d_%H-%M`
#s3_bucket=aws-acd-serverlessops-backups
#s3_path=$HOST

if [ ! -d $db_dir ]; then
   mkdir -p $db_dir
fi

for db in $DATABASES; do
  echo "Dumping database: $db"
  mysqldump -u$USER -h$HOST -p$PASSWORD --databases $db > $db_dir/$db-$date_format.sql
  if [ $? -ne 0 ]; then exit 1; fi

  echo "Compressing database: $db"
  tar -zcvf $db_dir/$db-$date_format.tgz $db_dir/$db-$date_format.sql
  if [ $? -ne 0 ]; then exit 1; fi

  echo "Uploading database: $db"
  aws s3 cp $db_dir/$db-$date_format.tgz s3://$s3_bucket/$s3_path/
  if [ $? -ne 0 ]; then exit 1; fi
done
exit 0
