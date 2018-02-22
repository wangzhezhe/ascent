import os, sys, glob

if len(sys.argv) != 5 :
    print 'usage: %s timing-file-pattern app-output-file output-file tight/loose' % sys.argv[0]
    sys.exit(-1)

inputFilePattern = sys.argv[1]
timingFiles = glob.glob('%s' % inputFilePattern)
if len(timingFiles) == 0 :
    print 'Error. No input files found'
    sys.exit(-1)


def dumpSummaryStats(stats, fields, selector, contourTimeList, renderTimeList, outputFile) :

    outputFile.write('Cycle, Field, Value\n')
    for c in range(len(stats)) :         
        stat = stats[c]
        val = None
        contourTime = 0
        renderTime = 0
        for (f,s) in zip(fields,selector) :
            if type(s) is int :
               val = stat[f][s]
               sel = '[%d]' % s
            elif type(s) is str :
               if s == 'max' :  
                   val = max(stat[f])
                   if f in contourTimeList :
                       contourTime = contourTime + val
                   elif f in renderTimeList :
                       renderTime = renderTime + val
               elif s == 'min' :  val = min(stat[f])
               elif s == 'avg' :  val = sum(stat[f]) / float(len(stat[f]))
               else : print 'Unkown selector ', s
               sel = '_' + s
            else :
                 print 'Unsupported selector type',  type(s)

            if val != None :
               output = '%d, %s%s, %f' % (c,f,sel, val)
               outputFile.write('%s\n' % output)
        output = '%d, Max_Contour, %f' % (c, contourTime)
        outputFile.write('%s\n' % output)
        output = '%d, Max_Render, %f' % (c, renderTime)
        outputFile.write('%s\n' % output)
        outputFile.write('\n')

            



#####################################################
## main
#####################################################

stats = []

appOutputFile = sys.argv[2]
outputFile = open(sys.argv[3], 'w') 
couplingType = sys.argv[4]   

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
##---- settings for tight coupling
if couplingType == 'tight' :
    fields = ['appTime', 'create_scene_scene1', 'source', 'verify', 'vtkh_data', 'pl1_0_vtkh_marchingcubes', 'pl1', 'plt1_scene1', 'add_plot_plt1_scene1', 'plt1_scene1_bounds', 'plt1_scene1_domain_ids', 'scene1_renders', 'exec_scene1']
    selector = [0, 'max', 'max', 'max', 'max', 'max', 'max', 'max', 'max', 'max', 'max', 'max'] #, 'min', 'avg']
    contourTimeList = ['create_scene_scene1', 'source', 'verify', 'vtkh_data', 'pl1_0_vtkh_marchingcubes']
    renderTimeList = ['pl1', 'plt1_scene1', 'add_plot_plt1_scene1', 'plt1_scene1_bounds', 'plt1_scene1_domain_ids', 'scene1_renders', 'exec_scene1']
##--

##---- settings for loose coupling
elif couplingType == 'loose' :
    fields = ['appTime']
    selector = [0]
    contourTimeList = []
    renderTimeList = []
##----

dumpSummaryStats(stats, fields, selector, contourTimeList, renderTimeList, outputFile)

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
