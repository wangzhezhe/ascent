import os, sys, glob

if len(sys.argv) != 5 :
    print 'usage: %s timing-file-pattern app-output-file output-file tight/loose' % sys.argv[0]
    sys.exit(-1)

inputFilePattern = sys.argv[1]
timingFiles = glob.glob('%s' % inputFilePattern)
if len(timingFiles) == 0 :
    print 'Error. No input files found'
    sys.exit(-1)
couplingType = sys.argv[4]   


def GetValue(values, s) :
    if type(s) is int :
        return values[s]
    elif type(s) is str :
        if s == 'avg' :
            return sum(values) / float(len(values))
        elif s == 'max' :
            return max(values)
        elif s == 'min' :
            return min(values)
    return None


def dumpSummaryAverages(stats, fields, selector, outputFile) :
    total = [0.0] * len(fields)
    mins = [1e10] * len(fields)
    maxs = [-1e10] * len(fields)
    labels = []
    
    for f in fields :
        if type(f) is str : labels.append(f)
        else : labels.append(f[0])
            
    for c in range(len(stats)) :
        stat = stats[c]
        print stat
        cTotal = []
        for (f,s) in zip(fields,selector) :
            values = []
            if type(f) is str :
                statName = f
                print f
                print stat
                values = stat[f]
                
            elif type(f) is list :
                statName = f[0]
                subNames = f[1]
                values = [0.0] * len(stat[subNames[0]])
                for fi in subNames :
                    vi = stat[fi]
                    values = [sum(i) for i in zip(vi,values)]

            value = GetValue(values, s)
            cTotal.append(value)
        mins = [min(i) for i in zip(mins, cTotal)]
        maxs = [max(i) for i in zip(maxs, cTotal)]
        total = [sum(i) for i in zip(total, cTotal)]

    ##Averages:
    avg = []
    for t in total :
        avg.append(t/float(len(stats)))
    outputFile.write('Field, Avg, Min, Max\n')
    for (l,a, vm, vM) in zip(labels, avg, mins, maxs) :
        outputFile.write('%s, %f, %f, %f\n' % (l, a, vm, vM))
    outputFile.write('\n\n')
        

def dumpSummaryStats2(stats, fields, selector, outputFile) :

    outputFile.write('Per cycle data\n')
    outputFile.write('Cycle, Field, Value\n')
    for c in range(len(stats)) :
        stat = stats[c]

        for (f,s) in zip(fields,selector) :
            values = []
            if type(f) is str :
                statName = f
                values = stat[f]
                
            elif type(f) is list :
                statName = f[0]
                subNames = f[1]
                values = [0.0] * len(stat[subNames[0]])
                for fi in subNames :
                    vi = stat[fi]
                    values = [sum(i) for i in zip(vi,values)]

#            print statName, values
            value = GetValue(values, s)
            outputFile.write('%d, %s, %f\n' % (c, statName, value))
        outputFile.write('\n')
#            print statName, value
#            print


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
               if f == "appTime" or f == 'ensure_blueprint_ADIOS' or (f == 'source' and couplingType == 'loose'):
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

## Process application output file
appLines = open(appOutputFile, 'r').readlines()
t0 = 0.0
cycle = 0
for al in appLines :
    if 'Wall clock' in al :
       t1 = float(al.split()[2])
       appTime = (t1-t0) * 1000.0 ##convert to ms
       t0 = t1
       cycle = cycle+1
       stats.append({'appTime' : [appTime]})

for tf in timingFiles :
    inputLines = open(tf, 'r').readlines()
    lastCycle = -1
    for l in inputLines :
        if 'VISapp_' in l :
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

        elif 'FLOWfilter' in l :
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

if couplingType == 'tight' :
    fields = ['appTime',
              ['contour', ['create_scene_scene1', 'source', 'verify', 'vtkh_data', 'pl1_0_vtkh_marchingcubes']],
              ['render', ['pl1', 'plt1_scene1', 'add_plot_plt1_scene1', 'plt1_scene1_bounds', 'plt1_scene1_domain_ids', 'scene1_renders', 'exec_scene1']]]
    selector = [0, 'max', 'max']
    
elif couplingType == 'loose' :
    fields = ['appTime', 'contour', 'render', ['staging', ['source', 'ensure_blueprint_ADIOS','ADIOS']]]
    selector = [0, 'max', 'max', 'max']    


dumpSummaryAverages(stats[2:], fields, selector, outputFile)
dumpSummaryStats2(stats, fields, selector, outputFile)

##dumpSummaryStats(stats, fields, selector, contourTimeList, renderTimeList, outputFile)

outputFile.write('\n\n')
outputFile.write('RawData\n')
outputFile.write('Cycle, rank, numRanks, operation, time (ms)\n')
for tf in timingFiles :
    inputLines = open(tf, 'r').readlines()
    lastCycle = -1
    for l in inputLines :
        if 'FLOWfilter' in l or 'VISapp' in l :
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
