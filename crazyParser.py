# !/usr/bin/python
'''

This script uses urlcrazy and dnstwist to identify possible typosquatted
domains. The output is compared against an existing list of typosquatted
domains generated by an initial review. If any new domains are identified,
the results are mailed off for review and blocking in your web proxy.

    Dependencies:
        mydomains.csv
            This file contains a list of domains you wish to monitor. 

        knowndomains.csv
            This file contains domains already identified from previous
            runs. The file contains a header "Domain,Reason" and a list of
            domains, 1 per line. The reason will either be Squatter or
            Valid Site if the domain belongs to a legitimate site.
            Note: Reason is not used by crazyParser.  It is for your
            reference only.

    urlcrazy: installed at /usr/bin/urlcrazy. If this installed in an
            alternate location, the value of urlcrazyPath will need to be
            updated to reflect its location.

    dnstwist: installed at /opt/dnstwist/dnstwist.py. If this installed in an
            alternate location, the value of dnstwistPath will need to be
            updated to reflect its location.

crazyParser.py - by @hardwaterhacker - http://hardwatersec.blogspot.com
mike@hardwatersecurity.com
'''

__author__ = 'Mike Saunders - @hardwaterhacker'
__version__ = '20151001'
__email__ = 'mike@hardwatersecurity.com'

import argparse
import os
import sys
import subprocess
import csv
import tempfile
import atexit

urlcrazyPath = '/Users/DJ/Desktop/CrazyParser/urlcrazy/urlcrazy'  # update if your installation differs
dnstwistPath = '/usr/local/lib/python3.7/site-packages'  # update if your installation differs

# set up global defaults
tempFiles = []  # define temporary files array


def checkPerms(docRoot, resultsFile):
    # Test if we have execute permissions to docRoot
    if not os.access(docRoot, os.X_OK):
        print "Destination directory " + docRoot + " not accessible."
        print "Please check permissions.  Exiting..."
        sys.exit()
    else:
        pass

    # Test if we have write permissions to docRoot
    try:
        permtest = tempfile.TemporaryFile('w+b', bufsize=-1, dir=docRoot)
    except OSError:
        print "Unable to write to desired directory: " + docRoot + "."
        print "Please check permissions.  Exiting..."
        sys.exit()


def checkDepends(myDomains, knownDomains, docRoot, resultsFile, urlcrazy, dnstwist):
    # Test if mydomains.csv exists
    if not os.access(myDomains, os.F_OK) or not os.access(knownDomains, os.F_OK):
        print "Required configuration files - mydomains.csv or knowndomains.csv - not found."
        print "Please verify configuration.  Exiting..."
        sys.exit()
    else:
        pass

    # Test if docRoot is actually a directory
    if not os.path.isdir(docRoot):
        print "Argument: -d " + docRoot + " is not a directory."
        print "Please review arguments.  Exiting..."
        sys.exit()
    else:
        pass

    # Ensure resultsFile isn't actually a directory
    if os.path.exists(resultsFile) and not os.path.isfile(resultsFile):
        # if not os.path.isfile(resultsFile):
        print "Argument: -o " + resultsFile + " should be a regular file but is something else."
        print "Please review arguments.  Exiting..."
        sys.exit()
    else:
        pass

    # Test if urlcrazy exists
    if urlcrazy:
        if not os.access(urlcrazyPath, os.F_OK):
            print "URLCrazy specified as " + urlcrazyPath + " but was not found."
            print "Please check urlcrazyPath in crazyParser.py.  Exiting..."
            sys.exit()

    # Test if dnstwist exists
    if dnstwist:
        if not os.access(dnstwistPath, os.F_OK):
            print "DNStwist specified as " + dnstwistPath + "but was not found."
            print "Please check urlcrazyPath in crazyParser.py.  Exiting..."
            sys.exit()


def doCrazy(docRoot, resultsFile, myDomains, urlcrazy, dnstwist):
    # cleanup old results file
    try:
        os.remove(resultsFile)
    except OSError:
        pass

    with open(myDomains, 'rbU') as domains:
        reader = csv.reader(domains)
        for domain in domains:
            domain = domain.rstrip()

            # Run urlcrazy if enabled
            if urlcrazy:
                ucoutfile = tempfile.NamedTemporaryFile('w', bufsize=-1, suffix='.uctmp', prefix=domain + '.',
                                                        dir=docRoot, delete=False)
                ucargs = [urlcrazyPath, '-f', 'csv', '-o', ucoutfile.name, domain]
                try:
                    with open(os.devnull, 'w') as devnull:
                        subprocess.call(ucargs, stdout=devnull, close_fds=True, shell=False)
                        tempFiles.append(ucoutfile.name)
                except:
                    # An error occurred running urlcrazy
                    print "Unexpected error running urlcrazy:", sys.exc_info()[0]
                    pass

            # Run dnstwist if enabled
            dtargs = [dnstwistPath, '-r', '-c', domain]
            if dnstwist:
                dtoutfile = tempfile.NamedTemporaryFile('w', bufsize=-1, suffix='.dttmp', prefix=domain + '.',
                                                        dir=docRoot, delete=False)
                try:
                    with open(dtoutfile.name, 'wb') as dtout:
                        output = subprocess.check_output(dtargs, shell=False)
                        dtout.write(output)
                    tempFiles.append(dtoutfile.name)
                except:
                    # An error occurred running dnstwist
                    print "Unexpected error running dnstwist:", sys.exc_info()[0]
                    pass


def parseOutput(docRoot, knownDomains, resultsFile, urlcrazy, dnstwist):
    # set up domains dictionary
    domains = []

    # compare known domains to discovered domains
    knowndom = []
    with open(knownDomains, 'rbU') as domfile:
        reader = csv.DictReader(domfile)
        for row in reader:
            knowndom.append(row['Domain'])

    if urlcrazy:
        # Parse each urlcrazy temp file in tempFiles list
        for file in tempFiles:
            if file.endswith(".uctmp"):
                with open(file, 'rbU') as csvfile:
                    reader = csv.DictReader(row.replace('\0', '') for row in csvfile)
                    for row in reader:
                        if len(row) != 0:
                            if row['CC-A'] != "?":
                                if row['Typo'] in knowndom:
                                    pass
                                else:
                                    domains.append(row['Typo'])

    if dnstwist:
        # Parse each dnstwist temp file in tempFiles list
        for file in tempFiles:
            if file.endswith(".dttmp"):
                with open(file, 'rbU') as csvfile:
                    reader = csv.reader(csvfile)
                    next(reader)  # Due to recent change in dnstwist, skip header line
                    next(reader)  # skip second line, contains original domain
                    for row in reader:
                        if row[1] in knowndom:
                            pass
                        else:
                            domains.append(row[1])

    # dedupe domains list
    domains = dedup(domains)

    # write out results
    # this file will only contain the header if there are no new results
    with open(resultsFile, 'wb') as outfile:
        fieldnames = ['Domain']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in domains:
            writer.writerow({'Domain': row})
    outfile.close()

def doCleanup(docRoot):
    # Delete all temporary .tmp files created by urlcrazy and dnstwist
    for f in tempFiles:
        try:
            os.remove(f)
        except OSError:
            print "Error removing temporary file: " + f
            pass


def dedup(domainslist, idfun=None):  # code from http://www.peterbe.com/plog/uniqifiers-benchmark
    if idfun is None:
        def idfun(x): return x
    seen = {}
    result = []
    for item in domainslist:
        marker = idfun(item)
        if marker in seen: continue
        seen[marker] = 1
        result.append(item)
    return result


def main():
    # Set up parser for command line arguments
    parser = argparse.ArgumentParser(prog='crazyParser.py',
                                     description='crazyParser - a tool to detect new typosquatted domain registrations by using the output from dnstwist and/or urlcrazy',
                                     add_help=True)
    parser.add_argument('-c', '--config', help='Directory location for required config files', default=os.getcwd(),
                        required=False)
    parser.add_argument('-o', '--output', help='Save results to file, defaults to results.csv', default='results.csv',
                        required=False)
    parser.add_argument('-d', '--directory', help='Directory for saving output, defaults to current directory',
                        default=os.getcwd(), required=False)
    parser.add_argument('--dnstwist', help='Use dnstwist for domain discovery, defaults to False', action="store_true",
                        default=False, required=False)
    parser.add_argument('--urlcrazy', help='Use urlcray for domain discovery, defaults to False', action="store_true",
                        default=False, required=False)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()

    if args.config != os.getcwd():
        if os.path.isdir(args.config):
            configDir = args.config
        else:
            print "ERROR! Specified configuration directory " + args.config + " does not exist!"
            print "Exiting..."
            sys.exit()
    else:
        configDir = args.config

    if args.directory != os.getcwd():
        if os.path.isdir(args.directory):
            docRoot = args.directory
        else:
            print "ERROR! Specified output directory " + args.directory + " does not exist!"
            print "Exiting..."
            sys.exit()
    else:
        docRoot = args.directory

    # set up global files
    resultsFile = os.path.join(docRoot, args.output)
    myDomains = os.path.join(configDir, 'mydomains.csv')
    knownDomains = os.path.join(configDir, 'knowndomains.csv')

    # Check to make sure we have the necessary permissions
    checkPerms(docRoot, resultsFile)

    # Check dependencies
    checkDepends(myDomains, knownDomains, docRoot, resultsFile, args.urlcrazy, args.dnstwist)

    # Clean up output files at exit
    atexit.register(doCleanup, docRoot)

    # Execute discovery
    doCrazy(docRoot, resultsFile, myDomains, args.urlcrazy, args.dnstwist)

    # parse output
    parseOutput(docRoot, knownDomains, resultsFile, args.urlcrazy, args.dnstwist)


if __name__ == "__main__":
    main()
