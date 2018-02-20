import os, sys, glob

if len(sys.argv) != 4 :
    print 'usage: %s timing-file-pattern app-output-file output-file' % sys.argv[0]
    sys.exit(-1)

inputFilePattern = sys.argv[1]
timingFiles = glob.glob('%s' % inputFilePattern)
if len(timingFiles) == 0 :
    print 'Error. No input files found'
    sys.exit(-1)


def dumpSummaryStats(stats, fields, selector, outputFile) :

    outputFile.write('Cycle, Field, Value\n')
    for c in range(len(stats)) :         
        stat = stats[c]
        val = None
        for (f,s) in zip(fields,selector) :
            if type(s) is int :
               val = stat[f][s]
               sel = '[%d]' % s
            elif type(s) is str :
               if s == 'max' :  val = max(stat[f])
               elif s == 'min' :  val = min(stat[f])
               elif s == 'avg' :  val = sum(stat[f]) / float(len(stat[f]))
               else : print 'Unkown selector ', s
               sel = '_' + s
            else :
                 print 'Unsupported selector type',  type(s)

            if val != None :
               output = '%d, %s%s, %f' % (c,f,sel, val)
               outputFile.write('%s\n' % output)
        outputFile.write('\n')

            



#####################################################
## main
#####################################################

stats = []

appOutputFile = sys.argv[2]
outputFile = open(sys.argv[3], 'w')    

## Process application output file
appLines = open(appOutputFile, 'r').readlines()
t0 = 0.0
cycle = 0
for al in appLines :
    if 'Wall clock' in al :
       t1 = float(al.split()[2])
       appTime = t1-t0
       t0 = t1
       cycle = cycle+1
       stats.append({'appTime' : [appTime]})

for tf in timingFiles :
    inputLines = open(tf, 'r').readlines()
    lastCycle = -1
    for l in inputLines :
        if 'FLOWfilter' in l :
            data = l.split(',')
            cycle = int(data[0])
            rank = int(data[1].split('_')[1])
            nRanks = int(data[1].split('_')[2])
            operation = data[2].strip()
            timeMS = float(data[3])
            if cycle >= len(stats) :
               print 'cycle overrun...', cycle, len(stats)
               continue

            if not stats[cycle].has_key(operation) :
               stats[cycle][operation] = []
            stats[cycle][operation].append(timeMS)


#Print summary stats:
fields = ['appTime', 'ADIOS', 'ADIOS', 'ADIOS']
selector = [0, 'max', 'min', 'avg']

dumpSummaryStats(stats, fields, selector, outputFile)

outputFile.write('\n\n')
outputFile.write('RawData\n')
outputFile.write('Cycle, rank, numRanks, operation, time (ms)\n')
for tf in timingFiles :
    inputLines = open(tf, 'r').readlines()
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
