#!/bin/bash
cd /home/mavit/src/trafficlimits
mkdir temp
export PYTHONPATH=./temp
python setup.py build develop --install-dir ./temp
cp ./temp/TrafficLimits.egg-link /home/mavit/.config/deluge/plugins
rm -fr ./temp
