FROM amazonlinux

# RUN on one line, one layer for all packages
RUN yum -y update && \
  yum -y install mysql && \
  yum -y install python3 && \
  python3 -m pip install boto3

WORKDIR /root

# Layer for our scripts
COPY worker.py .

# Entrypoint for prod
# call worker.py specifying this is a task from ECS launch 
# (thought is to use same logic from lambda and ECS and handle inputs/outputs differences appropriately)
ENTRYPOINT ["python3", "/root/worker.py", "ecstask"]