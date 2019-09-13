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

from plotly import tools
from plotly.offline import plot, init_notebook_mode
import plotly.graph_objs as go

import os as _os
import numpy as _np

import cmath as _cmath
import pygetdata as _gd

import matplotlib.pyplot as plt
plt.ion()

# This should be in another file/script
import detector_peaks as find_peaks
from scipy.signal import savgol_filter
import signal

# Offline mode. For plotly
init_notebook_mode(connected=True)


# TODO add bb_freqs to files in order to not load it here -- Done
def reloc_tones(diryfile, overlap_dist=20e3, plot=True, plot_tones=True):

    new_tonelist = []
    freqs,sweep = get_sweep_data(diryfile)

    for kid in sweep:
        peaks, mag_peaks = find_detectors(sweep[kid], freqs[kid])
        sweep_s21 = _get_log_mag(sweep[kid])

        if plot:
            plt.plot(freqs[kid], sweep_s21)
            plt.plot(freqs[kid][peaks], sweep_s21[peaks], "x")

        for peak in peaks:
            new_tone = freqs[kid][peak]
            if plot_tones:
                plt.axvline(new_tone, color='k')
            new_tonelist.append(new_tone)

    # Filter new toneslist from overlaps
    new_filter_tonelist = []
    new_tonelist = _np.sort(new_tonelist)

    for i in range(len(new_tonelist)-1):
        if (new_tonelist[i+1] - new_tonelist[i]) > overlap_dist:
            new_filter_tonelist.append(new_tonelist[i])

    # The last element
    if (new_tonelist[-1] - new_tonelist[-2]) > overlap_dist:
        new_filter_tonelist.append(new_tonelist[-1])

    return new_filter_tonelist

def rewrite_toneslist(toneslist, new_tones):

    header = "name\tfreq\tpower\toffset\tatt\tall\tnone\n"

    file = open(toneslist.tonelistfile,'w')
    file.write(header)

    nkid = 0
    for line in new_tones:
        name = "K" + str(nkid).zfill(3)
        row = name + '\t' + str(int(line)) + '\t' + "0\t0\t1\t0\t0\n"
        file.write(row)
        nkid += 1

    file.close()

    toneslist.load_tonelist(toneslist.tonelistfile)
    print "Toneslist updated"


def find_detectors(sweep, freq, start=10, stop=10, distance=70e3, limit=3, order=3, npoints=15, method='max_speed'):

    # Assuming that is constant
    df = freq[1]-freq[0]

    #freq = freq[start:stop]
    #sweep = sweep[start:stop]

    if method == "max_speed":
        signal = _get_speed(freq, sweep)[1]
        valley = False
    elif method == "min_s21":         # <--- THIS METHOD DOESNT WORK
        signal = _get_log_mag(sweep)
        valley = True

    # Detect peaks
    smooth_mag = savgol_filter(signal, npoints, order)

    mph = _np.nanmax(signal)/4
    mpd = distance/df

    peaks = find_peaks.detect_peaks(smooth_mag, mph=mph, mpd=mpd, valley=valley)

    if len(peaks) > limit:
        peaks = []

    print "Peaks detected: ", len(peaks)
    return peaks, sweep[peaks]

def _get_log_mag(cplx_IQ):
    """
    Get the magnitude from I, Q signals
    """
    return 20*_np.log10(abs(cplx_IQ))

def _get_mag(cplx_IQ):
    """
    Get the magnitude from I, Q signals
    """
    return abs(cplx_IQ)

def _get_phase(cplx_IQ, deg=False):
    """
    Get the phase from I,Q signals
    """
    phase = _cmath.phase(cplx_IQ)
    if deg:
        return phase*180/_np.pi
    else:
        return phase

def _get_speed(freqs, cplx_IQ):
    """
    Get the speed from I,Q signals
    """
    di_df = _np.diff(cplx_IQ.real)/_np.diff(freqs)
    dq_df = _np.diff(cplx_IQ.imag)/_np.diff(freqs)

    speed = _np.sqrt(di_df**2 + dq_df**2)

    return freqs[1:],speed

def get_sweep_data(diryfile):
    """
    Get data from a sweep dirfile which is the averaged data from raw directories
    """

    sweep_dirfile = _gd.dirfile(diryfile, _gd.RDONLY)

    field_lo = "sweep.lo_freqs"
    field_bb = "sweep.bb_freqs"
    kids_fields = [field[6:] for field in sweep_dirfile.field_list() if field.startswith("sweep.") and field != field_lo and field !=field_bb]

    sweep_lo = sweep_dirfile.get_carray(field_lo)
    bb_freqs = sweep_dirfile.get_carray(field_bb)

    # Sweep data, like complex numbers
    lo_freqs = dict()
    sweep_data = dict()

    n = 0
    for kid in kids_fields:
        lo_freqs[kid] = sweep_lo + bb_freqs[n]
        sweep_data[kid] = sweep_dirfile.get_carray("sweep." + kid)
        n += 1

    return lo_freqs, sweep_data

def get_stream_data(diryfile):
    """
    Get data from time stream dirfile
    """

    time_dirfile = _gd.dirfile(diryfile, _gd.RDONLY)

    time_field = "python_timestamp"
    fields_forbiden = ['metadata.raw_sweep_filename','INDEX', 'gpio_reg', 'raw_packet', 'packet_count', 'pps_timestamp', 'fine_timestamp', 'roach_checksum', 'packet_info_reg', 'python_timestamp']
    kids_fields = [field for field in time_dirfile.field_list() if not (field in fields_forbiden or field.startswith("sweep."))]

    try:
        field_lo = "sweep.lo_freqs"
        field_bb = "sweep.bb_freqs"
        sweep_fields = [field for field in time_dirfile.field_list() if field.startswith("sweep.") and field != field_lo and field !=field_bb]
        
        sweep_lo = time_dirfile.get_carray(field_lo)
        bb_freqs = time_dirfile.get_carray(field_bb)

        lo_freqs = dict()
        sweep_data = dict()

        n = 0
        for kid in kids_fields:
            lo_freqs[kid] = sweep_lo + bb_freqs[n]
            sweep_data[kid] = sweep_dirfile.get_carray("sweep." + kid)
            n += 1
    except:
        lo_freqs = []
        sweep_data = []

    time = time_dirfile.getdata(time_field)

    # Time data
    time_stream = dict()

    for kid in kids_fields:
        time_stream[kid] = time_dirfile.getdata(kid)

    return time, time_stream, lo_freqs, sweep_freqs

def get_dxdf(freqs, x, smooth=True, order=3, npoints=7):
    """
    Get dx/df, where x could be i or q
    """
    if smooth:
        x = savgol_filter(x, npoints, order)

    dx_df = _np.gradient(x, freqs)

    return dx_df

def get_df(I, Q, I_sweep, Q_sweep, didf, dqdf, f0):
    """
    Get df. Variaability in resonance frequency
    """
    speed_mag = (didf[f0]**2)+(dqdf[f0]**2)
    df = ( (I_sweep[f0]-I)*didf) + ( (Q_sweep[f0]-Q)*dqdf ) / speed_mag
    return df

def plot_df_psd(diryfile):
    """
    Get the PSD
    """



def color_msg(object):
    """
    Colors for messages. Short cuts to color the messages
    """
    def __init__(self):
        self.COLOR_SEQ = "\033[1;%dm"

        self.HEADER    = '\033[95m'
        self.OKBLUE    = '\033[94m'
        self.OKGREEN   = '\033[92m'
        self.WARNING   = '\033[93m'
        self.FAIL      = '\033[91m'
        self.ENDC      = '\033[0m'
        self.BOLD      = '\033[1m'
        self.UNDERLINE = '\033[4m'

        self.BLACKTXT, self.REDTXT, self.GREENTXT, self.YELLOWTXT, self.BLUETXT, self.MAGENTATXT, self.CYANTXT, self.WHITETXT = [30 + i for i in range(8)]
        self.LOGCOLORS = {
            'WARNING' : YELLOWTXT,
            'INFO'    : WHITETXT,
            'DEBUG'   : CYANTXT,
            'CRITICAL': BLUETXT,
            'ERROR'   : REDTXT }

# Bunch of functions to plot sweep averaged data using plotly
# To run
# >>  run pcp/visualization.py
# >>  plot_sweep_data('/path/of/dirfile', bb_freqs)

def plot_sweep_html(diryfile):
    """
    Debug function in order to plot
    """
    lo_freqs, sweep_data = get_sweep_data(diryfile)
    sample_freq = lo_freqs[lo_freqs.keys()[0]]
    bw = sample_freq[-1] - sample_freq[0]
    step = sample_freq[1] - sample_freq[0]
    nKIDS = len(lo_freqs)

    # Recuding the full path to just the name
    filename = ""
    for i in range(1, len(diryfile)):
        if diryfile[-i] == "/":
            break
        filename = diryfile[-i] + filename

    header = dict(text='<b>File: </b>'+filename+'<br><b>Bandwidth: </b>'+str(bw)+' Hz<br><b>Step: </b>'+str(step)+'<br><b>Number of KIDs: </b>'+str(nKIDS),
                    font=dict(color='white',size=10), borderpad=10, x=0.8, y=1.125, xref='paper',yref='paper', align='left', showarrow=False, bgcolor='black')

    _plt = pcp_plot(header)
    _plt.plot(lo_freqs, sweep_data)


class pcp_plot(object):

    def __init__(self, header):
        """
        Layout defintion and plot functions
        We define the basic structure of the pcp plot tool: buttons, sliders, text ...
        """

        # Text
        title = dict(text='<b>PCP Plot Tool Demo</b>', font=dict(color='white',size=20), borderpad=10, x=0, y=1.1, xref='paper',
                  yref='paper', align='left', showarrow=False, bgcolor='black')

        # Information about the plot
        notes = header

        # General Annotations
        self.annotations = list([title,notes])

        # Buttons
        self.updatemenus=list([
           # Basic buttons
           #  Sweep. Plot the frequency vs magnitude sqrt(I**2 + Q**2) of each KID
           #  IQ Circles. Plot I vs Q
           #  Speed IQ Circles. Plot frequency vs magnitude of speed vector of the IQ circles
           dict(
                buttons = list([
                    dict(label = 'Reset',
                         method = 'update',
                         args = [{'visible': [True]},
                                 {'annotations': self.annotations}]),
                ]),
                direction = "left",
                pad = {'r':10,'t':10},
                xanchor = 'left',
                yanchor = 'top',
                x = 0.89,
                y = 1.12,
                type = 'buttons',
                bgcolor = '#AAAAAA',
                active = 99,
                bordercolor = '#FFFFFF',
                font = dict(size=11, color='#000000')
            ),
            # Custom buttons. To customize the plot window
            # Tones. Show where the tone is sent
            # Max Sweep. Show where is the point with the maximum vector speed of IQ circles
            # Min Mag. Show the point with the minimum magnitude
            # Q fitting. Fits the Q curve
            dict(
                buttons = list([
                    dict(label = 'Annotations',
                         method = 'relayout',
                         args = [{'annotations':self.annotations,
                                 'visible': [True],
                                 'shapes':[]}]),
                ]),
                direction = "left",
                pad = {'r':10,'t':10},
                xanchor = 'left',
                yanchor = 'top',
                x = 0.82,
                y = 1.12,
                type = 'buttons',
                bgcolor = '#AAAAAA',
                active = 99,
                bordercolor = '#FFFFFF',
                font = dict(size=11, color='#000000')
            ),
        ])

        # Sliders
        #   The slides show one by one each KID sorted by the frequency
        steps = []
        for i in range(2):
            step = dict(
                method = 'restyle',
                args = ['visible', [False] * 2],
            )
            step['args'][1][i] = True
            steps.append(step)

        self.sliders = [dict(
            active = 10,
            currentvalue = {"prefix": "KID: "},
            pad = {"t": 50},
            steps = steps
        )]

        # Layout
        self.layout = go.Layout(dict(
            #margin = dict( t=100, b=100, l=100, r=100 ),
            font = dict( family='Courier New, monospace', color='#FFFFFF', size=15),
            paper_bgcolor = '#252525',
            plot_bgcolor = "#252525",

            xaxis1 = dict(
                 #anchor='x1',
                 title='<b>Frequency [Hz]</b>',
                 ticks='outside',
                 gridwidth=1,
                 gridcolor='#404040',
                 ticksuffix='Hz',
                 exponentformat="SI",
                 titlefont=dict(
                     family='Courier New, monospace',
                     size=18,
                     color='#7f7f7f'
                 )
             ),
             yaxis1 = dict(
                 #anchor='y1',
                 title='<b>S<sub>21</sub>[dB]</b>',
                 ticks='outside',
                 gridwidth=1,
                 gridcolor='#404040',
                 titlefont=dict(
                     family='Courier New, monospace',
                     size=18,
                     color='#7f7f7f'
                 )
             ),

            xaxis2 = dict(
                 #anchor='x2',
                 title='<b>I</b>',
                 ticks='outside',
                 gridwidth=1,
                 gridcolor='#404040',
                 exponentformat="SI",
                 titlefont=dict(
                     family='Courier New, monospace',
                     size=18,
                     color='#7f7f7f'
                 )
             ),
             yaxis2 = dict(
                 #anchor='y2',
                 title='<b>Q</b>',
                 ticks='outside',
                 gridwidth=1,
                 gridcolor='#404040',
                 exponentformat="SI",
                 titlefont=dict(
                     family='Courier New, monospace',
                     size=18,
                     color='#7f7f7f'
                 )
             ),

            xaxis3 = dict(
                 #anchor='x3',
                 title='<b>Frequency [Hz]</b>',
                 ticks='outside',
                 gridwidth=1,
                 gridcolor='#404040',
                 ticksuffix='Hz',
                 exponentformat="SI",
                 titlefont=dict(
                     family='Courier New, monospace',
                     size=18,
                     color='#7f7f7f'
                 )
             ),
             yaxis3 = dict(
                 #anchor='y3',
                 title='<b>Speed[dB]</b>',
                 ticks='outside',
                 gridwidth=1,
                 gridcolor='#404040',
                 exponentformat="SI",
                 titlefont=dict(
                     family='Courier New, monospace',
                     size=18,
                     color='#7f7f7f'
                 )
             ),

            updatemenus = self.updatemenus,
            sliders=self.sliders,
            annotations=self.annotations
        )
        )

    def plot(self, freqs, data, filename='pcp_plot.html'):

        self.sweep = []
        self.iq_circle = []
        self.speed_iq_circle = []

        self.tones = []
        self.tonesLines = []

        for kid in sorted(data):
            # Plots

            mag = _get_log_mag(data[kid])
            self.sweep.append(go.Scatter(x=freqs[kid],
                                    y=mag,
                                    name=kid,
                                    xaxis='x1',
                                    yaxis='y1',
                                    legendgroup = 'sweep_'+kid,
                                    showlegend=True,
                                    visible=True))
                                    #line=dict(color='#33CFA5'))

            self.iq_circle.append(go.Scatter(x=data[kid].real,
                                    y=data[kid].imag,
                                    xaxis='x2',
                                    yaxis='y2',
                                    name=kid,
                                    legendgroup = 'sweep_'+kid,
                                    showlegend=False,
                                    visible=True))

            freqs_speed, speed = _get_speed(freqs[kid], data[kid])
            self.speed_iq_circle.append(go.Scatter( x=freqs_speed,
                                                    y=speed,
                                                    name=kid,
                                                    xaxis='x3',
                                                    yaxis='y3',
                                                    legendgroup = 'sweep_'+kid,
                                                    showlegend=False,
                                                    visible=True))

            # Settings
            x_tone = _np.median(freqs[kid])
            arg_y_tone = _np.where(mag<x_tone)

            try:
                y_tone = mag[arg_y_tone[0][0]]
            except:
                continue

            self.tones.append(dict(x=x_tone,
                           y=y_tone,
                           xref='x', yref='y',
                           text='Tone:<br>'+str(_np.median(freqs[kid])),
                           ax=0, ay=-40))

            magFilter = [m for m in mag if not _np.isnan(m)]
            center = (_np.max(magFilter) - _np.min(magFilter))/3

            self.tonesLines.append(dict(
                type='line',
                x0=x_tone,
                y0=_np.min(magFilter) - center,
                x1=x_tone,
                y1=_np.max(magFilter) + center,
                line={
                    "color":'rgb(180, 180, 180)',
                    "dash": "dashdot",
                    "width": 2}))

            """
            self.tones.append(go.Scatter(x=[_np.median(freqs[kid])]*500,
                                    y=_np.linspace(_np.min(mag),_np.max(mag),500),
                                    name=kid,
                                    visible=False))
            """


        self.data = self.sweep + self.iq_circle + self.speed_iq_circle

        # Visibility of each plot
        self.updatemenus[0]["buttons"][0]["args"][0]["visible"] = [True]*len(self.data)
        self.updatemenus[1]["buttons"][0]["args"][0]["annotations"] = self.tones + self.annotations
        self.updatemenus[1]["buttons"][0]["args"][0]["shapes"] = self.tonesLines

        # Updating the sliders
        steps = []
        for i in range(len(data)):
            step = dict(
                method = 'restyle',
                label = sorted(data)[i],
                args = ['visible', [False] * len(self.data)],
            )
            # Sweep
            #if self.updatemenus[0]["buttons"][0]["args"][0]["visible"][0]:
            step['args'][1][i] = True
            # IQ
            #if self.updatemenus[0]["buttons"][1]["args"][0]["visible"][len(self.sweep) + 1]:
            step['args'][1][i + len(self.sweep)] = True
            # Speed
            #if self.updatemenus[0]["buttons"][1]["args"][0]["visible"][len(self.sweep) + len(self.iq_circle) + 2]:
            step['args'][1][i + len(self.sweep) + len(self.speed_iq_circle)] = True

            steps.append(step)

        self.sliders = [dict(
            active = 0,
            currentvalue = {"prefix": "KID: "},
            pad = {"t": 50},
            steps = steps
        )]

        self.layout["annotations"] = self.annotations
        self.layout["updatemenus"] = self.updatemenus
        self.layout["sliders"] = self.sliders

        fig = tools.make_subplots(rows=2, cols=4, specs=[[{'rowspan':2, 'colspan':3}, None, None, {}], [None, None, None, {}]], vertical_spacing=0.1)

        for sweep in self.sweep:
            fig.append_trace(sweep, 1, 1)

        for iq in self.iq_circle:
            fig.append_trace(iq, 1, 4)

        for speed in self.speed_iq_circle:
            fig.append_trace(speed, 2, 4)

        #fig['layout'] = self.layout
        fig['layout'].update(self.layout)
        #fig['layout'].update(height=600, width=800, title='i <3 annotations and subplots')

        #fig = dict(data=self.data, layout=self.layout)
        plot(fig, filename=filename)


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
