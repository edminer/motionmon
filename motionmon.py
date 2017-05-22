#!/usr/local/bin/python -u

import sys,os,logging,re,traceback
sys.path.append("/usr/local/bin/pymodules")
from genutil import EXENAME,EXEPATH,GeneralError
import genutil

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

 Function: Motion Monitor.  Watches for motion and then takes a photo/video and emails it out.
           Start it once and it will run forever.

 Syntax  : $EXENAME {--light} {--delay #} {--snooze #} {--debug #} emailAddress captureType

 Note    : Parm         Description
           ----------   --------------------------------------------------------
           email        email address of person to receive the photo/video file
           captureType  photo or video
           --snooze     # of seconds to snooze before re-arming for motion detection after detecting motion
                        defaults to 1800
           --light      optional: turn on a light before taking the photo/video
           --delay      # of seconds to wait after detecting motion before turning on the light (optionally) and taking the video/photo
                        defaults to No Delay.
           --debug      optionally specifies debug option
                        0=off 1=STDERR 2=FILE

 Examples: $EXENAME jdoeman@gmail.com photo --light --snooze 30 

 Change History:
  em  06/01/2016  first written
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

   GPIO.setwarnings(False)
   GPIO.setmode(GPIO.BOARD)
   sensorPin = 7
   relayPin  = 12

   if genutil.G_options.light:
      logger.info("setting up GPIO for light")
      GPIO.setup(relayPin, GPIO.OUT)
      GPIO.output(relayPin,1)  # switch light off

   ##############################################################################
   #
   # Logic
   #
   ##############################################################################

   try:

      # We only want 1 instance of this running.  So attempt to get the "lock".
      genutil.getLock(EXENAME)

      recordingFileName_h264 = "/tmp/%s.h264" % EXENAME
      recordingFileName_mp4  = "/tmp/%s.mp4" % EXENAME
      photoFileName          = "/tmp/%s.jpg" % EXENAME

      # set the sensor Pin as an INPUT with an initial voltage state of 0(LOW)
      GPIO.setup(sensorPin, GPIO.IN, GPIO.PUD_DOWN)

      previous_state = False
      current_state = False
      sleepTime = 3.0

      while True:
         print("Sleeping for %d seconds..." % sleepTime)
         time.sleep(sleepTime)
         previous_state = current_state
         current_state = GPIO.input(sensorPin)
         #current_state = True   # for testing.
         if current_state != previous_state:
            if current_state:
               print("GPIO pin %s is HIGH.  Motion detected." % (sensorPin))
               
               if genutil.G_options.delay:
                  print("Sleeping %d seconds before taking pictures..." % genutil.G_options.delay)
                  time.sleep(genutil.G_options.delay)
               
               print("Starting to take pictures...")

               if genutil.G_options.light: GPIO.output(relayPin,0)  # switch light on

               with picamera.PiCamera() as camera:
                  if genutil.G_options.captureType.lower() == 'video':
                     print("Taking some video...")
                     camera.start_recording(recordingFileName_h264)
                     time.sleep(5)
                     camera.stop_recording()
                     binaryFilename = recordingFileName_mp4
                  else:
                     print("Taking a photo...")
                     camera.capture(photoFileName)
                     binaryFilename = photoFileName

               if genutil.G_options.light: GPIO.output(relayPin,1)  # switch light off

               if genutil.G_options.captureType.lower() == 'video':
                  # Convert the H264 video file to MP4
                  print("Converting video to mp4...")
                  os.system("/usr/bin/MP4Box -fps 30 -add %s %s >/tmp/MP4Box.out 2>&1" % (recordingFileName_h264, recordingFileName_mp4))

               print("Sending the photo/video to %s..." % genutil.G_options.emailTo)
               subject = 'Something or someone just passed by at %s!' % datetime.datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
               bodyText = 'Please see the attached file.'
               genutil.sendEmail(genutil.G_options.emailTo, subject, bodyText, binaryFilepath=binaryFilename)
               genutil.sendTwitterDirectMessage(genutil.G_options.twitterTo, subject)

               # cleanup and reset
               if genutil.G_options.captureType.lower() == 'video':
                  os.remove(recordingFileName_h264)
                  os.remove(recordingFileName_mp4)
               else:
                  os.remove(photoFileName)

               # Wait a bit of time before rearming for motion detection again (to prevent triggering rapid photo/video captures
               sleepTime = genutil.G_options.snooze
               GPIO.setup(sensorPin, GPIO.IN, GPIO.PUD_DOWN)
               current_state = False
            else:
               print("GPIO pin %s is LOW.  Motion is no longer detected." % (sensorPin))
               sleepTime = 1.0

         else:
            print("No change to GPIO pin")
            sleepTime = 1.0

   except GeneralError as e:
      if genutil.G_options.debug:
         # Fuller display of the Exception type and where the exception occured in the code
         (eType, eValue, eTraceback) = sys.exc_info()
         tbprintable = ''.join(traceback.format_tb(eTraceback))
         genutil.exitWithErrorMessage("%s Exception: %s\n%s" % (eType.__name__, eValue, tbprintable), errorCode=e.errorCode)
      else:
         genutil.exitWithErrorMessage(e.message, errorCode=e.errorCode)

   except Exception as e:
      if genutil.G_options.debug:
         # Fuller display of the Exception type and where the exception occured in the code
         (eType, eValue, eTraceback) = sys.exc_info()
         tbprintable = ''.join(traceback.format_tb(eTraceback))
         genutil.exitWithErrorMessage("%s Exception: %s\n%s" % (eType.__name__, eValue, tbprintable))
      else:
         genutil.exitWithErrorMessage(str(e))

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
   parser.add_argument('twitterTo')                      # positional, required
   parser.add_argument('captureType')                    # positional, required.  photo or video
   parser.add_argument('-l', '--light', action="store_true", dest="light", help='Turn on a light when taking the photo/video.')
   parser.add_argument('--delay', dest="delay", type=int, help='# of seconds to delay after motion is detected before taking photo/video.  Default is 0.')
   parser.add_argument('--snooze', dest="snooze", type=int, help='# of seconds to snooze after detecting motion before checking again.  Default is 1800.')
   parser.add_argument('--debug', dest="debug", type=int, help='0=no debug, 1=STDERR, 2=log file')

   genutil.G_options = parser.parse_args()

   if genutil.G_options.debug == None or genutil.G_options.debug == 0:
      logging.disable(logging.CRITICAL)  # effectively disable all logging
   else:
      if genutil.G_options.debug == 9:
         genutil.configureLogging(loglevel='DEBUG')
      else:
         genutil.configureLogging()

   if genutil.G_options.delay == None:
      genutil.G_options.delay = 0

   if genutil.G_options.snooze == None:
      genutil.G_options.snooze = 1800

   #global G_config
   #G_config = genutil.processConfigFile()

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
