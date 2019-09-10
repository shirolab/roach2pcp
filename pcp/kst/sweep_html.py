from yattag import Doc
from yattag import indent
import glob, os, time, calendar
import numpy as np

def gen_menu(sweepdir = '/data/tuning/roach0/'):
    
    doc, tag, text = Doc().tagtext()
    # List of sweeps
    dirs = list(filter(os.path.isdir, glob.glob(sweepdir + '/2*')))
    # Sort by time - see utils/timestr2ctime
    times = []
    for mydir in dirs:
        struct = time.strptime(mydir[-15:], '%Y%m%d_%H%M%S')
        ctime = calendar.timegm(struct)
        times.append(ctime)

    inds = np.argsort(times)
    inds = np.flip(inds) # reverse chronological
    
    with tag('html'):
        for ii in range(len(inds)):
            thissweep = dirs[inds[ii]][-15:]
            with tag('p'):
                with tag('a', href=thissweep + '/index.html'):
                    text(thissweep)

    #print(indent(doc.getvalue()))
    myfile = open(sweepdir + '/index.html', 'w')
    myfile.write(indent(doc.getvalue()))
    myfile.close()

