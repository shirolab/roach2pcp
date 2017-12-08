Readme file for the new Python Roach control software for large arrays of kinetic inductance detectors. 

This code is basically a re-factoring of the original python scripts written by Sam Gordon (ASU) and Sam Rowe (Cardiff) to interface to the Roach systems. The aim of this work is to develop a set of software routines suitable for taking on-sky data at the telescope. To that end, improvements over the current software will target highly reliable, well documented code with detailed logging implementations and on-the-fly debugging capabilities. 

Most of the code of the individual functions is borrowed from the original code. The major difference is the structuring, and implementation of support for multiple roach subsystems. 

Development begins…

==================================================================================================
20171207 Update
We now have a number of small scripts written to test the basic implementation of new functions. An attempt will be made to document the use cases for each of them below:
	
- test_data_save_ncdf.py
	- simple script that writes some dummy data to a netcdf file. The goal of this script was to determine the netcdf4-python structure and syntax for writing to a netCDF file. 
	- The script generates fake data in a loop, in a similar fashion to that expected with the collection of Roach packets. The sample rate is currently hard coded, and can be modified by changing the number in the time.sleep() function on line 72. The parameter “chunksize” (line 66), is the length (with units of ‘packets’) of the buffered data before it is synced to the file. Simple %timeit tests show that this is more efficient that writing each packet to disk immediately as it reduces by a factor of “chunksize” the overhead associated with a disk write operation. 

	- To run the script, in a terminal, cd into the readout_new directory, and run “python test_data_save_ncdf.py”. This open (and, currently, overwrite if it exists) a file called “testdatawrite_ncdf3.nc” in the “run” directory. In addition, the data that is being saved to the file is also printed to the terminal, along with a message indicating when the write buffer is being flushed.

==================================================================================================
