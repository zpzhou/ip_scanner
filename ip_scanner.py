#-------------------------------------------------------------------------------
# Name:        IP Scanner
# Purpose:     Given a subnet and range, scans for all IP addresses
#              in the subnet within the range.
#
# Author:      Peter Zhou
#
# Created:     18-05-2017
# Copyright:   (c) PBES 2017
# Licence:     <your licence>
#-------------------------------------------------------------------------------

from platform import system as system_name  # Type of OS
import subprocess                           # subprocesses to execute ping

class cl_sub_process_spawner():

    _MAX_SUB_PROCESSES = 100

    def __init__(self, ip_list, fn_update_scan_progress_cb):

        # reference to list of IPs to ping
        self.ip_list = ip_list

        # function to increment gauge
        self._fn_update_scan_progress = fn_update_scan_progress_cb

        # to store spawned subprocesses
        self.sub_process_dict = dict()

        # set to false to stop spawn
        self._running = True

    def _fn_spawn(self):

        ip_list_len = len(self.ip_list)

        # ping all ip addresses within range
        step = self._MAX_SUB_PROCESSES
        for i in range(0, ip_list_len, step):

            # end position of subset within ip_set
            end = i + step

            # end position past the range of ip_set
            if end > ip_list_len:
                end = ip_list_len

            # send out pings sequentially
            for j in range(i, end):

                if self._running == False:
                    self._fn_terminate_sub_processes()
                    break

                else:

                    self._fn_ping(self.ip_list[j])

            # wait for replies
            self._fn_wait_for_replies()

    def _fn_wait_for_replies(self):

        for key in self.sub_process_dict.keys():

            sub_process = self.sub_process_dict[key]
            sub_process.wait()                              # wait for process to finish

            self._fn_process_ping(key, sub_process.returncode)
            del self.sub_process_dict[key]

    def _fn_ping(self, host):
        """
        Pings the host IP address specified by creating a subprocess,
        and creates an (host, sub_process) entry in the subprocess dictionary
        """
        # determine parameters from OS and execute ping
        if system_name().lower() == "windows":
            sub_process = subprocess.Popen(['ping', '-n', '1', host], stdout=subprocess.PIPE)
        else:
            sub_process = subprocess.Popen(['ping', '-c', '1', host], stdout=subprocess.PIPE)

        # append subprocess to list before returning
        self.sub_process_dict[host] = sub_process
        return

    def _fn_process_ping(self, ip, reply):

        result = (ip, reply == 0)
        self._fn_update_scan_progress(result)

    def _fn_terminate_sub_processes(self):

        self._running = False
        for key in self.sub_process_dict.keys():
            self.sub_process_dict[key].terminate()


class cl_ip_scanner():

    _MAX_FIELDS = 4

    def __init__(self,
                 prefix_list,
                 range_list,
                 fn_set_gauge_range_cb,
                 fn_update_scan_progress_cb,
                 fn_start_timer_cb):

        # needed data and functions from GUI class
        self.prefix_list = prefix_list
        self.range_list = range_list
        self._fn_set_gauge_range = fn_set_gauge_range_cb
        self._fn_update_scan_progress = fn_update_scan_progress_cb
        self._fn_start_timer = fn_start_timer_cb

        # to hold created threads
        self.thread_list = list()

    def _check_active_ips(self):

        # obtain subnet prefix
        prefix, prefix_len = get_subnet_prefix(self.prefix_list)

        # generate all ip addresses within range
        ip_list = list()
        starting_byte = self._MAX_FIELDS - prefix_len - 1
        get_in_range_ips(prefix, self.range_list, ip_list, starting_byte)
        ip_list_len = len(ip_list)

        # set timer and estimated run time with number of ips generated
        self._fn_start_timer(ip_list_len)

        # set range of progress bar
        self._fn_set_gauge_range(ip_list_len)

        # instantiate subprocess spawner
        self.sub_process_spawner = cl_sub_process_spawner(ip_list,
                                                      self._fn_update_scan_progress)

        # spawn subprocesses to execute pings
        self.sub_process_spawner._fn_spawn()

    def _fn_stop_scan(self):

        self.sub_process_spawner._fn_terminate_sub_processes()


def get_subnet_prefix(prefix_list):
    prefix_len = len(prefix_list)
    prefix = '.'.join(prefix_list)

    return prefix, prefix_len

def get_in_range_ips(prefix, ranges, ip_list, byte ):

    if byte < 0:
       return ip_list.append(prefix)

    index = byte - len(ranges) + 1
    cur_range = ranges[index]
    start = int(cur_range[0])
    end = int(cur_range[1])

    if byte == 0:
        for val in range(start, end+1):
            ip = prefix + '.{}'.format(str(val))
            ip_list.append(ip)
        return
    else:
        temp = list()
        for val in range(start, end+1):
            ip = prefix + '.{}'.format(str(val))
            temp.append(ip)

        for ip in temp:
            get_in_range_ips(ip, ranges, ip_list, byte - 1)


#----------------------------------------------------------------------------------------

def main():

    ip_list = list()
    prefix = '10.11'
    ranges = [(0,255),(0,255)]
    byte = 1

    get_in_range_ips(prefix, ranges, ip_list, byte)
    for ip in ip_list:
        print ip

if __name__ == '__main__':
    main()