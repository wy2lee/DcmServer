#!/usr/bin/python
#  Python code to rename dicom files sent from any scanner
#  Adapted from renameDicom.pl
#  Created to allow for great portability and flexibility between scanners
#       Checks dicom header if Philips scanner
#  Increased options with respect to output extension and anonymization 

#    File Name:  process_fmri.py
#
# OUTPUT STRUCTURE/home/researchPACS/dcmsrvr/datadump/MR.1.2.840.113619.2.312.4120.8419247.14553.1343646753.9
#	base_dir / series_dir / file_name
#
#	base_dir = <StudyDate>_<SubjectID>
#	series_dir = <SeriesNumber>_<ProtocolName>
#	file_name = I<InstanceNumber>.dcm
#		- InstanceNumber is padded to 4 digits
#
# LAST REVISION 
#	12/05/01 - WL - initial creation 
#   12/05/11 - WL - Fixed modify when moving, added valid char check
#   12/05/15 - WL - Added echo number (0018,0086) check in case of duplicate file
#                   Restore clobber functionality
#   12/05/30 - WL - Added error checking for echo number field 
#                   Modified to match naming convention used by Josh
#   12/08/07 - WL - Removed StudyDescription field, it's unused anyway

import os
import string   	
import shlex, subprocess
import datetime
from optparse import OptionParser, Option, OptionValueError


program_name = 'renameDicom.py'

# Defining dcm header names and tags

# What characters are valid in a file name?
# Anything not in this group is removed
valid_chars = '-_%s%s' % (string.ascii_letters, string.digits)

lut_value = {}     # Blank structure for storing header values

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

# 16-02-02 - WL - Deprecated no config file needed anymore
# def load_lut_list(fname_lut_list):
    # lut_tag={}
# #   Loads list of dicom headers to read
    # if not os.path.exists(fname_lut_list):
        # raise SystemExit, 'ERROR - Parameter File - File not found: %s' % (fname_lut_list,) 
        
    # file_lut_list = open(fname_lut_list,'r')
    # for line_dcm in file_lut_list:
		# if line_dcm[0]!="#":
			# lut_tag[line_dcm.split(':')[0].strip(' ')] = line_dcm.split(':')[1].strip(' ').strip('\n')
    # return lut_tag


def get_tag_value(dir_input, fname_dcm, tag_name):
    # Dump dcmheader and grap header line
    cmd_dcmdump = 'dcmdump %s/%s | grep %s' % (dir_input, fname_dcm, tag_name)
    output, errors = run_cmd(cmd_dcmdump, 0, 0)
    if scanner_type == 'philips' and tag_name=='InstanceNumber':    # Check if Philips type dicom and looking for InstanceNumber
        for line in output.split('\n'):    # split output into separate lines
            if not line=='' and line.find('[0]') == -1:     # Ignore all lines without 'real' instance information
                output = line
#	print tag_name
    if len(output)==0:                                  # ERROR CHECKING for missing DICOM
        tag_value = "No" + tag_name
    elif output.find("(no value available)")<0:           # ERROR CHECKING FOR EMPTY FIELDS
        tag_value = output.split('[')[1].split(']')[0]    # Grab value between [ ]
        # Initial replacing of bad characters into useful partitions
        tag_value = tag_value.replace(' ','-')   # replace spaces with -  12/05/30 - WL - Custom
        tag_value = tag_value.replace('.','-')   # replace . with -       12/05/30 - WL - Custom
        tag_value = tag_value.replace('/','-')   # replace / with -
        tag_value = tag_value.replace('\'','-')   # replace \ with -
        tag_value = tag_value.replace('*','s')   # replace * with s
        tag_value = tag_value.replace('?','q')   # replace ? with q
        tag_value = ''.join(c for c in tag_value if c in valid_chars) # scrub bad characters
    else:
        tag_value = "Empty" + tag_name
    return tag_value
            
if __name__ == '__main__' :
    usage = "Usage: "+program_name+" <options> dir_input fname_dcm dir_output\n"+\
            "   or  "+program_name+" -help\n" +\
            " For directories use: \n" +\
            " for file in <dir>; do renameDicom.py . ${file} <dir_output>; done \n\n" +\
            " For directory formats, seperate fields by '-'\n" +\
            " For directory formats, use # before fields to specify zero padding to that number of digits\n" 
    parser = OptionParser(usage)
    parser.add_option("-c","--clobber", action="store_true", dest="clobber",
                        default=0, help="overwrite output file")
    parser.add_option("-a","--anon", action="store_true", dest="anon",
                        default=0, help="make dicom anonymous")
    parser.add_option("--cfg_anon", type="string", dest="fname_cfg",
                        default="DcmServer.cfg", help="List of fields to wipe [default = %default]")
#    parser.add_option("--cfg_hdr", type="string", dest="fname_cfg_hdr",
#                        default="renameDicom.cfg", help="List of fields to wipe [default = %default]")
    parser.add_option("--fmt_base", type="string", dest="format_base",
                        default="StudyDate-PatientName", help="Directory format of base directory [default = %default]")
    parser.add_option("--fmt_series", type="string", dest="format_series",
                        default="###SeriesNum-SeriesDescription", help="Directory format of series directories [default = %default]")
    parser.add_option("-m","--move", action="store_true", dest="move",
                        default=0, help="move instead of copy")
    parser.add_option("-v","--verbose", action="store_true", dest="verbose",
                        default=0, help="Verbose output")
    parser.add_option("-d","--debug", action="store_true", dest="debug",
                        default=0, help="Run in debug mode")
    parser.add_option("-e","--extension", type="string", dest="extension",
                        default="dcm", help="File extension [default = dcm]")
    parser.add_option("-l","--logile", type="string", dest="logfile",
                        default="", help="Log file location [default = none]")

# # Parse input arguments and store them
    options, args = parser.parse_args()     
    if len(args) != 3:
        parser.error("incorrect number of arguments")
    dir_input, fname_dcm, dir_output = args

    if options.move:   # Determine what type of operation to carry out
        operation = 'mv'
    else:
        operation = 'cp'
    
    # Check that file exists
    if not os.path.exists('%s/%s' % (dir_input, fname_dcm)):
        raise SystemExit, 'DCM file does not exist - %s/%s' % \
            (dir_input, fname_dcm)
    
    # Check scanner type (0008,0070 - Manufacturer tag)
    cmd_dcmdump = 'dcmdump %s/%s | grep 0008,0070' % (dir_input, fname_dcm)
    output, errors = run_cmd(cmd_dcmdump,0, 0)
    if string.lower(output).find('philips') > 0:
        scanner_type = 'philips'
    elif string.lower(output).find('siemens'):
        scanner_type = 'siemens'
    elif string.lower(output).find('ge'):
        scanner_type = 'ge'
    else:
        scanner_type = 'other'

    # Creating output directories and namesq
    dir_base = ""
    for field in options.format_base.split('-'):
        zeropad = 1+field.rfind("#")
        if zeropad==0:
            curr_tag_value = get_tag_value(dir_input, fname_dcm, field)
            dir_base = '%s-%s' % (dir_base,curr_tag_value)
        else:
            field = field[zeropad:]
            curr_tag_value = get_tag_value(dir_input, fname_dcm, field)
            dir_base = '%s-%0*d' % (dir_series,zeropad,int(curr_tag_value))
    dir_base = dir_base[1:]

    dir_base_full = '%s/%s' % (dir_output,dir_base)

    if not os.path.exists(dir_base_full):
        cmd_mkdir = 'mkdir %s/%s' % (dir_output, dir_base)
        output, errors = run_cmd(cmd_mkdir, options.debug, options.verbose)

#    dir_series = '%03.d-%s' % (int(lut_value['SeriesNum']), lut_value['SeriesDescription'])
    dir_series = ""
    for field in options.format_series.split('-'):
        zeropad = 1+field.rfind("#")
        if zeropad==0:
            curr_tag_value = get_tag_value(dir_input, fname_dcm, field)
            dir_series = '%s-%s' % (dir_series,curr_tag_value)
        else:
            field = field[zeropad:]
            curr_tag_value = get_tag_value(dir_input, fname_dcm, field)
            dir_series = '%s-%0*d' % (dir_series,zeropad,int(curr_tag_value))
    dir_series = dir_series[1:]

    dir_series_full = '%s\%s' % (dir_base_full, dir_series)
    if not os.path.exists(dir_series_full):
        cmd_mkdir = 'mkdir %s/%s/%s' % (dir_output, dir_base, dir_series)
        output, errors = run_cmd(cmd_mkdir, options.debug, options.verbose)

        
    # iterative process to determine file name
    curr_tag_value = get_tag_value(dir_input, fname_dcm, 'InstanceNumber')
    fname_out = '%04.d' % (int(curr_tag_value))
    extension = options.extension
        
    full_out = '%s/%s/%s/%s.%s' % (dir_output, dir_base, dir_series, fname_out, extension)
    
# If Siemens scanner, check for possibility of Mag/Ph type output, where files will have the same 
# instance number (leading to the same destination file name) but different echo numbers (0018,0086)
# This problem does not appear to exist on GE and Philips scanners (which have different echo #s and
# instance #s
    if scanner_type  == 'siemens':
        # get source echo number
        cmd_dcmdump = 'dcmdump %s/%s | grep 0018,0086' % (dir_input, fname_dcm)
        output, errors = run_cmd(cmd_dcmdump, 0, 0)
        if output != '':
            echo_number_source = int(output.split('[')[1].split(']')[0])
        else:
            echo_number_source = 1
        if echo_number_source > 1:   # append echo number if it's >1
            # if non-suffixed file exists (ie. echo number = 1) then add suffix
            if os.path.exists(full_out):
                if options.verbose:
                    print 'Renaming destination file - first echo'
                fname_new = '%s_01.%s' % (os.path.splitext(full_out)[0], extension)
                cmd_mvdest = 'mv %s %s' % (full_out, fname_new)
                output, errors = run_cmd(cmd_mvdest, options.debug, options.verbose)
                if errors == '':
                    cmd_rmorig = 'rm %s' % (full_out)
                    output, errors = run_cmd(cmd_rmorig, options.debug, options.verbose)
            fname_out = '%s_%02.d' % (fname_out, echo_number_source)
            full_out = '%s/%s/%s/%s.%s' % \
                (dir_output, dir_base, dir_series, fname_out, extension)
        else:
            # if new file
            if not os.path.exists(full_out):
                dir_full_out = '%s/%s/%s' % (dir_output, dir_base, dir_series)
                list_existing = str(os.listdir(dir_full_out))
                # check if basic filename already exists
                if list_existing.find(fname_out)>-1: 
                    fname_out = '%s_01' % (fname_out,)
                full_out = '%s/%s/%s/%s.%s' % \
                    (dir_output, dir_base, dir_series, fname_out, extension)
        
    if not options.clobber:    # if not overwriting then must find unique filename 
        while os.path.exists(full_out):
            fname_out = fname_out + 'A'
            full_out = '%s/%s/%s/%s.%s' % (dir_output, dir_base, dir_series, fname_out, extension)
    
    time_stamp = str(datetime.datetime.now()).split('.')[0]  # grap timestamp, but drop ms

    cmd_mvdcm = '%s %s/%s %s' % \
        (operation, dir_input, fname_dcm, full_out)
    output, errors = run_cmd(cmd_mvdcm, options.debug, options.verbose)     # Copying DCM with new name
    line_log  = time_stamp + ' - ' + cmd_mvdcm + '\n'

    if not options.debug:
        if not options.logfile=='':   # log file
            file_log = open(options.logfile,'a')
            file_log.write(line_log)

     # Anonymize data options
    if options.anon:
        file_cfg = open(options.fname_cfg,'r')
        # find anonymous fields
        at_anon_start = 0;
        while not at_anon_start:
            line = file_cfg.readline()
            if line == '':
                raise SystemExit, 'ERROR - Blank line or missing "anon_field" variable in cfg file - %s ' % \
                    (options.fname_cfg,)
            if line[0] != '#' and line.find('anon_fields') > -1:
                at_anon_start = 1;
        cmd_modify = ''
        # read each subsequent line as a field to be anonymized 
        # as long as the line begins with a whitespace
        at_anon_end  = 0;
        while not at_anon_end:
            line = file_cfg.readline()
            # must have a white space infront of field DI
            if line == '':  # end of file
                at_anon_end = 1
            elif line[0] == ' ':
                tag = line.strip(' ')[0:9]   # First 9 characters is header
                if options.debug:   # if in debug mode, target original file
                    cmd_dcmdump = 'dcmdump %s/%s | grep %s' % (dir_input, fname_dcm, tag)
                else:   
                    cmd_dcmdump = 'dcmdump %s | grep %s' % (full_out, tag)
                output, errors = run_cmd(cmd_dcmdump, 0, 0)
                if not output == '':    # add valid fields to be removed
                    cmd_modify = '%s -ma "(%s)=0"' % (cmd_modify, tag)
            elif line[0] != '#':  # if line is not a comment then it is a variable
                at_anon_end = 1
        if cmd_modify != '':         # only run if there are fields to be removed
            cmd_dcmmodify = 'dcmodify -ie %s %s' % (cmd_modify, full_out)
            output, errors = run_cmd(cmd_dcmmodify, options.debug, options.verbose)
            cmd_rm_bak = 'rm %s.bak' % (full_out,)
            output, errors = run_cmd(cmd_rm_bak, options.debug, options.verbose)
                
        file_cfg.close()
        
