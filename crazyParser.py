#!/usr/bin/python
'''

This script uses urlcrazy to identify possible typosquatted domains.
The output is compared against an existing list of typosquatted domains.
If any new domains are identified, the results are mailed off for review
and blocking in your web proxy.

    Dependencies:
        mydomains.csv
            This file contains a list of domains you wish to monitor. 

        knowndomains.csv
            This file contains domains already identified from previous
            runs. The file contains a header "Domain,Reason" and a list of
            domains, 1 per line. The reason will either be Squatter or
            Valid Site if the domain belongs to a legitimate site.

	urlcrazy: installed at /usr/bin/urlcrazy. If this installed in an
            alternate location, the value of urlCrazy will need to be
            updated to reflect its location.

crazyParser.py - by @hardwaterhacker - http://hardwatersec.blogspot.com
'''

import argparse
import os
import sys
import subprocess
import csv
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email import Encoders

urlCrazy = '/usr/bin/urlcrazy' # update if your installation differs


# set up global defaults
tempFiles = [] # define temporary files array

def doCrazy(docRoot, resultsFile, myDomains):
    # cleanup old results file
    try:
        os.remove(resultsFile)
    except OSError: # file does not exist
        pass

    with open(myDomains, 'rb') as domains:
        reader = csv.reader(domains)
        for domain in domains:
            outfile = os.path.join(docRoot,(domain.rstrip() + '.tmp'))
            domain = domain.rstrip()
            try:
                subprocess.call('/usr/bin/urlcrazy -f csv' + ' -o ' + outfile + ' ' + domain, bufsize=4096, shell=True)
                tempFiles.append(outfile)
            except:
                # An error occurred running urlcrazy
                print "Unexpected error running urlcrazy:", sys.exc_info()[0]
                pass
    
def parseOutput(docRoot, knownDomains, resultsFile):

    # set up domains dictionary
    domains = []

    # compare known domains to discovered domains
    knowndom = []
    with open (knownDomains, 'rb') as domfile:
        reader = csv.DictReader(domfile)
        for row in reader:
            knowndom.append(row['Domain'])

    # Read all .tmp into dictionary
    filedict = []
    for f in os.listdir(docRoot):
        if f.endswith(".tmp"):
            filedict.append(os.path.join(docRoot, f))

    # Parse each file in dictionary
    for file in filedict:
        with open (file, 'rb') as csvfile:
            reader = csv.DictReader(row.replace('\0', '') for row in csvfile)
            for row in reader:
                if len(row) != 0:
                    if row['CC-A'] != "?":
                        if row['Typo'] in knowndom:
                            pass
                        else:
                            domains.append(row['Typo'])

    # write out results
    # this file will only contain the header if there are no new results
    with open(resultsFile, 'wb') as outfile:
        fieldnames = ['Domain']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in domains:
            writer.writerow({'Domain': row})
    

def sendMail(resultsFile):

    '''
            sendMail sends the results of urlcrazy scans,
            including diffs to your selected address
            using a given address.

            Specify your sending account username in mail_user.
            Specify your account password in mail_pwd.

            Configure for your mail server by modifying the
            mailServer = line.

            This assumes your mail server supports starttls.
            Future versions will allow you to specify whether
            or not to use starttls. To suppress starttls,
            remove the line mailServer.starttls().

    '''

    mail_user = "mail_sender_account"
    mail_pwd = "your_pass_here"
    mail_recip = ["recipient_address_1", "recipient_address_2"]

    def mail(to, subject, text, attachment, numResults):
            msg = MIMEMultipart()

            msg['From'] = mail_user
            msg['To'] = ", ".join(to)
            msg['Subject'] = subject

            msg.attach(MIMEText(text))

            # Attach the attachment if there are new results
            # numResults is the number of rows in the results file
            # This is always at least 1 due to the header row
            if numResults >= 2:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(open(attachment, 'rb').read())
                Encoders.encode_base64(part)
                part.add_header('Content-Disposition',
                        'attachment; filename="%s"' % os.path.basename(attachment))
                msg.attach(part)
            else:
                pass

            mailServer = smtplib.SMTP("smtp.gmail.com", 587)
            mailServer.ehlo()
            mailServer.starttls()
            mailServer.ehlo()
            mailServer.login(mail_user, mail_pwd)
            mailServer.sendmail(mail_user, to, msg.as_string())
            # Should be mailServer.quit(), but that crashes...
            mailServer.close()

    # define our attachment
    attachment = resultsFile
    
    # this counts the number of line in the results file
    # if it is 1, there were no results
    numResults = sum(1 for line in open(attachment))
    if numResults == 1:
        mail(mail_recip,
                "Daily DNS typosquatting recon report", # subject line
                "There were no new results in today's scan", # your message here
                attachment, numResults)

    else:
        mail(mail_recip,
                "Daily DNS typosquatting recon report", # subject line
                "The results from today's DNS typosquatting scan are attached", # your message here
                attachment, numResults)

def doCleanup(docRoot):
    # Delete all temporary .tmp files created by urlcrazy
    # Read all .tmp into dictionary
    filedict = []
    for f in os.listdir(docRoot):
        if f.endswith(".tmp"):
            filedict.append(os.path.join(docRoot, f))
    for f in tempFiles:
        try:
            os.remove(f)
        except OSError:
            print "Error removing temporary file: " + f
            pass

def main():

    # Set up parser for command line arguments
    parser = argparse.ArgumentParser(prog='crazyParser.py', description='crazyParser 0.1', add_help=True)
    parser.add_argument('-c', '--config', help='Directory location for required config files', default=os.getcwd(), required=False)
    parser.add_argument('-o', '--output', help='Save results to file', default='results.csv', required=False)
    parser.add_argument('-d', help='Directory for saving output, defaults to current directory', default=os.getcwd(), required=False)
    parser.add_argument('-m', '--email', help='Email results upon completion, defaults to True', default=True, required=False)
    args = parser.parse_args()

    if args.config != os.getcwd():
        if os.path.isdir(args.config):
            configDir = args.config
        else:
            print "ERROR! Specified configuration directory " + args.config + " does not exist!"
            sys.exit()
    else:
        configDir = args.config

    if args.d != os.getcwd():
        if os.path.isdir(args.d):
            docRoot = args.d
        else:
            print "ERROR! Specified output directory " + args.d + " does not exist!"
            sys.exit()
    else:
        docRoot = args.d

    # set up global files
    resultsFile = os.path.join(docRoot, args.output)
    myDomains = os.path.join(configDir,'mydomains.csv')
    knownDomains = os.path.join(configDir,'knowndomains.csv')

    # Make sure to clean up any stale output files
    doCleanup(docRoot)

    # Execute urlcrazy
    doCrazy(docRoot, resultsFile, myDomains)

    # parse output from urlcrazy
    parseOutput(docRoot, knownDomains, resultsFile)

    # send results if -m/--email is true
    if args.email == True:
        sendMail(resultsFile)
    else:
        pass

    # Clean up output files
    doCleanup(docRoot)

if __name__ == "__main__":
    main()
