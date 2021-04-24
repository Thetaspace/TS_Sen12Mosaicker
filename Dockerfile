# use debian as base image
FROM debian:latest

# get list of installable packets and install wget
RUN apt-get update && \
    apt-get -y install \
        'wget'

# download snap installer version 7.0
RUN wget http://step.esa.int/downloads/7.0/installers/esa-snap_sentinel_unix_7_0.sh

#change file execution rights for snap installer
RUN chmod +x esa-snap_sentinel_unix_7_0.sh

# install snap with gpt
RUN ./esa-snap_sentinel_unix_7_0.sh -q

# link gpt so it can be used systemwide
RUN ln -s /usr/local/snap/bin/gpt /usr/bin/gpt

# set gpt max memory to 16GB
RUN sed -i -e 's/-Xmx1G/-Xmx16G/g' /usr/local/snap/bin/gpt.vmoptions

# install jdk and python3 with required modules
RUN apt-get -y install default-jdk python python-pip git maven python-jpy
RUN python -m pip install --user --upgrade setuptools wheel

# set JDK_HOME env
ENV JDK_HOME="/usr/lib/jvm/default-java"
ENV JAVA_HOME=$JDK_HOME
ENV PATH=$PATH:/root/.local/bin

# install snappy the SNAP python module
RUN /usr/local/snap/bin/snappy-conf /usr/bin/python
RUN cd /root/.snap/snap-python/snappy/ && \
    python setup.py install
RUN ln -s /root/.snap/snap-python/snappy /usr/lib/python2.7/dist-packages/snappy

# copy python files and install dependencies
#COPY ./api python-app/
#WORKDIR /python-app
#RUN python -m pip install --user -r requirements.txt

# update snap
RUN snap --nosplash --nogui --modules --update-all

# clone the TS_Sen12Mosaicker repository, set workdir and install python dependencies
RUN git clone https://github.com/Thetaspace/TS_Sen12Mosaicker.git
WORKDIR /TS_Sen12Mosaicker
RUN python -m pip install --user -r requirements.txt

