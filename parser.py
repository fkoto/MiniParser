#!/usr/bin/python

import os
import sys
import glob

#set of comms to be used by 'all' operations (i.e. AllReduce)
commDict = {}
counterDict = {}

#list of different MPI messages
ignore = ["init", "barrier", "recv", "Irecv", "finalize", "wait", "Phase"]
p2p = ["send", "Rsend", "Bsend", "Ssend", "Isend"]	#probably only "send" may be sufficient. Needs testing.
multi = ["reduce", "gather", "bcast", "scatter"]
multiv = ["gatherv", "scatterv"]
multiAll = ["allReduce", "allGather"]
multiAllv = ["allGatherv", "allToAllv"]
comm = ["split"]

def containsOneOf(lst, string):
	"searches a string if it contains any of the strings in the provided list."
	for el in lst:
		if el in string:
			 return 1
	return 0

def Open(path):
	"Creates the readSet with all the trace files and opens them."
	os.chdir(path)
	filenames = glob.glob("*.txt")
	commDict['MPI_COMM_WORLD'] = {}
	commDict['MPI_COMM_WORLD']['size'] = len(filenames)
	commDict['MPI_COMM_WORLD']['members'] = list(range(0, len(filenames)))
	temp = []
	for name in filenames:
		temp.append(open(name, "r"))

	return temp

def Close(lst):
	"Closes all files in argument list."
	for f in lst:
		f.close()

def printTuple(tup):
	"Converts a tuple to a printable string."
	if (len(tup) == 0):
		return ''
	res = ' '.join(tup)
#	print "printTuple returning " + res
	return '(' + res + ')\n' 

def parseLine(line):
	"This is the parsers main logic. It reads a line and converts it to an appropriate tuple."
	try:
		if (containsOneOf(ignore, line)):
			#print "found ignore: " + line
			return ()

		if (containsOneOf(p2p, line)):
			#print "found p2p: " + line
			splitted = line.split()
			temp = []
			temp.append(splitted[0]) #from
			temp.append(splitted[2]) #to
			temp.append(str(int(splitted[3]) * int(splitted[5]))) #payload
			if int(splitted[7]) < 100: #MPI_Datatype type
				temp.append("contig")
			else:
				temp.append("no contig")

			if (splitted[-1] != "MPI_COMM_WORLD"):
				temp.append("on comm " + splitted[-1])
			return tuple(temp)

		if (containsOneOf(multiAll, line)):
			#TODO add implementation
			splitted = line.split()
			temp = []
			temp.append(splitted[1]) #op
			temp.append(str(int(splitted[2]) * int(splitted[5]))) #payload
			temp.append(splitted[-2]) #comm
			if splitted[-1] in counterDict:
				if (counterDict[splitted[-1]] + 1) == int(commDict[splitted[-2]]['size']):
					print 'commiting'
					#all found
					del counterDict[splitted[-1]]
					return tuple(temp)
				else:
					print 'increasing'
					counterDict[splitted[-1]] += 1 #add one more
			else:
				print 'new id'
				counterDict[splitted[-1]] = 1 #add new id
				
			return ()

		if (containsOneOf(multi, line)):
			#print "found multi: " + line
			splitted = line.split()
			if splitted[0] == splitted[6]:
				temp = []
				temp.append(splitted[1]) #operation
				temp.append(splitted[6]) #root
				temp.append(str(int(splitted[2]) * int(splitted[4]))) #payload
				if int(splitted[7]) < 100: #MPI_Datatype type
					temp.append("contig")
				else:
					temp.append("no contig")
				if (splitted[-1] != "MPI_COMM_WORLD"):
					temp.append("on comm " + splitted[-1]) #comm
				return tuple(temp)
			else:
				return ()

		if (containsOneOf(comm, line)):
			#TODO add implementation
			if ('split' in line):
				if not ('UNDEFINED' in line):
					splitted = line.split('.')
					splitted2 = splitted[-1].split()
					splitted3 = splitted[0].split()
					#comms.write(splitted[2] + ' ' +  splitted[-1] + '\n')
					#commDict[splitted[2]] = {}
					#commDict[splitted[2]]['size']
					#commDict[splitted[2]] = splitted[-1] #new entry in dict
					#counterDict[splitted[2]] = 0 #set counter to 0
					if splitted2[2] in commDict:
						#add member
						commDict[splitted2[2]]['members'].append(splitted3[0])
					else:
						#new comm
						commDict[splitted2[2]] = {}
						commDict[splitted2[2]]['size'] = int(splitted2[-1])
						commDict[splitted2[2]]['members'] = []
						commDict[splitted2[2]]['members'].append(splitted3[0])
						
			return()

		print "found other line: " + line
		return ()
	except:
		print "Exception for line: " + line + " Ignoring!"
		return ()

#
# Main flow
#
if (len(sys.argv) < 2):
	print "Please specify traces directory."
	sys.exit()

#Get traces dir and open files
wdir = sys.argv[1]
readSet = Open(wdir)

#Open global output files
path = "parserOutput"
filename = "global.txt"
os.mkdir(path)
glPhase = open(path + "/" + filename, "w")
comms = open(path + "/communicators.txt", "w")
outputStack = [] #stack that stores files
outputStackNames = []
outputStack.append(glPhase)
outputStackNames.append(filename)
currentOutput = glPhase
nextOutput = ""

completedFiles = []	#temporarily stores files to be removed from readSet
nextPhaseStartFiles = [] #stores files that have reached a new phase
nextPhaseEndFiles = [] #stores files that have completed a phase

#start parsing
while(len(readSet) > 0):
	for f in readSet:
		line = f.readline()
		if (line == ""):	#EOF
			completedFiles.append(f)
			continue
	
		if ("Phase" in line): #new block
			if ("start" in line):
				nextPhaseStartFiles.append(f)
				splitted = line.split()
				#outputStackNames.append(filename)
				nextOutput = splitted[1] + ".txt"
			else:
				nextPhaseEndFiles.append(f)
	
		currentOutput.write(printTuple(parseLine(line)))

	for f in completedFiles:	#remove finished files
		readSet.remove(f)
	
	completedFiles = []	#reset


	for f in nextPhaseStartFiles:	#remove next phase from current one
		if f in readSet:
			readSet.remove(f)

	for f in nextPhaseEndFiles:	#remove next phase from current one
		if f in readSet:
			readSet.remove(f)

	if not readSet and len(nextPhaseStartFiles) > 0: #move to next phase
		currentOutput.write("Going to " + nextOutput + "\n")
		outputStack.append(currentOutput)
		currentOutput = open(path + "/" + nextOutput, "w")
		currentOutput.write("Coming from " + filename + "\n")
		outputStackNames.append(filename)
		filename = nextOutput
		readSet = nextPhaseStartFiles
		nextPhaseStartFiles = []
		continue

	if not readSet and len(nextPhaseEndFiles) > 0: #return from a phase
		nextOutput = outputStackNames.pop()
		currentOutput.write("Returning to " + nextOutput + "\n")
		currentOutput.close() #close file
		currentOutput = outputStack.pop()
		currentOutput.write("Returned from " + filename + "\n")
		filename = nextOutput
		readSet = nextPhaseEndFiles
		nextPhaseEndFiles = []
		
		
	
#print comms
for commName, commValue in commDict.items():
	comms.write(str(commName) + ' ' + str(commValue) + '\n')
#comms.write(str(commDict))

#Close files
Close(readSet)
glPhase.close()
comms.close()
