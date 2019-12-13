# Dear god
import numpy as np

kstF = open('mysession.kst', 'w')
kstF.write('<?xml version="1.0" encoding="UTF-8"?>'); kstF.write('\n')
kstF.write('<kst version="2.0">'); kstF.write('\n')

###############
# Default things to stick in each line - make everything a string, but
# no quotation marks
file = '/data/dirfiles/roach0/sf.txt'
fileRelative = '../../data/dirfiles/roach0/sf.txt'
start = '-1'
count = '15000'
skip = '10'

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
numarr = np.arange(0,2)
tone_fields = []
tone_noiq = []
for nn in numarr:
    tone_fields.append('K' + '%03i' % nn + '_I')
    tone_fields.append('K' + '%03i' % nn + '_Q')
    tone_noiq.append('K' + '%03i' % nn)
    tone_fields.append('B' + '%03i' % nn + '_I')
    tone_fields.append('B' + '%03i' % nn + '_Q')
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
    Istr = printmyvec(tonename + '_I',fields, vnum)
    Qstr = printmyvec(tonename + '_Q',fields, vnum)
    # Note that when Istr, etc are PRINTED, the correct backslash appears
    if eqn == 'mag':
        expr = '20*log(sqrt([' + Istr + ']^2 + [' + Qstr + ']^2))'
    if eqn == 'phase':
        expr = 'atanx([' + Qstr + '], [' + Istr + '])'
    return expr

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

kstF.write('</objects>'); kstF.write('\n')
# Wow that worked
##################    
# Populate curves - right now, everything as a function of python_timestamp
kstF.write('<relations>'); kstF.write('\n')

# First do the ROACH registers 
cc = 1
for gg, ggv in enumerate(gen_fields[2:]):
    mystr = '<curve xvector="' + printmyvec('python_timestamp',fields,vnum) + \
            '" yvector="' + printmyvec(ggv,fields,vnum) + '" color="#000000" alpha="255" headcolor="#000000" headalpha="255" barfillcolor="#000000" barfillalpha="255" haslines="true" linewidth="0" linestyle="0" haspoints="false" pointtype="0" pointdensity="0" pointsize="12" hasbars="false" ignoreautoscale="false" hashead="false" headtype="0" descriptiveNameIsManual="true" descriptiveName="' + gen_field_names[2:][gg] + '" initialCNum="' + str(cc) + '"/>'
    kstF.write(mystr); kstF.write('\n')
    cc = cc + 1

# Now Mag/phase
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

kstF.write('</relations>'); kstF.write('\n')

kstF.write('</kst>'); kstF.write('\n')
kstF.close()
