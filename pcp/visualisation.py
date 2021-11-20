#
# Plotting routines to visualise various data products

# Demo visualisation tool
#   [20190304] Plot for averaged data completed. It shows sweeps, IQ circles and speed figures
#
#   [20181217] So far you can plot the data from a the raw directory, but it has to be able to read it from the sweep folder as well.
# It just plot the magnitude vs frequency and IQ circles, the rest of the options are empty. The plot functions need to take in consideration
# the tonelist and the central frequency to correct the x-axis
#
# To run:
#
#   bb-> For the moment comes from toneslist, but in future it should be in the directories
# >> dirfile = "./pcp/testing/run/data/dummyroach/20181125_172118_sweep_raw/"
# >> plot_sweep_data(dirfile,bb)

# from plotly import tools
# from plotly.offline import plot, init_notebook_mode
# import plotly.graph_objs as go

import os as _os, sys as _sys, time as _time
import numpy as _np
import logging as _logging
_logger = _logging.getLogger(__name__)
import cmath as _cmath
import pygetdata as _gd

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.widgets import MultiCursor
from matplotlib.ticker import FormatStrFormatter

plt.ion()

# This should be in another file/script
import detector_peaks as find_peaks
from scipy.signal import savgol_filter
import signal

from .sweep import pcpSweep

# # Offline mode. For plotly
# init_notebook_mode(connected=True)
#
#
# # TODO add bb_freqs to files in order to not load it here -- Done
# def reloc_tones(diryfile, overlap_dist=20e3, plot=True, plot_tones=True):
#
#     new_tonelist = []
#     freqs,sweep = get_sweep_data(diryfile)
#
#     for kid in sweep:
#         peaks, mag_peaks = find_detectors(sweep[kid], freqs[kid])
#         sweep_s21 = _get_log_mag(sweep[kid])
#
#         if plot:
#             plt.plot(freqs[kid], sweep_s21)
#             plt.plot(freqs[kid][peaks], sweep_s21[peaks], "x")
#
#         for peak in peaks:
#             new_tone = freqs[kid][peak]
#             if plot_tones:
#                 plt.axvline(new_tone, color='k')
#             new_tonelist.append(new_tone)
#
#     # Filter new toneslist from overlaps
#     new_filter_tonelist = []
#     new_tonelist = _np.sort(new_tonelist)
#
#     for i in range(len(new_tonelist)-1):
#         if (new_tonelist[i+1] - new_tonelist[i]) > overlap_dist:
#             new_filter_tonelist.append(new_tonelist[i])
#
#     # The last element
#     if (new_tonelist[-1] - new_tonelist[-2]) > overlap_dist:
#         new_filter_tonelist.append(new_tonelist[-1])
#
#     return new_filter_tonelist
#
# def rewrite_toneslist(toneslist, new_tones):
#
#     header = "name\tfreq\tpower\toffset\tatt\tall\tnone\n"
#
#     file = open(toneslist.tonelistfile,'w')
#     file.write(header)
#
#     nkid = 0
#     for line in new_tones:
#         name = "K" + str(nkid).zfill(3)
#         row = name + '\t' + str(int(line)) + '\t' + "0\t0\t1\t0\t0\n"
#         file.write(row)
#         nkid += 1
#
#     file.close()
#
#     toneslist.load_tonelist(toneslist.tonelistfile)
#     print "Toneslist updated"
#
#
# def find_detectors(sweep, freq, start=10, stop=10, distance=70e3, limit=3, order=3, npoints=15, method='max_speed'):
#
#     # Assuming that is constant
#     df = freq[1]-freq[0]
#
#     #freq = freq[start:stop]
#     #sweep = sweep[start:stop]
#
#     if method == "max_speed":
#         signal = _get_speed(freq, sweep)[1]
#         valley = False
#     elif method == "min_s21":         # <--- THIS METHOD DOESNT WORK
#         signal = _get_log_mag(sweep)
#         valley = True
#
#     # Detect peaks
#     smooth_mag = savgol_filter(signal, npoints, order)
#
#     mph = _np.nanmax(signal)/4
#     mpd = distance/df
#
#     peaks = find_peaks.detect_peaks(smooth_mag, mph=mph, mpd=mpd, valley=valley)
#
#     if len(peaks) > limit:
#         peaks = []
#
#     print "Peaks detected: ", len(peaks)
#     return peaks, sweep[peaks]
#
# def _get_log_mag(cplx_IQ):
#     """
#     Get the magnitude from I, Q signals
#     """
#     return 20*_np.log10(abs(cplx_IQ))
#
# def _get_mag(cplx_IQ):
#     """
#     Get the magnitude from I, Q signals
#     """
#     return abs(cplx_IQ)
#
# def _get_phase(cplx_IQ, deg=False):
#     """
#     Get the phase from I,Q signals
#     """
#     phase = _cmath.phase(cplx_IQ)
#     if deg:
#         return phase*180/_np.pi
#     else:
#         return phase
#
# def _get_speed(freqs, cplx_IQ):
#     """
#     Get the speed from I,Q signals
#     """
#     di_df = _np.diff(cplx_IQ.real)/_np.diff(freqs)
#     dq_df = _np.diff(cplx_IQ.imag)/_np.diff(freqs)
#
#     speed = _np.sqrt(di_df**2 + dq_df**2)
#
#     return freqs[1:],speed
#
# def get_sweep_data(diryfile):
#     """
#     Get data from a sweep dirfile which is the averaged data from raw directories
#     """
#
#     sweep_dirfile = _gd.dirfile(diryfile, _gd.RDONLY)
#
#     field_lo = "sweep.lo_freqs"
#     field_bb = "sweep.bb_freqs"
#     kids_fields = [field[6:] for field in sweep_dirfile.field_list() if field.startswith("sweep.") and field != field_lo and field !=field_bb]
#
#     sweep_lo = sweep_dirfile.get_carray(field_lo)
#     bb_freqs = sweep_dirfile.get_carray(field_bb)
#
#     # Sweep data, like complex numbers
#     lo_freqs = dict()
#     sweep_data = dict()
#
#     n = 0
#     for kid in kids_fields:
#         lo_freqs[kid] = sweep_lo + bb_freqs[n]
#         sweep_data[kid] = sweep_dirfile.get_carray("sweep." + kid)
#         n += 1
#
#     return lo_freqs, sweep_data
#
# def get_stream_data(diryfile):
#     """
#     Get data from time stream dirfile
#     """
#
#     time_dirfile = _gd.dirfile(diryfile, _gd.RDONLY)
#
#     time_field = "python_timestamp"
#     fields_forbiden = ['metadata.raw_sweep_filename','INDEX', 'gpio_reg', 'raw_packet', 'packet_count', 'pps_timestamp', 'fine_timestamp', 'roach_checksum', 'packet_info_reg', 'python_timestamp']
#     kids_fields = [field for field in time_dirfile.field_list() if not (field in fields_forbiden or field.startswith("sweep."))]
#
#     try:
#         field_lo = "sweep.lo_freqs"
#         field_bb = "sweep.bb_freqs"
#         sweep_fields = [field for field in time_dirfile.field_list() if field.startswith("sweep.") and field != field_lo and field !=field_bb]
#
#         sweep_lo = time_dirfile.get_carray(field_lo)
#         bb_freqs = time_dirfile.get_carray(field_bb)
#
#         lo_freqs = dict()
#         sweep_data = dict()
#
#         n = 0
#         for kid in kids_fields:
#             lo_freqs[kid] = sweep_lo + bb_freqs[n]
#             sweep_data[kid] = sweep_dirfile.get_carray("sweep." + kid)
#             n += 1
#     except:
#         lo_freqs = []
#         sweep_data = []
#
#     time = time_dirfile.getdata(time_field)
#
#     # Time data
#     time_stream = dict()
#
#     for kid in kids_fields:
#         time_stream[kid] = time_dirfile.getdata(kid)
#
#     return time, time_stream, lo_freqs, sweep_freqs
#
# def get_dxdf(freqs, x, smooth=True, order=3, npoints=7):
#     """
#     Get dx/df, where x could be i or q
#     """
#     if smooth:
#         x = savgol_filter(x, npoints, order)
#
#     dx_df = _np.gradient(x, freqs)
#
#     return dx_df
#
# def get_df(I, Q, I_sweep, Q_sweep, didf, dqdf, f0):
#     """
#     Get df. Variaability in resonance frequency
#     """
#     speed_mag = (didf[f0]**2)+(dqdf[f0]**2)
#     df = ( (I_sweep[f0]-I)*didf) + ( (Q_sweep[f0]-Q)*dqdf ) / speed_mag
#     return df
#
# def plot_df_psd(diryfile):
#     """
#     Get the PSD
#     """
#
#
#
# def color_msg(object):
#     """
#     Colors for messages. Short cuts to color the messages
#     """
#     def __init__(self):
#         self.COLOR_SEQ = "\033[1;%dm"
#
#         self.HEADER    = '\033[95m'
#         self.OKBLUE    = '\033[94m'
#         self.OKGREEN   = '\033[92m'
#         self.WARNING   = '\033[93m'
#         self.FAIL      = '\033[91m'
#         self.ENDC      = '\033[0m'
#         self.BOLD      = '\033[1m'
#         self.UNDERLINE = '\033[4m'
#
#         self.BLACKTXT, self.REDTXT, self.GREENTXT, self.YELLOWTXT, self.BLUETXT, self.MAGENTATXT, self.CYANTXT, self.WHITETXT = [30 + i for i in range(8)]
#         self.LOGCOLORS = {
#             'WARNING' : YELLOWTXT,
#             'INFO'    : WHITETXT,
#             'DEBUG'   : CYANTXT,
#             'CRITICAL': BLUETXT,
#             'ERROR'   : REDTXT }
#
# # Bunch of functions to plot sweep averaged data using plotly
# # To run
# # >>  run pcp/visualization.py
# # >>  plot_sweep_data('/path/of/dirfile', bb_freqs)
#
# def plot_sweep_html(diryfile):
#     """
#     Debug function in order to plot
#     """
#     lo_freqs, sweep_data = get_sweep_data(diryfile)
#     sample_freq = lo_freqs[lo_freqs.keys()[0]]
#     bw = sample_freq[-1] - sample_freq[0]
#     step = sample_freq[1] - sample_freq[0]
#     nKIDS = len(lo_freqs)
#
#     # Recuding the full path to just the name
#     filename = ""
#     for i in range(1, len(diryfile)):
#         if diryfile[-i] == "/":
#             break
#         filename = diryfile[-i] + filename
#
#     header = dict(text='<b>File: </b>'+filename+'<br><b>Bandwidth: </b>'+str(bw)+' Hz<br><b>Step: </b>'+str(step)+'<br><b>Number of KIDs: </b>'+str(nKIDS),
#                     font=dict(color='white',size=10), borderpad=10, x=0.8, y=1.125, xref='paper',yref='paper', align='left', showarrow=False, bgcolor='black')
#
#     _plt = pcp_plot(header)
#     _plt.plot(lo_freqs, sweep_data)
#
#
# class pcp_plot(object):
#
#     def __init__(self, header):
#         """
#         Layout defintion and plot functions
#         We define the basic structure of the pcp plot tool: buttons, sliders, text ...
#         """
#
#         # Text
#         title = dict(text='<b>PCP Plot Tool Demo</b>', font=dict(color='white',size=20), borderpad=10, x=0, y=1.1, xref='paper',
#                   yref='paper', align='left', showarrow=False, bgcolor='black')
#
#         # Information about the plot
#         notes = header
#
#         # General Annotations
#         self.annotations = list([title,notes])
#
#         # Buttons
#         self.updatemenus=list([
#            # Basic buttons
#            #  Sweep. Plot the frequency vs magnitude sqrt(I**2 + Q**2) of each KID
#            #  IQ Circles. Plot I vs Q
#            #  Speed IQ Circles. Plot frequency vs magnitude of speed vector of the IQ circles
#            dict(
#                 buttons = list([
#                     dict(label = 'Reset',
#                          method = 'update',
#                          args = [{'visible': [True]},
#                                  {'annotations': self.annotations}]),
#                 ]),
#                 direction = "left",
#                 pad = {'r':10,'t':10},
#                 xanchor = 'left',
#                 yanchor = 'top',
#                 x = 0.89,
#                 y = 1.12,
#                 type = 'buttons',
#                 bgcolor = '#AAAAAA',
#                 active = 99,
#                 bordercolor = '#FFFFFF',
#                 font = dict(size=11, color='#000000')
#             ),
#             # Custom buttons. To customize the plot window
#             # Tones. Show where the tone is sent
#             # Max Sweep. Show where is the point with the maximum vector speed of IQ circles
#             # Min Mag. Show the point with the minimum magnitude
#             # Q fitting. Fits the Q curve
#             dict(
#                 buttons = list([
#                     dict(label = 'Annotations',
#                          method = 'relayout',
#                          args = [{'annotations':self.annotations,
#                                  'visible': [True],
#                                  'shapes':[]}]),
#                 ]),
#                 direction = "left",
#                 pad = {'r':10,'t':10},
#                 xanchor = 'left',
#                 yanchor = 'top',
#                 x = 0.82,
#                 y = 1.12,
#                 type = 'buttons',
#                 bgcolor = '#AAAAAA',
#                 active = 99,
#                 bordercolor = '#FFFFFF',
#                 font = dict(size=11, color='#000000')
#             ),
#         ])
#
#         # Sliders
#         #   The slides show one by one each KID sorted by the frequency
#         steps = []
#         for i in range(2):
#             step = dict(
#                 method = 'restyle',
#                 args = ['visible', [False] * 2],
#             )
#             step['args'][1][i] = True
#             steps.append(step)
#
#         self.sliders = [dict(
#             active = 10,
#             currentvalue = {"prefix": "KID: "},
#             pad = {"t": 50},
#             steps = steps
#         )]
#
#         # Layout
#         self.layout = go.Layout(dict(
#             #margin = dict( t=100, b=100, l=100, r=100 ),
#             font = dict( family='Courier New, monospace', color='#FFFFFF', size=15),
#             paper_bgcolor = '#252525',
#             plot_bgcolor = "#252525",
#
#             xaxis1 = dict(
#                  #anchor='x1',
#                  title='<b>Frequency [Hz]</b>',
#                  ticks='outside',
#                  gridwidth=1,
#                  gridcolor='#404040',
#                  ticksuffix='Hz',
#                  exponentformat="SI",
#                  titlefont=dict(
#                      family='Courier New, monospace',
#                      size=18,
#                      color='#7f7f7f'
#                  )
#              ),
#              yaxis1 = dict(
#                  #anchor='y1',
#                  title='<b>S<sub>21</sub>[dB]</b>',
#                  ticks='outside',
#                  gridwidth=1,
#                  gridcolor='#404040',
#                  titlefont=dict(
#                      family='Courier New, monospace',
#                      size=18,
#                      color='#7f7f7f'
#                  )
#              ),
#
#             xaxis2 = dict(
#                  #anchor='x2',
#                  title='<b>I</b>',
#                  ticks='outside',
#                  gridwidth=1,
#                  gridcolor='#404040',
#                  exponentformat="SI",
#                  titlefont=dict(
#                      family='Courier New, monospace',
#                      size=18,
#                      color='#7f7f7f'
#                  )
#              ),
#              yaxis2 = dict(
#                  #anchor='y2',
#                  title='<b>Q</b>',
#                  ticks='outside',
#                  gridwidth=1,
#                  gridcolor='#404040',
#                  exponentformat="SI",
#                  titlefont=dict(
#                      family='Courier New, monospace',
#                      size=18,
#                      color='#7f7f7f'
#                  )
#              ),
#
#             xaxis3 = dict(
#                  #anchor='x3',
#                  title='<b>Frequency [Hz]</b>',
#                  ticks='outside',
#                  gridwidth=1,
#                  gridcolor='#404040',
#                  ticksuffix='Hz',
#                  exponentformat="SI",
#                  titlefont=dict(
#                      family='Courier New, monospace',
#                      size=18,
#                      color='#7f7f7f'
#                  )
#              ),
#              yaxis3 = dict(
#                  #anchor='y3',
#                  title='<b>Speed[dB]</b>',
#                  ticks='outside',
#                  gridwidth=1,
#                  gridcolor='#404040',
#                  exponentformat="SI",
#                  titlefont=dict(
#                      family='Courier New, monospace',
#                      size=18,
#                      color='#7f7f7f'
#                  )
#              ),
#
#             updatemenus = self.updatemenus,
#             sliders=self.sliders,
#             annotations=self.annotations
#         )
#         )
#
#     def plot(self, freqs, data, filename='pcp_plot.html'):
#
#         self.sweep = []
#         self.iq_circle = []
#         self.speed_iq_circle = []
#
#         self.tones = []
#         self.tonesLines = []
#
#         for kid in sorted(data):
#             # Plots
#
#             mag = _get_log_mag(data[kid])
#             self.sweep.append(go.Scatter(x=freqs[kid],
#                                     y=mag,
#                                     name=kid,
#                                     xaxis='x1',
#                                     yaxis='y1',
#                                     legendgroup = 'sweep_'+kid,
#                                     showlegend=True,
#                                     visible=True))
#                                     #line=dict(color='#33CFA5'))
#
#             self.iq_circle.append(go.Scatter(x=data[kid].real,
#                                     y=data[kid].imag,
#                                     xaxis='x2',
#                                     yaxis='y2',
#                                     name=kid,
#                                     legendgroup = 'sweep_'+kid,
#                                     showlegend=False,
#                                     visible=True))
#
#             freqs_speed, speed = _get_speed(freqs[kid], data[kid])
#             self.speed_iq_circle.append(go.Scatter( x=freqs_speed,
#                                                     y=speed,
#                                                     name=kid,
#                                                     xaxis='x3',
#                                                     yaxis='y3',
#                                                     legendgroup = 'sweep_'+kid,
#                                                     showlegend=False,
#                                                     visible=True))
#
#             # Settings
#             x_tone = _np.median(freqs[kid])
#             arg_y_tone = _np.where(mag<x_tone)
#
#             try:
#                 y_tone = mag[arg_y_tone[0][0]]
#             except:
#                 continue
#
#             self.tones.append(dict(x=x_tone,
#                            y=y_tone,
#                            xref='x', yref='y',
#                            text='Tone:<br>'+str(_np.median(freqs[kid])),
#                            ax=0, ay=-40))
#
#             magFilter = [m for m in mag if not _np.isnan(m)]
#             center = (_np.max(magFilter) - _np.min(magFilter))/3
#
#             self.tonesLines.append(dict(
#                 type='line',
#                 x0=x_tone,
#                 y0=_np.min(magFilter) - center,
#                 x1=x_tone,
#                 y1=_np.max(magFilter) + center,
#                 line={
#                     "color":'rgb(180, 180, 180)',
#                     "dash": "dashdot",
#                     "width": 2}))
#
#             """
#             self.tones.append(go.Scatter(x=[_np.median(freqs[kid])]*500,
#                                     y=_np.linspace(_np.min(mag),_np.max(mag),500),
#                                     name=kid,
#                                     visible=False))
#             """
#
#
#         self.data = self.sweep + self.iq_circle + self.speed_iq_circle
#
#         # Visibility of each plot
#         self.updatemenus[0]["buttons"][0]["args"][0]["visible"] = [True]*len(self.data)
#         self.updatemenus[1]["buttons"][0]["args"][0]["annotations"] = self.tones + self.annotations
#         self.updatemenus[1]["buttons"][0]["args"][0]["shapes"] = self.tonesLines
#
#         # Updating the sliders
#         steps = []
#         for i in range(len(data)):
#             step = dict(
#                 method = 'restyle',
#                 label = sorted(data)[i],
#                 args = ['visible', [False] * len(self.data)],
#             )
#             # Sweep
#             #if self.updatemenus[0]["buttons"][0]["args"][0]["visible"][0]:
#             step['args'][1][i] = True
#             # IQ
#             #if self.updatemenus[0]["buttons"][1]["args"][0]["visible"][len(self.sweep) + 1]:
#             step['args'][1][i + len(self.sweep)] = True
#             # Speed
#             #if self.updatemenus[0]["buttons"][1]["args"][0]["visible"][len(self.sweep) + len(self.iq_circle) + 2]:
#             step['args'][1][i + len(self.sweep) + len(self.speed_iq_circle)] = True
#
#             steps.append(step)
#
#         self.sliders = [dict(
#             active = 0,
#             currentvalue = {"prefix": "KID: "},
#             pad = {"t": 50},
#             steps = steps
#         )]
#
#         self.layout["annotations"] = self.annotations
#         self.layout["updatemenus"] = self.updatemenus
#         self.layout["sliders"] = self.sliders
#
#         fig = tools.make_subplots(rows=2, cols=4, specs=[[{'rowspan':2, 'colspan':3}, None, None, {}], [None, None, None, {}]], vertical_spacing=0.1)
#
#         for sweep in self.sweep:
#             fig.append_trace(sweep, 1, 1)
#
#         for iq in self.iq_circle:
#             fig.append_trace(iq, 1, 4)
#
#         for speed in self.speed_iq_circle:
#             fig.append_trace(speed, 2, 4)
#
#         #fig['layout'] = self.layout
#         fig['layout'].update(self.layout)
#         #fig['layout'].update(height=600, width=800, title='i <3 annotations and subplots')
#
#         #fig = dict(data=self.data, layout=self.layout)
#         plot(fig, filename=filename)


class pcpInteractivePlot(object):
    """Simple interactive plotting interface based on matplotlib for convenient visualisation
    of the sweep data. """

    # TODO
    #   - make this compatible with the pcp.sweep object
    #   - plot everything else...
    # - this class should be used by pcp.pcpSweep to plot all sweeps
    # want the ability to plot multiple sweeps on the same axis, and loop through in the same way

    #def __init__(self, fdata, iqdata, caldata, calparams, tonenames, sortfreqs = True, block=False):
    def __init__(self, pcpsweeps, sortfreqs = True, block=False, usepyplot = True):

        self.usepyplot = usepyplot

        self.block = block

        pcpsweeps = _np.atleast_1d(pcpsweeps).tolist() # numpy atleast_1d is easy way to ensure list/array input
        assert all([isinstance(pcpsweep, pcpSweep) for pcpsweep in pcpsweeps]), "input doesn't appear to be a set of pcpSweeps"
        self.sweeplist = pcpsweeps

        # check that sweep names are different and set to be different if true
        names = [si.name for si in pcpsweeps]

        if len(set(names)) < len(names):
            # need to append some strings
            for i, si in enumerate(pcpsweeps[1:]):
                si.name = si.name + "_" + str(i+1)

        self.names = [si.name for si in pcpsweeps]

        # check all the sweeps have the same number of tones as a preliminary check
        assert len(set([len(s.tonenames) for s in pcpsweeps]))==1, "the given sweeps appear to have a different number of tones"
        #assert [s.tonenames for s in pcpsweeps]))==1, "the given sweeps appear to have different tonenames"
        self.ntones = len(s.tonenames)

        self.sortidxs = _np.argsort(self.sweeplist[0].rf_freqs.T[0]) if sortfreqs else _np.arange(self.ntones) # sort on the first frequency element
        self.tonenames = _np.array(s.tonenames)[self.sortidxs].tolist()

        #
        self.idx = 0
        self._picked    = [] # empty list used to store which resonators have been picked
        #self._isvisible = _np.zeros(self.ntones, dtype='bool') # empty list used to store which resonators have manual picked frequencies
        self._pkdidxs   = _np.zeros(self.ntones, dtype=_np.int32)

        self._linedict = {s.name: {} for s in self.sweeplist}
        self._color_dict = { 'default' : (1,1,1,1), 'picked' : (0.5, 0.8, 0.9, 1.0) }

        self._shift_is_held = False

        self._configure_axes()
        self._configure_plots()
        self.print_help()

    def print_help(self):
        print ("""
        Simple sweep visualizer. Possible options:
            - Use left/right arrow keys to browse through tones.
            - Shift + click to add a tone to the re-analyze list.
            - Double left click on the IQ plot to manually reposition the tone.
            - Double right click on the IQ plot to add a new tone at that position

        """)
    @property
    def exclude_idxs(self):
        return _np.array( list(set(_np.arange(self.ntones)).difference(self._picked)))

    def reshow(self):
        self._configure_axes()
        self._configure_plots()

    def save_plots_to_file(self, savedir = None, all_in_one = False, overwrite=False):
        """Function to save the latest version of the plots to a file. Note that it takes a while. """

        # allow user to set a custom savedir, otherwise get the savedir sweep directory name
        lastsweep = self.sweeplist[0]
        savedir = savedir if savedir else _os.path.join( lastsweep.outputdir, lastsweep.name )

        # add check to see if the save directory already exists
        if not _os.path.exists(savedir):
            _logger.info ( "creating directory - {0}".format(savedir) )
            _os.makedirs(savedir)

        else :
            _logger.warning ("directory - {0} - exists - potential to overwrite existing plots.".format(savedir))
            _time.sleep(0.01)

            if overwrite or raw_input("overwrite? [y/[n] : ") == 'y':
                pass
            else:
                _logger.info("returning - nothing done")
                return

        plt.ioff()
        # use pdfpages to create a single page if desired
        if all_in_one:
            from matplotlib.backends.backend_pdf import PdfPages
            pp = PdfPages(_os.path.join(savedir+'plots.pdf'))
        else:
            pp = None

        for idx in range(self.ntones):
            self.idx = idx
            resname = _np.roll( self.tonenames, -self.idx )[0]
            suffix = _os.extsep + 'pdf'
            fout   = _os.path.join(savedir, resname + suffix )
            self.refresh_plot()

            # save the figures
            if all_in_one:
                pp.savefig(self.fig.canvas)
            else:
                self.fig.savefig(fout)
            _sys.stdout.write( "saving figure {0}/{1} : {2}\r".format(idx, self.ntones, _os.path.basename(fout)) )
            _sys.stdout.flush( )

        plt.ion()

    def _configure_axes(self):

        do_figsum=False

        if self.usepyplot == False:
            fig = matplotlib.figure.Figure(figsize=(13.5,  7))
            canvas = matplotlib.backends.backend_qt5agg.FigureCanvasQTAgg(fig)
            if do_figsum:
                figsum = matplotlib.figure.Figure(figsize=(13.5,  7))
                cansum = matplotlib.backends.backend_qt5agg.FigureCanvasQTAgg(figsum)
        else:
            fig = plt.figure(figsize=(13.5,  7))
            canvas = fig.canvas
            if do_figsum:
                figsum = plt.figure(figsize=(13.5,  7))
                cansum = figsum.canvas

        axiq  = fig.add_subplot(122)
        axmag = fig.add_subplot(321)
        axphi = fig.add_subplot(323, sharex = axmag)
        axcal = fig.add_subplot(325, sharex = axmag)

        axiq.set_xlabel("I [ADC]"); axiq.set_ylabel("Q [ADC]")
        axiq.yaxis.tick_right()
        axmag.set_ylabel("Mag(S21) [dB]")
        axphi.set_ylabel("Ang(S21) [rad]")
        axcal.set_xlabel("Frequency [MHz]"); axcal.set_ylabel("Speed")
        axcal.xaxis.set_major_formatter(FormatStrFormatter('%3.2f'))
        axiq.grid(); axmag.grid(); axphi.grid(); axcal.grid()

        fig.canvas.mpl_connect('key_press_event',   self._on_key_press)
        fig.canvas.mpl_connect('key_release_event', self._on_key_release)
        fig.canvas.mpl_connect('button_press_event', self._on_mouse_click)

        fig.canvas.mpl_connect('pick_event', self._onpick)

        # set figure and axes to class attributes
        self.fig = fig
        self.axiq = axiq; self.axmag = axmag; self.axphi = axphi; self.axcal = axcal

        # --- do stuff with summary figure here ---
        if do_figsum:
            ax1  = figsum.add_subplot(122)
            ax2  = figsum.add_subplot(222)

            self.figsum = figsum
            self.ax1 = ax1; self.ax2 = ax2


    def _configure_plots(self):

        for sweep in self.sweeplist:

            self._linedict[sweep.name]['iqmain'], = self.axiq.plot(sweep.data[self.sortidxs][self.idx].real, sweep.data[self.sortidxs][self.idx].imag, '-o', c='C0', picker=5)
            #self._linedict[sweep.name]['iqmain_freq'] = self.axiq.scatter(sweep.data[self.sortidxs][self.idx].real, sweep.data[self.sortidxs][self.idx].imag, c=sweep.rf_freqs[self.sortidxs][self.idx]/1.e6, edgecolors='none');
            self._linedict[sweep.name]['iqtone'],    = self.axiq.plot(1,1, 'rD', ms=10, label = 'tone')
            self._linedict[sweep.name]['iqf0'],      = self.axiq.plot(1,1, 'gD', ms=10, label = 'calcf0')
            self._linedict[sweep.name]['iqf0man'],   = self.axiq.plot(1,1, 'mD', ms=10, label = 'manf0')

            self._linedict[sweep.name]['magmain'], = self.axmag.plot(sweep.rf_freqs[self.sortidxs][self.idx]/1.e6, 20*_np.log10(_np.abs(sweep.data[self.sortidxs][self.idx])), c='C0')
            self._linedict[sweep.name]['magtone']  = self.axmag.axvline(sweep.tonefreqs[self.sortidxs][self.idx]/1.e6, c='r', ls='dashed')
            self._linedict[sweep.name]['magf0']    = self.axmag.axvline(sweep.calparams['f0s'][self.sortidxs][self.idx]/1.e6, c='g', ls='dashed')

            self._linedict[sweep.name]['phimain'], = self.axphi.plot(sweep.rf_freqs[self.sortidxs][self.idx]/1.e6,_np.unwrap(_np.angle(sweep.data[self.sortidxs][self.idx])), c='C0' )
            self._linedict[sweep.name]['phitone']  = self.axphi.axvline(sweep.tonefreqs[self.sortidxs][self.idx]/1.e6, c='r', ls='dashed')
            self._linedict[sweep.name]['phif0']    = self.axphi.axvline(sweep.calparams['f0s'][self.sortidxs][self.idx]/1.e6, c='g', ls='dashed')

            self._linedict[sweep.name]['speedre'],   = self.axcal.plot(sweep.rf_freqs[self.sortidxs][self.idx]/1.e6, sweep.caldata[self.sortidxs][self.idx].real, c='C1' ) # didf
            self._linedict[sweep.name]['speedim'],   = self.axcal.plot(sweep.rf_freqs[self.sortidxs][self.idx]/1.e6, sweep.caldata[self.sortidxs][self.idx].imag, c='C5' ) # dqdf
            self._linedict[sweep.name]['speedab'],   = self.axcal.plot(sweep.rf_freqs[self.sortidxs][self.idx]/1.e6, abs(sweep.caldata[self.sortidxs][self.idx]), c='C4' ) # sqrt(didf^2 + dqdf^2)
            self._linedict[sweep.name]['speedtone']  = self.axcal.axvline(sweep.tonefreqs[self.sortidxs][self.idx]/1.e6, c='r', ls='dashed')
            self._linedict[sweep.name]['speedf0']    = self.axcal.axvline(sweep.calparams['f0s'][self.sortidxs][self.idx]/1.e6, c='g', ls='dashed')

            #self._linedict[sweep.name]['magmain'].set_label(sweep.name)
            self._linedict[sweep.name]['magmain'].set_label('Sweep')
            self._linedict[sweep.name]['speedre'].set_label('Re(Speed)')
            self._linedict[sweep.name]['speedim'].set_label('Im(Speed)')
            self._linedict[sweep.name]['speedab'].set_label('|Speed|')

            # unset manf0idx visibility
            self._linedict[sweep.name]['iqf0man'].set_visible(False)

        self.refresh_plot()

    def refresh_plot(self):

        for sweep in self.sweeplist:

            f0idxs = _np.array([_np.searchsorted(a, v) for a, v in zip(sweep.rf_freqs, sweep.calparams['f0s'])])

            toneidx = _np.where(sweep.lo_freqs==sweep._lo_freq)
            f0idx   = f0idxs[self.idx]
            pkdidx = self._pkdidxs[self.idx]

            self._linedict[sweep.name]['iqmain'].set_data(sweep.data[self.sortidxs][self.idx].real, sweep.data[self.sortidxs][self.idx].imag)
            #self._linedict[sweep.name]['iqmain_freq'].set_data(sweep.data[self.sortidxs][self.idx].real, sweep.data[self.sortidxs][self.idx].imag)
            self._linedict[sweep.name]['iqtone'].set_data(sweep.data[self.sortidxs][self.idx].real[toneidx], sweep.data[self.sortidxs][self.idx].imag[toneidx])
            self._linedict[sweep.name]['iqf0'  ].set_data(sweep.data[self.sortidxs][self.idx].real[f0idx],   sweep.data[self.sortidxs][self.idx].imag[f0idx])
            self._linedict[sweep.name]['iqf0man'].set_data(sweep.data[self.sortidxs][self.idx].real[pkdidx], sweep.data[self.sortidxs][self.idx].imag[pkdidx])
            self._linedict[sweep.name]['iqf0man'].set_visible(pkdidx) # <-- if not zero, shows the index, otherwise remains unset

            self._linedict[sweep.name]['magmain'].set_data(sweep.rf_freqs[self.sortidxs][self.idx]/1.e6, 20*_np.log10( _np.abs(sweep.data[self.sortidxs][self.idx]) ) )
            self._linedict[sweep.name]['magtone'].set_data(sweep.tonefreqs[      self.sortidxs][self.idx]/1.e6, [0,1] )
            self._linedict[sweep.name]['magf0'  ].set_data(sweep.calparams['f0s'][self.sortidxs][self.idx]/1.e6, [0,1] )

            self._linedict[sweep.name]['phimain'].set_data(sweep.rf_freqs[self.sortidxs][self.idx]/1.e6, _np.unwrap(_np.angle(sweep.data[self.sortidxs][self.idx])) )
            self._linedict[sweep.name]['phitone'].set_data(sweep.tonefreqs[      self.sortidxs][self.idx]/1.e6, [0,1] )
            self._linedict[sweep.name]['phif0'  ].set_data(sweep.calparams['f0s'][self.sortidxs][self.idx]/1.e6, [0,1] )

            self._linedict[sweep.name]['speedre'].set_data(sweep.rf_freqs[self.sortidxs][self.idx]/1.e6, sweep.caldata[self.sortidxs][self.idx].real ) # didf
            self._linedict[sweep.name]['speedim'].set_data(sweep.rf_freqs[self.sortidxs][self.idx]/1.e6, sweep.caldata[self.sortidxs][self.idx].imag ) # dqdf
            self._linedict[sweep.name]['speedab'].set_data(sweep.rf_freqs[self.sortidxs][self.idx]/1.e6, abs(sweep.caldata[self.sortidxs][self.idx]) ) # sqrt(didf^2 + dqdf^2)
            self._linedict[sweep.name]['speedtone'].set_data(sweep.tonefreqs[      self.sortidxs][self.idx]/1.e6, [0,1] )
            self._linedict[sweep.name]['speedf0'  ].set_data(sweep.calparams['f0s'][self.sortidxs][self.idx]/1.e6, [0,1] )

            #self._linedict[sweep.name]['magmain'].set_label('Sweep')
            self._linedict[sweep.name]['magtone'].set_label('Set tone: %3.3f' % (sweep.tonefreqs[self.sortidxs][self.idx]/1.e6) )
            self._linedict[sweep.name]['magf0'].set_label('Calc f0: %3.3f' % (sweep.calparams['f0s'][self.sortidxs][self.idx]/1.e6) )

            self.axmag.legend(loc='lower left', bbox_to_anchor= (0.0, 1.01), ncol=3, borderaxespad=0, frameon=False)
            self.axcal.legend(loc='upper left', ncol=1, borderaxespad=0, frameon=False)

        # self._linedict['iqmain'].set_data(self.iqdata[ self.idx ].real, self.iqdata[ self.idx ].imag)
        # self._linedict['magmain'].set_data(self.freqs[ self.idx ]/1.e6, 20*_np.log10( _np.abs(self.iqdata[ self.idx ]) ) )
        # self._linedict['phimain'].set_data(self.freqs[ self.idx ]/1.e6, _np.angle(self.iqdata[ self.idx ] ) )
        # self._linedict['speedre'].set_data(self.freqs[ self.idx ]/1.e6, self.caldata[ self.idx ].real )
        # self._linedict['speedim'].set_data(self.freqs[ self.idx ]/1.e6, self.caldata[ self.idx ].imag )
        # self._linedict['speedab'].set_data(self.freqs[ self.idx ]/1.e6, abs(self.caldata[ self.idx ]) )

        self.axiq.relim();  self.axiq.autoscale()
        self.axmag.relim(); self.axmag.autoscale()
        self.axphi.relim(); self.axphi.autoscale()
        self.axcal.relim(); self.axcal.autoscale()

        #self.fig.suptitle('res {0}'.format( _np.roll( _np.arange(self.ntones), -self.idx)[0] ), fontsize=16)
        self.fig.suptitle(sweep.name[0:15] + ': Resonator {0}'.format( _np.roll( self.tonenames, -self.idx )[0] ), fontsize=16)

        self.fig.set_facecolor( self._color_dict['picked'] ) if self.idx in self._picked \
                                                            else self.fig.set_facecolor( self._color_dict['default'] )
        self.fig.canvas.draw()

        #plt.draw()
        #plt.show(block=self.block)

    def get_picked_f0s(self, swpidx = 0):
        """Get the current list of resonant frequencies, including any manually modified ones. If none are modified,
        it returns calparams['f0s']. """

        #for sweep in self.sweeplist:
        sweep = self.sweeplist[ swpidx ]
        # generate an index and bool mask to set only the frequencies that have been manually picked
        idxmask  = range(len(self._pkdidxs)), self._pkdidxs
        boolmask = self._pkdidxs.astype('bool')

        # create copy of the existing F0s, and change only the ones that were modified
        newf0s = _np.copy(sweep.calparams['f0s'])
        _np.putmask(newf0s, boolmask, sweep.rf_freqs[idxmask])

        return newf0s

    def _on_key_press(self, event):
        if event.key == 'right':
            self.idx = (self.idx + 1) % self.ntones
            self.refresh_plot()

        if event.key == 'left':
            self.idx = (self.idx - 1) % self.ntones
            self.refresh_plot()

        if event.key == 'shift':
            self._shift_is_held = True

    def _on_key_release(self, event):
        if event.key == 'shift':
            self._shift_is_held = False

    def _on_mouse_click(self, event):

        if self._shift_is_held:
            # add index to a _picked + check if self.idx already exists in self._picked and remove
            self._picked.remove(self.idx) if self.idx in self._picked else self._picked.append(self.idx)
            # redraw plot
            self.refresh_plot()

    def _onpick(self, event):
        self.event = event
        if event.mouseevent.dblclick:

            # handle multiple indicies returned by picked event correctly
            idx = _np.atleast_1d(event.ind).mean()

            if event.mouseevent.button == 1:
            # if a particular idx already exists, then set back to zero to clear
                self._pkdidxs[self.idx] = idx if self._pkdidxs[self.idx] != idx else 0

            elif event.mouseevent.button == 3:
                print 'new frequency added '
                # need to add a new point
                # 
                # add a new index to the array

            # redraw plot
            self.refresh_plot()








#------------------------------------------------------------------------------------
# playing aorund with embedding mpl figures into simple qt application
#------------------------------------------------------------------------------------
# #
# from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
# from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
# from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QTabWidget, QVBoxLayout
# #import matplotlib.pyplot as plt
# # import sys
# #
# class plotWindow():
#     def __init__(self, parent=None):
#         self.app = QtWidgets.QApplication(sys.argv)
#         self.MainWindow = QtWidgets.QMainWindow()
#         self.MainWindow.__init__()
#         self.MainWindow.setWindowTitle("plot window")
#         self.canvases = []
#         self.figure_handles = []
#         self.toolbar_handles = []
#         self.tab_handles = []
#         self.current_window = -1
#         self.tabs = QtWidgets.QTabWidget()
#         self.MainWindow.setCentralWidget(self.tabs)
#         self.MainWindow.resize(1280, 900)
#         self.MainWindow.show()
#
#     def addPlot(self, title, figure):
#         new_tab = QtWidgets.QWidget()
#         layout = QtWidgets.QVBoxLayout()
#         new_tab.setLayout(layout)
#
#         #figure.subplots_adjust(left=0.05, right=0.99, bottom=0.05, top=0.91, wspace=0.2, hspace=0.2)
#         new_canvas = FigureCanvas(figure)
#         new_toolbar = NavigationToolbar(new_canvas, new_tab)
#
#         layout.addWidget(new_canvas)
#         layout.addWidget(new_toolbar)
#         self.tabs.addTab(new_tab, title)
#
#         self.toolbar_handles.append(new_toolbar)
#         self.canvases.append(new_canvas)
#         self.figure_handles.append(figure)
#         self.tab_handles.append(new_tab)
#
#     def show_app(self):
#         self.app.exec_()

#
# import sys
# import time
#
# import numpy as np
#
# from matplotlib.backends.qt_compat import QtCore, QtWidgets, is_pyqt5
# from PyQt5.QtWidgets import QDialog, QApplication, QPushButton, QVBoxLayout
#
# from matplotlib.backend_bases import FigureManagerBase, key_press_handler
#
# if is_pyqt5():
#     from matplotlib.backends.backend_qt5agg import (
#         FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
# else:
#     from matplotlib.backends.backend_qt4agg import (
#         FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
# from matplotlib.figure import Figure
#
#
# class ApplicationWindow(QtWidgets.QMainWindow):
#     def __init__(self):
#         super(ApplicationWindow, self).__init__()
#         self._main = QtWidgets.QWidget()
#         self.setCentralWidget(self._main)
#         layout = QtWidgets.QVBoxLayout(self._main)
#
#         static_canvas = FigureCanvas(Figure(figsize=(5, 3)))
#         layout.addWidget(static_canvas)
#         self.addToolBar(NavigationToolbar(static_canvas, self))
#
#         self._static_ax = static_canvas.figure.subplots()
#         t = np.linspace(0, 10, 501)
#         self._static_ax.plot(t, np.tan(t), ".")
#
#
# class Window(QtWidgets.QDialog):
#     def __init__(self, parent=None, figure = None):
#         super(Window, self).__init__(parent)
#
#         # a figure instance to plot on
#         if not figure:
#             self.figure = plt.figure()
#         else:
#             self.figure = figure
#         # this is the Canvas Widget that displays the `figure`
#         # it takes the `figure` instance as a parameter to __init__
#         self.canvas = FigureCanvas(self.figure)
#
#         self.canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
#         self.canvas.setFocus()
#         # this is the Navigation widget
#         # it takes the Canvas widget and a parent
#         self.toolbar = NavigationToolbar(self.canvas, self)
#
#         # Just some button connected to `plot` method
#         self.button = QPushButton('Plot')
#         self.button.clicked.connect(self.plot)
#
#         self.canvas.mpl_connect('key_press_event', self.on_key_press)
#
#         # set the layout
#         layout = QVBoxLayout()
#         layout.addWidget(self.toolbar)
#         layout.addWi  dget(self.canvas)
#         layout.addWidget(self.button)
#         self.setLayout(layout)
#
#     def plot(self):
#         ''' plot some random stuff '''
#         # random data
#         data = [_np.random.random() for i in range(10)]
#
#         # instead of ax.hold(False)
#         self.figure.clear()
#
#         # create an axis
#         ax = self.figure.add_subplot(111)
#
#         # discards the old graph
#         # ax.hold(False) # deprecated, see above
#
#         # plot data
#         ax.plot(data, '*-')
#
#         # refresh canvas
#         self.canvas.draw()
#
#     def on_key_press(self, event):
#         print 'you pressed', event.key
#         # implement the default mpl key press events described at
#         # http://matplotlib.sourceforge.net/users/navigation_toolbar.html#navigation-keyboard-shortcuts
#         key_press_handler(event, self.canvas, self.toolbar)
#





## VERSION 1. FUNCIONADO BIEN!
#
# # Plotting routines to visualise various data products
#
# # Demo visualisation tool
# #   [20190304] Plot for averaged data completed. It shows sweeps, IQ circles and speed figures
# #
# #   [20181217] So far you can plot the data from a the raw directory, but it has to be able to read it from the sweep folder as well.
# # It just plot the magnitude vs frequency and IQ circles, the rest of the options are empty. The plot functions need to take in consideration
# # the tonelist and the central frequency to correct the x-axis
# #
# # To run:
# #
# #   bb-> For the moment comes from toneslist, but in future it should be in the directories
# # >> dirfile = "./pcp/testing/run/data/dummyroach/20181125_172118_sweep_raw/"
# # >> plot_sweep_data(dirfile,bb)
#
# from plotly import tools
# from plotly.offline import plot, init_notebook_mode
# import plotly.graph_objs as go
#
# import os as _os
# import numpy as _np
#
# import cmath as _cmath
# import pygetdata as _gd
#
# import matplotlib.pyplot as plt
# plt.ion()
#
# # This should be in another file/script
# import detector_peaks as find_peaks
# from scipy.signal import savgol_filter
# import signal
#
# # Offline mode. For plotly
# init_notebook_mode(connected=True)
#
#
# # TODO add bb_freqs to files in order to not load it here
# def reloc_tones(diryfile, bb_freqs, overlap_dist=20e3, plot=True, plot_tones=True):
#
#     new_tonelist = []
#     freqs,sweep = get_sweep_data(diryfile, bb_freqs)
#
#     for kid in sweep:
#         peaks, mag_peaks = find_detectors(sweep[kid], freqs[kid])
#         sweep_s21 = _get_log_mag(sweep[kid])
#
#         if plot:
#             plt.plot(freqs[kid], sweep_s21)
#             plt.plot(freqs[kid][peaks], sweep_s21[peaks], "x")
#
#         for peak in peaks:
#             new_tone = freqs[kid][peak]
#             if plot_tones:
#                 plt.axvline(new_tone, color='k')
#             new_tonelist.append(new_tone)
#
#     # Filter new toneslist from overlaps
#     new_filter_tonelist = []
#     new_tonelist = _np.sort(new_tonelist)
#
#     for i in range(len(new_tonelist)-1):
#         if (new_tonelist[i+1] - new_tonelist[i]) > overlap_dist:
#             new_filter_tonelist.append(new_tonelist[i])
#
#     # The last element
#     if (new_tonelist[-1] - new_tonelist[-2]) > overlap_dist:
#         new_filter_tonelist.append(new_tonelist[-1])
#
#     return new_filter_tonelist
#
# def rewrite_toneslist(toneslist, new_tones):
#
#     # This shouldn't be like this
#     header = "name\tfreq\tpower\toffset\tatt\tall\tnone\n"
#
#     file = open(toneslist.tonelistfile,'w')
#     file.write(header)
#
#     nkid = 0
#     for line in new_tones:
#         name = "K" + str(nkid).zfill(3)
#         row = name + '\t' + str(int(line)) + '\t' + "0\t0\t1\t0\t0\n"
#         file.write(row)
#         nkid += 1
#
#     file.close()
#
#     toneslist.load_tonelist(toneslist.tonelistfile)
#     print "Toneslist updated"
#
#
# def find_detectors(sweep, freq, start=10, stop=10, distance=70e3, limit=3, order=3, npoints=15, method='max_speed'):
#
#     # Assuming that is constant
#     df = freq[1]-freq[0]
#
#     #freq = freq[start:stop]
#     #sweep = sweep[start:stop]
#
#     if method == "max_speed":
#         signal = _get_speed(freq, sweep)[1]
#         valley = False
#     elif method == "min_s21":         # <--- THIS METHOD DOESNT WORK
#         signal = _get_log_mag(sweep)
#         valley = True
#
#     # Detect peaks
#     smooth_mag = savgol_filter(signal, npoints, order)
#
#     mph = _np.nanmax(signal)/4
#     mpd = distance/df
#
#     peaks = find_peaks.detect_peaks(smooth_mag, mph=mph, mpd=mpd, valley=valley)
#
#     if len(peaks) > limit:
#         peaks = []
#
#     print "Peaks detected: ", len(peaks)
#     return peaks, sweep[peaks]
#
# def _get_log_mag(cplx_IQ):
#     """
#     Get the magnitude from I, Q signals
#     """
#     return 20*_np.log10(abs(cplx_IQ))
#
# def _get_mag(cplx_IQ):
#     """
#     Get the magnitude from I, Q signals
#     """
#     return abs(cplx_IQ)
#
# def _get_phase(cplx_IQ, deg=False):
#     """
#     Get the phase from I,Q signals
#     """
#     phase = _cmath.phase(cplx_IQ)
#     if deg:
#         return phase*180/_np.pi
#     else:
#         return phase
#
# def _get_speed(freqs, cplx_IQ):
#     """
#     Get the speed from I,Q signals
#     """
#     di_df = _np.diff(cplx_IQ.real)/_np.diff(freqs)
#     dq_df = _np.diff(cplx_IQ.imag)/_np.diff(freqs)
#
#     speed = _np.sqrt(di_df**2 + dq_df**2)
#
#     return freqs[1:],speed
#
# def get_sweep_data(diryfile, bb_freqs):
#     """
#     Get data from a sweep dirfile which is the averaged data from raw directories
#     """
#
#     sweep_dirfile = _gd.dirfile(diryfile, _gd.RDONLY)
#
#     field_lo = "sweep.lo_freqs"
#     field_bb = "sweep.bb_freqs"
#     kids_fields = [field[6:] for field in sweep_dirfile.field_list() if field.startswith("sweep.") and field != field_lo]
#
#     sweep_lo = sweep_dirfile.get_carray(field_lo)
#     #bb_freqs_tst = sweep_dirfile.getr_carray(field_bb)
#     #print bb_freqs_tst
#
#     # Sweep data, like complex numbers
#     lo_freqs = dict()
#     sweep_data = dict()
#
#     n = 0
#     for kid in kids_fields:
#         lo_freqs[kid] = sweep_lo + bb_freqs[n]
#         sweep_data[kid] = sweep_dirfile.get_carray("sweep." + kid)
#         n += 1
#
#     return lo_freqs, sweep_data
#
#
# # Bunch of functions to plot sweep averaged data using plotly
# # To run
# # >>  run pcp/visualization.py
# # >>  plot_sweep_data('/path/of/dirfile', bb_freqs)
#
# def plot_sweep_html(diryfile, bb_freqs):
#     """
#     Debug function in order to plot
#     """
#     lo_freqs, sweep_data = get_sweep_data(diryfile, bb_freqs)
#     sample_freq = lo_freqs[lo_freqs.keys()[0]]
#     bw = sample_freq[-1] - sample_freq[0]
#     step = sample_freq[1] - sample_freq[0]
#     nKIDS = len(lo_freqs)
#
#     # Recuding the full path to just the name
#     filename = ""
#     for i in range(1, len(diryfile)):
#         if diryfile[-i] == "/":
#             break
#         filename = diryfile[-i] + filename
#
#     header = dict(text='<b>File: </b>'+filename+'<br><b>Bandwidth: </b>'+str(bw)+' Hz<br><b>Step: </b>'+str(step)+'<br><b>Number of KIDs: </b>'+str(nKIDS),
#                     font=dict(color='white',size=10), borderpad=10, x=0.2, y=1.125, xref='paper',yref='paper', align='left', showarrow=False, bgcolor='black')
#
#     _plt = pcp_plot(header)
#     _plt.plot(lo_freqs, sweep_data)
#
#
# class pcp_plot(object):
#
#     def __init__(self, header):
#         """
#         Layout defintion and plot functions
#         We define the basic structure of the pcp plot tool: buttons, sliders, text ...
#         """
#
#         # Text
#         title = dict(text='<b>PCP Plot Tool Demo</b>', font=dict(color='white',size=20), borderpad=10, x=0, y=1.1, xref='paper',
#                   yref='paper', align='left', showarrow=False, bgcolor='black')
#
#         # Information about the plot
#         notes = header
#
#         # General Annotations
#         self.annotations = list([title,notes])
#
#         # Buttons
#         self.updatemenus=list([
#             # Basic buttons
#             # Sweep. Plot the frequency vs magnitude sqrt(I**2 + Q**2) of each KID
#             # IQ Circles. Plot I vs Q
#             # Speed IQ Circles. Plot frequency vs magnitude of speed vector of the IQ circles
#             dict(
#                 buttons = list([
#                     dict(label = 'Sweep',
#                          method = 'update',
#                          args = [{'visible': [True, False, False]},
#                                  {'xaxis':dict(
#                                          title='<b>Frequency [Hz]</b>',
#                                          ticks='outside',
#                                          gridwidth=1,
#                                          gridcolor='#404040',
#                                          ticksuffix='Hz',
#                                          exponentformat="SI",
#                                          titlefont=dict(
#                                              family='Courier New, monospace',
#                                              size=18,
#                                              color='#7f7f7f'
#                                          )
#                                      ),
#                                      'yaxis':dict(
#                                          title='<b>S<sub>21</sub>[dB]</b>',
#                                          ticks='outside',
#                                          gridwidth=1,
#                                          gridcolor='#404040',
#                                          titlefont=dict(
#                                              family='Courier New, monospace',
#                                              size=18,
#                                              color='#7f7f7f'
#                                          )
#                                      ),
#                                  'title': '<b>Magnitude Sweep</b>',
#                                  'mapbox.style': 'dark',
#                                  'annotations': self.annotations}]),
#                     dict(label = 'IQ Circles',
#                          method = 'update',
#                          args = [{'visible': [False, True, False]},
#                                  {'xaxis':dict(
#                                           title='<b>Q</b>',
#                                           ticks='outside',
#                                           gridwidth=1,
#                                           gridcolor='#404040',
#                                           exponentformat="SI",
#                                           titlefont=dict(
#                                               family='Courier New, monospace',
#                                               size=18,
#                                               color='#7f7f7f'
#                                           )
#                                       ),
#                                       'yaxis':dict(
#                                           title='<b>I</b>',
#                                           ticks='outside',
#                                           gridwidth=1,
#                                           gridcolor='#404040',
#                                           titlefont=dict(
#                                               family='Courier New, monospace',
#                                               size=18,
#                                               color='#7f7f7f'
#                                           )
#                                       ),
#                                  'title': '<b>IQ Circles</b>',
#                                  'annotations': self.annotations}]),
#                     dict(label = 'Speed IQ Circles',
#                          method = 'update',
#                          args = [{'visible': [False, False, True]},
#                                  {'xaxis':dict(
#                                           title='<b>Frequency [Hz]</b>',
#                                           ticks='outside',
#                                           gridwidth=1,
#                                           gridcolor='#404040',
#                                           ticksuffix='Hz',
#                                           exponentformat="SI",
#                                           titlefont=dict(
#                                               family='Courier New, monospace',
#                                               size=18,
#                                               color='#7f7f7f'
#                                           )
#                                       ),
#                                       'yaxis':dict(
#                                           title='<b>Speed[dB/Hz]</b>',
#                                           ticks='outside',
#                                           gridwidth=1,
#                                           gridcolor='#404040',
#                                           titlefont=dict(
#                                               family='Courier New, monospace',
#                                               size=18,
#                                               color='#7f7f7f'
#                                           )
#                                       ),
#                                  'title': '<b>Speed IQ Circles</b>',
#                                  'annotations': self.annotations}])
#                 ]),
#                 direction = "left",
#                 pad = {'r':10,'t':10},
#                 xanchor = 'left',
#                 yanchor = 'top',
#                 x = 0.7,
#                 y = 1.12,
#                 type = 'buttons',
#                 bgcolor = '#AAAAAA',
#                 active = 99,
#                 bordercolor = '#FFFFFF',
#                 font = dict(size=11, color='#000000')
#             ),
#
#             # Custom buttons. To customize the plot window
#             # Tones. Show where the tone is sent
#             # Max Sweep. Show where is the point with the maximum vector speed of IQ circles
#             # Min Mag. Show the point with the minimum magnitude
#             # Q fitting. Fits the Q curve
#             dict(
#                 buttons = list([
#                     dict(label = 'Legend',
#                          method = 'relayout',
#                          args = [{'annotations':self.annotations,
#                                  'shapes':[]}]),
#                     dict(label = 'Reset',
#                          method = 'relayout',
#                          args = [{'annotations':self.annotations,
#                                  'shapes':[]}]),
#                 ]),
#                 direction = "left",
#                 pad = {'r':10,'t':10},
#                 xanchor = 'left',
#                 yanchor = 'top',
#                 x = 0.7,
#                 y = 1.065,
#                 type = 'buttons',
#                 bgcolor = '#AAAAAA',
#                 active = 99,
#                 bordercolor = '#FFFFFF',
#                 font = dict(size=11, color='#000000')
#             ),
#         ])
#
#         # Sliders
#         #   The slides show one by one each KID sorted by the frequency
#         steps = []
#         for i in range(2):
#             step = dict(
#                 method = 'restyle',
#                 args = ['visible', [False] * 2],
#             )
#             step['args'][1][i] = True
#             steps.append(step)
#
#         self.sliders = [dict(
#             active = 10,
#             currentvalue = {"prefix": "KID: "},
#             pad = {"t": 50},
#             steps = steps
#         )]
#
#         # Layout
#         self.layout = dict(
#             #margin = dict( t=100, b=100, l=100, r=100 ),
#             font = dict( family='Courier New, monospace', color='#FFFFFF', size=15),
#             paper_bgcolor = '#252525',
#             plot_bgcolor = "#252525",
#
#             xaxis=dict(
#                 title='<b>Frequency [Hz]</b>',
#                 ticks='outside',
#                 gridwidth=1,
#                 gridcolor='#404040',
#                 ticksuffix='Hz',
#                 exponentformat="SI",
#                 titlefont=dict(
#                     family='Courier New, monospace',
#                     size=18,
#                     color='#7f7f7f'
#                 )
#             ),
#             yaxis=dict(
#                 title='<b>S<sub>21</sub>[dB]</b>',
#                 ticks='outside',
#                 gridwidth=1,
#                 gridcolor='#404040',
#                 titlefont=dict(
#                     family='Courier New, monospace',
#                     size=18,
#                     color='#7f7f7f'
#                 )
#             ),
#
#             updatemenus = self.updatemenus,
#             sliders=self.sliders,
#             annotations=self.annotations
#         )
#
#     def plot(self, freqs, data, filename='pcp_plot.html'):
#
#         self.sweep = []
#         self.iq_circle = []
#         self.speed_iq_circle = []
#
#         self.tones = []
#         self.tonesLines = []
#
#         for kid in sorted(data):
#             # Plots
#             mag = _get_log_mag(data[kid])
#             self.sweep.append(go.Scatter(x=freqs[kid],
#                                     y=mag,
#                                     name=kid,
#                                     visible=True))
#                                     #line=dict(color='#33CFA5'))
#
#             self.iq_circle.append(go.Scatter(x=data[kid].real,
#                                     y=data[kid].imag,
#                                     name=kid,
#                                     visible=False))
#
#             freqs_speed, speed = _get_speed(freqs[kid], data[kid])
#             self.speed_iq_circle.append(go.Scatter( x=freqs_speed,
#                                                     y=speed,
#                                                     name=kid,
#                                                     visible=False))
#
#             # Settings
#             x_tone = _np.median(freqs[kid])
#             y_tone = mag[_np.where(mag<x_tone)[0][0]]
#
#             self.tones.append(dict(x=x_tone,
#                            y=y_tone,
#                            xref='x', yref='y',
#                            text='Tone:<br>'+str(_np.median(freqs[kid])),
#                            ax=0, ay=-40))
#
#             magFilter = [m for m in mag if not _np.isnan(m)]
#             center = (_np.max(magFilter) - _np.min(magFilter))/3
#
#             self.tonesLines.append(dict(
#                 type='line',
#                 x0=x_tone,
#                 y0=_np.min(magFilter) - center,
#                 x1=x_tone,
#                 y1=_np.max(magFilter) + center,
#                 line={
#                     "color":'rgb(180, 180, 180)',
#                     "dash": "dashdot",
#                     "width": 2}))
#
#             """
#             self.tones.append(go.Scatter(x=[_np.median(freqs[kid])]*500,
#                                     y=_np.linspace(_np.min(mag),_np.max(mag),500),
#                                     name=kid,
#                                     visible=False))
#             """
#
#         self.data = self.sweep + self.iq_circle + self.speed_iq_circle
#
#         # Visibility of each plot
#         self.updatemenus[0]["buttons"][0]["args"][0]["visible"] = [True]*len(data) + [False]*(len(data)*2)
#         self.updatemenus[0]["buttons"][1]["args"][0]["visible"] = [False]*len(data) + [True]*len(data) + [False]*len(data)
#         self.updatemenus[0]["buttons"][2]["args"][0]["visible"] = [False]*(len(data)*2) + [True]*len(data)
#         self.updatemenus[1]["buttons"][0]["args"][0]["annotations"] = self.tones + self.annotations
#         self.updatemenus[1]["buttons"][0]["args"][0]["shapes"] = self.tonesLines
#
#         # Updating the sliders
#         steps = []
#         for i in range(len(data)):
#             step = dict(
#                 method = 'restyle',
#                 label = sorted(data)[i],
#                 args = ['visible', [False] * len(self.data)],
#             )
#             # Sweep
#             #if self.updatemenus[0]["buttons"][0]["args"][0]["visible"][0]:
#             step['args'][1][i] = True
#             # IQ
#             #if self.updatemenus[0]["buttons"][1]["args"][0]["visible"][len(self.sweep) + 1]:
#             #step['args'][1][i + len(self.sweep)] = True
#             # Speed
#             #if self.updatemenus[0]["buttons"][1]["args"][0]["visible"][len(self.sweep) + len(self.iq_circle) + 2]:
#             #   step['args'][1][i + len(self.sweep) + len(self.speed_iq_circle)] = True
#
#             steps.append(step)
#
#         self.sliders = [dict(
#             active = 0,
#             currentvalue = {"prefix": "KID: "},
#             pad = {"t": 50},
#             steps = steps
#         )]
#
#         self.layout["annotations"] = self.annotations
#         self.layout["updatemenus"] = self.updatemenus
#         self.layout["sliders"] = self.sliders
#
#         #fig = tools.make_subplots(rows=2, cols=4)
#
#         #for sweep in self.sweep:
#         #    fig.append_trace(sweep, 1, 1)
#
#         #for iq in self.iq_circle:
#         #    fig.append_trace(iq, 1, 4)
#
#         #for speed in self.speed_iq_circle:
#         #    fig.append_trace(speed, 2, 4)
#
#         #fig['layout'] = self.layout
#         #fig['layout'].update(self.layout)
#         #fig['layout'].update(height=600, width=800, title='i <3 annotations and subplots')
#
#         fig = dict(data=self.data, layout=self.layout)
#         plot(fig, filename=filename)
