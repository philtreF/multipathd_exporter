import subprocess
import time
import re
import shlex
import yaml
import sys
import getopt
from prometheus_client import start_http_server, Gauge



def multipath_parse():
    """
    Some documentation
    https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/7/html/dm_multipath/mpio_output
    """

    """
    This code is intended for production. Remote developing is done
    using a file
    multipath_process = subprocess.Popen(multiprocess_command,
    stdout=subprocess.PIPE, shell=True)
    multiprocess_command_output = multipath_process.stdout.read()
    assert multipath_process.wait() == 0
    """

    h = open("multipath_ll.var")
    hdata = h.read()
    hdata_table = hdata.split("\n")
    parsed_data = []
    temp_parsing_data = {}
    path_index = 0
    this_is_a_new_block = False
    for hdata_line in hdata_table:
        # If line starts with a character we assume this is a header
        if re.match(r"^\w", hdata_line):
            if re.match("^size", hdata_line):
                # This is the second header line
                temp_parsing_data.update({"size":
                                         str(shlex.split(hdata_line)[0])})
                temp_parsing_data.update({"features":
                                         shlex.split(hdata_line)[1]})
                temp_parsing_data.update({"hwhandler":
                                         shlex.split(hdata_line)[2]})
                temp_parsing_data.update({"write_permission":
                                         shlex.split(hdata_line)[3]})
            else:
                # This is the first header line
                this_is_a_new_block = True
                """ As this is the first line of a new block
                we copy and reset tables if not in first object
                """
                if len(temp_parsing_data) > 0 and this_is_a_new_block:
                    # import pdb; pdb.set_trace()
                    # if first_loop:
                        # first_loop = False
                    # else:
                    parsed_data.append(temp_parsing_data.copy())
                    temp_parsing_data.clear()
                    this_is_a_new_block = False
                # First, check if an alias is set :
                if re.match(r"^.*\([\w]{33}\)", hdata_line):
                    """There is an alias
                    TODO: This part of code should work but has to be tested
                    """
                    temp_parsing_data.update({"alias":
                                             shlex.split(hdata_line)[0]})
                    temp_parsing_data.update({"wwid":
                                             shlex.split(hdata_line)[1]})
                    temp_parsing_data.update({"dm_device_name":
                                             shlex.split(hdata_line)[2]})
                    temp_parsing_data.update({"vendor":
                                             shlex.split(hdata_line)[3]})

                elif re.match(r"^[\w]{33} ", hdata_line):
                    # There is no alias
                    temp_parsing_data.update({"wwid":
                                             shlex.split(hdata_line)[0]})
                    temp_parsing_data.update({"dm_device_name":
                                             shlex.split(hdata_line)[1]})
                    temp_parsing_data.update({"vendor":
                                             shlex.split(hdata_line)[2]})
                else:
                    raise  # Something went wrong
        else:  # This lines starts with some kind of a symbol
            if re.match(r".*-\+-", hdata_line):
                # This is a path group
                temp_parsing_data.update({"scheduling_policy":
                                         shlex.split(hdata_line)[1]})
                temp_parsing_data.update({"prio": shlex.split(hdata_line)[2]})
                temp_parsing_data.update({"status":
                                         shlex.split(hdata_line)[3]})
                path_index = 0  # we are before pathes resetting pathes_index
            elif re.match(".*-", hdata_line):
                # this is a path
                path_array = []
                cleaned_line = str(re.findall("^.*- (.*).*$", hdata_line)[0])
                path_array.append({"path": cleaned_line.split()[0]})
                path_array.append({"devnode": cleaned_line.split()[1]})
                path_array.append({"major:minor": cleaned_line.split()[2]})
                path_array.append({"dm_status": cleaned_line.split()[3]})
                path_array.append({"path_status": cleaned_line.split()[4]})
                path_array.append({"online_status": cleaned_line.split()[5]})
                temp_parsing_data.update({"path" +
                                         str(path_index): path_array.copy()})
                del(path_array)
                path_index = path_index + 1

    if len(temp_parsing_data) > 0:
        parsed_data.append(temp_parsing_data.copy())
        temp_parsing_data.clear()
    return parsed_data


def get_path_count(parsed_data):
    """
    Now we have parsed_data array populated with all interresting data
    Now have a look on data which would be interresting to be monitored
    with Prometheus.
    Here is a quick TODO list :
    - identified by WWID :
    - number of active path
    - number of inactive path
    """
    result_array = []
    for path in parsed_data:
        # In a first time we will search the number of path available
        wwid = path.get("wwid")
        count_path = 0
        for key in path.keys():
            if re.match(r"^path\d+$", key):
                count_path = count_path + 1
        result_dict = dict()
        result_dict = {str(wwid): str(count_path)}
        result_array.append(result_dict)
    return result_array


def main(argv):
    # First check args in order to get configuration file path
    configuration_file_path = ""
    usage_to_print = "{} --config <configurationfile>".format(__file__)
    try:
        opts, args = getopt.getopt(argv, "h", ["config="])
    except getopt.GetoptError:
        print(usage_to_print)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(usage_to_print)
            sys.exit()
        elif opt == "--config":
            configuration_file_path = arg
    # Checking for mandatory options
    if configuration_file_path == "":
        print(usage_to_print)
        sys.exit(2)

    # Now open this configuration file
    configuration_file = open(configuration_file_path, 'r')
    configuration = yaml.load(configuration_file)
    # And try to get needed keys
    if configuration.get('command') is None \
            or configuration.get('http_server_port') is None \
            or configuration.get('sleep_seconds') is None:
        print("Configuration error, you should have a look on README file")
        sys.exit(3)

    # Start up the server to expose the metrics.
    start_http_server(configuration.get('http_server_port'))
    # Generate some requests.
    # wwid = Prometheus_objects()
    prometheus_objects = {}
    while True:
        parsed_data = multipath_parse()
        path_count_by_wwid = get_path_count(parsed_data)
        for path in path_count_by_wwid:
            wwid = str(next(iter(path.keys())))
            if not prometheus_objects.get(wwid):
                prometheus_objects[wwid] = Gauge('path_' + wwid,
                                                 'another wwid path count')
            # Let's update all data
            prometheus_objects[wwid].set(int(next(iter(path.values()))))
        time.sleep(configuration.get('sleep_seconds'))

if __name__ == '__main__':
    main(sys.argv[1:])
