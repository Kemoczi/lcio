# Use the latest Python Version as the base image
FROM python:3.12.0a6-slim-buster

# Setup the working directory for the container
WORKDIR /code

# Copy the requirements file to the container
COPY ./requirements.txt ./

# HTTPS
# RUN apt-get update && apt-get install -y apt-transport-https

# Custom package server
RUN  apt-get update \
  && apt-get install -y wget \
  && rm -rf /var/lib/apt/lists/*


# Install cairo
RUN apt-get update && apt-get install -y libcairo2

# Install exempi
RUN apt-get update && \
    apt-get install -y gnupg
RUN gpg --keyserver hkps://keyserver.ubuntu.com --recv-keys 0xA5D32F012649A5A9
RUN gpg --export 0xA5D32F012649A5A9 | apt-key add -
RUN wget -O- http://neuro.debian.net/lists/buster.de-m.libre | tee /etc/apt/sources.list.d/neurodebian.sources.list
# RUN apt-key adv --recv-keys --keyserver hkps://keyserver.ubuntu.com 0xA5D32F012649A5A9
RUN apt-get update && apt-get install -y libexempi3
RUN apt-get update && apt-get install -y libvips

# Install the Python dependencies using Python 
RUN pip install --no-cache-dir -r requirements.txt

# RUN mkdir ./Supplement/

# Copy suppimages
# COPY ./Supplement/* ./Supplement/

# Copy the rest of the application code to the container
COPY ./ ./

# RUN python django_app/manage.py makemigrations
# RUN python django_app/manage.py migrate

# Setup the command to run when the container starts
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
