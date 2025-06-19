# Ping Monitor Script

This script allows you to monitor the availability of multiple hosts using ICMP ping commands. You can specify the hosts directly as arguments, provide them through a file, set the interval between checks, and control the monitoring process behavior.

## Usage

``` bash
python pinger.py [options] hosts
```

## Arguments
### Hosts (positional argument): A list of IP addresses of the hosts to monitor. Example: 192.168.1.1 192.168.1.2.
## Options
 ```
-f, --file (optional): Path to a file containing a list of IP addresses, one per line. If specified, the hosts argument will be ignored.
-i, --interval (optional): Interval time in seconds between each check. The default value is 5 seconds. Example: -i 10.
-c, --continuous (optional): Runs the monitoring continuously, checking the hosts at the specified interval. Without this option, the script will only check once.
-l, --log (optional): Specifies the log file name where the status changes (up/down) of the hosts will be saved. Example: -l status.log.
-t, --timeout (optional): Duration of the timeout for each ping request, in seconds. The default value is 0.5 seconds. Example: -t 1.5.
-s, --sequential (optional): Performs the ping checks sequentially (one at a time) instead of in parallel.
```
## Examples
```
#Monitor a list of hosts with default settings:
python pinger.py 192.168.1.1 192.168.1.2
```
```
#Monitor hosts from a file with a 10-second interval:
python pinger.py -f hosts.txt -i 10
```
```
#Monitor hosts continuously and log status changes:
python pinger.py 192.168.1.1 192.168.1.2 -c -l status.log
```
