#!/usr/bin/python
#  Simple Dicom Server utility
#    Starts / stops storescp utility for receiving and sorting dicomfiles
#  Adapted from LaunchServer.pl
#  Created to allow for great portability and flexibility between scanners
#    File Name:  DCMServer.py
#
# LAST REVISION 
#	12/05/11 - WL - initial creation 
#	12/05/15 - WL - Carry over from 12/05/14, added config file
#   12/05/30 - WL - Added variable user name to cfg, and remove leading spaces from get PID
#   14/03/04 - WL - Added option to enable / disable queue mode

import os, sys, time
import string
import shlex, subprocess
from optparse import OptionParser, Option, OptionValueError

program_name = 'DcmServer.py'

# list of mandatory dcm server variables
list_server_var = ['user','port','AETitle','dir_dump','dir_out','renameDicom','fname_log']

def run_cmd(sys_cmd, debug, verbose):
# one line call to output system command and control debug state
    if verbose:
        print sys_cmd
    if not debug:
        p = subprocess.Popen(sys_cmd, stdout = subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, errors = p.communicate()
        return output, errors
    else:
        return '','' 

def getPID(user):
    cmd_getPID = 'ps -u %s | grep storescp' % (user,)
    p = subprocess.Popen(cmd_getPID, stdout = subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, errors = p.communicate()
    if output != '':
        PID = output.lstrip(' ').split(' ')[0]    # remove leading spaces to start
    else:
        PID = ''
    return PID

def printReport(options):
    print 'AETitle - %s' % (options.AETitle,)
    print 'Port - %s' % (options.port,)
    print 'Dump Directory - %s' % (options.dir_dump,)
    print 'Sorted Directory - %s' % (options.dir_out,)
    print 'renameDicom command  - %s' % (options.renameDicom,)
    print 'Log File - %s' % (options.fname_log,)

def load_cfg(options):
    file_cfg = open(options.fname_cfg,'r')
    for line in file_cfg:
        # skip any line that is a comment, blank or indicates start of anon_fields
        if line[0] != '#' and line[0] != ' ' and   line.find('anon_fields')<0:
            name_var = line.split('=')[0].strip(' ')
            value_var = line.split('=')[1].strip(' ').strip('\n')
            if name_var in list_server_var:
                setattr(options, name_var, value_var)
                # remove stored variable from list
                list_server_var.pop(list_server_var.index(name_var))
            elif name_var=='extension':
                setattr(options, name_var, value_var)
            else:
                raise SystemExit, 'Invalid configuration variable name - %s' % (name_var,)
    if len(list_server_var) > 0:
        raise SystemExit, 'Missing the following configuration variables - %s' %  (list_server_var,)
    return options
    
    
if __name__ == '__main__' :
    usage = "Usage: "+program_name+" operation\n"+\
            "   or  "+program_name+" -help\n" +\
            " Valid operations - status, shutdown, start"
    parser = OptionParser(usage)
    parser.add_option("--cfg", type="string", dest="fname_cfg",
                        default="DcmServer.cfg", help="DcmServer Configuration [default = DcmServer.cfg]")
    parser.add_option("-q","--queue", action="store_true", dest="queue",
                        default=0, help="Queue rename calls using atq (for slower computers)")

    options, args = parser.parse_args()     
    options = load_cfg(options)  # load additional cfg options

    if len(args) != 1:
        parser.error("incorrect number of arguments")
    operation = args[0]

    if operation == 'status':
        PID = getPID(options.user)
        if PID == '':
            print 'Storescp is NOT running'
        else:
            print 'Storescp is running (PID = %s)' % (PID,)
            cmd_PIDinfo = 'ps -fp %s | grep storescp' % (PID,)
            output,errors = run_cmd(cmd_PIDinfo,0,0)
            options.port = output.split(' ')[-1].strip('\n')
            options.AETitle = output.split('-aet ')[1].split(' ')[0]  # first thing after -aet
            options.dir_dump = output.split('-od ')[1].split(' ')[0]  # first thing after -od
            options.dir_out = output.split('\#f ')[1].split(' ')[0]  # first thing after \#f
            options.renameDicom = output.split('-xcr ')[1].split(' ')[0]  # first thing after -xcr
            if (str.find(output,'-l') > -1):   # check if log file
                options.fname_log = output.split('-l ')[1].split(' ')[0]  # first thing after -l
            else:
                options.fname_log = 'none'            
            printReport(options)
            
    elif operation == 'shutdown':
        PID = getPID(options.user)
        if PID == '':
            print 'Storescp not running, nothing to shutdown'
        else:
            cmd_killps = 'kill %s' % (PID,)
            output, errors = run_cmd(cmd_killps,0,0)
            if errors == '':
                print 'Successfully killed storescp (PID - %s)' % (PID,)
            else:
                print 'ERROR - Unsuccessfull killing of storescp (PID - %s) > %s' % \
                    (PID, errors)
    elif operation == 'start':
        PID = getPID(options.user)
        if PID == '':  # check to make sure storescp isn't already running
            if options.fname_log != '':    # if log file
                log_cmd = '-l %s' % (options.fname_log,)
            else:
                log_cmd = ''

            if hasattr(options,'extension'):
                ext_cmd = '-e %s' % (options.extension,)
            else:
                ext_cmd = ''
            # 12/05/30 - WL - CUSTOM - removed -a
            if options.queue:
                cmd_process_file = "echo '%s -m %s %s \#p \#f %s' | at -q A now" % \
                    (options.renameDicom, log_cmd, ext_cmd, options.dir_out)
            else:
                cmd_process_file = "%s -m %s %s \#p \#f %s" % \
                    (options.renameDicom, log_cmd, ext_cmd, options.dir_out)
            print cmd_process_file
            cmd_launchserver = 'storescp -aet %s -xcr "%s" -od %s %s &' % \
                (options.AETitle, cmd_process_file, options.dir_dump, options.port)
            print cmd_launchserver            

            os.system(cmd_launchserver)    # subprocess doesn't work because storescp stays 'open'
            time.sleep(1) # Give a little time for storescp to startup
            PID = getPID(options.user)
            if PID == '':
                print 'ERROR - Storescp did not start properly'
            else:
                print 'Storescp successfully started (PID = %s)' % (PID,)
                printReport(options)
        else:
            print 'ERROR - Storescp is already running (PID = %s)' % (PID,)
            printReport(options)
    else:
        raise SystemExit, 'Invalid Operation (start, shutdown, status)'
              

