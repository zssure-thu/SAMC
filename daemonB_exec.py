#!/usr/bin/python
# python script that identifies tarfiles, in a specific directory, and executes a series of commands if the tarfile is newer than the last run of the script
# The main funcitonof the script is to initiate Monte Carlo simulations using BEAMnrc
#
#    Copyright [2016] [Rickard Cronholm] Licensed under the
#    Educational Community License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may
#    obtain a copy of the License at
#
#http://www.osedu.org/licenses/ECL-2.0
#
#    Unless required by applicable law or agreed to in writing,
#    software distributed under the License is distributed on an "AS IS"
#    BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#    or implied. See the License for the specific language governing
#    permissions and limitations under the License.
#

import os
import sys
import datetime
import shutil
import fnmatch
import time
import samcUtil
import tarfile
import subprocess

# get current time
now = datetime.datetime.now()
newTime = now.strftime("%y%m%d%H%M%S")

# change dir to where the script is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

# check if lock file exists, otherwise create it
lockFile = 'Db.lock'
if os.path.isfile(lockFile):
    print 'Busy, quitting'
    sys.exit(0)
else:
    flock = open(lockFile, 'w')
    flock.write('Busy\n')
    flock.close()

# get variables from confFile
confFile = 'samc.conf'
with open(confFile) as f:
    confCont = f.readlines()
whatToGet = ['daemonB.timeFile', 'common.EGS_HOME', 'common.dosxyzDir',
'common.VCUinp', 'daemonB.nBatch', 'daemonB.beamPegs']
# generate struct
cv = samcUtil.struct()
# read variables
cv = samcUtil.getConfVars(cv, whatToGet, confCont)
# convert types
cv = samcUtil.typeCast(cv, ['nBatch'], [int])

'''
# get variables from confFile
confFile = 'samc.conf'
timeFile = samcUtil.getVariable(confFile,'daemonB.timeFile')
EGS_HOME = samcUtil.getVariable(confFile,'common.EGS_HOME')
VCUinp = samcUtil.getVariable(confFile,'common.VCUinp')
dosxyznrc = samcUtil.getVariable(confFile,'common.dosxyzDir')
nBatch = int(samcUtil.getVariable(confFile,'daemonB.nBatch'))
beamPegs = samcUtil.getVariable(confFile,'daemonB.beamPegs')
logFile = samcUtil.getVariable(confFile,'daemonB.logFile')
'''

# get time of last run
f = open(cv.timeFile, 'r')
oldTime = f.readline().rstrip()
print 'This was last run at {0}'.format(oldTime)
f.close()

# get list of tarfiles
tarfiles = []
for file in [tarfileList for tarfileList in os.listdir(dname) if tarfileList.endswith(".tar") and not tarfileList.startswith("post")]:
    # get time of modification of file
    fileTime = os.path.getmtime(file)
    fileTime = time.localtime(fileTime)
    fileTime = time.strftime("%y%m%d%H%M%S", fileTime)
    # if more recent than last run, append to list
    if fileTime > oldTime:
        tarfiles.append(file)

print 'Found {0} tarfile(s)'.format(len(tarfiles))
# quit if no tarfiles found
if len(tarfiles) == 0:
    print 'Nothing to do, exiting'
    samcUtil.writeTimeToFile(cv.timeFile, newTime)
    os.remove(lockFile)  # remove lockFile
    sys.exit()

# execute a series of commands for each tarfile found
for i in range(0, len(tarfiles)):
    # myTarfile = tarfiles[i]
    # os.system('tar -C %(dname)s -xf %(myTarfile)s' % locals())
    # remove tarfile
    #os.remove(tarfiles[i]) # uncomment this line when finnished testing
    # untar
    tar = tarfile.open(tarfiles[i])
    tar.extractall()
    tar.close()
    os.remove(tarfiles[i])  # remove tarfile

    # get the timeStamp from the name of the tarfile
    timeStamp, fileExt = os.path.splitext(tarfiles[i])

    print 'timeStamp: ', timeStamp
    sys.stdout.flush()

    # get BEAMdir
    f = open(os.path.join(timeStamp, timeStamp + '.beamDir'), 'r')
    beamDir = f.readline().rstrip()
    f.close()

    # get MLCdir
    mlcDir = False
    try:
        f = open(os.path.join(timeStamp, timeStamp + '.mlcDir'), 'r')
        mlcDir = f.readline().rstrip()
        f.close()
    except IOError:
            pass

    # copy files to destination folders
    dirList = os.listdir(timeStamp + os.path.sep)
    for file1 in dirList:  # file the files
        if fnmatch.fnmatch(file1, '*BEAM*'):  # match the wildcard
            # copy the files from origin to destination
            shutil.copy2(os.path.join(timeStamp, file1), cv.EGS_HOME + beamDir)
        if fnmatch.fnmatch(file1, '*vcu*'):  # match the wildcard
            # copy the files from origin to destination
            shutil.copy2(os.path.join(timeStamp, file1), cv.VCUinp)
        if fnmatch.fnmatch(file1, '*DOSXYZ*'):  # match the wildcard
            # copy the files from origin to destination
            shutil.copy2(os.path.join(timeStamp, file1), cv.dosxyzDir)
        if fnmatch.fnmatch(file1, '*phant'):  # match the wildcard
            # copy the files from origin to destination
            shutil.copy2(os.path.join(timeStamp, file1), cv.dosxyzDir)
        if mlcDir and fnmatch.fnmatch(file1, '*MLC*'):  # match the wildcard
            # copy the files from origin to destination
            shutil.copy2(os.path.join(timeStamp, file1), cv.EGS_HOME + mlcDir)


    # get number of beams
    f = open(os.path.join(timeStamp, timeStamp + '.numBeams'), 'r')
    numBeams = int(f.readline().rstrip())

    for j in range(0, numBeams):
        thisBeamName = timeStamp + '_' + str(j) + '_BEAMnrc'
        if j == 0:
            if not os.path.exists(os.path.sep.join([cv.EGS_HOME + beamDir, '.'.join([thisBeamName, 'egsinp'])])):
                thisBeamName = timeStamp + '_BEAMnrc'

        HEN_HOUSE = os.environ.get('HEN_HOUSE')
        exb = 'scripts/run_user_code_batch'
        exbCall = ''.join([HEN_HOUSE, exb])
        '''
        f = open('/home/ricr/MCQA/queue', 'a')
        f.write('{0} {1} {2} {3} p={4}\n'.format(exbCall, cv.beamDir,
        thisBeamName, cv.beamPegs, cv.nBatch))
        f.close()
        '''
        #os.system('%(exbCall)s %(cv.beamDir)s %(thisBeamName)s %(cv.beamPegs)s p=%(cv.nBatch)s' % locals())
        subprocess.call([exbCall, beamDir, thisBeamName, cv.beamPegs,
        '='.join(['p', str(cv.nBatch)])])

'''
    # write to log file
    if i==0:  # overwrite existing file
        flog = open(logFile, 'w')
    else:  # append to file
        flog = open(logFile, 'a')
    # get currentTime
    currTime = datetime.datetime.now()
    flog.write('{0}\t{1}\n'.format(timeStamp,currTime.strftime("%y%m%d%H%M%S")))
    flog.close()
'''

# update time of last run
samcUtil.writeTimeToFile(cv.timeFile, newTime)

os.remove(lockFile)  # remove lockFile
