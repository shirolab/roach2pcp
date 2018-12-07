"""
Bunch of functions to get the network interface parameters, in order to
check if they are available in the computer
"""

import subprocess          

def get_ifconfig():
    """
    Get the ifconfig ouput to get network parameters
    """
    cmd = "ifconfig"
    if_config_output = subprocess.check_output(cmd, shell=True)
    return if_config_output

def _get_device(paragraph):
    """
    Get the device from the ifconfig output
    """
    inet = paragraph.split(" Link ")[0]
    device = ""
    for w in inet:
        if w != " ":
            device += w
    return device

def _get_ip_msk(paragraph):
    """
    Get the IP and Mask parameter of each device in ifconfig output
    """
    inet_mask = paragraph.split("\n")[1]
    ip = ""
    msk = ""
    acum = ""
    mark = 0
    for i in inet_mask:
        acum += i
        if "addr:" in acum:
            if i != " ":
                ip += i
            else:
                acum = ""
        elif "Mask:" in acum:
            if i != " ":
                msk += i
            else:
                acum = ""

    return ip[1:], msk[1:]

def _get_mac(paragraph):
    """
    Get the mac address of each network interface
    """
    if "HWaddr" in paragraph.split("\n")[0]:
        mac_s = paragraph.split("\n")[0].split("HWaddr")[1]
        mac = ""
        for m in mac_s:
            if m != " " and m != ":":
                mac += m
        return mac
    else:
        return -1

def get_ifaces(if_config):
    """
    Get all the network device parameters
    """
    ifaces = []
    for paragraph in if_config.split('\n\n')[:-1]:
        dev = _get_device(paragraph)
        ip = _get_ip_msk(paragraph)[0]
        msk = _get_ip_msk(paragraph)[1]
        mac = _get_mac(paragraph)

        ifaces.append([dev,ip,msk,mac])

    return ifaces

