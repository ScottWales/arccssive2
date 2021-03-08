#!/usr/bin/env python
# Copyright 2018 ARC Centre of Excellence for Climate Extremes
# author: Paola Petrelli <paola.petrelli@utas.edu.au>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import smtplib
import os
import itertools
import csv
import platform

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


def write_request(project, missing):
    """Write missing dataset_ids to file to create download request for synda
 
    Args:
        project (string): project, i.e. CMIP5/CMIP6
        missing (list): dataset_id not yet on local db or in the download queue 
    """

    user = os.environ.get('USER', 'unknown')
    tstamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    # open file and write missing dataset_ids
    fname = "_".join([project,user,tstamp])+".txt"
    fpath = os.path.join(os.getcwd(),fname)
    f = open(fpath, 'w')
    # with CMIP5 variable/s have to be specified too
    variables=set()
    for m in missing:
        if project == 'CMIP5':
            did,var = m.split(" ")
            variables.add(var)
        else:
            did = m
        f.write('dataset_id='+did+'\n')
    if len(variables) > 0:
        f.write(" ".join(['variable='] + list(variables)))
    f.close()

    # print('\nFinished writing file: '+fname)
    if platform.node()[0:3] == 'vdi':
        answer = input('Do you want to proceed with request for missing files? (N/Y)\n No is default\n')
        if answer  in ['Y','y','yes','YES']:
            helpdesk(user, fpath, project)
            return
    print(f'Your request has been saved in \n {fpath}')
    print('You can use this file to request the data via the NCI helpdesk: help@nci.org.au  or https://help.nci.org.au.')
    return


def helpdesk(user, fpath, project):
    """Send e-mail and synda request to helpdesk
 
    Args:
        user (string): NCI user id
        fpath (string): path of request file
        project (string): project, i.e. CMIP5/CMIP6
    """
    fname = os.path.basename(fpath)
    msg = MIMEMultipart()
    msg['From'] = user+'@nci.org.au'
    msg['To'] = 'help@nf.nci.org.au'
    msg['Subject'] = 'Synda request: ' + fname
    message = project + " synda download requested from user: " + user
    msg.attach(MIMEText(message, 'plain'))
    f = open(fpath)
    attachment=MIMEText(f.read())
    f.close()
    attachment.add_header('Content-Disposition','attachment', filename=fname)
    msg.attach(attachment)
    try:
       smtpObj = smtplib.SMTP('localhost')
       smtpObj.sendmail(msg['From'],msg['To'],msg.as_string())
       print( "Your request was successfully sent to the NCI helpdesk")
       print(f'A copy of your request has been saved in \n {f.name}')
    except smtplib.SMTPException:
       print("Error: unable to send email")
       print(f'Your request has been saved in \n {f.name}')
       print('You can use this file to request the data via the NCI helpdesk:\n'+
             ' help@nci.org.au  or https://help.nci.org.au.')
    return

def read_queue(project):
    """Read queue csv file

    Args:
        project (string): project, i.e. CMIP5/CMIP6

    Returns:
        rows (dict): - prsenting each record stored in the file
        dids (set): dataset_ids stored in the file
    """
    rows={}
    dids=set()
    # open csv file and read data in dictionary with dataset_id as key
    try:
        with open("/g/data/hh5/clef/tables/" + project + "_clef_table.csv","r") as csvfile:
            table_read = csv.reader(csvfile)
        # for each row save did-var (to distinguish CMIP5) and separate set of unique dids
            for row in table_read:
                if project == 'CMIP5':
                    rows[(row[1],row[0])] = row[2]
                    dids.add(row[1])
                elif project == 'CMIP6':
                    rows[(row[0])] = row[1]
                    dids.add(row[0])
    except FileNotFoundError:
        # Queue not available
        pass
    return rows, dids
 

def find_dids(qm, rows, dids, project, varlist):
    """ Retrieve missing dataset ids from dictionary representing queue table
    :input: qm - query results
    :input: rows - a dictionary representing each record stored in the file
    :input: dids - a set of unique dataset_ids stored in the file
    :input: project - CMIP5 or CMIP6 currently
    :input: varlist - optional list of requested variables for CMIP5
    :return: queued - a dictionary with (did+var,status) for CMIP5 and (did,status) for CMIP6
             filtered based on query results
    """
    queued={}
    for q in qm:
        did = q[0].replace('output.','output1.')
        if did in dids:
        # when CMIP5 you need to match also the variable
            if project == "CMIP5":
                if varlist != []:
                    queued.update({k[0]+" "+k[1]: v for k,v in rows.items() if k[0]==did and k[1] in varlist})
                else:
                    queued.update({k[0]+" "+k[1]: v for k,v in rows.items() if k[0]==did})
            elif project == "CMIP6":
                queued.update({k: v for k,v in rows.items() if k==did})
            else:
                 pass
    return queued

def search_queue_csv(qm, project, varlist):
    """Search missing dataset ids in download queue

    Args:
        qm - missing query results
        project (string): project, i.e. CMIP5/CMIP6
        varlist (list): optional list of requested variables for CMIP5

     Returns:
        missing (list): updated list of missing dataset_ids, after searching in download queue
    """

    # read queue file
    rows, dids = read_queue(project)
    
    # retrieve from table the missing dataset_ids
    queued = find_dids(qm, rows, dids, project, varlist)
    if len(queued) > 0:
        print("\nThe following datasets are not yet available in the database," +
              "\nbut they have been requested or recently downloaded\n")
        for did,status in queued.items():
            print(" ".join([did,'status:',status]))
    if project == 'CMIP5' and varlist != []:
        # this combines every dataset_id with all the variables, returns a list of "did  var" strings
        combs = [x[0]+" "+x[1] for x in itertools.product([q[0] for q in qm], varlist)]
        missing = [x for x in combs if x not in queued]
    else:
        missing = [q[0] for q in qm if q[0] not in queued]
    return missing
