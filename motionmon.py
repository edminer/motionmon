#!/usr/local/bin/python -u
"""
Used to test motion sensor
https://www.raspberrypi.org/learning/parent-detector/worksheet/

Exec: ./test_pir.py
"""

import sys,os,traceback
sys.path.append(os.path.join(os.path.dirname(__file__), "pymodules"))

# Import smtplib for the actual sending function
import smtplib

# Import the email modules we'll need
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email import encoders

# Import the modules we'll need
import RPi.GPIO as GPIO
import time
import picamera,datetime

# import socket for singleton lock
import socket

def main():

   try:
      
      # We only want 1 instance of this running.  So attempt to get the "lock".
      get_lock('edm_watch_and_tell')
      
      camera = picamera.PiCamera()
      emailTo = "edminernew@gmail.com"
      recordingFileName_h264 = "/home/pi/edm_watch_and_tell.h264"
      recordingFileName_mp4  = "/home/pi/edm_watch_and_tell.mp4"

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

               print("Sending the video to %s..." % emailTo)
               emailFile(emailTo, recordingFileName_mp4)

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


   except Exception as e:
      # Fuller display of the Exception type and where the exception occured in the code
      (eType, eValue, eTraceback) = sys.exc_info()
      tbprintable = ''.join(traceback.format_tb(eTraceback))
      print("%s Exception: %s\n%s" % (eType.__name__, eValue, tbprintable))

   print("Done!")

   exit()


def get_lock(process_name):
  global lock_socket   # Without this our lock gets garbage collected
  lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
  try:
    lock_socket.bind('\0' + process_name)
    print('We got the lock')
  except socket.error:
    print('Lock exists so another instance of this script must be running.  Exiting.')
    exit()


def emailFile(emailTo, binaryFilename):

   #---------------------------------------------------------------------------
   # Send an email with a file attachment
   #---------------------------------------------------------------------------

   hostname   = os.uname().nodename
   emailFrom  = 'donotreply@%s' % hostname
   gmailUsername = 'edminerpi@gmail.com'
   gmailPassword = 'piplayt1me'

   print("Sending an email with a file attachment...")
   # Create the enclosing (outer) message
   msg = MIMEMultipart()
   msg['Subject'] = 'Something or someone just passed by at %s!' % datetime.datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
   msg['To'] = emailTo
   msg['From'] = emailFrom
   msg.preamble = 'You will not see this in a MIME-aware mail reader.\n'
   msg.attach(MIMEText('This file is attached: %s' % binaryFilename))

   ctype = 'application/octet-stream'
   maintype, subtype = ctype.split('/', 1)
   with open(binaryFilename,"rb") as INFILE:
      fileAttachment = MIMEBase(maintype, subtype)
      fileAttachment.set_payload(INFILE.read())

   # Encode the payload using Base64
   encoders.encode_base64(fileAttachment)

   # Set the filename parameter and attach file to outer message
   fileAttachment.add_header('Content-Disposition', 'attachment', filename=binaryFilename)
   msg.attach(fileAttachment)

   # Now send the message
   mailServer = smtplib.SMTP('smtp.gmail.com:587')
   mailServer.starttls()
   mailServer.login(gmailUsername,gmailPassword)

   mailServer.sendmail(emailFrom, emailTo, msg.as_string())
   mailServer.quit()

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
