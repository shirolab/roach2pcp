# Dear god
import numpy as np

# Taken partially from https://sashat.me/2017/01/11/list-of-20-simple-distinct-colors/
collist = ['#e6194B',# red
           '#3cb44b',# green
           '#ffe119',# yellow
           '#4363d8',# blue
           '#f58231',# orange
           '#911eb4',# purple
           '#42d4f4',# cyan
           '#f032e6',# magenta
           #'#bfef45',# lime
           #'#fabebe',# pink
           '#469990',# teal
           '#e6beff',# lavender
           '#9A6324',# brown
           #'#fffac8',# beige
           '#800000',# maroon
           #'#aaffc3',# mint
           '#808000',# olive
           #'#ffd8b1',# apricot
           '#000075',# navy
           ]#'#a9a9a9']

kstF = open('mysession2.kst', 'w')
kstF.write('<?xml version="1.0" encoding="UTF-8"?>'); kstF.write('\n')
kstF.write('<kst version="2.0">'); kstF.write('\n')

###############
# Default things
file = '/data/dirfiles/roach0/sf.txt'
fileRelative = '../../data/dirfiles/roach0/sf.txt'
start = '-1'
count = '15000'
skip = '10' # 10 standard
n_tones = 120
samprate = 488 # Hz

###############
# Write data sources
kstF.write('<data>');  kstF.write('\n')
mystr = '<source reader="Source List" updateType="0" file="' + file + '" fileRelative="' + \
        fileRelative + '" initialXNum="1" initialTNum="1" initialDSNum="1"/>'
kstF.write(mystr); kstF.write('\n')
kstF.write('</data>');  kstF.write('\n')

################
# First come up with arrays of fields to populate datavector
gen_fields = ['INDEX','python_timestamp','packet_count','pps_timestamp',
              'fine_timestamp','packet_info_reg','gpio_reg','roach_checksum']
gen_field_names = ['Index', 'Python Timestamp', 'Packet Count', 'PPS Timestamp',
                   'Fine Timestamp', 'Packet Info Register', 'GPIO Register',
                   'ROACH Checksum']
# Allow for all tones to have an associated blind tone
numarr = np.arange(0,n_tones)
tone_fields = []
tone_noiq = []
for nn in numarr:
    tone_fields.append('K' + '%03i' % nn + '_I')
    tone_fields.append('K' + '%03i' % nn + '_Q')
    tone_fields.append('K' + '%03i' % nn + '_df')
    tone_fields.append('K' + '%03i' % nn + '_magz')
    tone_fields.append('K' + '%03i' % nn + '_angz')
    tone_noiq.append('K' + '%03i' % nn)
    tone_fields.append('B' + '%03i' % nn + '_I')
    tone_fields.append('B' + '%03i' % nn + '_Q')
    tone_fields.append('B' + '%03i' % nn + '_df')
    tone_fields.append('B' + '%03i' % nn + '_magz')
    tone_fields.append('B' + '%03i' % nn + '_angz')
    tone_noiq.append('B' + '%03i' % nn)
    
fields = gen_fields + tone_fields
vnum = np.arange(1, len(fields) + 1)

###################
# Populate "variables" tags
kstF.write('<variables>'); kstF.write('\n')

x_init = 3 # Based on just looking at the damn thing
dx = 11 # Again, god knows why

# Print a string for each variable
xx = x_init
for ff, ffv in enumerate(fields):
    mystr = '<datavector file="' + file + '" fileRelative="' + fileRelative + \
            '" field="' + fields[ff] + '" start="' + start + '" count="' + \
            count + '" skip="' + skip + '" startUnits="" rangeUnits="" ' + \
            'initialVNum="' + str(vnum[ff]) + '" initialXNum="' + \
            str(xx) + '"/>'
    kstF.write(mystr); kstF.write('\n')
    xx = xx + dx

kstF.write('</variables>'); kstF.write('\n')
# Wow that worked
##################    
# Populate equations.
kstF.write('<objects>'); kstF.write('\n')

def findmyvnum(fieldname, fields, vnum):
    return vnum[fields.index(fieldname)]

def printmyvec(fieldname, fields, vnum, incr = 0):
    myvnum = findmyvnum(fieldname, fields, vnum)
    expr = fieldname + ' (V' + str(myvnum + incr) + ')'
    expr = expr.replace('_','\_')
    return expr

def printmyeqn(tonename, eqn, fields, vnum):
    Istr = printmyvec(tonename + '_I', fields, vnum)
    Qstr = printmyvec(tonename + '_Q', fields, vnum)
    magstr = printmyvec(tonename + '_magz', fields, vnum)
    # Note that when Istr, etc are PRINTED, the correct backslash appears
    if eqn == 'mag':
        expr = '20*log(sqrt([' + Istr + ']^2 + [' + Qstr + ']^2))'
    if eqn == 'magdB':
        expr = '20*log([' + magstr + '])'
    if eqn == 'phase':
        expr = 'atanx([' + Qstr + '], [' + Istr + '])'
    return expr

""" Now that magz, angz are working, no need for these
# For each of K/B, do mag and phase
# For the vnum, xnum to work, must execute in order
xvecstr = printmyvec('python_timestamp',fields,vnum)
ee = 1
v_init = max(vnum) # Because we now have to increment by 2...lame
vv = 1
for tt in tone_noiq:
    # Set name and vnum
    descrname = tt + ' Mag'
    fields.append(descrname)
    vnum = np.append(vnum, v_init + vv)
    mystr = '<equation expression="' + printmyeqn(tt,'mag',fields,vnum) \
            + '" xvector="' + xvecstr + '" interpolate="true"' + \
            ' descriptiveNameIsManual="true" descriptiveName="' + \
            descrname + '" initialVNum="' + str(vnum[-1]) + \
            '" initialXNum="' + str(xx) + '" initialENum="' + str(ee) + '"/>'
    kstF.write(mystr); kstF.write('\n')
    xx = xx + dx
    ee = ee + 1
    vv = vv + 2

    # Set name and vnum
    descrname = tt + ' Phase'
    fields.append(descrname)
    vnum = np.append(vnum, v_init + vv)
    mystr = '<equation expression="' + printmyeqn(tt,'phase',fields,vnum) \
            + '" xvector="' + xvecstr + '" interpolate="true"' + \
            ' descriptiveNameIsManual="true" descriptiveName="' + \
            descrname + '" initialVNum="' + str(vnum[-1]) + \
            '" initialXNum="' + str(xx) + '" initialENum="' + str(ee) + '"/>'
    kstF.write(mystr); kstF.write('\n')
    xx = xx + dx
    ee = ee + 1
    vv = vv + 2
"""
# But do allow for 'magdB'
xvecstr = printmyvec('python_timestamp',fields,vnum)
ee = 1
v_init = max(vnum) # Because we now have to increment by 2...lame
vv = 1
for tt in tone_noiq:
    # Set name and vnum
    descrname = tt + ' MagdB'
    fields.append(descrname)
    vnum = np.append(vnum, v_init + vv)
    mystr = '<equation expression="' + printmyeqn(tt,'magdB',fields,vnum) \
            + '" xvector="' + xvecstr + '" interpolate="true"' + \
            ' descriptiveNameIsManual="true" descriptiveName="' + \
            descrname + '" initialVNum="' + str(vnum[-1]) + \
            '" initialXNum="' + str(xx) + '" initialENum="' + str(ee) + '"/>'
    kstF.write(mystr); kstF.write('\n')
    xx = xx + dx
    ee = ee + 1
    vv = vv + 2

# df PSDs

pp = 1
for tt in tone_noiq:
    # Set name and vnum
    descrname = tt + ' PSD'
    fields.append(descrname)
    vnum = np.append(vnum, v_init + vv)
    mystr = '<powerspectrum vector="' + printmyvec(tt + '_df',fields, vnum) \
            + '" samplerate="' + str(samprate/int(skip)) + '" gaussiansigma="1" average="true" fftlength="11" removemean="true" apodize="true" apodizefunction="0" vectorunits="V" rateunits="Hz" outputtype="1" initialVNum="' + str(vnum[-1]) + \
            '" initialXNum="' + str(xx) + '" initialPSDNum="' + str(pp) + '"/>'
    kstF.write(mystr); kstF.write('\n')
    xx = xx + dx
    vv = vv + 2
    pp = pp + 1

kstF.write('</objects>'); kstF.write('\n')
# Wow that worked

##################    
# Populate curves - right now, everything as a function of python_timestamp
kstF.write('<relations>'); kstF.write('\n')

# First do the ROACH registers 
cc = 1
for gg, ggv in enumerate(gen_fields[2:]):
    mystr = '<curve xvector="' + printmyvec('python_timestamp',fields,vnum) + \
            '" yvector="' + printmyvec(ggv,fields,vnum) + '" color="#4363d8" alpha="255" headcolor="#000000" headalpha="255" barfillcolor="#000000" barfillalpha="255" haslines="true" linewidth="0" linestyle="0" haspoints="false" pointtype="0" pointdensity="0" pointsize="12" hasbars="false" ignoreautoscale="false" hashead="false" headtype="0" descriptiveNameIsManual="true" descriptiveName="' + gen_field_names[2:][gg] + '" initialCNum="' + str(cc) + '"/>'
    kstF.write(mystr); kstF.write('\n')
    cc = cc + 1

# Now df, mag, ang, PSD
for tt in tone_noiq:

    mycolor = collist[ int(tt[1:]) % len(collist) ] 
    name = tt + '_df'
    mystr = '<curve xvector="' + printmyvec('python_timestamp',fields,vnum) + \
            '" yvector="' + printmyvec(name,fields,vnum) + '" color="' + mycolor + '" alpha="255" headcolor="#000000" headalpha="255" barfillcolor="#000000" barfillalpha="255" haslines="true" linewidth="0" linestyle="0" haspoints="false" pointtype="0" pointdensity="0" pointsize="12" hasbars="false" ignoreautoscale="false" hashead="false" headtype="0" descriptiveNameIsManual="true" descriptiveName="' + tt + ' df' + '" initialCNum="' + str(cc) + '"/>'
    kstF.write(mystr); kstF.write('\n')
    cc = cc + 1

    # This is straight magnitude - no real need
    """
    name = tt + '_magz'
    mystr = '<curve xvector="' + printmyvec('python_timestamp',fields,vnum) + \
            '" yvector="' + printmyvec(name,fields,vnum) + '" color="#000000" alpha="255" headcolor="#000000" headalpha="255" barfillcolor="#000000" barfillalpha="255" haslines="true" linewidth="0" linestyle="0" haspoints="false" pointtype="0" pointdensity="0" pointsize="12" hasbars="false" ignoreautoscale="false" hashead="false" headtype="0" descriptiveNameIsManual="true" descriptiveName="' + tt + ' Mag' + '" initialCNum="' + str(cc) + '"/>'
    kstF.write(mystr); kstF.write('\n')
    cc = cc + 1
    """
    # Use equation-based mag instead to get in dB
    descrname = tt + ' MagdB'
    xvecname = printmyvec(descrname, fields, vnum)
    xvecname = xvecname.replace(' (V', ':x (V')
    yvecname = printmyvec(descrname, fields, vnum, incr=1)
    yvecname = yvecname.replace(' (V', ':y (V')
    mystr = '<curve xvector="' + xvecname + \
            '" yvector="' + yvecname + '" color="' + mycolor + '" alpha="255" headcolor="#000000" headalpha="255" barfillcolor="#000000" barfillalpha="255" haslines="true" linewidth="0" linestyle="0" haspoints="false" pointtype="0" pointdensity="0" pointsize="12" hasbars="false" ignoreautoscale="false" hashead="false" headtype="0" descriptiveNameIsManual="true" descriptiveName="' + descrname + '" initialCNum="' + str(cc) + '"/>'
    kstF.write(mystr); kstF.write('\n')
    cc = cc + 1

    name = tt + '_angz'
    mystr = '<curve xvector="' + printmyvec('python_timestamp',fields,vnum) + \
            '" yvector="' + printmyvec(name,fields,vnum) + '" color="' + mycolor + '" alpha="255" headcolor="#000000" headalpha="255" barfillcolor="#000000" barfillalpha="255" haslines="true" linewidth="0" linestyle="0" haspoints="false" pointtype="0" pointdensity="0" pointsize="12" hasbars="false" ignoreautoscale="false" hashead="false" headtype="0" descriptiveNameIsManual="true" descriptiveName="' + tt + ' Phase' + '" initialCNum="' + str(cc) + '"/>'
    kstF.write(mystr); kstF.write('\n')
    cc = cc + 1

    # PSD: like equations above
    descrname = tt + ' PSD'
    xvecname = printmyvec(descrname, fields, vnum)
    xvecname = xvecname.replace(' (V', ':f (V')
    yvecname = printmyvec(descrname, fields, vnum, incr=1)
    yvecname = yvecname.replace(' (V', ':psd (V')
    mystr = '<curve xvector="' + xvecname + \
            '" yvector="' + yvecname + '" color="' + mycolor + '" alpha="255" headcolor="#000000" headalpha="255" barfillcolor="#000000" barfillalpha="255" haslines="true" linewidth="0" linestyle="0" haspoints="false" pointtype="0" pointdensity="0" pointsize="12" hasbars="false" ignoreautoscale="false" hashead="false" headtype="0" descriptiveNameIsManual="true" descriptiveName="' + descrname + '" initialCNum="' + str(cc) + '"/>'
    kstF.write(mystr); kstF.write('\n')
    cc = cc + 1


"""
for tt in tone_noiq:
    # Set name and vnum
    descrname = tt + ' Mag'
    xvecname = printmyvec(descrname, fields, vnum)
    xvecname = xvecname.replace(' (V', ':x (V')
    yvecname = printmyvec(descrname, fields, vnum, incr=1)
    yvecname = yvecname.replace(' (V', ':y (V')
    mystr = '<curve xvector="' + xvecname + \
            '" yvector="' + yvecname + '" color="#000000" alpha="255" headcolor="#000000" headalpha="255" barfillcolor="#000000" barfillalpha="255" haslines="true" linewidth="0" linestyle="0" haspoints="false" pointtype="0" pointdensity="0" pointsize="12" hasbars="false" ignoreautoscale="false" hashead="false" headtype="0" descriptiveNameIsManual="true" descriptiveName="' + descrname + '" initialCNum="' + str(cc) + '"/>'
    kstF.write(mystr); kstF.write('\n')
    cc = cc + 1

    descrname = tt + ' Phase'
    xvecname = printmyvec(descrname, fields, vnum)
    xvecname = xvecname.replace(' (V', ':x (V')
    yvecname = printmyvec(descrname, fields, vnum, incr=1)
    yvecname = yvecname.replace(' (V', ':y (V')
    mystr = '<curve xvector="' + xvecname + \
            '" yvector="' + yvecname + '" color="#000000" alpha="255" headcolor="#000000" headalpha="255" barfillcolor="#000000" barfillalpha="255" haslines="true" linewidth="0" linestyle="0" haspoints="false" pointtype="0" pointdensity="0" pointsize="12" hasbars="false" ignoreautoscale="false" hashead="false" headtype="0" descriptiveNameIsManual="true" descriptiveName="' + descrname + '" initialCNum="' + str(cc) + '"/>'
    kstF.write(mystr); kstF.write('\n')
    cc = cc + 1
"""

# Now IQ
for tt in tone_noiq:
    mycolor = collist[ int(tt[1:]) % len(collist) ] 
    descrname = tt + ' IQ'
    xvecname = printmyvec(tt + '_I', fields, vnum)
    yvecname = printmyvec(tt + '_Q', fields, vnum)
    mystr =  '<curve xvector="' + xvecname + \
             '" yvector="' + yvecname + '" color="' + mycolor + '" alpha="15" headcolor="#000000" headalpha="255" barfillcolor="#000000" barfillalpha="255" haslines="true" linewidth="0" linestyle="0" haspoints="false" pointtype="13" pointdensity="0" pointsize="1" hasbars="false" ignoreautoscale="false" hashead="true" headtype="6" descriptiveNameIsManual="true" descriptiveName="' + descrname + '" initialCNum="' + str(cc) + '"/>'
    kstF.write(mystr); kstF.write('\n')
    cc = cc + 1

kstF.write('</relations>'); kstF.write('\n')
kstF.write('</kst>'); kstF.write('\n')
kstF.close()
