import os, sys, glob

print sys.argv

if len(sys.argv) != 3 :
    print 'usage: %s input-file-pattern output-file' % sys.argv[0]
    sys.exit(-1)

inputFilePattern = sys.argv[1]
inputFiles = glob.glob('%s' % inputFilePattern)
if len(inputFiles) == 0 :
    print 'Error. No input files found'
    sys.exit(-1)

outputFile = open(sys.argv[2], 'w')    
outputFile.write('Cycle, rank, numRanks, operation, time (ms)\n')

for f in inputFiles :
    inputLines = open(f, 'r').readlines()
    lastCycle = -1
    for l in inputLines :
        if 'FLOWfilter' in l :
            data = l.split(',')
            cycle = int(data[0])
            rank = int(data[1].split('_')[1])
            nRanks = int(data[1].split('_')[2])
            operation = data[2]
            timeMS = float(data[3])
            if cycle > 0 and cycle != lastCycle :
                outputFile.write('\n')
                lastCycle = cycle
            
        outputFile.write('%d, %d, %d, %s, %f\n' % (cycle, rank, nRanks, operation, timeMS))



outputFile.close()
