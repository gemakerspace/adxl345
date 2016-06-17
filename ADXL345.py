import time
import spidev
import RPi.GPIO as GPIO
import numpy as np

GPIO.setmode(GPIO.BOARD)
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

spi = spidev.SpiDev()
spi.open(0,0)
spi.mode = 3

id = spi.xfer([128,0])
print 'Device ID (Should be 0xE5):\n'+str(hex(id[1])) + '\n'

# Read the offsets
xoffset = spi.xfer2([30 | 128,0])
yoffset = spi.xfer2([31 | 128,0])
zoffset = spi.xfer2([32 | 128,0])
print 'Offsets: '
print xoffset[1]
print yoffset[1]
print str(zoffset[1]) + "\n\nRead the ADXL345 at 800Hz:"

# Initialize the ADXL345
def initadxl345():
    # Enter power saving state
    spi.xfer2([0x2D, 0b00000000])
	
    #Turn Data Ready Interrupt to not generate 
    spi.xfer2([0x2E, 0b00000000])

    #Send Interrupt to INT1
    spi.xfer2([0x2F, 0b00000000])
	
    # Set data rate to 400 Hz
    spi.xfer2([0x2C, 0b00001100])

    # Enable (10 bits resolution) and +/- 8g 
    spi.xfer2([0x31, 0b00000010])

    # Enable measurement
    spi.xfer2([0x2D, 0b00001000])

    #FIFO Mode (Collect 5 samples before setting watermark intterupt)
    spi.xfer([0x38, 0b01000101])

def readadxl345():
    rx = spi.xfer2([242,0,0,0,0,0,0])
 
    out = [rx[1] | (rx[2] << 8),rx[3] | (rx[4] << 8),rx[5] | (rx[6] << 8)]
     #Format x-axis
    if (out[0] & (1<<16 - 1 )):
        out[0] = out[0] - (1<<16)
    out[0] = out[0] * 0.0156
     #Format y-axis
    if (out[1] & (1<<16 - 1 )):
       out[1] = out[1] - (1<<16)
    out[1] = out[1] * 0.0156
     #Format z-axis
    if (out[2] & (1<<16 - 1 )):
        out[2] = out[2] - (1<<16)
    out[2] = out[2] * 0.0156

    return out

# Initialize the ADXL345 accelerometer

buffer_array = np.empty(shape=(1201,3))

initadxl345()

#Turn Watermark Interrupt to  generate
spi.xfer2([0x2E, 0b00000010])

spi.xfer2([242,0,0,0,0,0,0])

trigger = 0
event = 1
arrayindex = 0
counter = 0

while (True):                                 #Time that data will be collected. Number*5/800 = amount of time in seconds
    
    if (GPIO.input(22) == False):                           #Check to make sure the trigger is not already set. If it isn't wait for the trigger.
        GPIO.wait_for_edge(22, GPIO.RISING)
        
    fivecounter = 0                                         #Reset the counter that goes through the five data points in the FIFO buffer
    
    while (fivecounter < 5):                                #Count through buffer five times pulling data each time
        axia = readadxl345()                                #Read the accelerometer and store value in the numpy array.
        buffer_array[arrayindex] = [axia[0],axia[1],axia[2]]#Store X, Y, and Z
        
        if (axia[0] > 2 or axia[0] < -2 or axia[1] > 2 or axia[1] < -2 or axia[2] > 3 or axia[2] < -1) and trigger == 0: #Check for g's outside of range
            trigger = 1                                                                                                  #and that the trigger is not set.
            counter = 0                                                                                                  #Reset the counter the goes for 2 more seconds.
            buffer_array[1200] = [arrayindex,0,0]
            
        if arrayindex == 1199:                  #Loop through the 1200 row array
            arrayindex = 0                      #Go back to the first spot if at the end of the array
            
        else:                                   #If not at the end increment the array index
            arrayindex = arrayindex + 1
            
        if trigger == 1:
            counter = counter + 1                   #Increment the counter that counts for 1200 samples
            
        fivecounter = fivecounter + 1           #Increment counter that goes through the five buffer values

    if counter > 799:                          #2 seconds after the trigger hits, write out the file
            counter = 0
            trigger = 0
            
            np.savetxt('/media/usb/RawEvent_%d.txt' % event, buffer_array, delimiter=',', newline='\n')
            event = event + 1
            

