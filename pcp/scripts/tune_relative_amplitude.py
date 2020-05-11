#!/usr/bin/env python

import logging as _logging
_logger = _logging.getLogger(__name__)

import numpy as _np, os as _os, scipy as _scipy, matplotlib.pyplot as _plt, time as _time

from .. import sweep
from .. import ROACH_LIST, mux_channel
from ..kid import resonator_routines
from ..lib import lib_dirfiles
from ..configuration import filesys_config, logging_config
'''
workflow
1. We start given a logfile that contains the result of a power sweep. 
Several sweeps as function of input attenuation are in this file with dirfile names.
2. Load logfile. Loop over sweeps. Do fit on each KID for each sweep. 
4. save fit results in a dictionary
3. Calculate optimal power setting
4. Rewrite tones amplitude'''
def main(muxch,logfname, save_ampcorr=True, write_tones=False, plot_bifpar=False):
    #load data from the log, including attenuations and dirfile names from the sweep
    powersweeplogpath = _os.path.join(filesys_config['rootdir'], filesys_config['logfiledir'], logfname)
    dirfnames, att_in , att_out = load_sweep_log(powersweeplogpath)
    #sorting the above so that the arrays will be in increasing att_in order
    sortargs = _np.argsort(att_in)
    dirfnames = dirfnames[sortargs]; att_in = att_in[sortargs]; att_out = att_out[sortargs]
    #construct paths to dirfiles
    #this needs to change for multi roach use
    dirfpaths = _np.array([_os.path.join(filesys_config['rootdir'], filesys_config['savedatadir'],'roach0', dp) for dp in dirfnames]) 
    Nsweep = len(dirfpaths)
    fitfunc = resonator_routines.nonlinear_mag_sq 
    fit_result_dicts = []
    for ii in range(Nsweep):
        print 'analyzing sweep {}'.format(dirfnames[ii])
        thisdirfpath = dirfpaths[ii]
        dfobj = lib_dirfiles.open_dirfile(thisdirfpath)
        sweepobj = sweep.pcpSweep(dfobj)
        Nkid = len(sweepobj.tonenames)
        print 'N_KID = {} in sweep'.format(Nkid)
        #do fit, looping over KIDs
        '''Note, fitting is done in |S21|**2
        the function resonator_routines.nonlinear_mag_sq() gives |S21|**2 '''
        fit_results_single_pow = _np.empty(Nkid, dtype=object)
        for jj in range(Nkid):
            #grab data
            freq = sweepobj.rf_freqs[jj,:]
            S21 = sweepobj.data[jj,:]
            S21_mag_sq = _np.abs(S21)**2
            #calc initial guess and do fit
            x0, bounds = set_x0_mag(freq, S21_mag_sq)
            fitparams, fitcov = _scipy.optimize.curve_fit(fitfunc, freq, S21_mag_sq ,x0, bounds=bounds)
            #save fit result to dictionary, and store in array
            fit_result = fitfunc(freq,*fitparams)
            x0_result = fitfunc(freq,*x0)
            #measure goodness of fit
            #Do we need to normalize this fit_chisq? seems to have units of arbitrary ADC units
            # could have bad dependence on att in/out if not linked properly
            fit_chisq = _np.sum(((S21_mag_sq - fit_result)**2) / fit_result)
            fit_dict = {'fit_params': fitparams,'fit_cov':fitcov, 'fit_chisq':fit_chisq, 'fit_result': fit_result, 'x0_result': x0_result, 'x0':x0, 'S21mag':_np.sqrt(S21_mag_sq)}
            fit_results_single_pow[jj] = fit_dict
        fit_result_dicts.append(fit_results_single_pow)
     
    fit_result_dicts = _np.array(fit_result_dicts)
     
     
    ###Done with fitting, now we analyze the result
    #from each kid in each sweep, we extract parameter 'a' asymmetry parameter. As function of 
    optimal_att_in = _np.empty(Nkid)
    for kk in range(Nkid):
        [fit_result_dicts[ll,kk] for ll in range(Nsweep)]
         
        kidbifparam = _np.array([dd['fit_params'][4] for dd in fit_result_dicts[:,kk]])
        kidchisq = _np.array([dd['fit_chisq'] for dd in fit_result_dicts[:,kk]])
        #sort things so that data is in increasing att_in order
        afun = _scipy.interpolate.interp1d(att_in, kidbifparam, fill_value=(_np.min(att_in),_np.max(att_in) ), bounds_error=False)
        interpxx = _np.linspace(_np.min(att_in), _np.max(att_in), 1e3)
        afun_2 = lambda x: afun(x) - 0.5
        try:
            optatten = _scipy.optimize.newton(afun_2, _np.min(att_in))
        except:
            optatten = _np.min(att_in)
        optimal_att_in[kk] = optatten
        interpyy = afun(interpxx)
        
        if plot_bifpar==True:
            _plt.figure()
            _plt.scatter(att_in, kidbifparam)
            _plt.xlabel('input attenuation [dB]')
            _plt.plot(interpxx, interpyy)
            _plt.ylabel('Bifurcation parameter')
            _plt.axvline(optatten, color='r', label='optimal atten')
            _plt.legend()
            
            
            _plt.figure()
            _plt.scatter(att_in, kidchisq)
            _plt.xlabel('input_attenuation [dB]')
            _plt.ylabel('Sum square diff fit vs. data')
            _plt.show()
    ### We've calculated the optimal input attenuation for each KID
    # Use this to calculate optimal amplitude correction
    #This minimum optimal attenuation will is the highest power tone. Set amp = 1 for this tone
    relative_optimal_power_db = -1.0*(optimal_att_in - _np.min(optimal_att_in))
    ampcorr = 10**( relative_optimal_power_db / 20.0 )

    # add new entry to mc.tonelist.ampcorr with unix time as the key
    muxch.toneslist.ampcorr.update( { str(int(_time.time())): ampcorr} )
    _logger.info('New amplitude correction saved')

    if save_ampcorr == True:
        # save to a new ampcorr file
        muxch.toneslist._write_ampcorrfile(ignore_dups=False)
    if write_tones == True:
        '''Is this up to date?'''
        muxch.toneslist.amps =  muxch.toneslist.amps*ampcorr
        muxch.write_freqs_to_fpga(auto_write=True)
    return fit_result_dicts, ampcorr

'''This is temporary, subject to change based on how log file of a power sweep is generated'''
def load_sweep_log(logpath):
    data  = _np.loadtxt(logpath, dtype=object)
    att_in = _np.array([_np.float(xx[:-1]) for xx in data[:,-4]])
    att_out = _np.array([_np.float(xx[:-1]) for xx in data[:,-2]])
    dirfnames = data[:,-1]
    return dirfnames, att_in, att_out

def set_x0_mag(freq, S21_mag_sq):
    '''
    This is a function to generate an initial guess for fit parameters for the function 
    kid.resonator_routines.nonlinear_mag_sq()
    with parameter [fr,Qr,amp,phi,a,b0,b1,flin]
    Can be improved, particularly guess for amp, phi. a. Could use history from previous fit?'''
    f0_grad_guess = freq[_np.argmax(_np.gradient(S21_mag_sq))]
    fr_data = [_np.min(freq), f0_grad_guess, _np.max(freq)]
#         fr_data = [np.min(freq), freq[np.argmin(S21_mag_sq)], np.max(freq)]
    Qr_data = [1.e2, 6.e3, 1.e6]
    amp_data = [0.01, 0.5, 200]
    phi_data = [-_np.pi, 0, _np.pi]
    a_data = [0.0, 0.2, 5]
    b0_data = [-_np.inf, S21_mag_sq[0], _np.inf]
    b1guess = ((S21_mag_sq[-1] - S21_mag_sq[0]) / (freq[-1] - freq[0])) * fr_data[1]
    b1_data = [-_np.inf, b1guess, _np.inf]
    flin_data = fr_data
    param_data = [fr_data, Qr_data, amp_data, phi_data, a_data, b0_data, b1_data, flin_data]
    x0 = []
    boundlow = []; boundhigh = []
    for dd in param_data:
        x0.append(dd[1])
        boundlow.append(dd[0])
        boundhigh.append(dd[2])
    bounds = (boundlow, boundhigh)
    return x0, bounds
