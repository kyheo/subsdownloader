#!/bin/bash

ENV_TYPE=dev
ENV_NAME=dev_env

# Create basic virtualenv
virtualenv --no-site-packages $ENV_NAME

# Starter script
echo "source $ENV_NAME/bin/activate" > env_start.sh

# Updater script
echo "source $ENV_NAME/bin/activate" > env_update.sh
echo "" >> env_update.sh
echo "python bootstrap.py" >> env_update.sh
echo "bin/buildout" >> env_update.sh
echo "" >> env_update.sh
echo "deactivate" >> env_update.sh

# Cleaner script
echo "rm -rf bin develop-eggs $ENV_NAME eggs env_start.sh env_update.sh env_clear.sh .installed.cfg parts subsdownloader.egg-info " >> env_clear.sh


# Install needed stuff inside the virtualenv
. ./$ENV_NAME/bin/activate

easy_install zc.buildout

buildout init
python bootstrap.py
bin/buildout install $ENV_TYPE

deactivate
