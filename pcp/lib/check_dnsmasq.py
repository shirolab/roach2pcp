import os,time


def check_dnsmasq():
    """
    Checks if dnsmasq service is running.
    
    Tries to start it if necessary but will require a password unless someone 
    edits the sudoers file with visudo and adds a line like:    
    %LimitedAdmins ALL=NOPASSWD: /bin/systemctl start dnsmasq
    
    """

    #silently check (should return 0 if running)
    ret = os.system('/bin/systemctl -l --no-pager status dnsmasq  >/dev/null')
    
    if ret:
        print 'Trying to start dnsmasq service for roach dhcp leasing'
        #try and start the service
        ret = os.system('/bin/systemctl -l --no-pager start dnsmasq')
        if ret:
            print( 'Cannot start dnsmasq, may not find roaches')
            return
        
        #loudly and proudly print status!
        ret = os.system('/bin/systemctl -l --no-pager status dnsmasq ')
        
        print ('check_dnsmasq: started dnsmasq service')
        print ('check_dnsmasq: please wait a moment for dhcp leases to be acquired, sleep(5)')
        time.sleep(5)
        
    return

    