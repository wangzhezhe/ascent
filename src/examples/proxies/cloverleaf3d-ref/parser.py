import os, sys, glob
#import numpy
#import matplotlib.pyplot as plt

SKIP = 2

if len(sys.argv) != 6 :
    print 'usage: %s timing-file-pattern app-output-file output-file tight/loose/noVis numSteps' % sys.argv[0]
    sys.exit(-1)

inputFilePattern = sys.argv[1]
timingFiles = glob.glob('%s' % inputFilePattern)
couplingType = sys.argv[4]
ENDSKIP = int(sys.argv[5])

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
            #print 'cycle overrun...', cycle, len(stats)
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

def dumpArray(x, fname) :
    print fname, min(x), max(x), 'Total= ', sum(x)
    
    f = open(fname, 'w')
    f.write('%s\n' % fname)
    for i in x :
        f.write('%f\n' % i)
    f.close()

def dumpHistogramsAtStep(stats, fields, outputFileName, couplingType) :
    appTime = stats['appTime'][0]
    visTime = stats['visTime'][0]
#    print appTime, visTime
#    print stats.keys()
    
    N = len(stats[fields[2]])
    data = []
    indy500 = [0.0]*N
    total = [0.0]*N
    idle = [0.0]*N
    busy = [visTime]*N
    for f in fields[2:] :
        x = stats[f]
        data.append(x)
        for i in range(N) : total[i] = total[i] + x[i]

    maxTotal = max(total)
    for i in range(N) : idle[i] = visTime - total[i]
    minIdle = min(idle)
    
    for i in range(N) : busy[i] = max(0.0, total[i] - idle[i])
    
    for i in range(N) : idle[i] = idle[i] - minIdle
    for i in range(N) : indy500[i] = maxTotal - total[i]

    dumpArray(total, 'total.hist')
    dumpArray(idle, 'idle.hist')
    dumpArray(busy, 'busy.hist')
    dumpArray(indy500, 'indy500.hist')
    print 'Total Idle= ', sum(idle)
    print 'Total Busy= ', sum(busy)
    print 'Total Total= ', sum(total)
    titles = ['Total', 'Idle', 'Busy', 'Indy500']
    plotVars = [total, idle, busy, indy500]

    for f in fields[2:] :
        titles.append(f)
        plotVars.append(stats[f])

    for (t,p) in zip(titles, plotVars) :
        dumpArray(p, couplingType + '.' + t +'.hist')

    # binVar = 20
    # for (t,p) in zip(titles, plotVars) :        
    #     plt.title(t)
    #     plt.hist(p, bins=binVar)
    #     plt.yscale('log')
    #     plt.savefig(couplingType + '.' + t+'.png')
    #     plt.show()        
        
    print 'appTime= ', appTime
    print 'visTime= ', visTime

def dumpVisTimeHistograms(stats, couplingType) :
    vals = []
    for s in stats :
        vals.append(s['visTime'][0])

    dumpArray(vals, couplingType + '.visTime.hist')
    

#####################################################
## main
#####################################################

stats = []

appOutputFile = sys.argv[2]
outputFileName = sys.argv[3]
outputFile = open(outputFileName, 'w')

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
    fields = ['appTime', 'visTime', 'read', 'point_average', 'contour', 'render', 'ts_time']
    selector = [0, 0, 'max', 'max', 'max', 'max', 'max']
else :
    fields = ['appTime', 'visTime']
    selector = [0, 0]

dumpSummaryAverages(stats[SKIP:ENDSKIP], fields, selector, outputFile)
dumpSummaryStats2(stats, fields, selector, outputFile)
dumpRawData(stats, outputFile)

dumpHistogramsAtStep(stats[98], fields, outputFileName, couplingType)
dumpVisTimeHistograms(stats[SKIP:len(stats)-1], couplingType)

outputFile.close()
