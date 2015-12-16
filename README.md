# DcmServer
DCM receive 'server' software built around dcmtk, written in Python 

DICOM Storage Server
MR Data can be sent directly from the scanner to a computer ("server") with a properly configured DICOM Storage Server. A simple, free and elegant solution has been developed for linux-based servers using python and the DICOM toolkit (DCMTK).

How it works
1) Storescp runs in the background on a storage server, waiting for dicom data to arrive on a given port
2) Data is sent from a scanner to a server
  - storescp receives dicom data into a dump directory
  - 'Raw' dicom data generally arrives unsorted and with long cryptic file names
3) renameDicom.py reads the dicom header and sorts the 'raw' data so it has a friendly file name and directory structure.
  - <base_dir>/<subject_ID>/<series_#>-<series_name>/<instance_number>

Setting up your DICOM Storage Server

What you will need
1) A linux-based computer with sufficient storage space
  - Assign this server an AETitle (ie. its name)
  - Get its IP address (must have a fixed address)
  - Pick a listening port
2) The DICOM Toolkit compiled and working on your system
  - Source and binaries are available on the official site http://dicom.offis.de/dcmtk.php.en
3) The DcmServer package
  - Three files - DcmServer.py, renameDicom.py, DcmServer.cfg

Server Side
1) Create a new user for dicomserver
  - Edit their default file permissions to umask 002 (rwxrwxr-x)
2) Create a dicom dump directory dir_dump
3) Create a sorted dicom directory dir_out
4) Unpack the DcmServer package into a directory of your choice
  - Add this directory to dicomserver's paths
  - Edit DcmServer.cfg to reflect your server's configuration
    - port, AETitle, dir_dump, dir_out
    - renameDicom - if properly pathed, this can be left as renameDicom.py
    - fname_log - leave blank to disable logging
    - extension - (optional) default is dcm
    - anon_fields - Include this field and add lines below it to wipe those header fields. The program will automatically skip any fields that don't exist
5) Starting DcmServer - DcmServer.py Start
6) Shutting down DcmServer - DcmServer.py Shutdown
7) Checking the status of DcmServer - DcmServer.py Status

Scanner Side
1) Email a research MRT requesting a new 'Network Node' and the following information
  - IP address
  - AETitle
  - port
2) Arrange to meet with an MRT when your server has been added
3) Send a few test datasets and ensure they are transferred successfully

Notes and tips
1) Data Security - The default DcmServer.py installation will not overwrite existing files. Instead, it will keep appending the letter A to the end of the file name until it finds a valid file name. As such, it is strongly recommended that you do not use dir_out as the final resting place for your data. Otherwise, you could end up with multiple copies in the same directory.
2) Scanner side transfer failures - This error only indicates that a file was not properly received. These errors will occur if you try sending processed data (ie. MRS) because these files are not recognized as dicom compliant by storescp. This error DOES NOT tell you if there was any trouble renaming or sorting the data.
  - To the best of my knowledge there no easy way to setup the scanner to receive notification messages from a storage server.
3) What port number should I use? - I have no idea. The first storage server implementation I came across used 4006, so I have continued using ports in the same range. Please note the specified port must be 'free' as storescp effectively 'locks' whatever port it is listening on, blocking any other application from using the same port.
4) Can multiple scanners sent to the same port? - Yes. However, I'm not sure what happens if multiple scanners try sending to the same port on the same server at the same time.
5) SIEMENS NOTES
  - For GRE Fieldmaps, the Magnitude and Phase images will have the same InstanceNumber, which would lead to file naming issues. They will have different EchoNumbers(0018,0086), but an EchoTrainLength of 1 (making it difficult to know if you're dealing with Mag/Ph images). To minimize Siemens dicom naming issues the following happens:
    - EchoNumbers > 1 are automatically added to the end of any filename (2 digits)
    - If multiple echo numbers are detected, then dicoms with an EchoNumber equal to 1, will be named (or renamed) to include this information.
6) GE NOTES
  - Get11 (which is being phased out) will not work if the port it connects with is being used by an active DcmServer
7) PHILIPS NOTES
  - For some reason Philips dicom files sometimes have multiple InstanceNumber(0020,0013) fields. Most of these fields aren't used (value = [0]). To prevent naming errors, RenameDicom.py (rev 12/05/15) reads the first InstanceNumber with a non-zero value
