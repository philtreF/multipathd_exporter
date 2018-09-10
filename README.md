# multipathd_exporter
This is a GNU GPL Prometheus exporter for multipathd

- Current project status is : *Alpha :* I need to test it in a real environment as development is done using a sample text file
- Current focus is to make it work in a real environment
- Testings are done in a Centos 7 environment
- Pull requests and issues will be welcome as soon as I will have made the first tests.

## Features

- path count per wwid

This script is already parsing all data output from `multipath -ll` command, it will be easy to add other features in the future if needed

## installation and usage

Installation process is straight-forward. You need a python3 environment with theses dependencies : 
 - python yaml package
 - python prometheus_client package

Exporter is launched using this command : 

```
python3 prometheus_multipathll_exporter.py --config=prometheus_multipathll_exporter.yaml
```

## configuration
The configuration file provided with this exporter contains all configurable options. Feel free to edit it.





