# USE: from ldc-bpcsad directory, run:
#
#          docker build -f Dockerfile
FROM ubuntu:20.04
MAINTAINER Neville Ryant "nryant@ldc.upenn.edu"

COPY . /ldc-bpcsad
WORKDIR /ldc-bpcsad

RUN apt-get update -yqq && apt-get install -yqq --no-install-recommends gcc-multilib make patch libsndfile1 python3 python3-pip
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 0
RUN update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 0
RUN ./tools/install_htk.sh ./src/HTK-3.4.1.tar.gz 
RUN pip install .

ENTRYPOINT ["/bin/bash", "-lc", "--"]