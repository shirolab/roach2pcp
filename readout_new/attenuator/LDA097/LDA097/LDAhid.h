
// --------------------------------- VNX_atten.h -------------------------------------------
//
//	Include file for LabBrick attenuator API
//
// (c) 2011 by Vaunix Corporation, all rights reserved
//
//	HME Version 1.0 based on RD Version 1.0 for Windows
//	RD	updated for LDA-302 family
//	RD	updated to support High Res LDA devices
//-----------------------------------------------------------------------------


#define VNX_MIN_DWELLTIME 1
#define STATUS_PROFILE_ACTIVE 0x80	// MASK: A profile is playing
#define STATUS_RF_ON 0x8		// MASK: The RF HW is on

// Bit masks and equates for the Sweep command byte (stored in Sweep_mode, and reported also in Status)									
#define SWP_DIRECTION		0x04	// MASK: bit = 0 for sweep or ramp up, 1 for sweep or ramp down 
#define SWP_CONTINUOUS		0x02	// MASK: bit = 1 for continuous sweeping
#define SWP_ONCE		0x01	// MASK: bit = 1 for single sweep
#define SWP_BIDIR		0x10	// MASK: bit = 0 for ramp style sweep, 1 for triangle style sweep

// ----------- Profile Control -----------
#define PROFILE_ONCE	1		// play the profile once
#define PROFILE_REPEAT	2		// play the profile repeatedly
#define PROFILE_OFF	0		// stop the profile

// HID report equates
#define HR_BLOCKSIZE 6			// size of the block of bytes buffer in our HID report


#define HID_REPORT_LENGTH 8 		// use an 8 byte report..

typedef struct 
{
  char reportid;
  char status;
  char count;
  char byteblock[HR_BLOCKSIZE];
} HID_REPORT1;

typedef struct 
{
  char reportid;
  char command;
  char count;
  char byteblock[HR_BLOCKSIZE];
} HID_REPORT_OUT;

// Misc commands to send to the device
// For the input reports the first byte is the status, for the output it is the command. The high bit sets the 
// direction.
//
//	count is the number of valid bytes in the byteblock array
// 	byteblock is an array of bytes which make up the value of the command's argument or arguments.
//
// For result reports the command portion of the status byte is equal to the command sent if the command was successful.
// status byte layout:

// Bit0 - Bit5 = command result, equal to command if everything went well
// Bit6 = --reserved--
// Bit7 = --reserved--

// All sweep related data items are DWORD (unsigned) quantities, stored in normal Microsoft byte order.
// Dwell time is a DWORD (unsigned)


// Misc commands to send to the device

#define VNX_SET			0x80
#define VNX_GET			0x00	// the set and get bits are or'd into the msb of the command byte


// ---------------------- Attenuator commands ------------------------
#define VNX_PWR			0x0D	// power output setting, relative to calibrated value - adds to calibrated
						// attenuator setting. It is a byte, with the attenuation expressed in HW
						// specific steps.
						
#define VNX_FREQUENCY		0x04	// working frequency in 100Khz units
// ----------------- Attenuator ramp commands ------------------------
#define VNX_SWEEP		0x09	// command to start/stop sweep, data = 01 for single sweep, 00 to stop
				// sweeping, and 02 for continuous sweeping.

#define VNX_RFMUTE		0x0A	// enable or disable RF output, byte = 01 to enable, 00 to disable

#define VNX_ASTART		0x30	// initial value for attenuation ramp

#define VNX_ASTOP		0x31	// final value for attenuation ramp

#define VNX_ASTEP		0x32	// step size for attenuation ramp
#define VNX_ASTEP2		0x38	// step size for the second phase of the ramp

#define VNX_ADWELL		0x33	// dwell time for each attenuation step
#define VNX_ADWELL2		0x37	// dwell time for the second phase of the ramp

#define VNX_AIDLE		0x36	// idle time between attenuation ramps in milliseconds
#define VNX_AHOLD		0x39	// hold time between phase 1 and 2

#define VNX_SETPROFILE		0x3A	// set/get profile values, first byte is unused
					// second data byte is the index (0 based)
					// the third is the attenuation value for that profile entry
									
#define VNX_PROFILECOUNT	0x3B	// number of elements in the profile, 1 to PROFILE_MAX = 100

#define VNX_PROFILEDWELL	0x3C	// dwell time for each profile element

#define VNX_PROFILEIDLE		0x3D	// idle time at the end of each repeating profile 

#define VNX_SAVEPAR		0x0C	// command to save user parameters to flash, data bytes must be
					// set to 0x42, 0x55, 0x31 as a key to enable the flash update
					// all of the above settings are saved (RF Mute State, Attenuation, 
					// sweep parameters, etc.

#define VNX_MINATTEN		0x34	// get the minimum attenuation level which is 0 for every case now

#define VNX_MAXATTEN		0x35	// get the maximum attenuation level which is 252 or 63db for both products now

#define VNX_GETSERNUM		0x1F	// get the serial number, value is a DWORD

#define VNX_MODELNAME		0x22	// get (no set allowed) the device's model name string -- last 6 chars only

#define VNX_DEFAULTS		0x0F	// restore all settings to factory default
					// ASTART = 0 = MINATTEN, ASTOP = MAXATTEN
					// ADWELL = 1000 = 1 second, ASTEP = 2 = .5db, AIDLE = 0 
					
// ------------------------ Hi Res Attenuator Commands --------------------------------
#define VNX_MINFREQUENCY	0x20	// get (no set allowed) the device's minimum working frequency
#define VNX_MAXFREQUENCY	0x21	// get (no set allowed) the device's maximum working frequency

//------------------------- Status Report ID Byte -------------------------------------
#define VNX_STATUS		0x0E	// Not really a command, but the status byte value for periodic status reports.
#define VNX_HRSTATUS		0x52	// status report used by HiRes

// ----------- Global Equates ------------
#define MAXDEVICES 64
#define MAX_MODELNAME 32
#define PROFILE_MAX 100

// ----------- Data Types ----------------

#define DEVID unsigned int

typedef struct
{
  int DevStatus;
  int WorkingFrequency;
  int MinFrequency;
  int MaxFrequency;
  int Attenuation;
  int MinAttenuation;
  int MaxAttenuation;			// maximum attenuation in .05 db units
  int MinAttenStep;			// replaces DevResolution, smallest attenuation step in .05 db units
  int RampStart;
  int RampStop;
  int AttenuationStep;			// ramp step size for the first phase of the ramp
  int AttenuationStep2;			// ramp step size for second phase of the ramp 
  int UnitScale;			// size of hardware unit in .05 db units ( .25db = 5, .05db = 1. .5db = 10, 1db = 20)
  int DwellTime;
  int DwellTime2;
  int IdleTime;
  int HoldTime;
  int ProfileIndex;
  int Modebits;
  int SerialNumber;
  char ModelName[MAX_MODELNAME];
  int Profile[PROFILE_MAX];
  /* so we can find this device again later */
  unsigned int idVendor;
  unsigned int idProduct;
  unsigned int idType;
  char Serialstr[16];
  char thread_command;
  char sndbuff[8];
  char rcvbuff[24];
  char decodewatch;
  int MyDevID;

} LDAPARAMS;

// ----------- Mode Bit Masks ------------

#define MODE_RFON 		0x00000010 	// bit is 1 for RF on, 0 if RF is off
#define MODE_INTREF 		0x00000020 	// bit is 1 for internal osc., 0 for external reference
#define MODE_SWEEP 		0x0000000F 	// bottom 4 bits are used to keep the sweep control bits

#define MODE_PWMON 		0x00000100 	// we keep a copy of the PWM control bits here, 1 for int PWM on
#define MODE_EXTPWM 		0x00000200 	// 1 for ext. PWM input enabled
#define PWM_MASK 		0x00000300

// ----------- Command Equates -----------

// Status returns for commands
#define LVSTATUS unsigned int

#define STATUS_OK 0
#define BAD_PARAMETER  		0x80010000 	// out of range input -- frequency outside min/max etc.
#define BAD_HID_IO     		0x80020000
#define DEVICE_NOT_READY  	0x80030000 	// device isn't open, no handle, etc.

// Status returns for DevStatus

#define INVALID_DEVID 		0x80000000 	// MSB is set if the device ID is invalid
#define DEV_CONNECTED 		0x00000001 	// LSB is set if a device is connected
#define DEV_OPENED 		0x00000002 	// set if the device is opened
#define SWP_ACTIVE 		0x00000004 	// set if the device is sweeping
#define SWP_UP 			0x00000008 	// set if the device is sweeping up in frequency
#define SWP_REPEAT 		0x00000010 	// set if the device is in continuous sweep mode
#define SWP_BIDIRECTIONAL	0x00000020	// set if the device is in bi-directional ramp mode
#define PROFILE_ACTIVE		0x00000040	// set if a profile is playing

// Internal values in DevStatus
#define DEV_LOCKED   		0x00002000 	// set if we don't want read thread updates of the device parameters
#define DEV_RDTHREAD   		0x00004000 	// set when the read thread is running
#define DEV_V2FEATURES		0x00008000	// set for devices with V2 feature sets
#define DEV_HIRES		0x00010000	// set for HiRes devices

void fnLDA_Init(void);

void fnLDA_SetTestMode(bool testmode);
int fnLDA_GetNumDevices();
int fnLDA_GetDevInfo(DEVID *ActiveDevices);
int fnLDA_GetModelName(DEVID deviceID, char *ModelName);
int fnLDA_InitDevice(DEVID deviceID);
int fnLDA_CloseDevice(DEVID deviceID);
int fnLDA_GetSerialNumber(DEVID deviceID);

LVSTATUS fnLDA_SetAttenuation(DEVID deviceID, int attenuation);
LVSTATUS fnLDA_SetRampStart(DEVID deviceID, int rampstart);
LVSTATUS fnLDA_SetRampEnd(DEVID deviceID, int rampstop);
LVSTATUS fnLDA_SetAttenuationStep(DEVID deviceID, int attenuationstep);
LVSTATUS fnLDA_SetDwellTime(DEVID deviceID, int dwelltime);
LVSTATUS fnLDA_SetIdleTime(DEVID deviceID, int idletime);

LVSTATUS fnLDA_SetWorkingFrequency(DEVID deviceID, int frequency);

LVSTATUS fnLDA_SetRFOn(DEVID deviceID, bool on);

LVSTATUS fnLDA_SetRampDirection(DEVID deviceID, bool up);
LVSTATUS fnLDA_SetRampMode(DEVID deviceID, bool mode);
LVSTATUS fnLDA_StartRamp(DEVID deviceID, bool go);

LVSTATUS fnLDA_SaveSettings(DEVID deviceID);

int fnLDA_GetAttenuation(DEVID deviceID);
int fnLDA_GetRampStart(DEVID deviceID);
int fnLDA_GetRampEnd(DEVID deviceID);
int fnLDA_GetDwellTime(DEVID deviceID);
int fnLDA_GetIdleTime(DEVID deviceID);
int fnLDA_GetWorkingFrequency(DEVID deviceID);

int fnLDA_GetAttenuationStep(DEVID deviceID);
int fnLDA_GetRF_On(DEVID deviceID);

int fnLDA_GetMaxAttenuation(DEVID deviceID);
int fnLDA_GetMinAttenuation(DEVID deviceID);
int fnLDA_GetDevResolution(DEVID deviceID);

char* fnLDA_perror(LVSTATUS status);
char* fnLDA_LibVersion(void);
