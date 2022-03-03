'''
    Requirements:

    pip install flask flask-socketio eventlet opencv-python-headless RPi.GPIO w1thermsensor

    References:
        https://learn.alwaysai.co/build-your-own-video-streaming-server-with-flask-socketio
            This approach takes a JPEG image, encodes it using base64 and sends it to the client.
            The client just replaces each image with a new one. Good enough and get reasonable frame rates.
        https://blog.miguelgrinberg.com/post/flask-video-streaming-revisited
            This approach takes an image and sets it as a multipart image.
            Each frame is sent as a section of a multipart continuous image.
            Runs ok but initially had issues with client control of the light using socketio.
'''

from flask_socketio import SocketIO
from flask import Flask, render_template, request
import cv2
import datetime
import time
import threading
import RPi.GPIO as GPIO
from w1thermsensor import W1ThermSensor, Sensor
import base64

# Variables for the temperature sensors
TEMP_READ_RATE = 2.0          # The rate (in Hz) at which temperatures should be read
TEMP_RECORD_INTERVAL = 30     # Time interval (s) to record temperature in logfile
LOGNAME = f'{timestamp.strftime("%Y%m%d-%H%M")}.log'
INTERNAL_TEMPERATURE = 0    # The temperature inside the enclosure (Celsius)
EXTERNAL_TEMPERATURE = 0    # The temperature outside the enclosure (Celsius)
TEMPERATURE_SETPOINT = 30   # The desired temperature inside the enclosure
EXTERNAL_TEMPERATURE_SENSOR = W1ThermSensor(Sensor.DS18B20, '2029ab00098b')
INTERNAL_TEMPERATURE_SENSOR = W1ThermSensor(Sensor.DS18B20, '2029ab000999')

# Variables for toggling the light/RELAY_PIN on/off
GPIO.setmode(GPIO.BCM)
RELAY_PIN = 24
GPIO.setup(RELAY_PIN, GPIO.OUT, initial=GPIO.LOW)

# Variables for the webcam
camera = cv2.VideoCapture(0)
VIDEO_FRAME_RATE = 30             # Frame read rate (in Hz)
IMAGE_FRAME = None          # The current frame from the webcam

# Variables for the Flask webserver
app = Flask(__name__)
socketio = SocketIO(app)
CLIENT_CONNECTED = False    # Flag to indicate if a client is connected and needs to be updated

lock = threading.Lock()

def toggle_light():
    '''
        Toggle the light/RELAY_PIN by setting the GPIO pin appropriately
    '''
    if GPIO.input(RELAY_PIN) == 1 or GPIO.input(RELAY_PIN) == True or GPIO.input(RELAY_PIN) == GPIO.HIGH:
        # Turn the RELAY_PIN off/low
        try:
            GPIO.output(RELAY_PIN, GPIO.LOW)
            print('Light has been turned off.')
        except:
            print(f'Could not set pin {RELAY_PIN} to LOW')
    else:
        # Turn the RELAY_PIN on/high
        try:
            GPIO.output(RELAY_PIN, GPIO.HIGH)
            
            print('Light has been turned on.')
        except:
            print(f'Could not set pin {RELAY_PIN} to HIGH')

def read_temp():
    '''
        Continuously reads temperature values at a specified rate and sends the data to the web client.
        Updates INTERNAL_TEMPERATURE and EXTERNAL_TEMPERATURE global variables, used to control the
        thermoelectric modules.
    '''
    global INTERNAL_TEMPERATURE, EXTERNAL_TEMPERATURE
    print(f'Reading temperature values at {TEMP_READ_RATE} Hz.')
    while True:
        try:
            int_temp = INTERNAL_TEMPERATURE_SENSOR.get_temperature()
            ext_temp = EXTERNAL_TEMPERATURE_SENSOR.get_temperature()
            lock.acquire()
            INTERNAL_TEMPERATURE = int_temp
            EXTERNAL_TEMPERATURE = ext_temp
            lock.release()            
            print(f'Internal: {int_temp:.1f}C   External: {ext_temp:.1f}C')
        except:
            pass
        time.sleep(1.0/TEMP_READ_RATE)

def record_temp():
    print(f'Starting temperature recording at {TEMP_RECORD_INTERVAL} second intervals')
    while True:
        timestamp = datetime.datetime.now()
        lock.acquire()
        data = f'{timestamp.strftime("%Y%m%d %H:%M:%S")},{INTERNAL_TEMPERATURE:.1f},{EXTERNAL_TEMPERATURE:.1f}'
        lock.release()
        with open(LOGNAME, 'a') as f:
            f.write(data+'\n')
            print(data)
        time.sleep(TEMP_RECORD_INTERVAL)

def read_frame():
    '''
        Reads a frame from the webcam when a client is connected and sends the image to the web client.
    '''
    global IMAGE_FRAME
    print(f'Frames are being read from the camera')
    while CLIENT_CONNECTED:
        success, frame = camera.read()
        if not success:
            # Camera not ready and no frame was read, so do nothing
            pass
        else:
            try:
                success, encodedImage = cv2.imencode(".jpg", frame) # Encode the frame as a jpg image
                if not success:
                    pass
                else:
                    encodedImageb64 = base64.b64encode(encodedImage).decode('utf-8') # Encode the jpg image into base64
                    lock.acquire()
                    int_temp = INTERNAL_TEMPERATURE
                    ext_temp = EXTERNAL_TEMPERATURE
                    lock.release()
                    socketio.emit('server2web', {
                        'ext_temp': f'{EXTERNAL_TEMPERATURE:.1f}',
                        'int_temp': f'{INTERNAL_TEMPERATURE:.1f}',
                        'image': encodedImageb64
                    })
                    socketio.sleep(0)
            except:
                pass
        time.sleep(1.0/VIDEO_FRAME_RATE)
    print(f'No more frames are being read from the camera')

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def connect_web():
    global CLIENT_CONNECTED
    CLIENT_CONNECTED = True
    print(f'Web client {format(request.sid)} has connected')
    socketio.start_background_task(target=read_frame)

@socketio.on('disconnect')
def disconnect_web():
    global CLIENT_CONNECTED
    CLIENT_CONNECTED = False
    print(f'Web client {format(request.sid)} has disconnected')

@socketio.on('toggle clicked')
def client_clicked_toggle(toggle):
    socketio.start_background_task(target=toggle_light)

if __name__ == "__main__":

    read_temp_thread = threading.Thread(target=read_temp, )
    read_temp_thread.daemon = True
    read_temp_thread.start()

    record_temp_thread = threading.Thread(target=record_temp, )
    record_temp_thread.daemon = True
    record_temp_thread.start()

    print('Starting server...')
    socketio.run(app=app, host='0.0.0.0', port=5001)