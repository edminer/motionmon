#!/usr/local/bin/python -u

import sys,os,logging,re,traceback
sys.path.append("/usr/local/bin/pymodules")
from emgenutil import EXENAME,EXEPATH,GeneralError
import emgenutil

# Import the modules we'll need
import RPi.GPIO as GPIO
import time
import picamera,datetime
#------------------------------------------------------------------------------
# GLOBALS
#------------------------------------------------------------------------------

logger=logging.getLogger(EXENAME)

#------------------------------------------------------------------------------
# USAGE
#------------------------------------------------------------------------------

def usage():
   from string import Template
   usagetext = """

 $EXENAME

 Function: Whatever

 Syntax  : $EXENAME {--debug #}

 Note    : Parm       Description
           ---------- --------------------------------------------------------
           --debug    optionally specifies debug option
                      0=off 1=STDERR 2=FILE

 Examples: $EXENAME

 Change History:
  em  XX/XX/2016  first written
.
"""
   template = Template(usagetext)
   return(template.substitute({'EXENAME':EXENAME}))


#------------------------------------------------------------------------------
# Subroutine: main
# Function  : Main routine
# Parms     : none (in sys.argv)
# Returns   : nothing
# Assumes   : sys.argv has parms, if any
#------------------------------------------------------------------------------
def main():

   ##############################################################################
   #
   # Main - initialize
   #
   ##############################################################################

   initialize()

   ##############################################################################
   #
   # Logic
   #
   ##############################################################################

   try:
      
      # We only want 1 instance of this running.  So attempt to get the "lock".
      emgenutil.getLock(EXENAME)
      
      camera = picamera.PiCamera()
      recordingFileName_h264 = "/tmp/%s.h264" % EXENAME
      recordingFileName_mp4  = "/tmp/%s.mp4" % EXENAME

      sensor = 4

      GPIO.setmode(GPIO.BCM)
      # set the sensor channel as an INPUT with an initial voltage state of 0(LOW)
      GPIO.setup(sensor, GPIO.IN, GPIO.PUD_DOWN)

      previous_state = False
      current_state = False
      sleepTime = 3.0

      while True:
         print("Sleeping for %d seconds..." % sleepTime)
         time.sleep(sleepTime)
         previous_state = current_state
         current_state = GPIO.input(sensor)
         #current_state = True   # for testing.
         if current_state != previous_state:
            if current_state:
               print("GPIO pin %s is HIGH.  Motion detected.  Starting to take pictures..." % (sensor))
               print("Taking some video...")
               camera.start_recording(recordingFileName_h264)
               time.sleep(5)
               camera.stop_recording()

               # Convert the H264 video file to MP4
               print("Converting video to mp4...")
               os.system("/usr/bin/MP4Box -fps 30 -add %s %s >/tmp/MP4Box.out 2>&1" % (recordingFileName_h264, recordingFileName_mp4))

               print("Sending the video to %s..." % emgenutil.G_options.emailTo)
               subject = 'Something or someone just passed by at %s!' % datetime.datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
               bodyText = 'Please see the attached file.'
               emgenutil.sendEmail(emgenutil.G_options.emailTo, subject, bodyText, binaryFilepath=recordingFileName_mp4)

               # cleanup and reset
               os.remove(recordingFileName_h264)
               os.remove(recordingFileName_mp4)
               sleepTime = 1800
               GPIO.setup(sensor, GPIO.IN, GPIO.PUD_DOWN)
               current_state = False
            else:
               print("GPIO pin %s is LOW.  Motion is no longer detected." % (sensor))
               sleepTime = 1.0

         else:
            print("No change to GPIO pin")
            sleepTime = 1.0

   except GeneralError as e:
      if emgenutil.G_options.debug:
         # Fuller display of the Exception type and where the exception occured in the code
         (eType, eValue, eTraceback) = sys.exc_info()
         tbprintable = ''.join(traceback.format_tb(eTraceback))
         emgenutil.exitWithErrorMessage("%s Exception: %s\n%s" % (eType.__name__, eValue, tbprintable), errorCode=e.errorCode)
      else:
         emgenutil.exitWithErrorMessage(e.message, errorCode=e.errorCode)

   except Exception as e:
      if emgenutil.G_options.debug:
         # Fuller display of the Exception type and where the exception occured in the code
         (eType, eValue, eTraceback) = sys.exc_info()
         tbprintable = ''.join(traceback.format_tb(eTraceback))
         emgenutil.exitWithErrorMessage("%s Exception: %s\n%s" % (eType.__name__, eValue, tbprintable))
      else:
         emgenutil.exitWithErrorMessage(str(e))

   ##############################################################################
   #
   # Finish up
   #
   ##############################################################################

   logger.info(EXENAME+" exiting")
   logging.shutdown()

   exit()


#------------------------------------------------------------------------------
# Subroutine: initialize
# Function  : performs initialization of variable, CONSTANTS, other
# Parms     : none
# Returns   : nothing
# Assumes   : ARGV has parms, if any
#------------------------------------------------------------------------------
def initialize():

   # PROCESS COMMAND LINE PARAMETERS

   import argparse  # http://www.pythonforbeginners.com/modules-in-python/argparse-tutorial/

   parser = argparse.ArgumentParser(usage=usage())
   parser.add_argument('emailTo')                        # positional, required
   parser.add_argument('--debug', dest="debug", type=int, help='0=no debug, 1=STDERR, 2=log file')

   emgenutil.G_options = parser.parse_args()

   if emgenutil.G_options.debug == None or emgenutil.G_options.debug == 0:
      logging.disable(logging.CRITICAL)  # effectively disable all logging
   else:
      if emgenutil.G_options.debug == 9:
         emgenutil.configureLogging(loglevel='DEBUG')
      else:
         emgenutil.configureLogging()

   #global G_config
   #G_config = emgenutil.processConfigFile()

   logger.info(EXENAME+" starting:"+__name__+" with these args:"+str(sys.argv))

# Standard boilerplate to call the main() function to begin the program.
if __name__ == "__main__":
   main()

#               print("1st Picture")
#               # image capture here: fswebcam -r 1280x720 image.jpg
#               camera.capture('/tmp/image1.jpg')
#               #os.system("/usr/bin/fswebcam -r 1280x720 /tmp/image1.jpg 2>/dev/null")
#               time.sleep(3)
#               print("2nd Picture")
#               # image capture here
#               camera.capture('/tmp/image2.jpg')
#               #os.system("/usr/bin/fswebcam -r 1280x720 /tmp/image2.jpg 2>/dev/null")
#               time.sleep(3)
#               print("3rd Picture")
#               # image capture here
#               camera.capture('/tmp/image3.jpg')
#               #os.system("/usr/bin/fswebcam -r 1280x720 /tmp/image3.jpg 2>/dev/null")
