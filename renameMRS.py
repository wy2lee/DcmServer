#!/usr/bin/python
#  Python code to sort and rename MRS files sent from any scanner
#
#    File Name:  renameMRS.py
#
# Assumed naming structure is 
#   <Subject_ID>+<unused filename seperation>.<extension>
#
#   Subject_ID must be encoded in filename because we want final MRS filename
#   to match the anonymized subjectIDs given to a dataset before it is sent to
#   researchPACS. It is non-trivial to anonymize the raw MRS headers, so we're leaving
#   them alone.
#
# OUTPUT STRUCTURE
#	base_dir / series_dir / MRS_dir
#
#   series_dir = <StudyDate>_<SubjectID>
#           * This must match researchPACs format
#	file_name = <ID#>-<SeriesDescription>.<extension>
#       Siemens - ID# = SeriesNumber
#                 extension = .rda
#       GE - ID# = Pfile Number
#            extension = .7
#
# LAST REVISION 
#	12/06/05 - WL - initial creation 

import os
import copy
import string
import shlex, subprocess
import datetime
import glob
from optparse import OptionParser, Option, OptionValueError


program_name = 'renameDicom.py'

# Defining Luts / header locations for different scanners
lut_siemens  = {}
lut_siemens['StudyDate'] = 'StudyDate'
lut_siemens['PatientName'] = 'PatientName'
lut_siemens['SeriesNumber'] = 'SeriesNumber'
lut_siemens['SeriesDescription'] = 'SeriesDescription'
lut_siemens['AcquisitionNumber'] = 'AcquisitionNumber'
lut_siemens['InstanceNumber'] = 'InstanceNumber'

# GE header locations for od -S4
#    12/06/05 - Software release HD16.0_V02_1131.a
lut_GE = {}
lut_GE['StudyDate'] = '0000020'
lut_GE['PatientName'] = '0424070'
lut_GE['SeriesNumber'] = '0000012'   # Actually pfile number
lut_GE['SeriesDescription'] = '0425756'


# What characters are valid in a file name?
# Anything not in this group is removed
valid_chars = '-_%s%s' % (string.ascii_letters, string.digits)

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

def clean_name(tag_value):
# Cleans file names
    tag_value = tag_value.replace(' ','_')   # replace spaces with _
    tag_value = tag_value.replace('.','_')   # replace . with _
    tag_value = tag_value.replace('/','-')   # replace / with -
    tag_value = tag_value.replace('\'','-')   # replace \ with -
    tag_value = tag_value.replace('*','s')   # replace * with s
    tag_value = tag_value.replace('?','q')   # replace ? with q
    tag_value = ''.join(c for c in tag_value if c in valid_chars) # scrub bad characters
    return tag_value

def siemens_mrs(dir_input, fname_mrs, lut_mrs):
    file_mrs = open('%s/%s' % (dir_input, fname_mrs));
    line = file_mrs.readline()   # skip first line because it is beginning of header
    line = file_mrs.readline()
    while (line.find('End of header') < 0):
        tag_name = line.split(': ')[0]
        tag_value = line.split(': ')[1].strip('\n').strip('\r')
        if tag_name in lut_mrs:
            lut_mrs[tag_name] = clean_name(tag_value)
        line = file_mrs.readline()
    lut_mrs['PatientName'] = fname_mrs[0:fname_mrs.rfind('+')]
    return lut_mrs

def ge_mrs(dir_input, fname_mrs, lut_mrs):
    for tag_name in lut_mrs:
        cmd_Pfiledump = 'od -S4 %s/%s | grep %s' % (dir_input, fname_mrs, lut_mrs[tag_name])
        output, errors = run_cmd(cmd_Pfiledump, 0, 0)
        if tag_name == 'StudyDate':    # MM/DD/1YY
            tag_value = '20%s%s%s' % \
                (output[15:17], output[8:10], output[11:13])  # YY/MM/DD
        elif tag_name == 'SeriesNumber':   # conver # in pfilename
            tag_value = 'P%05d' % (int(output[8:].strip('\n')),)            
        else:
            tag_value = output[8:].strip('\n')
        lut_mrs[tag_name] = clean_name(tag_value) 
    lut_mrs['PatientName'] = fname_mrs[0:fname_mrs.rfind('+')]
    return lut_mrs
    
if __name__ == '__main__' :
    usage = "Usage: "+program_name+" <options> dir_input dir_output\n"+\
            "   or  "+program_name+" -help\n"
    parser = OptionParser(usage)
    parser.add_option("-c","--clobber", action="store_true", dest="clobber",
                        default=0, help="overwrite output file")
    parser.add_option("-f","--fname_mrs", type="string", dest="list_fname_mrs",
                        default="", help="Single MRS file option")
    parser.add_option("-a","--anon", action="store_true", dest="anon",
                        default=0, help="make dicom anonymous")
    parser.add_option("--cfg", type="string", dest="fname_cfg",
                        default="DcmServer.cfg", help="List of fields to wipe [default = DcmServer.cfg]")
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
    
    if len(args) != 2:
        parser.error("incorrect number of arguments")
    dir_input, dir_output = args

    if options.move:   # Determine what type of operation to carry out
        operation = 'mv'
    else:
        operation = 'cp'
    
    if options.list_fname_mrs == "":     # All files in directory option
        options.list_fname_mrs = glob.glob('%s/*.7' % (dir_input,)) + \
            glob.glob('%s/*.rda' % (dir_input,))
    
    for fname_mrs in options.list_fname_mrs:
        fname_mrs = os.path.basename(fname_mrs)
        
        # Check that file exists
        if not os.path.exists('%s/%s' % (dir_input, fname_mrs)):
            raise SystemExit, 'DCM file does not exist - %s/%s' % \
                (dir_input, fname_mrs)

        MRS_type = fname_mrs.split('.')[-1]
       
        if MRS_type == 'rda':        # Siemens type MRS
            mrs_info = siemens_mrs(dir_input, fname_mrs, copy.deepcopy(lut_siemens))
        elif MRS_type == '7':            # GE type MRS
            mrs_info = ge_mrs(dir_input, fname_mrs, copy.deepcopy(lut_GE))

        # Creating output directories and names
        dir_base = '%s_%s' % (mrs_info['StudyDate'], mrs_info['PatientName'])
        if not os.path.exists(dir_base):
            cmd_mkdir = 'mkdir %s/%s' % (dir_output, dir_base)
            output, errors = run_cmd(cmd_mkdir, options.debug, options.verbose)
        dir_base = '%s_%s/MRS' % (mrs_info['StudyDate'], mrs_info['PatientName'])
        if not os.path.exists(dir_base):
            cmd_mkdir = 'mkdir %s/%s' % (dir_output, dir_base)
            output, errors = run_cmd(cmd_mkdir, options.debug, options.verbose)

        fname_out = '%s-%s-%s' % (mrs_info['SeriesNumber'], mrs_info['SeriesDescription'],
            mrs_info['InstanceNumber'])
        full_out = '%s/%s/%s.%s' % (dir_output, dir_base, fname_out, MRS_type)
        
        if not options.clobber:    # if not overwriting then must find unique filename 
            while os.path.exists(full_out):
                fname_out = fname_out + 'A'
                full_out = '%s/%s/%s.%s' % (dir_output, dir_base, fname_out, MRS_type)
        
        
        cmd_mvdcm = '%s %s/%s %s' % \
            (operation, dir_input, fname_mrs, full_out)
        output, errors = run_cmd(cmd_mvdcm, options.debug, options.verbose)     # Copying DCM with new name
    
    # time_stamp = str(datetime.datetime.now()).split('.')[0]  # grap timestamp, but drop ms

    # cmd_mvdcm = '%s %s/%s %s' % \
        # (operation, dir_input, fname_dcm, full_out)
    # output, errors = run_cmd(cmd_mvdcm, options.debug, options.verbose)     # Copying DCM with new name
    # line_log  = time_stamp + ' - ' + cmd_mvdcm + '\n'

    # if not options.debug:
        # if not options.logfile=='':   # log file
            # file_log = open(options.logfile,'a')
            # file_log.write(line_log)

     # # Anonymize data options
    # if options.anon:
        # file_cfg = open(options.fname_cfg,'r')
        # # find anonymous fields
        # at_anon_start = 0;
        # while not at_anon_start:
            # line = file_cfg.readline()
            # if line == '':
                # raise SystemExit, 'ERROR - Blank line or missing "anon_field" variable in cfg file - %s ' % \
                    # (options.fname_cfg,)
            # if line[0] != '#' and line.find('anon_fields') > -1:
                # at_anon_start = 1;
        # cmd_modify = ''
        # # read each subsequent line as a field to be anonymized 
        # # as long as the line begins with a whitespace
        # at_anon_end  = 0;
        # while not at_anon_end:
            # line = file_cfg.readline()
            # # must have a white space infront of field DI
            # if line == '':  # end of file
                # at_anon_end = 1
            # elif line[0] == ' ':
                # tag = line.strip(' ')[0:9]   # First 9 characters is header
                # if options.debug:   # if in debug mode, target original file
                    # cmd_dcmdump = 'dcmdump %s/%s | grep %s' % (dir_input, fname_dcm, tag)
                # else:   
                    # cmd_dcmdump = 'dcmdump %s | grep %s' % (full_out, tag)
                # output, errors = run_cmd(cmd_dcmdump, 0, 0)
                # if not output == '':    # add valid fields to be removed
                    # cmd_modify = '%s -ma "(%s)=0"' % (cmd_modify, tag)
            # elif line[0] != '#':  # if line is not a comment then it is a variable
                # at_anon_end = 1
        # if cmd_modify != '':         # only run if there are fields to be removed
            # cmd_dcmmodify = 'dcmodify -ie %s %s' % (cmd_modify, full_out)
            # output, errors = run_cmd(cmd_dcmmodify, options.debug, options.verbose)
            # cmd_rm_bak = 'rm %s.bak' % (full_out,)
            # output, errors = run_cmd(cmd_rm_bak, options.debug, options.verbose)
                
        # file_cfg.close()
        