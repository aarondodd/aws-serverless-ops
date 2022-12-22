FROM amazonlinux

WORKDIR /root

# RUN on one line, one layer for all packages
RUN yum -y update && \
  yum -y install mysql python3 tar curl unzip && \
  python3 -m pip install boto3

# Install AWSCLIv2
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "/tmp/awscliv2.zip" && \
  unzip /tmp/awscliv2.zip -d /tmp && \
  /tmp/aws/install && \
  rm /tmp/awscliv2.zip && \
  rm -rf /tmp/aws 

# Layer for our scripts
COPY worker.py db_backup.sh ./

# Entrypoint for prod
# call worker.py specifying this is a task from ECS launch 
# (thought is to use same logic from lambda and ECS and handle inputs/outputs differences appropriately)
ENTRYPOINT ["python3", "/root/worker.py", "ecstask"]