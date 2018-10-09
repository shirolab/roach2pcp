#include <linux/hid.h>	/* AK: Changed include for modern linux */
#include <stdbool.h>	/* AK: Added include for 'bool' type */
#include <stdio.h>
#include <unistd.h>   	/* AK: Added include for error-free getlogin(). */
#include "LDAhid.h"
#include <math.h>

#define FALSE 0
#define TRUE !FALSE

#define PROFILETIME 60  /* length of a profile test in seconds */

/* function prototypes */
void profileSine(int attenmax);
void profileTriangle(int attenmax);
void profileSquare(int attenmax);
void profileShow(int height);

/* globals */
unsigned int profile[PROFILETIME]; /* storage for an attenuation profile */


/* code begins here */
int main (int argc, char *argv[]) {
  int nDevices, nActive;
  int i, j, result, status;
  int powerlevel;
  char cModelName[32];
  char c;
  char *username;
  DEVID activeDevices[MAXDEVICES];
  bool realhardware;

  /* AK: Added <unistd.h> to includes to avoid seg fault on getlogin(). */
  username = getlogin(); 

	    printf("Hi %s,\r\n", username);

  if (0 != strcmp(username, "root")) {
    printf("Hi %s,\r\n", username);
    printf("Accessing USB ports on a Linux machine may require root level\r\n");
    printf("access. You are not logged in as root. You may be able to\r\n");
    printf("proceed if you have used 'chmod' to change the access mode\r\n");
    printf("of the appropriate devices in /dev/bus/usb. That requires\r\n");
    printf("root access also. We'll continue, but if you don't see your\r\n");
    printf("LDA devices or no data can be read from or written to them,\r\n");
    printf("that's probably the problem. su to root and try again.\r\n\r\n");
    printf("Try running with 'sudo', or become root by running 'su' before.\r\n\r\n");
	printf("You can use udev rules to allow access to USB devices by user processes.\r\n\r\n");
    
  }
  fnLDA_Init();
  /* If you have actual hardware attached, set this to TRUE. Setting to FALSE will run in test mode */
  realhardware = TRUE;
  fnLDA_SetTestMode(!realhardware);
start_over:
  nDevices = fnLDA_GetNumDevices();
  printf("LDA test/demonstration program using library version %s\r\n\r\n", fnLDA_LibVersion());
  if (0 == nDevices) {
    printf("No Vaunix LDA devices located. Would you like to run in test mode? "); fflush(0);
    c = getchar();
    if ('Y' == (c & 0xdf)) {
      printf("\r\nSwitching to test mode.\r\n");
      realhardware = FALSE;
      fnLDA_Init();
      fnLDA_SetTestMode(!realhardware);
      nDevices = fnLDA_GetNumDevices();
    }
  }
  printf("Found %d devices\r\n", nDevices);

  for (i=1; i<=nDevices; i++) {
    result = fnLDA_GetModelName(i, cModelName);
    printf("  Model %d is %s (%d chars)\r\n", i, cModelName, result);
  }
  printf("\r\n");
  
  nActive = fnLDA_GetDevInfo(activeDevices);
  printf("We have %d active devices\r\n", nActive);

  for (i=0; i<nActive; i++) {
    /* let's open and init each device to get the threads running */
    status = fnLDA_InitDevice(activeDevices[i]);
    printf("  Opened device %d of %d. Return status=0x%08x (%s)\r\n", activeDevices[i], nActive, status, fnLDA_perror(status));
  }

  /* the data structure is filled by polling and we need a few seconds to do that */

  for (i=0; i<nActive; i++) {
    if (i > 0) printf("\r\n");

    /* only do this if not in test mode */
    printf("  Device %d is active\r\n", activeDevices[i]);
    /* dump what we know - that we read from the hardware */
    if (realhardware) {
      printf("  GetAttenuation returned %d\r\n", result=fnLDA_GetAttenuation(activeDevices[i]));
      if (result < 0) goto device_pulled;
      printf("  GetRampStart returned %d\r\n", result=fnLDA_GetRampStart(activeDevices[i]));
      if (result < 0) goto device_pulled;
      printf("  GetRampEnd returned %d\r\n", result=fnLDA_GetRampEnd(activeDevices[i]));
      if (result < 0) goto device_pulled;
      printf("  GetDwellTime returned %d\r\n", result=fnLDA_GetDwellTime(activeDevices[i]));
      if (result < 0) goto device_pulled;
      printf("  GetIdleTime returned %d\r\n", result=fnLDA_GetIdleTime(activeDevices[i]));
      if (result < 0) goto device_pulled;

      printf("  GetAttenuationStep returned %d\r\n", result=fnLDA_GetAttenuationStep(activeDevices[i]));
      if (result < 0) goto device_pulled;
      printf("  GetRF_On returned %d\r\n", result=fnLDA_GetRF_On(activeDevices[i]));
      if (result < 0) goto device_pulled;

      printf("  GetMaxAttenuation returned %d\r\n", result=fnLDA_GetMaxAttenuation(activeDevices[i]));
      if (result < 0) goto device_pulled;
      printf("  GetMinAttenuation returned %d\r\n", fnLDA_GetMinAttenuation(activeDevices[i]));
      if (result < 0) goto device_pulled;
    }
//    printf("  Device %d is active\r\n", activeDevices[i]);
    
    status = fnLDA_GetModelName(activeDevices[i], cModelName);
    if (status < 0) goto device_pulled;
    printf("  Device %d (%s) has ", activeDevices[i], cModelName);
    status = fnLDA_GetSerialNumber(activeDevices[i]);
    if (status < 0) goto device_pulled;
    printf("  Serial number=%d\r\n", status);

    /* for every other device, alternate between a sine wave and a triangle wave */
    if (0 == i%2)
      profileSine(fnLDA_GetMaxAttenuation(activeDevices[i]));
    else
      profileTriangle(fnLDA_GetMaxAttenuation(activeDevices[i]));
    //profileShow(10);

    printf("Minimum attenuation for 5 seconds...\r\n");
    status = fnLDA_SetAttenuation(activeDevices[i], 0);
    if (status < 0) goto device_pulled;
    sleep(5);
    printf("Maximum attenuation for 5 seconds...\r\n");
    status = fnLDA_SetAttenuation(activeDevices[i], fnLDA_GetMaxAttenuation(activeDevices[i]));
    if (status < 0) goto device_pulled;
    sleep(5);
    printf("30 dB attenuation for 5 seconds...\r\n");
    status = fnLDA_SetAttenuation(activeDevices[i], 30 * 20);
    if (status < 0) goto device_pulled;
    sleep(5);
    printf("45 dB attenuation for 5 seconds...\r\n");
    status = fnLDA_SetAttenuation(activeDevices[i], 45 * 20);
    if (status < 0) goto device_pulled;
    sleep(5);
    printf("Minimum attenuation for 5 seconds...\r\n");
    status = fnLDA_SetAttenuation(activeDevices[i], 0);
    if (status < 0) goto device_pulled;
    sleep(5);

    /* now step through the profile */
    for (j=0; j<sizeof(profile); j++) {
      if (j>0) sleep(1); /* wait one second except before the first one */
      status = fnLDA_SetAttenuation(activeDevices[i], profile[j]);
      if (status < 0) goto device_pulled;
      printf("Set attenuation for device %d to %d (%.1f dB). %d seconds remain... Return status=0x%08x (%s)\r\n", activeDevices[i], profile[j], (float)profile[j]/20, PROFILETIME-j, status, fnLDA_perror(status));
    }

  }
  /* close the devices */
  for (i=0; i<nActive; i++) {
    status = fnLDA_CloseDevice(activeDevices[i]);
    printf("Closed device %d. Return status=0x%08x (%s)\r\n", activeDevices[i], status, fnLDA_perror(status));
  }
  printf("End of test\r\n");
  return 0;

device_pulled:
  printf("Replace the LDA USB plug to try again. Press Ctrl-C to exit.\r\n");
  nDevices = fnLDA_GetNumDevices();
  while (0 == nDevices) {
    nDevices = fnLDA_GetNumDevices();
  }
  goto start_over;
}

/* support functions */
void profileSine(int attenmax) {
  /* calculate values for a sine wave attenuation profile. Use the size of
     the 'profile' array and divide a full wave into that many segments. */
  int i, nsegs;
  float fi, fstart, fend, fstep;
  float ftemp;
  
  nsegs = sizeof(profile);
  printf("Making a sine wave in %d segments\r\n", nsegs);
  fstart = 0;
  fend = 2.0 * M_PI; /* 2 PI = 1 whole circle */
  fstep = (fend - fstart) / (float)nsegs;
  fi = fstart;
  for (i=0; i<nsegs; i++) {
    /* sin() results range from -1.0 to +1.0, and we want te rescale this
       to 0.0 to 1.0 */
    ftemp = (1.0 + sin(fi)) / 2.0;
    /* and now that we have a 0-1 value, multiply that by the maximum
       attenuation value */
    ftemp = ftemp * (float)attenmax;
    /* store that as the next step in the profile */
    profile[i] = (int)ftemp;
    /* we've set a value where the *attenuation* follows the curve. Now
       let's invert that so the *signal* follows. Comment this out if
       you want the attenuation to follow the instead. */
    profile[i] = attenmax - profile[i];
    /* get ready for the next one */
    fi = fi + fstep;
  }
}

void profileTriangle(int attenmax) {
  /* calculate values for a triangle attenuation profile. Use the size of
     the 'profile' array and divide a full wave into that many segments. */
  int i, nsegs;
  float fi, fstep;
  float ftemp;
  
  nsegs = sizeof(profile);
  printf("Making a triangle wave in %d segs\r\n", nsegs);
  /* the wave really has 4 parts - up to max, down to 0, down to min, up to 0
     so we'll divide into 4 pieces and then 'bounce' off of the extremes */
  fstep = 4.0 / (float)nsegs;
  fi = 0.0;
  for (i=0; i<nsegs; i++) {
    ftemp = (1.0 + fi) / 2.0;
    /* and now that we have a 0-1 value, multiply that by the maximum
       attenuation value */
    ftemp = ftemp * (float)attenmax;
    /* store that as the next step in the profile */
    profile[i] = (int)ftemp;
    /* we've set a value where the *attenuation* ramps. Now let's invert that
       so the *signal* ramps. Comment ths out if you want the attenuation
       to follow the ramp instead. */
    profile[i] = attenmax - profile[i];
    /* get ready for the next one */
    fi = fi + fstep;
    if (fi >= 1.0) {
      fi = 1.0;
      fstep = -fstep;
    }
    if (fi <= -1.0) {
      fi = -1.0;
      fstep = -fstep;
    }
  }
}

/* a little bonus profile generator - not as exciting as the other two */
void profileSquare(int attenmax) {
  /* calculate values for a square wave attenuation profile. Use the size of
     the 'profile' array and divide a full wave into that many segments. */
  int i, nsegs;

  nsegs = sizeof(profile);
  printf("Making two square waves in %d segs\r\n", nsegs);
  /* the wave really has 4 parts - max, min, max, min so we'll divide into
     4 pieces */
  for (i=0; i<nsegs; i++) {
    if ((i < (nsegs/4)) || ((i > nsegs/2) && (i < (3*nsegs)/4)))
      profile[i] = attenmax;
    else
      profile[i] = 0;
    /* we've set a value where the *attenuation* ramps. Now let's invert that
       so the *signal* ramps. Comment ths out if you want the attenuation
       to follow the ramp instead. */
    profile[i] = attenmax - profile[i];
  }
}

/* displays the profile data as a cheesy graph on the terminal output */
void profileShow(int height) {
  int i, j;
  int rl, rh, rs;

  rs = 252 / height;
  rh = 252;
  rl = rh - rs + 1;
  for (i=height; i>0; i--) {
    for (j=0; j<PROFILETIME; j++) {
      if ((profile[j] >= rl) && (profile[j] <= rh))
	printf("*");
      else
	printf(" ");
    }
    printf("\r\n");
    rh = rh - rs;
    rl = rl - rs;
    if (rl < rs) rl = 0;
  }
}
