import os, sys, glob

SKIP = 2

if len(sys.argv) != 5 :
    print 'usage: %s timing-file-pattern app-output-file output-file tight/loose/noVis' % sys.argv[0]
    sys.exit(-1)

inputFilePattern = sys.argv[1]
timingFiles = glob.glob('%s' % inputFilePattern)
couplingType = sys.argv[4]


if couplingType != 'noVis' :
    if len(timingFiles) == 0 :
        print 'Error. No input files found'
        sys.exit(-1)
  

def GetValue(values, s) :
    if len(values) == 0 : return -999999

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
        cTotal = []
        for (f,s) in zip(fields,selector) :
            values = []
            if type(f) is str :
                statName = f
                if stat.has_key(f) : values = stat[f]
                
            elif type(f) is list :
                statName = f[0]
                subNames = f[1]
                values = [0.0] * len(stat[subNames[0]])
                for fi in subNames :
                    vi = stat[fi]
                    values = [sum(i) for i in zip(vi,values)]

            if len(values) > 0 :
               value = GetValue(values, s)
               cTotal.append(value)
            else : cTotal.append(cTotal[-1])

        mins = [min(i) for i in zip(mins, cTotal)]
        maxs = [max(i) for i in zip(maxs, cTotal)]
        total = [sum(i) for i in zip(total, cTotal)]

    ##Averages:
    avg = []
    for t in total :
        avg.append(t/float(len(stats)))
    outputFile.write('Field, Total, Avg, Min, Max\n')
    for (l,t,a, vm, vM) in zip(labels, total, avg, mins, maxs) :
        outputFile.write('%s, %f, %f, %f, %f\n' % (l, t, a, vm, vM))
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
                if stat.has_key(f) : values = stat[f]
                
            elif type(f) is list :
                statName = f[0]
                subNames = f[1]
                values = [0.0] * len(stat[subNames[0]])
                for fi in subNames :
                    vi = stat[fi]
                    values = [sum(i) for i in zip(vi,values)]
            value = GetValue(values, s)
#            print c, statName, values, '-->', value
            outputFile.write('%d, %s, %f\n' % (c, statName, value))
        outputFile.write('\n')


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


def dumpRawData(stats, outputFile) :
    outputFile.write('\n\n')
    outputFile.write('RawData\n')
    outputFile.write('Cycle, rank, numRanks, operation, time (s)\n')

    for c in range(len(stats)) :
        stat = stats[c]
        for k in stat.keys() :
            val = stat[k]
            for i in range(len(val)) :
                rank = i
                nRanks = len(val)
                timeS = stat[k][i]
                outputFile.write('%d, %d, %d, %s, %f\n' % (c, rank, nRanks, k, timeS))                



def ParseAppFile(appOutputFile, stats) :
    appLines = open(appOutputFile, 'r').readlines()
    t0 = 0.0
    cycle = 0
    appTimes = []
    visTimes = []
    t0 = 0.0
    for l in appLines :
        if 'Wall clock' in l :
            t1 = float(l.split()[2])
            appTimes.append(t1-t0)        
            t0 = t1
        elif 'Visit time' in l :
            visTimes.append(float(l.split()[2]))

    for (a,v) in zip(appTimes, visTimes) :
        stats.append({'appTime' : [a], 'visTime' : [v]})
    return stats

def ParseVisService(tf, stats) :
    inputLines = open(tf, 'r').readlines()
    for l in inputLines :
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
        timeS = timeMS/1000.0
        stats[cycle][operation].append(timeS)

    return stats

def ParseInsituVis(tf, stats) :
    inputLines = open(tf, 'r').readlines()
    cycle = -1
    token = inputLines[0].split('_')[1]
    for l in inputLines :
        if token in l :
            cycle = cycle+1
            
        data = l.split(' ')
        operation = data[0].split('_')[1]
        rank = int(data[0].split('_')[2])
        tmp = data[0].split('_')
        nRanks = -1
        if len(tmp) > 3 :
            nRanks = int(data[0].split('_')[3])
        timeMS = float(data[1])
        timeS = timeMS/1000.0
        if not stats[cycle].has_key(operation) :
            stats[cycle][operation] = []

        stats[cycle][operation].append(timeS)
    return stats

def ParseVisFiles(timingFiles, stats) :
    for tf in timingFiles :
        if '.vis.' in tf :
            stats = ParseVisService(tf, stats)
        else :
            stats = ParseInsituVis(tf, stats)
    return stats

#####################################################
## main
#####################################################

stats = []

appOutputFile = sys.argv[2]
outputFile = open(sys.argv[3], 'w') 

stats = ParseAppFile(appOutputFile, stats)
if couplingType != 'noVis' :
    stats = ParseVisFiles(timingFiles, stats)

print len(stats)
#print stats[0]
#print stats[1]
if couplingType == 'tight' :
#    fields = ['appTime','visTime', 'PointAverageFilter', 'ContourFilter', ['Render', ['RenderPlot', 'Bounds', 'DomainIDs', 'DefaultRender']]]
    fields = ['appTime','visTime', 'PointAverageFilter', 'ContourFilter', 'ExecScene']
    selector = [0, 0, 'max', 'max', 'max']
elif couplingType == 'loose' :
    fields = ['appTime', 'visTime', 'point_average', 'contour', 'render']
    selector = [0, 0, 'max', 'max', 'max']
else :
    fields = ['appTime', 'visTime']
    selector = [0, 0]

dumpSummaryAverages(stats[SKIP:len(stats)-1], fields, selector, outputFile)
dumpSummaryStats2(stats, fields, selector, outputFile)
dumpRawData(stats, outputFile)

outputFile.close()
