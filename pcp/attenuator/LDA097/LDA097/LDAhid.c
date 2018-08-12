// -------- High Resolution LDA Linux Library ------------
//
// RD 6/9/2017
//
// This library uses .05db units for attenuation values, so 10db is represented by 200. (multiply by 20 to convert db to api units)


#include <usb.h>
#include <linux/hid.h>	/* AK: Changed include for modern linux. */
#include <stdbool.h>	/* AK: Added include for 'bool' type */
#include <stdio.h>
#include <math.h>
#include <string.h>
#include <pthread.h>
#include <time.h>
#include "LDAhid.h"

#define DEBUG_OUT 0  	/* set this to 1 in order to see debugging output, 2 for a ton of output, or 3 for many tons */
#define FALSE 0
#define TRUE !FALSE

#define PACKET_CTRL_LEN 8
#define PACKET_INT_LEN 8
#define INTERFACE 0
#define ENDPOINT_INT_IN 0x82
#define TIMEOUT 500

#define LIBVER "0.97"	// RD:	added support for more devices, including High Res attenuators,
			//	internal representation of attenuation is now in .05 db units

void *brick_handler_function (void *ptr);

/* ----------------------------------------------------------------- */
/* globals we'll be using at runtime */
char errmsg[32]; // For the status->string converter

bool bVerbose = FALSE; // True to generate debug oriented printf output

bool TestMode = TRUE; // if TestMode is true we fake it -- no HW access
// TestMode defaults to FALSE for production builds

LDAPARAMS lda [MAXDEVICES]; // an array of structures each of which holds the info for a given 
// device. The DeviceID is the index into the array. Devices may come and go
// so there is no guarantee that the active elements are contiguous

time_t starttime, currtime;

// product names
char sVNX1[32] = "LDA-102";
char sVNX2[32] = "LDA-602";
char sVNX3[32] = "LDA-302P-H";
char sVNX4[32] = "LDA-302P-1";
char sVNX5[32] = "LDA-302P-2";
char sVNX6[32] = "LDA-102-75";
char sVNX7[32] = "LDA-102E";
char sVNX8[32] = "LDA-602E";
char sVNX9[32] = "LDA-183";

char sVNX10[32]	= "LDA-203";
char sVNX11[32]	= "LDA-102EH";
char sVNX12[32]	= "LDA-602EH";


// device VID and PID

unsigned short devVID = 0x041f; // device VID for Vaunix Devices

unsigned short dev1PID = 0x1207; // device PID for Vaunix LDA-102
unsigned short dev2PID = 0x1208; // device PID for Vaunix LDA-602
unsigned short dev3PID = 0x120D; // device PID for Vaunix LDA-302P-H
unsigned short dev4PID = 0x120E; // device PID for Vaunix LDA-302P-1	RD: fixed typo
unsigned short dev5PID = 0x120F; // device PID for Vaunix LDA-302P-2	RD: fixed typo
unsigned short dev6PID = 0x1210; // device PID for Vaunix LDA-102-75	RD: added 8/2014
unsigned short dev7PID = 0x120B; // device PID for Vaunix LDA-102E	RD: added 8/2014
unsigned short dev8PID = 0x120C; // device PID for Vaunix LDA-602E	RD: added 8/2014
unsigned short dev9PID = 0x1211; // device PID for Vaunix LDA-183	RD: added 8/2014

unsigned short dev10PID = 0x1212; // device PID for Vaunix LDA-203	RD: added 6/2017
unsigned short dev11PID = 0x1213; // device PID for Vaunix LDA-102EH	RD: added 6/2017
unsigned short dev12PID = 0x1214; // device PID for Vaunix LDA-602EH	RD: added 6/2017

/* stuff for the threads */
pthread_t threads[MAXDEVICES];
usb_dev_handle *thread_devhandles[MAXDEVICES];
#define THREAD_IDLE 0
#define THREAD_START 1
#define THREAD_EXIT 3
#define THREAD_DEAD 4
#define THREAD_ERROR -1

// --------------------- other device specific equates ------------------------
#define HW_MAXP 40; // MaxPower is the output of the device in db -- +10 in this case
                    // NB -- the value used in the SetPower function is relative attenuation
                    // not absolute power!!

// --------------- Device IO support functions ----------------------------

bool CheckDeviceOpen(DEVID deviceID) {
  if (TestMode) return TRUE;// in test mode all devices are always available
  //  if ((lda[deviceID].DevStatus & DEV_OPENED) && (deviceID != 0) && (threads[deviceID] != NULL))
  if ((lda[deviceID].DevStatus & DEV_OPENED) && (deviceID != 0))
    return TRUE;
  else
    return FALSE;
}

// ------------------------------------------------------------------------
bool DevNotLocked(DEVID deviceID) {
  if (TestMode) return TRUE;// this shouldn't happen, but just in case...
  if (!(lda[deviceID].DevStatus & DEV_LOCKED))
    return TRUE;// we return TRUE if the device is not locked!
  else
    return FALSE;
}

// ------------------------------------------------------------------------
void LockDev(DEVID deviceID, bool lock) {
  if (TestMode) return;// this shouldn't happen, but just in case...
  if (lock) {
    lda[deviceID].DevStatus = lda[deviceID].DevStatus | DEV_LOCKED;
    return;
  } else {
    lda[deviceID].DevStatus = lda[deviceID].DevStatus & ~DEV_LOCKED;
    return;
  }
}

/* A function to display the status as string */
char* fnLDA_perror(LVSTATUS status) {
  strcpy(errmsg, "STATUS_OK");
  if (BAD_PARAMETER == status) strcpy(errmsg, "BAD_PARAMETER");
  if (BAD_HID_IO == status) strcpy(errmsg, "BAD_HID_IO");
  if (DEVICE_NOT_READY == status) strcpy(errmsg, "DEVICE_NOT_READY");
  
  // Status returns for DevStatus
  if (INVALID_DEVID == status) strcpy(errmsg, "INVALID_DEVID");
  if (DEV_CONNECTED == status) strcpy(errmsg, "DEV_CONNECTED");
  if (DEV_OPENED == status) strcpy(errmsg, "DEV_OPENED");
  if (SWP_ACTIVE == status) strcpy(errmsg,  "SWP_ACTIVE");
  if (SWP_UP == status) strcpy(errmsg, "SWP_UP");
  if (SWP_REPEAT == status) strcpy(errmsg, "SWP_REPEAT");
  
  return errmsg;

}

bool CheckHiRes(DEVID deviceID) {
 if (lda[deviceID].DevStatus & DEV_HIRES)
 {
   return TRUE;
 }
   else return FALSE;
}


char LibVersion[] = LIBVER;
char* fnLDA_LibVersion(void) {
  return LibVersion;
}
  
/* functions based on hid_io.cpp */
bool VNXOpenDevice(DEVID deviceID) {

  if (!(lda[deviceID].DevStatus & DEV_CONNECTED))	// we can't open a device that isn't there!
    return DEVICE_NOT_READY;
  
  if (DEBUG_OUT > 1) printf("Starting thread %d\r\n", deviceID);
  lda[deviceID].thread_command = THREAD_START; /* open device and start processing */
  pthread_create(&threads[deviceID], NULL, brick_handler_function, (void*)deviceID);
  lda[deviceID].DevStatus = lda[deviceID].DevStatus | DEV_OPENED;
  
  return STATUS_OK;
}

void report_data_decode(unsigned char rcvdata[], int tid) {
  int i;
  unsigned long dataval;
  char temp[32];

  if ((DEBUG_OUT > 0) && (rcvdata[0] != 0x4e)) {
    printf("Decoding ");
    for (i=0; i<8; i++)
      printf("%02x ", rcvdata[i]);
    printf("\r\n");
  }

  /* the first byte tells us the type, the second is the data length
     tid is the thread ID it came from so we can stash the value into lda[] */
  /* first decode the bytes */
  dataval = 0;
  if (0 < rcvdata[1]) {
    for (i=0; i<rcvdata[1]; i++)
      dataval = (dataval<<8) + rcvdata[1+rcvdata[1]-i];
  }
  if ((DEBUG_OUT > 1) && (rcvdata[0] != VNX_STATUS)) printf("Data payload decodes to %ld (%08x)\r\n", dataval, dataval);
  /* now we'll assign it to lda[] */

  // handle the status report
  switch(rcvdata[0]) {
  case VNX_STATUS:
    if (DEBUG_OUT > 2) printf("VNX_STATUS: got one!\r\n");
    if (DevNotLocked(tid)) {

	lda[tid].Attenuation = lda[tid].UnitScale * (int)rcvdata[7];	// update the attenuation level, converting HW units to our .05db units
  
      if (DEBUG_OUT > 0) printf("  VNX_STATUS reports Attenuation=%d\r\n", lda[tid].Attenuation);

      if (rcvdata[6] & (SWP_ONCE | SWP_CONTINUOUS))		// are we ramping?
	lda[tid].DevStatus = lda[tid].DevStatus | SWP_ACTIVE;
      else
	lda[tid].DevStatus = lda[tid].DevStatus & ~SWP_ACTIVE;

      // -- fill in the SWP_UP status bit
      if (rcvdata[6] & (SWP_DIRECTION))		// are we downwards?
	lda[tid].DevStatus = lda[tid].DevStatus & ~SWP_UP;
      else
	lda[tid].DevStatus = lda[tid].DevStatus | SWP_UP;

      // -- fill in the continuous sweep bit
      if (rcvdata[6] & (SWP_CONTINUOUS))	// are we in continuous sweep mode?
	lda[tid].DevStatus = lda[tid].DevStatus | SWP_REPEAT;
      else
	lda[tid].DevStatus = lda[tid].DevStatus & ~SWP_REPEAT;

      // -- fill in the bidirectional ramp bit
      if (rcvdata[6] & (SWP_BIDIR))		// are we in bi-directional ramp mode?
	lda[tid].DevStatus = lda[tid].DevStatus | SWP_BIDIRECTIONAL;
      else
	lda[tid].DevStatus = lda[tid].DevStatus & ~SWP_BIDIRECTIONAL;

      // -- fill in the profile active bit
      if (rcvdata[6] & (STATUS_PROFILE_ACTIVE))	// is an attenuation profile playing?
	lda[tid].DevStatus = lda[tid].DevStatus | PROFILE_ACTIVE;
      else
	lda[tid].DevStatus = lda[tid].DevStatus & ~PROFILE_ACTIVE;

      // -- fill in the current profile index --
	lda[tid].ProfileIndex = rcvdata[4];
	if (lda[tid].ProfileIndex > 99) lda[tid].ProfileIndex = 99;	// clip to profile length

      if (DEBUG_OUT > 0) printf("  VNX_STATUS sez Status=%02x\r\n", lda[tid].DevStatus);
      break;
    } /* if devnotlocked() */
    break;
    
  case VNX_HRSTATUS:
    if (DEBUG_OUT > 2) printf("VNX_HRSTATUS: got one!\r\n");
    if (DevNotLocked(tid)) {

	lda[tid].Attenuation = (int)rcvdata[5] + 256 * (int)rcvdata[6];	// update the HiRes attenuation level (in .05 db units already)
 
      if (DEBUG_OUT > 0) printf("  VNX_HRSTATUS reports Attenuation=%d\r\n", lda[tid].Attenuation);

      if (rcvdata[6] & (SWP_ONCE | SWP_CONTINUOUS))// are we ramping?
	lda[tid].DevStatus = lda[tid].DevStatus | SWP_ACTIVE;
      else
	lda[tid].DevStatus = lda[tid].DevStatus & ~SWP_ACTIVE;

      // -- fill in the SWP_UP status bit
      if (rcvdata[6] & (SWP_DIRECTION))		// are we ramping downwards?
	lda[tid].DevStatus = lda[tid].DevStatus & ~SWP_UP;
      else
	lda[tid].DevStatus = lda[tid].DevStatus | SWP_UP;

      // -- fill in the continuous sweep bit
      if (rcvdata[6] & (SWP_CONTINUOUS))	// are we in continuous sweep mode?
	lda[tid].DevStatus = lda[tid].DevStatus | SWP_REPEAT;
      else
	lda[tid].DevStatus = lda[tid].DevStatus & ~SWP_REPEAT;

      // -- fill in the bidirectional ramp bit
      if (rcvdata[6] & (SWP_BIDIR))		// are we in bi-directional ramp mode?
	lda[tid].DevStatus = lda[tid].DevStatus | SWP_BIDIRECTIONAL;
      else
	lda[tid].DevStatus = lda[tid].DevStatus & ~SWP_BIDIRECTIONAL;

      // -- fill in the profile active bit
      if (rcvdata[6] & (STATUS_PROFILE_ACTIVE))	// is an attenuation profile playing?
	lda[tid].DevStatus = lda[tid].DevStatus | PROFILE_ACTIVE;
      else
	lda[tid].DevStatus = lda[tid].DevStatus & ~PROFILE_ACTIVE;

      // -- fill in the current profile index --
	lda[tid].ProfileIndex = rcvdata[4];
	if (lda[tid].ProfileIndex > 49) lda[tid].ProfileIndex = 49;	// clip to max HiRes profile length

      if (DEBUG_OUT > 0) printf("  VNX_HRSTATUS sez Status=%02x\r\n", lda[tid].DevStatus);
      break;
    } /* if devnotlocked() */
    break;
  
  case VNX_FREQUENCY:
 	if (DEBUG_OUT > 0) printf(" Working Frequency = %d\n", dataval);

    if (DevNotLocked(tid))
	lda[tid].WorkingFrequency = dataval;
    break;
        
  case VNX_PWR:
    if (lda[tid].DevStatus & DEV_HIRES) {
      dataval = (int)rcvdata[2] + 256 * (int)rcvdata[3];	// HiRes data is already in .05db units
    }
    else {
      dataval = lda[tid].UnitScale * (int)rcvdata[2];		// We have to scale the other devices HW units to our .05db units
    }
    if (DEBUG_OUT > 0) printf(" Attenuation Level = %d\n", dataval);
    if (DevNotLocked(tid))
	lda[tid].Attenuation = dataval;
    break;

  case VNX_ADWELL:
    if (DEBUG_OUT > 0) printf(" Dwell Time = %d\n", dataval);
    if (DevNotLocked(tid))
      lda[tid].DwellTime = dataval;
    break;

  case VNX_ADWELL2:
    if (DEBUG_OUT > 0) printf(" 2nd Dwell Time = %d\n", dataval);
    if (DevNotLocked(tid))
      lda[tid].DwellTime2 = dataval;
    break;
    
  case VNX_AIDLE:
    if (DEBUG_OUT > 0) printf(" Idle Time = %d\n", dataval);
    if (DevNotLocked(tid))
      lda[tid].IdleTime = dataval;
    break;
    
  case VNX_AHOLD:
    if (DEBUG_OUT > 0) printf(" Hold Time = %d\n", dataval);
    if (DevNotLocked(tid))
      lda[tid].HoldTime = dataval;
    break;
    
  case VNX_ASTART:
    if (lda[tid].DevStatus & DEV_HIRES) {
      dataval = (int)rcvdata[2] + 256 * (int)rcvdata[3];	// HiRes data is already in .05db units
    }
    else {
      dataval = lda[tid].UnitScale * (int)rcvdata[2];		// We have to scale the other devices HW units to our .05db units
    }
    if (DEBUG_OUT > 0) printf(" Ramp Start Attenuation Level = %d\n", dataval);
    if (DevNotLocked(tid))
      lda[tid].RampStart = dataval;
    break;

  case VNX_ASTEP:
    if (lda[tid].DevStatus & DEV_HIRES) {
      dataval = (int)rcvdata[2] + 256 * (int)rcvdata[3];	// HiRes data is already in .05db units
    }
    else {
      dataval = lda[tid].UnitScale * (int)rcvdata[2];		// We have to scale the other devices HW units to our .05db units
    }
    if (DEBUG_OUT > 0) printf(" Attenuation Step Size = %d\n", dataval);
    if (DevNotLocked(tid))
      lda[tid].AttenuationStep = dataval;
    break;
    
  case VNX_ASTEP2:
    if (lda[tid].DevStatus & DEV_HIRES) {
      dataval = (int)rcvdata[2] + 256 * (int)rcvdata[3];	// HiRes data is already in .05db units
    }
    else {
      dataval = lda[tid].UnitScale * (int)rcvdata[2];		// We have to scale the other devices HW units to our .05db units
    }
    if (DEBUG_OUT > 0) printf(" Attenuation Step Size = %d\n", dataval);
    if (DevNotLocked(tid))
      lda[tid].AttenuationStep2 = dataval;
    break;
    
  case VNX_ASTOP:
    if (lda[tid].DevStatus & DEV_HIRES) {
      dataval = (int)rcvdata[2] + 256 * (int)rcvdata[3];	// HiRes data is already in .05db units
    }
    else {
      dataval = lda[tid].UnitScale * (int)rcvdata[2];		// We have to scale the other devices HW units to our .05db units
    }
    if (DEBUG_OUT > 0) printf(" Ramp End Attenuation Level = %d\n", dataval);
    if (DevNotLocked(tid))
      lda[tid].RampStop = dataval;
    break;

  case VNX_SWEEP:
    if (DEBUG_OUT > 0) printf(" Ramp Mode = %d\n", rcvdata[2]);
    if (DevNotLocked(tid)) {
 	// not used, same information available in the VNX_STATUS report
    }
    break;

  case VNX_RFMUTE:
    if (DEBUG_OUT > 0) {
      if (rcvdata[2])
	strcpy(temp, "RF ON");
      else
	strcpy(temp, "RF OFF");
      printf("%s \n", temp);
    }

    if (DEBUG_OUT > 0) printf("Parsing a RFMUTE report..\n");

    if (DevNotLocked(tid)) {
      if (rcvdata[0])
	lda[tid].Modebits = lda[tid].Modebits | MODE_RFON;
      else
	lda[tid].Modebits = lda[tid].Modebits & ~MODE_RFON;
    }
    break;

  case VNX_MINATTEN:
    if (lda[tid].DevStatus & DEV_HIRES) {
      dataval = (int)rcvdata[2] + 256 * (int)rcvdata[3];	// HiRes data is already in .05db units
    }
    else {
      dataval = lda[tid].UnitScale * (int)rcvdata[2];		// We have to scale the other devices HW units to our .05db units
    }
    if (DEBUG_OUT > 0) printf(" Minimum Attenuation = %d\n", dataval);
    if (DevNotLocked(tid))
      lda[tid].MinAttenuation = dataval;
    break;

  case VNX_MAXATTEN:
    if (lda[tid].DevStatus & DEV_HIRES) {
      dataval = (int)rcvdata[2] + 256 * (int)rcvdata[3];	// HiRes data is already in .05db units
    }
    else {
      dataval = lda[tid].UnitScale * (int)rcvdata[2];		// We have to scale the other devices HW units to our .05db units
    }
    if (DEBUG_OUT > 0) printf(" Maximum Attenuation = %d\n", dataval);
    if (DevNotLocked(tid))
      lda[tid].MaxAttenuation = dataval;
    break;

  case VNX_GETSERNUM:
    if (DEBUG_OUT > 0) printf(" Serial Number = %d\n", dataval);
    if (DevNotLocked(tid))
      lda[tid].SerialNumber = dataval;		// NB -- we never use this path!
    break;
  } /* switch */

  return;
}

// ************* The read thread handler for the brick ***********************
void *brick_handler_function (void *threadID) {
  int i, tid;
  tid = (int)threadID;
  struct usb_bus *busses;
  struct usb_bus *bus;
  int usb_status;
  char fullpath[128];
  int retries;
 
  if (DEBUG_OUT > 0) printf("Starting thread for device %d\r\n", tid);
  while ((lda[tid].thread_command >=0) &&
	 (lda[tid].thread_command != THREAD_EXIT)) {
    switch(lda[tid].thread_command) {
    case THREAD_IDLE: /* idle */
      /* this is where we wait for incoming USB data */
      usb_status = -1;
      retries = 50;
      while ((usb_status < 0) && (retries--) && (THREAD_IDLE == lda[tid].thread_command)) {
	usb_status = usb_interrupt_read(thread_devhandles[tid],  // handle
					ENDPOINT_INT_IN, // endpoint
					lda[tid].rcvbuff, // buffer
					PACKET_INT_LEN, // max length
					TIMEOUT);
	if (usb_status < 0) usleep(1000); /* wait 20 ms before trying again */
      }
      //      printf("Thread %d reports %d...\r\n", tid, usb_status);
      if (usb_status >= 0) {
	if (DEBUG_OUT > 1) {
	  printf("Thread %d reports %d...", tid, usb_status);
	  for (i=0; i<usb_status; i++)
	    printf("%02x ", lda[tid].rcvbuff[i]);
	  printf("\r\n");
	}
	/* decode the HID data */
	report_data_decode(lda[tid].rcvbuff, tid);
	if (DEBUG_OUT > 1) printf("Decoded device %d data %02x, decodewatch=%02x\r\n", tid, lda[tid].rcvbuff[0], lda[tid].decodewatch);
	if (lda[tid].decodewatch == lda[tid].rcvbuff[0]) {
	  if (DEBUG_OUT > 0) printf("Clearing decodewatch %02x for thread %d\r\n", lda[tid].decodewatch, tid);
	  lda[tid].decodewatch = 0;
	}
      } else
	if (DEBUG_OUT > 0) perror("THREAD_IDLE");
      break;
    case THREAD_START: /* starting up */
      /* we'll open the device. First we have to locate it */
      if (DEBUG_OUT > 0) printf("Thread %d is looking for the device\r\n", tid);

      usb_find_busses();
      usb_find_devices();
      busses = usb_get_busses();

      lda[tid].thread_command = THREAD_ERROR; /* assume it will fail */
      for (bus = busses; bus; bus = bus->next) {
	if (THREAD_IDLE == lda[tid].thread_command) break;
	struct usb_device *dev;

	for (dev = bus->devices; dev; dev = dev->next) {
	  if (THREAD_IDLE == lda[tid].thread_command) break;
	  if (DEBUG_OUT > 1) printf("Thread %d sez- Vendor: %04x PID: %04x\r\n", tid, dev->descriptor.idVendor, dev->descriptor.idProduct);
	  thread_devhandles[tid] = usb_open(dev);
	  usb_status = usb_get_string_simple(thread_devhandles[tid], dev->descriptor.iSerialNumber, lda[tid].rcvbuff, sizeof(lda[tid].rcvbuff));
	  if (DEBUG_OUT > 1) printf("string %d = [%s] looking to match [%s]\r\n", dev->descriptor.iSerialNumber, lda[tid].rcvbuff, lda[tid].Serialstr);
	  if ((dev->descriptor.idVendor == lda[tid].idVendor) &&
	      (dev->descriptor.idProduct == lda[tid].idProduct) &&
	      (0 == strcmp(lda[tid].rcvbuff, lda[tid].Serialstr))) {
	    /* we found the device. We'll open it */
	    if (DEBUG_OUT > 1) printf("Opening file [%s]\r\n", dev->filename);
	    thread_devhandles[tid] = usb_open(dev);

	    usb_detach_kernel_driver_np(thread_devhandles[tid], 0);

	    usb_status = usb_set_configuration (thread_devhandles[tid], 1);
	    if (DEBUG_OUT > 1) printf ("set configuration: %s\n", usb_status ? "failed" : "passed");

	    usb_status = usb_claim_interface (thread_devhandles[tid], 0);
	    if (DEBUG_OUT > 1) printf ("claim interface: %s\n", usb_status ? "failed" : "passed");

	    lda[tid].thread_command = THREAD_IDLE;
	    break;
	  } else {
	    /* if the device we opened isn't the one we wanted, close it */
	    usb_close(thread_devhandles[tid]);
	  }
	} /* for dev */
      } /* for bus */
      break;
    } /* switch */
  } /* while */
  if (DEBUG_OUT > 0) printf("Exiting thread for device %d because command=%d\r\n", tid, lda[tid].thread_command);
  if (THREAD_EXIT == lda[tid].thread_command) {
    usb_close(thread_devhandles[tid]);
	thread_devhandles[tid] = 0;
	}
  lda[tid].thread_command = THREAD_DEAD;
  pthread_exit(NULL);
}

// -------------- SendReport -------------------------------------------------

bool SendReport(int deviceID, char command, char *pBuffer, int cbBuffer)
{
  int i;
  int send_status;
  int retries;
  // Make sure the buffer that is being passed to us fits
  if (cbBuffer > HR_BLOCKSIZE) {
    // Report too big, don't send!
    return FALSE;
  }

  char Report[8];
  
  if (DEBUG_OUT > 1) printf("SR: command=%x cbBuffer=%x\r\n", command, cbBuffer);
  lda[deviceID].sndbuff[0] = command;		// command to device
  lda[deviceID].sndbuff[1] = cbBuffer;
  lda[deviceID].sndbuff[2] = pBuffer[0];
  lda[deviceID].sndbuff[3] = pBuffer[1];
  lda[deviceID].sndbuff[4] = pBuffer[2];
  lda[deviceID].sndbuff[5] = pBuffer[3];
  lda[deviceID].sndbuff[6] = pBuffer[4];
  lda[deviceID].sndbuff[7] = pBuffer[4];
  if (DEBUG_OUT > 1) {
    printf("SR: ");
    for (i=0; i<8; i++) {
      printf("%02x ", lda[deviceID].sndbuff[i]);
    }
    printf("\r\n");
  }

  /* we have to wait for a file handle to appear */
  retries = 0;
  while ((0 == thread_devhandles[deviceID]) && (retries++ < 10))
    sleep(1);
  /* we have data to write to the device */
  if (DEBUG_OUT > 1) printf("SR: sending the write...\r\n");
  send_status = usb_control_msg(thread_devhandles[deviceID],
				0x21,
				0x09, //HID_REPORT_SET,
				0x200,
				0,
				lda[deviceID].sndbuff,
				PACKET_CTRL_LEN,
				TIMEOUT);

  if (DEBUG_OUT > 1) {
    printf("(status=%d handle=%d)", send_status, thread_devhandles[deviceID]);
    if (send_status < 0) perror("SendReport"); else printf("\r\n");
  }

  return TRUE;
}

// ------------ GetParameter ---------------------------------------------
//
// The GetParam argument is the command byte sent to the device to get
// a particular value. The response is picked up by the read thread and
// parsed by it. The parser clears the corresponding event.


bool GetParameter(int deviceID, int GetParam)
{
	char VNX_param[4] = {0, 0, 0, 0};
	int timedout;

	if (DEBUG_OUT > 0) printf(" sending a GET command = %x\n", (char) GetParam );
	lda[deviceID].decodewatch = (char) GetParam;
	if (!SendReport(deviceID, (char)GetParam, VNX_param, 0)) {
	  return FALSE;
	}

	if (DEBUG_OUT > 0) printf(" SendReport sent a GET command successfully to device %d = %x\n", deviceID, (char) GetParam );
	
	starttime = time(NULL);
	timedout = 0;

	/* wait until the value is decoded or 2 seconds have gone by */
	while ((lda[deviceID].decodewatch > 0) && (0 == timedout)) {
	  if ((time(NULL)-starttime) > 2) timedout = 1;
	}

	return (0 == timedout) ? TRUE : FALSE;
}

// -------------- Get Routines to read device settings --------------------
//
// Note: for these functions deviceID is not checked for validity
//		 since it was already checked in the calling program.

bool GetAttenuation(DEVID deviceID) {
  if (!GetParameter(deviceID, VNX_PWR))
    return FALSE;

  return TRUE;
}

bool GetFrequency(DEVID deviceID) {
  if (!GetParameter(deviceID, VNX_FREQUENCY))
    return FALSE;

  return TRUE;
}



// -------------------------------

bool GetIdleTime(DEVID deviceID) {
  if (!GetParameter(deviceID, VNX_AIDLE))
    return FALSE;

  return TRUE;
}

// -------------------------------

bool GetRampStart(DEVID deviceID) {
  if (!GetParameter(deviceID, VNX_ASTART))
    return FALSE;

  return TRUE;
}

// -------------------------------
bool GetRampStep(DEVID deviceID) {	
  if (!GetParameter(deviceID, VNX_ASTEP))
    return FALSE;

  return TRUE;
}

// -------------------------------

bool GetRampEnd(DEVID deviceID) {	
  if (!GetParameter(deviceID, VNX_ASTOP))
    return FALSE;

  return TRUE;
}

// -------------------------------
bool GetDwellTime(DEVID deviceID) {
  if (!GetParameter(deviceID, VNX_ADWELL))
    return FALSE;

  return TRUE;
}


// -------------------------------
bool GetRF_On(DEVID deviceID) {
  if (!GetParameter(deviceID, VNX_RFMUTE))
    return FALSE;

  return TRUE;
}


/* functions to manage devices, not getting or retrieving data */
/*-------------------------------------------------------------*/

void FindVNXDevices()
{
  bool bFound;
  int hTemp;  			// temporary variable
  int HWType; 			// temporary variable for hardware/model type
  int HWMinAttenuation;		// temporary variable for default minimum attenuation
  int HWMaxAttenuation;		// temporary variable for default maximum attenuation
  int HWAttenuationStep;	// temporary variable for the devices minimum attenuation step in .05 db units
  int HWMinFrequency;		// temporary variable for HRes minimum frequency
  int HWMaxFrequency;		// temporary variable for HRes maximum frequency
  int HWUnitScale;		// temporary variable for unit scaling -- we use .05db internally
  char HWName[32];  		// temporary variable for the hardware model name
  char HWSerial[8]; 		// temporary holder for the serial number
  
  struct usb_dev_handle *devhandle;
  struct usb_bus *busses;
  char sendbuff[8];
  char rcvbuff[32];
  int usb_status;
    
  usb_init();
  if (DEBUG_OUT > 2)
    usb_set_debug(3); 	/* if we want lots of debug, let's see the USB output too. */
  else
    usb_set_debug(0);
  usb_find_busses();
  usb_find_devices();
  
  busses = usb_get_busses();
        
  struct usb_bus *bus;
  int c, i, a;
  int send_status, open_status;
  
  /* ... */
    
  // We need to remove devices from our table that are no longer connected ---
  // to do this we clear the "connected" flag for each table entry that is not open initially
  // then, as we find them we re-set the "connected" flag
  // anybody who doesn't have his "connected" flag set at the end is gone - we found it
  // previously but not this time
  
  for (i = 1; i<MAXDEVICES; i++){
    if ((lda[i].SerialNumber != 0) && !(lda[i].DevStatus & DEV_OPENED))
      lda[i].DevStatus = lda[i].DevStatus & ~DEV_CONNECTED; 	
  }

  for (bus = busses; bus; bus = bus->next) {
    struct usb_device *dev;
    
    for (dev = bus->devices; dev; dev = dev->next) {
      if (DEBUG_OUT > 1) printf("Vendor: %04x PID: %04x\r\n", dev->descriptor.idVendor, dev->descriptor.idProduct);
      
      HWType = 0;
      HWMinAttenuation = 0;
      HWMinFrequency = 0;
      HWMaxFrequency = 0;	// defaults for non HiRes devices
      
      /* check this device to see if it's one of our devices */
      if ((devVID == dev->descriptor.idVendor) &&
	  (dev1PID == dev->descriptor.idProduct)) HWType = 1;
      if ((devVID == dev->descriptor.idVendor) &&
	  (dev2PID == dev->descriptor.idProduct)) HWType = 2;
	  if ((devVID == dev->descriptor.idVendor) &&
	  (dev3PID == dev->descriptor.idProduct)) HWType = 3;
	  if ((devVID == dev->descriptor.idVendor) &&
	  (dev4PID == dev->descriptor.idProduct)) HWType = 4;
	  if ((devVID == dev->descriptor.idVendor) &&
	  (dev5PID == dev->descriptor.idProduct)) HWType = 5;
	  if ((devVID == dev->descriptor.idVendor) &&
	  (dev6PID == dev->descriptor.idProduct)) HWType = 6;
	  if ((devVID == dev->descriptor.idVendor) &&
	  (dev7PID == dev->descriptor.idProduct)) HWType = 7;
	  if ((devVID == dev->descriptor.idVendor) &&
	  (dev8PID == dev->descriptor.idProduct)) HWType = 8;
	  if ((devVID == dev->descriptor.idVendor) &&
	  (dev9PID == dev->descriptor.idProduct)) HWType = 9;
	  if ((devVID == dev->descriptor.idVendor) &&
	  (dev10PID == dev->descriptor.idProduct)) HWType = 10;
	  if ((devVID == dev->descriptor.idVendor) &&
	  (dev11PID == dev->descriptor.idProduct)) HWType = 11;
	  if ((devVID == dev->descriptor.idVendor) &&
	  (dev12PID == dev->descriptor.idProduct)) HWType = 12;
	  
	  
	  
      if (HWType) { /* we like this device and we'll keep it */
	if (DEBUG_OUT > 1) printf("Opening device %04x:%04x serial %04x type %d\r\n",
			      dev->descriptor.idVendor,
			      dev->descriptor.idProduct,
			      dev->descriptor.iSerialNumber, HWType);
	devhandle = usb_open(dev);
	if (DEBUG_OUT > 1)  printf("LDA device found @ address [%s]\r\n", dev->filename);
	usb_status = usb_get_string_simple(devhandle, dev->descriptor.iSerialNumber, rcvbuff, sizeof(rcvbuff));
	if (DEBUG_OUT > 1) printf("string %d = [%s]\r\n", dev->descriptor.iSerialNumber, rcvbuff);
	if (usb_status < 0) strcpy(HWSerial, ""); else strcpy(HWSerial, rcvbuff+3);
	usb_close(devhandle);
	
	// --- Set parameters for each type of hardware ---
	switch(HWType) {
	case 1: // LDA-102
	  strcpy(HWName, sVNX1);
	  HWMaxAttenuation = 1260;	// 63db max attenuation
	  HWAttenuationStep = 10;	// .5db
	  HWUnitScale = 5;		// .25db units
	  break;
	case 2:  // LDA-602
	  strcpy(HWName, sVNX2);
	  HWMaxAttenuation = 1260;	// 63db max attenuation
	  HWAttenuationStep = 10;	// .5db
	  HWUnitScale = 5;		// .25db units
	  break;
	case 3:  // LDA-302P-H
	  strcpy(HWName, sVNX3);
	  HWMaxAttenuation = 630;	// 31.5db max attenuation
	  HWAttenuationStep = 10;	// .5 db steps
	  HWUnitScale = 5;		// .25db units
	  break;	  
	case 4:  // LDA-302P-1
	  strcpy(HWName, sVNX4);
	  HWMaxAttenuation = 1260;	// 63 db, expressed in .1 db units
	  HWAttenuationStep = 20;	// 1 db steps
	  HWUnitScale = 5;		// uses the standard .25 db encodin
	  break;	  
	case 5:  // LDA-302P-2
	  strcpy(HWName, sVNX5);
	  HWMaxAttenuation = 1800;	// 90 db, expressed in .05db units, but the HW works in 1 db units!!
	  HWAttenuationStep = 40;	// 2 db steps (expressed in .05db units, but the HW uses a lsb = 1db encoding)
	  HWUnitScale = 20;		// the HW works in 1 db units!
	  break;
	case 6:  // LDA-102-75
	  strcpy(HWName, sVNX6);
	  HWMaxAttenuation = 2400;	// 120 db, expressed in .05db units
	  HWAttenuationStep = 10;	// .5 db steps (expressed in .05db units here, but the HW uses a lsb = .5db encoding)
	  HWUnitScale = 10;		// the HW works in .5 db units!
	  break;
	case 7:  // LDA-102E
	  strcpy(HWName, sVNX7);
	  HWMaxAttenuation = 2400;	// 120 db, expressed in .05db units, but the HW works in .5 db units!!
	  HWAttenuationStep = 10;	// .5 db steps (expressed in .05db units here, but the HW uses a lsb = .5db encoding)
	  HWUnitScale = 10;		// the HW works in .5 db units!
	  break;
	case 8:  // LDA-602E
	  strcpy(HWName, sVNX8);
	  HWMaxAttenuation = 1900;	// 95 db, expressed in .25db units, but the HW works in .5 db units!!
	  HWAttenuationStep = 10;	// .5 db steps (expressed in .05db units here, but the HW uses a lsb = .5db encoding)
	  HWUnitScale = 10;		// the HW works in .5 db units!
	  break;
	case 9:  // LDA-183
	  strcpy(HWName, sVNX9);
	  HWMaxAttenuation = 1260;	// 63 db, expressed in .05db units, but the HW works in .5 db units!!
	  HWAttenuationStep = 10;	// .5 db steps (expressed in .05db units here, but the HW uses a lsb = .5db encoding)
	  HWUnitScale = 10;		// the HW works in .5 db units!
	  break;
	
	case 10:  // LDA-203
	  strcpy(HWName, sVNX10);
	  HWMaxAttenuation = 1260;	// 63 db, expressed in .05db units, but the HW works in .5 db units!!
	  HWAttenuationStep = 10;	// .5 db steps (expressed in .25db units here, but the HW uses a lsb = .5db encoding)
	  HWUnitScale = 10;		// the HW works in .5 db units!
	  break;
	case 11:  // LDA-102EH
	  strcpy(HWName, sVNX11);
	  HWMaxAttenuation = 2400;	// 120 db, expressed in .05db units
	  HWAttenuationStep = 2;	// .1 db steps (expressed in .05db units here)
	  HWUnitScale = 1;			// the HW works in .05 db units!

	  HWMinFrequency = 2000;	// 200 MHz
	  HWMaxFrequency = 10000;	// 1 GHz
	  break;
	case 12:  // LDA-602EH
	  strcpy(HWName, sVNX12);
	  HWMaxAttenuation = 2400;	// 120 db, expressed in .05db units
	  HWAttenuationStep = 2;	// .1 db steps
	  HWUnitScale = 1;			// the HW works in .05 db units!

	  HWMinFrequency = 2000;	// 200 MHz
	  HWMaxFrequency = 60000;	// 6 GHz
	  break;
	  
	
	} /* HWType switch */
	
	/* find an open slot to save the data */
	// lets see if we have this unit in our table of devices already
	bFound = FALSE;
	
	for (i = 1; i<MAXDEVICES; i++){
	  if (lda[i].SerialNumber == atoi(HWSerial)) {
	    // we already have the device in our table
	    bFound = TRUE;
	    lda[i].DevStatus = lda[i].DevStatus | DEV_CONNECTED; // its here, mark it as connected
	    // at this point the device is present, but not in use, no sense looking more
	    break;
	  }
	}	// end of for loop
	
	// if the device isn't in the table we need to add it
	if (!bFound) {
	  hTemp = 0;
	  for (i = 1; i<MAXDEVICES; i++) {
	    if (lda[i].SerialNumber == 0) {
	      hTemp = i;
	      break;
	    }
	  } // end of for loop search for an empty slot in our array of devices
	  
	  /* save all of the data we've already acquired */
	  if (hTemp) {
	    lda[hTemp].SerialNumber = atoi(HWSerial);		            // save the device's serial number
	    lda[hTemp].DevStatus = lda[hTemp].DevStatus | DEV_CONNECTED;    // mark it as present
	    strcpy (lda[hTemp].ModelName, HWName);     		    	    // save the device's model name
	    
	    if (lda[hTemp].SerialNumber == 0 || lda[hTemp].SerialNumber > 4300) {
		 lda[hTemp].DevStatus = lda[hTemp].DevStatus | DEV_V2FEATURES;	// these devices have V2 firmware
	    }
	    else {
		 lda[hTemp].DevStatus = lda[hTemp].DevStatus & ~DEV_V2FEATURES; // these don't
	    }
		
	    if (HWType == 11 || HWType == 12) {
		lda[hTemp].DevStatus = lda[hTemp].DevStatus | DEV_HIRES; 	// HiRes LDAs
	    }
	    else {
		lda[hTemp].DevStatus = lda[hTemp].DevStatus & ~DEV_HIRES;	// everybody else
	    }
	    

	    lda[hTemp].MinAttenStep = HWAttenuationStep;
	    lda[hTemp].MinAttenuation = HWMinAttenuation;
	    lda[hTemp].MaxAttenuation = HWMaxAttenuation;		    // default values for attenuation range
	    lda[hTemp].UnitScale = HWUnitScale;				    // size of hardware unit in .05db units
									    // .25db = 5, .05db = 1. .5db = 10, 1db = 20
	    lda[hTemp].MinFrequency = HWMinFrequency;
	    lda[hTemp].MaxFrequency = HWMaxFrequency;
	    
	    /* The device has been closed so let's make sure we can find it again */
	    lda[hTemp].idVendor = dev->descriptor.idVendor;
	    lda[hTemp].idProduct = dev->descriptor.idProduct;
		lda[hTemp].idType = HWType;
	    strcpy(lda[hTemp].Serialstr, rcvbuff);
		
	    if (DEBUG_OUT > 1) {
	      printf("Stored as new device #%d\r\n", hTemp);
	      printf("Serial number=%d\r\n", lda[hTemp].SerialNumber);
	      printf("Devstatus=%08x\r\n", lda[hTemp].DevStatus);
	      printf("Model name=%s\r\n", lda[hTemp].ModelName);
	      printf("MinAttenuation=%d\r\n", lda[hTemp].MinAttenuation);
	      printf("MaxAttenuation=%d\r\n", lda[hTemp].MaxAttenuation);
	      printf("Resolution=%d\r\n", lda[hTemp].MinAttenStep);
	      printf("Vendor ID=%04x\r\n", lda[hTemp].idVendor);
	      printf("Product ID=%04x\r\n", lda[hTemp].idProduct);
	      printf("Serial number=%s\r\n", lda[hTemp].Serialstr);
	    }
	  } else {
	    // our table of devices is full, not much we can do
	  }
	} /* if !bfound  */
	/* get any other data we might need */
      } /* if HWType */
    } /* for dev */
  } /* for bus */

  /* clean up the structure and mark unused slots */
  for (i = 1; i<MAXDEVICES; i++){
    if ((lda[i].SerialNumber != 0) && !(lda[i].DevStatus & DEV_CONNECTED))
      lda[i].SerialNumber = 0;	// mark this slot as unused 	

    if (lda[i].SerialNumber == 0)
      lda[i].DevStatus = 0;		// clear the status for robustness!
  }	// end of zombie removal for loop
}

/* ----------------------------------------------------------------- */

void fnLDA_Init(void) {
  /* clear out the storage structure. Must be called once before anything else */
  int i;
  int status;

  for (i = 0; i<MAXDEVICES; i++){
    lda[i].DevStatus = 0; // init to no devices connected
    lda[i].SerialNumber = 0; // clear the serial number
    lda[i].ModelName[0] = 0; // put a null string in each model name field
  }

  usb_init();
  if (DEBUG_OUT > 0)  printf("library version %s\r\n", fnLDA_LibVersion());
}

void fnLDA_SetTestMode(bool testmode) {
  TestMode = testmode;
}

int fnLDA_GetNumDevices() {
  int retval = 0;
  int NumDevices = 0;
  int i;
  
  // See how many devices we can find, or have found before
  if (TestMode){
    // construct a fake device

    lda[1].SerialNumber = 55102;
    lda[1].DevStatus = lda[1].DevStatus | DEV_CONNECTED;
    lda[1].idType = 1;
    lda[1].MinAttenuation = 0;		// 0db is always the minimum
    lda[1].MaxAttenuation = 1260;	// 63 db in .05db units
    lda[1].MinAttenStep = 10;		// .5db resolution of the attenuator
    lda[1].UnitScale = 5;		// for consistency...

    strcpy (lda[1].ModelName, "LDA-102");

    // construct a second fake device
    lda[2].SerialNumber = 55602;
    lda[2].DevStatus = lda[2].DevStatus | DEV_CONNECTED;
    lda[2].idType = 2;
    lda[2].MinAttenuation = 0;		// 0db is always the minimum
    lda[2].MaxAttenuation = 1260;	// 63 db in .05db units
    lda[2].MinAttenStep = 10;		// .5db resolution of the attenuator
    lda[1].UnitScale = 5;		// for consistency...
    
    strcpy (lda[2].ModelName, "LDA-602");

    retval = 2;
    
  } else {
    // go look for some real hardware
    FindVNXDevices();

    // Total up the number of devices we have
    for (i = 0; i < MAXDEVICES; i++){
      if (lda[i].DevStatus & DEV_CONNECTED) NumDevices++; 
    }
    retval = NumDevices;

  }
  return retval;
}

int fnLDA_GetDevInfo(DEVID *ActiveDevices) {
  int i;
  int NumDevices = 0;
  
  if ( ActiveDevices == NULL) return 0; // bad array pointer, no place to put the DEVIDs
  
  for (i = 1; i < MAXDEVICES; i++){ // NB -- we never put an active device in lda[0] - so DEVIDs start at 1
    if (lda[i].DevStatus & DEV_CONNECTED) {
      ActiveDevices[NumDevices] = i;
      NumDevices++;
    }
  }
  
  return NumDevices;
}

int fnLDA_GetModelName(DEVID deviceID, char *ModelName) {
  int NumChars = 0;

  if (deviceID >= MAXDEVICES){
    return 0;
  }

  NumChars = strlen(lda[deviceID].ModelName);
  // If NULL result pointer, just return the number of chars in the name
  if ( ModelName == NULL) return NumChars;
  strcpy(ModelName, lda[deviceID].ModelName);

  return NumChars;
}

int fnLDA_InitDevice(DEVID deviceID) {

  if ((deviceID >= MAXDEVICES) || (deviceID == 0)) {
    return INVALID_DEVID;
  }
  
  if (TestMode)
    lda[deviceID].DevStatus = lda[deviceID].DevStatus | DEV_OPENED;
  else {
    // Go ahead and open a handle to the hardware
    if (VNXOpenDevice(deviceID))//VNXOpenDevice returns 0 if the open succeeded
      return DEVICE_NOT_READY;

    // Get the rest of the device parameters from the device
    if (DEBUG_OUT > 0) printf("Time to start getting parameters from device %d\r\n", deviceID);
    if (!GetAttenuation(deviceID)) {
	return BAD_HID_IO;
    }

  	if (DEBUG_OUT > 1) printf("about to get ramp start\r\n");  
    if (!GetRampStart(deviceID)) {
      return BAD_HID_IO;
    }

  	if (DEBUG_OUT > 1) printf("about to get ramp step\r\n");  
    if (!GetRampStep(deviceID)) {
      return BAD_HID_IO;
    }

  	if (DEBUG_OUT > 1) printf("about to get ramp end\r\n");   
    if (!GetRampEnd(deviceID)) {
      return BAD_HID_IO;
    }

  	if (DEBUG_OUT > 1) printf("about to get dwell time\r\n");  
    if (!GetDwellTime(deviceID)) {
      return BAD_HID_IO;
    }
 	printf("about to get idle time\r\n");   
    if (!GetIdleTime(deviceID)) {
      return BAD_HID_IO;
    }

  	if (DEBUG_OUT > 1) printf("about to get RF On\r\n");   
    if (!GetRF_On(deviceID)) {
      return BAD_HID_IO;
    }

  	if (DEBUG_OUT > 1) printf("about to get Working Frequency\r\n");
    if (lda[deviceID].DevStatus & DEV_HIRES) {		// for HiRes devices get the current working frequency
	 if (!GetFrequency(deviceID)) {
	   return BAD_HID_IO;
	 }
    }  
    
  } // end of real device open process case

  // if we got here everything worked OK
  return STATUS_OK;
}

int fnLDA_CloseDevice(DEVID deviceID) {
  
  if (deviceID >= MAXDEVICES)
    return INVALID_DEVID;
  
  if (!CheckDeviceOpen(deviceID))
    return DEVICE_NOT_READY;

  if (TestMode)
    lda[deviceID].DevStatus = lda[deviceID].DevStatus & ~DEV_OPENED;
  else {

    // Go ahead and close this hardware - the first step is to stop its read thread
    lda[deviceID].thread_command = THREAD_EXIT;
    
    // The thread handler will close the device. We'll wait up to 1 second then give up.
    int retries;
    retries = 10;
    while (retries && (lda[deviceID].thread_command != THREAD_DEAD)) {
      usleep(100000); /* wait 100 ms */
      retries--;
    }
    if (DEBUG_OUT > 0) printf("After telling the thread to close, we have thread_command=%d retries=%d\r\n", lda[deviceID].thread_command, retries);
    lda[deviceID].thread_command = THREAD_IDLE;

    // Mark it closed in our list of devices
    lda[deviceID].DevStatus = lda[deviceID].DevStatus & ~DEV_OPENED;
  }

  return STATUS_OK;

}

int fnLDA_GetSerialNumber(DEVID deviceID) {
  if (deviceID >= MAXDEVICES)
    return 0;
  
  return lda[deviceID].SerialNumber;
}


// Functions to set parameters

// Set the attenuator - the function now uses .05db units
LVSTATUS fnLDA_SetAttenuation(DEVID deviceID, int attenuation) {
	
	int tmp_attenuation = 0;
	
	if (deviceID >= MAXDEVICES)
	  return INVALID_DEVID;

	if (!CheckDeviceOpen(deviceID))
	  return DEVICE_NOT_READY;

	LockDev(deviceID, TRUE);

	int old_attenuation = lda[deviceID].Attenuation;
	
	if ((attenuation >= lda[deviceID].MinAttenuation) && (attenuation <= lda[deviceID].MaxAttenuation)) {
	  lda[deviceID].Attenuation = attenuation;
	  if (TestMode){
	    LockDev(deviceID, FALSE);
	    return STATUS_OK;		// in test mode we update our internal variables, but don't talk to the real HW
	  }
	} else {
	  LockDev(deviceID, FALSE);
	  return BAD_PARAMETER;
	}

	// the attenuation value is OK, lets send it to the hardware
	
	if (lda[deviceID].UnitScale > 0)
		tmp_attenuation = lda[deviceID].Attenuation / lda[deviceID].UnitScale;

	unsigned char *ptr = (unsigned char *) &tmp_attenuation;

	if (!SendReport(deviceID, VNX_PWR | VNX_SET, ptr, 4)) {
	  lda[deviceID].Attenuation = old_attenuation;
	  LockDev(deviceID, FALSE);
	  return BAD_HID_IO;
	}

	LockDev(deviceID, FALSE);
	return STATUS_OK;
}


// Set the attenuation ramp start value
LVSTATUS fnLDA_SetRampStart(DEVID deviceID, int rampstart) {
	int tmp_rampstart = 0;
	
	if (deviceID >= MAXDEVICES)
	  return INVALID_DEVID;

	if (!CheckDeviceOpen(deviceID))
	  return DEVICE_NOT_READY;

	int old_rampstart = lda[deviceID].RampStart;

	if ((rampstart >= lda[deviceID].MinAttenuation) && (rampstart <= lda[deviceID].MaxAttenuation)) {
	  lda[deviceID].RampStart = rampstart;
	  if (TestMode){
	    return STATUS_OK;		// in test mode we update our internal variables, but don't talk to the real HW
	  }
	} else {
	  return BAD_PARAMETER;
	}
	
	// the ramp start value is OK, lets send it to the hardware
	if (lda[deviceID].UnitScale > 0)
		tmp_rampstart = lda[deviceID].RampStart / lda[deviceID].UnitScale;
		
	unsigned char *ptr = (unsigned char *) &tmp_rampstart;
	
	if (!SendReport(deviceID, VNX_ASTART | VNX_SET, ptr, 4)){
	  lda[deviceID].RampStart = old_rampstart;	
	  return BAD_HID_IO;
	}

	return STATUS_OK;
}

// Set the attenuation ramp end value
LVSTATUS fnLDA_SetRampEnd(DEVID deviceID, int rampstop) {
	int tmp_rampstop = 0;
		
	if (deviceID >= MAXDEVICES)
	  return INVALID_DEVID;

	if (!CheckDeviceOpen(deviceID))
	  return DEVICE_NOT_READY;

	int old_rampstop = lda[deviceID].RampStop;
	
	if ((rampstop >= lda[deviceID].MinAttenuation) && (rampstop <= lda[deviceID].MaxAttenuation)){
	  
	  lda[deviceID].RampStop = rampstop;
	  if (TestMode)
	    return STATUS_OK;		// in test mode we update our internal variables, but don't talk to the real HW
	} else {
	  return BAD_PARAMETER;
	}
	// the ramp end value is OK, lets send it to the hardware
	if (lda[deviceID].UnitScale > 0)
		tmp_rampstop = lda[deviceID].RampStop / lda[deviceID].UnitScale;

	unsigned char *ptr = (unsigned char *) &tmp_rampstop;

	if (!SendReport(deviceID, VNX_ASTOP | VNX_SET, ptr, 4)) {
	  lda[deviceID].RampStop = old_rampstop;	
	  return BAD_HID_IO;
	}

	return STATUS_OK;
}

// Set the attenuation ramp step size for the first phase
LVSTATUS fnLDA_SetAttenuationStep(DEVID deviceID, int attenuationstep) {
	int tmp_attenuationstep = 0;
		
	if (deviceID >= MAXDEVICES)
	  return INVALID_DEVID;

	if (!CheckDeviceOpen(deviceID))
	  return DEVICE_NOT_READY;

	int old_attenuationstep = lda[deviceID].AttenuationStep;

	if (attenuationstep < (lda[deviceID].MaxAttenuation - lda[deviceID].MinAttenuation)) {
	  lda[deviceID].AttenuationStep = attenuationstep;
	  if (TestMode)
	    return STATUS_OK;		// in test mode we update our internal variables, but don't talk to the real HW
	} else {
	  return BAD_PARAMETER;
	}
	// the attenuation ramp step value is OK, lets send it to the hardware
	if (lda[deviceID].UnitScale > 0)
		tmp_attenuationstep = lda[deviceID].AttenuationStep / lda[deviceID].UnitScale;

	unsigned char *ptr = (unsigned char *) &tmp_attenuationstep;

	if (!SendReport(deviceID, VNX_ASTEP | VNX_SET, ptr, 4)) {
		lda[deviceID].AttenuationStep = old_attenuationstep;	
		return BAD_HID_IO;
	}

	return STATUS_OK;
}

// Set the working frequency for HiRes LDA devices, frequency is in 100KHz units
LVSTATUS fnLDA_SetWorkingFrequency(DEVID deviceID, int frequency) {
	int tmp_frequency = 0;
	
	if (deviceID >= MAXDEVICES)
	  return INVALID_DEVID;

	if (!CheckDeviceOpen(deviceID))
	  return DEVICE_NOT_READY;
  
	if (!CheckHiRes(deviceID)) return BAD_PARAMETER;	// only HiRes devices have a working frequency
	
	int old_frequency = lda[deviceID].WorkingFrequency;

	if ((frequency >= lda[deviceID].MinFrequency) && (frequency <= lda[deviceID].MaxFrequency)) {
	  lda[deviceID].WorkingFrequency = frequency;
	  if (TestMode)
	    return STATUS_OK;		// in test mode we update our internal variables, but don't talk to the real HW
	} else {
	  return BAD_PARAMETER;
	}
	
	// the working frequency value is OK, lets send it to the hardware
	tmp_frequency = frequency;
	unsigned char *ptr = (unsigned char *) &tmp_frequency;

	if (!SendReport(deviceID, VNX_FREQUENCY | VNX_SET, ptr, 4)) {
	  lda[deviceID].WorkingFrequency = old_frequency;	
	  return BAD_HID_IO;
	}

	return STATUS_OK;
}


// Set the time to dwell at each step on the first phase of the ramp
LVSTATUS fnLDA_SetDwellTime(DEVID deviceID, int dwelltime) {
	if (deviceID >= MAXDEVICES)
	  return INVALID_DEVID;

	if (!CheckDeviceOpen(deviceID))
	  return DEVICE_NOT_READY;
	
	int old_dwelltime = lda[deviceID].DwellTime;

	if (dwelltime >= VNX_MIN_DWELLTIME) {
	  lda[deviceID].DwellTime = dwelltime;
	  if (TestMode)
	    return STATUS_OK;		// in test mode we update our internal variables, but don't talk to the real HW
	} else {
	  return BAD_PARAMETER;
	}

	// the dwell time value is OK, lets send it to the hardware
	unsigned char *ptr = (unsigned char *) &lda[deviceID].DwellTime;

	if (!SendReport(deviceID, VNX_ADWELL | VNX_SET, ptr, 4)) {
	  lda[deviceID].DwellTime = old_dwelltime;	
	  return BAD_HID_IO;
	}

	return STATUS_OK;
}

// Set the time to wait at the end of the ramp
LVSTATUS fnLDA_SetIdleTime(DEVID deviceID, int idletime) {
	if (deviceID >= MAXDEVICES)
	  return INVALID_DEVID;

	if (!CheckDeviceOpen(deviceID))
	  return DEVICE_NOT_READY;

	int old_idletime = lda[deviceID].IdleTime;

	if (idletime >= VNX_MIN_DWELLTIME) {
	  lda[deviceID].IdleTime = idletime;
	  if (TestMode)
	    return STATUS_OK;		// in test mode we update our internal variables, but don't talk to the real HW
	} else {
	  return BAD_PARAMETER;
	}

	// the idle time value is OK, lets send it to the hardware
	unsigned char *ptr = (unsigned char *) &lda[deviceID].IdleTime;

	if (!SendReport(deviceID, VNX_AIDLE | VNX_SET, ptr, 4)) {
	  lda[deviceID].IdleTime = old_idletime;	
	  return BAD_HID_IO;
	}

	return STATUS_OK;
}




// Set the RF output on or off (not supported by all attenuators)
LVSTATUS fnLDA_SetRFOn(DEVID deviceID, bool on) {
	if (deviceID >= MAXDEVICES) 
	  return INVALID_DEVID;
	
	if (!CheckDeviceOpen(deviceID)) {
	  return DEVICE_NOT_READY;

	char VNX_command[] = {0, 0, 0, 0};

	if (on) {
	  lda[deviceID].Modebits = lda[deviceID].Modebits & ~MODE_RFON;
	  lda[deviceID].Modebits = lda[deviceID].Modebits | MODE_RFON;
	  VNX_command[0] = 1;
	} else 	{
	  lda[deviceID].Modebits = lda[deviceID].Modebits & ~MODE_RFON;
	  VNX_command[0] = 0;
	}

	if (TestMode)
	  return STATUS_OK;		// in test mode we update our internal variables, but don't talk to the real HW
	}

	//qqq	if (!SendReport(deviceID, VNX_RFMUTE | VNX_SET, VNX_command, 1))
	  return BAD_HID_IO;
	
	return STATUS_OK;
}


// Set the ramp direction -- "up" is TRUE to ramp upwards
LVSTATUS fnLDA_SetRampDirection(DEVID deviceID, bool up) {
	if (deviceID >= MAXDEVICES)
	  return INVALID_DEVID;

	if (!CheckDeviceOpen(deviceID))
	  return DEVICE_NOT_READY;

	if (up)
	  lda[deviceID].Modebits = lda[deviceID].Modebits & ~SWP_DIRECTION;	// ramp or sweep direction up (bit == 0)
	else
	  lda[deviceID].Modebits = lda[deviceID].Modebits | SWP_DIRECTION;	// ramp or sweep direction downwards


	return STATUS_OK;
}

// Set the ramp mode -- mode = TRUE for repeated ramp, FALSE for one time ramp
LVSTATUS fnLDA_SetRampMode(DEVID deviceID, bool mode) {
	if (deviceID >= MAXDEVICES)
	  return INVALID_DEVID;

	if (!CheckDeviceOpen(deviceID))
	  return DEVICE_NOT_READY;

	if (mode) {
	  lda[deviceID].Modebits = lda[deviceID].Modebits | SWP_CONTINUOUS;		// Repeated ramp or sweep
	  lda[deviceID].Modebits = lda[deviceID].Modebits & ~SWP_ONCE;
	} else {
	  lda[deviceID].Modebits = lda[deviceID].Modebits | SWP_ONCE;			// one time ramp or sweep
	  lda[deviceID].Modebits = lda[deviceID].Modebits & ~SWP_CONTINUOUS;
	}

	return STATUS_OK;
}

// Start the ramp
LVSTATUS fnLDA_StartRamp(DEVID deviceID, bool go) {
	if (deviceID >= MAXDEVICES)
	  return INVALID_DEVID;

	if (!CheckDeviceOpen(deviceID))
	  return DEVICE_NOT_READY;

	char VNX_ramp[] = {0, 0, 0, 0};

	if (go)
	  VNX_ramp[0] = (char) lda[deviceID].Modebits & MODE_SWEEP;
	else
	  VNX_ramp[0] = 0;

	if (TestMode)
	  return STATUS_OK;		// in test mode we update our internal variables, but don't talk to the real HW

	// printf(" sending a ramp command = %x\n", VNX_sweep[0] );

	if (!SendReport(deviceID, VNX_SWEEP | VNX_SET, VNX_ramp, 1))
	  return BAD_HID_IO;

	return STATUS_OK;
}

// Save the user settings to flash for autonomous operation
LVSTATUS fnLDA_SaveSettings(DEVID deviceID) {
  if (deviceID >= MAXDEVICES)
    return INVALID_DEVID;

  if (!CheckDeviceOpen(deviceID))
    return DEVICE_NOT_READY;

  if (TestMode)
    return STATUS_OK;		// in test mode we update our internal variables, but don't talk to the real HW

  char VNX_savesettings[] = {0x42, 0x55, 0x31}; //three byte key to unlock the user protection.

  if (!SendReport(deviceID, VNX_SAVEPAR | VNX_SET, VNX_savesettings, 3))
    return BAD_HID_IO;
  
  return STATUS_OK;
}

// ------------- Functions to get parameters --------------------- 

// Get the attenuation setting in .05db units
int fnLDA_GetAttenuation(DEVID deviceID) {
  if (deviceID >= MAXDEVICES)
    return INVALID_DEVID;
  
  if (!CheckDeviceOpen(deviceID))
    return DEVICE_NOT_READY;
  
  return lda[deviceID].Attenuation;
}

// Get the ramp start attenuation level
int fnLDA_GetRampStart(DEVID deviceID) {
  if (deviceID >= MAXDEVICES)
    return INVALID_DEVID;
  
  if (!CheckDeviceOpen(deviceID))
    return DEVICE_NOT_READY;
  
  return lda[deviceID].RampStart;
}

// Get the attenuation at the end of the ramp
int fnLDA_GetRampEnd(DEVID deviceID) {
  if (deviceID >= MAXDEVICES)
    return INVALID_DEVID;

  if (!CheckDeviceOpen(deviceID))
    return DEVICE_NOT_READY;

  return lda[deviceID].RampStop;
}

// Get the time to dwell at each step along the first phase of the ramp
int fnLDA_GetDwellTime(DEVID deviceID) {

  if (deviceID >= MAXDEVICES)
    return INVALID_DEVID;

  if (!CheckDeviceOpen(deviceID))
    return DEVICE_NOT_READY;

  return lda[deviceID].DwellTime;
}

// Get the idle time to wait at the end of the ramp
int fnLDA_GetIdleTime(DEVID deviceID) {

  if (deviceID >= MAXDEVICES)
    return INVALID_DEVID;

  if (!CheckDeviceOpen(deviceID))
    return DEVICE_NOT_READY;

  return lda[deviceID].IdleTime;
}


// Get the size of the attenuation step for the first phase of the ramp in .05db units
int fnLDA_GetAttenuationStep(DEVID deviceID) {

  if (deviceID >= MAXDEVICES)
    return INVALID_DEVID;

  if (!CheckDeviceOpen(deviceID))
    return DEVICE_NOT_READY;

  return lda[deviceID].AttenuationStep;
}

// Get the working frequency for HiRes Attenuators in 100 KHz units
int fnLDA_GetWorkingFrequency(DEVID deviceID) {

  if (deviceID >= MAXDEVICES)
    return INVALID_DEVID;

  if (!CheckDeviceOpen(deviceID))
    return DEVICE_NOT_READY;

  if (!CheckHiRes(deviceID)) return BAD_PARAMETER;	// only HiRes devices have a working frequency

  return lda[deviceID].WorkingFrequency;
}


// Get the state of the RF output - on or off
int fnLDA_GetRF_On(DEVID deviceID) {

  if (deviceID >= MAXDEVICES)
    return INVALID_DEVID;

  if (!CheckDeviceOpen(deviceID))
    return DEVICE_NOT_READY;

  if (lda[deviceID].Modebits & MODE_RFON)
    return 1;
  else
    return 0;
}

// Get the maximum attenuation in .05db units
int fnLDA_GetMaxAttenuation(DEVID deviceID) {

  if (deviceID >= MAXDEVICES)
    return INVALID_DEVID;

  return lda[deviceID].MaxAttenuation;
}

// Get the minimum attenuation in .05db units
int fnLDA_GetMinAttenuation(DEVID deviceID) {

  if (deviceID >= MAXDEVICES)
    return INVALID_DEVID;

  return lda[deviceID].MinAttenuation;
}

// Get the resolution of the attenuator, in .05db units
int fnLDA_GetDevResolution(DEVID deviceID) {

  if (deviceID >= MAXDEVICES)
    return INVALID_DEVID;

  return lda[deviceID].MinAttenStep;
}


