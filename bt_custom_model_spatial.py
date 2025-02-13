# first, import all necessary modules
#these files are great
from pathlib import Path
import matplotlib.pyplot as plt
import blobconverter
import cv2
import depthai
import numpy as np
import time
import decouple
import os

import pyodbc

newConfig = False
stepSize = 0.05

# Pipeline tells DepthAI what operations to perform when running - you define all of the resources used and flows here
pipeline = depthai.Pipeline()

# First, we want the Color camera as the output
cam_rgb = pipeline.createColorCamera()
cam_rgb.setPreviewSize(300, 300)  # 300x300 will be the preview frame size, available as 'preview' output of the node
cam_rgb.setInterleaved(False)

# Next, we want a neural network that will produce the detections
detection_nn = pipeline.createMobileNetDetectionNetwork()
# Blob is the Neural Network file, compiled for MyriadX. It contains both the definition and weights of the model
# We're using a blobconverter tool to retreive the MobileNetSSD blob automatically from OpenVINO Model Zoo

#Get the path to the model

detection_nn.setBlobPath("Model\custom_model.blob")#this is a local version

################################
# Define sources and outputs

monoLeft = pipeline.create(depthai.node.MonoCamera)
monoRight = pipeline.create(depthai.node.MonoCamera)
stereo = pipeline.create(depthai.node.StereoDepth)
spatialLocationCalculator = pipeline.create(depthai.node.SpatialLocationCalculator)

xoutDepth = pipeline.create(depthai.node.XLinkOut)
xoutSpatialData = pipeline.create(depthai.node.XLinkOut)
xinSpatialCalcConfig = pipeline.create(depthai.node.XLinkIn)

xoutDepth.setStreamName("depth")
xoutSpatialData.setStreamName("spatialData")
xinSpatialCalcConfig.setStreamName("spatialCalcConfig")
################################
# Properties

monoLeft.setResolution(depthai.MonoCameraProperties.SensorResolution.THE_400_P)
monoLeft.setBoardSocket(depthai.CameraBoardSocket.LEFT)
monoRight.setResolution(depthai.MonoCameraProperties.SensorResolution.THE_400_P)
monoRight.setBoardSocket(depthai.CameraBoardSocket.RIGHT)

lrcheck = False
subpixel = False

#stereo.setDefaultProfilePreset(depthai.node.StereoDepth.PresetMode.HIGH_DENSITY) #chenged to try high accuracy mode instead of density
stereo.setDefaultProfilePreset(depthai.node.StereoDepth.PresetMode.HIGH_ACCURACY)
stereo.setLeftRightCheck(lrcheck)
stereo.setSubpixel(subpixel)


###################################
# Config the bounding box

topLeft = depthai.Point2f(0.83, 0.52)
bottomRight = depthai.Point2f(0.87, 0.57)

config = depthai.SpatialLocationCalculatorConfigData()
config.depthThresholds.lowerThreshold = 400
config.depthThresholds.upperThreshold = 600
config.roi = depthai.Rect(topLeft, bottomRight)

spatialLocationCalculator.inputConfig.setWaitForMessage(False)
spatialLocationCalculator.initialConfig.addROI(config)

###################################
# Linking
monoLeft.out.link(stereo.left)
monoRight.out.link(stereo.right)

spatialLocationCalculator.passthroughDepth.link(xoutDepth.input)
stereo.depth.link(spatialLocationCalculator.inputDepth)

spatialLocationCalculator.out.link(xoutSpatialData.input)
xinSpatialCalcConfig.out.link(spatialLocationCalculator.inputConfig)

###################################
#Set camera and neural network properties

# Next, we filter out the detections that are below a confidence threshold. Confidence can be anywhere between <0..1>
detection_nn.setConfidenceThreshold(0.3)

# Next, we link the camera 'preview' output to the neural network detection input, so that it can produce detections
cam_rgb.preview.link(detection_nn.input)

# XLinkOut is a "way out" from the device. Any data you want to transfer to host need to be send via XLink
xout_rgb = pipeline.createXLinkOut()
# For the rgb camera output, we want the XLink stream to be named "rgb"
xout_rgb.setStreamName("rgb")
# Linking camera preview to XLink input, so that the frames will be sent to host
cam_rgb.preview.link(xout_rgb.input)

# The same XLinkOut mechanism will be used to receive nn results
xout_nn = pipeline.createXLinkOut()
xout_nn.setStreamName("nn")
detection_nn.out.link(xout_nn.input)

#######################################
#Get the UID from the database

server = decouple.config('server',default='')
database = decouple.config('database',default='')
username = decouple.config('UserID',default='')
password = decouple.config('password',default='') 

cnxn = pyodbc.connect('DRIVER={SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username+';PWD='+ password)
cursor = cnxn.cursor()

# Insert Dataframe into SQL Server:
query = """SELECT ID from bt_plan where starttime= (SELECT MAX(starttime) FROM bt_plan)""" 

cursor.execute(query)
row = cursor.fetchone()
UID = (row[0])

#Video Writer

fourcc = cv2.VideoWriter_fourcc(*'mp4v')

outpath_string = "Videos\\%s.mp4" %(UID)

outpath = outpath_string
out_video = cv2.VideoWriter(outpath, fourcc, 30.0, (300,300))

# Pipeline is now finished, and we need to find an available device to run our pipeline
# we are using context manager here that will dispose the device after we stop using it
with depthai.Device(pipeline) as device:
    # From this point, the Device will be in "running" mode and will start sending data via XLink

    # To consume the device results, we get two output queues from the device, with stream names we assigned earlier
    q_rgb = device.getOutputQueue("rgb")
    q_nn = device.getOutputQueue("nn")
    #######################################
    #get the depth info

    depthQueue = device.getOutputQueue(name="depth", maxSize=4, blocking=False)
    spatialCalcQueue = device.getOutputQueue(name="spatialData", maxSize=4, blocking=False)
    spatialCalcConfigInQueue = device.getInputQueue("spatialCalcConfig")
    color = (255, 255, 255)

    #print("Use WASD keys to move ROI")
    i=0

    # Here, some of the default values are defined. Frame will be an image from "rgb" stream, detections will contain nn results
    frame = None
    detections = []

    # Since the detections returned by nn have values from <0..1> range, they need to be multiplied by frame width/height to
    # receive the actual position of the bounding box on the image
    def frameNorm(frame, bbox):
        normVals = np.full(len(bbox), frame.shape[0])
        normVals[::2] = frame.shape[1]
        return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)

    stack_temp = []
    stack_act = []

    start_time = time.time()  #start the timer

    inlist = []
    
    # Main host-side application loop
    start_time_query = time.time()
    while True:
        t_time = time.time() - start_time_query
        counter = []
        sequence = []
        
        # we try to fetch the data from nn/rgb queues. tryGet will return either the data packet or None if there isn't any
        in_rgb = q_rgb.tryGet()
        in_nn = q_nn.tryGet()
        in_depthQueue = depthQueue.tryGet()

        if in_rgb is not None:
            # If the packet from RGB camera is present, we're retrieving the frame in OpenCV format using getCvFrame
            frame = in_rgb.getCvFrame()

        if in_nn is not None:
            # when data from nn is received, we take the detections array that contains mobilenet-ssd results
            detections = in_nn.detections

        ################################
        # Business Logic for Detection Tracking
        if frame is not None:
            for detection in detections:
                t_diff = time.time() - start_time
                # for each bounding box, we first normalize it to match the frame size
                bbox = frameNorm(frame, (detection.xmin, detection.ymin, detection.xmax, detection.ymax))
                coordinate_xmin = str(round(detection.xmin,2))
                coordinate_ymin = str(round(detection.ymin,2))
                coordinate_str = 'x=%s, y=%s'%(coordinate_xmin,coordinate_ymin)
                text_label = detection.label
                
                stack_temp.append(text_label)

                if in_depthQueue is not None and detection.xmin >0.6:
                    inDepth = depthQueue.get() # Blocking call, will wait until a new data has arrived
                    depthFrame = inDepth.getFrame() # depthFrame values are in millimeters
                    #depthFrameColor = cv2.normalize(depthFrame, None, 255, 0, cv2.NORM_INF, cv2.CV_8UC1)
                    #depthFrameColor = cv2.equalizeHist(depthFrameColor)
                    #depthFrameColor = cv2.applyColorMap(depthFrameColor, cv2.COLORMAP_RAINBOW )
       
                    spatialData = spatialCalcQueue.get().getSpatialLocations()
                
                    for depthData in spatialData:
                        roi = depthData.config.roi 
                        roi = roi.denormalize(width=300, height=300) 
                        xmin = int(roi.topLeft().x)
                        ymin = int(roi.topLeft().y)
                        xmax = int(roi.bottomRight().x)
                        ymax = int(roi.bottomRight().y)

                        depthMin = depthData.depthMin
                        depthMax = depthData.depthMax
                
                        fontType = cv2.FONT_HERSHEY_TRIPLEX
                        #cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), color, cv2.FONT_HERSHEY_SCRIPT_SIMPLEX)
                        #cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), color, 1)
                        #cv2.putText(frame, f"X: {int(depthData.spatialCoordinates.x)} mm", (xmin + 10, ymin + 20), fontType, 0.5, 255)
                        #cv2.putText(frame, f"Y: {int(depthData.spatialCoordinates.y)} mm", (xmin + 10, ymin + 35), fontType, 0.5, 255)
                        #cv2.putText(frame, f"Z: {int(depthData.spatialCoordinates.z)} mm", (xmin + 10, ymin + 50), fontType, 0.5, 255)

                #######################################
                #Add data to database
                
                color = text_label
                uid = UID
                height = depthData.depthAverage
                seconds = t_time
                
                inlist.append([color,uid,height,seconds,coordinate_xmin,coordinate_ymin])

                counter.append(1)
                conf = round(detection.confidence * 100,0)

                if detection.label == 3:
                    sequence.append('Red')
                    text_label ='Red '
                elif detection.label == 2:
                    sequence.append('Blue')
                    text_label ='Blue '
                elif detection.label == 1:
                    sequence.append('Black') 
                    text_label ='Black ' 
                
                # and then draw a rectangle on the frame to show the actual result
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (255, 0, 0), 1)
                cv2.putText(frame, text_label, (bbox[0], bbox[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)
                cv2.putText(frame, coordinate_str, (bbox[0], bbox[1]+10), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0,255,255), 1)

                cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), color, 1)
                #cv2.putText(frame, f"X: {int(depthData.spatialCoordinates.x)} mm", (xmin + 10, ymin + 20), fontType, 0.5, 255)
                #cv2.putText(frame, f"Y: {int(depthData.spatialCoordinates.y)} mm", (xmin + 10, ymin + 35), fontType, 0.5, 255)
                #cv2.putText(frame, f"Z: {int(depthData.spatialCoordinates.z)} mm", (xmin + 10, ymin + 50), fontType, 0.5, 255)
                #cv2.putText(frame, f"{int(depthData.spatialCoordinates.z)} mm", (xmin + 10, ymin + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 255)

            # After all the drawing is finished, we show the frame on the screen
            cv2.imshow("preview", frame)
            #cv2.putText(frame, outstring_count, (10, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (36,255,12), 1)
            #cv2.putText(frame, outstring_seq, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (36,255,12), 1)
            out_video.write(frame)

        # at any time, you can press "q" and exit the main loop, therefore exiting the program itself
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
           
            key = cv2.waitKey(1)
            if key == ord('w'):
                if topLeft.y - stepSize >= 0:
                    topLeft.y -= stepSize
                    bottomRight.y -= stepSize
                    newConfig = True
            elif key == ord('a'):
                if topLeft.x - stepSize >= 0:
                    topLeft.x -= stepSize
                    bottomRight.x -= stepSize
                    newConfig = True
            elif key == ord('s'):
                if bottomRight.y + stepSize <= 1:
                    topLeft.y += stepSize
                    bottomRight.y += stepSize
                    newConfig = True
            elif key == ord('d'):
                if bottomRight.x + stepSize <= 1:
                    topLeft.x += stepSize
                    bottomRight.x += stepSize
                    newConfig = True

            if newConfig:
                config.roi = depthai.Rect(topLeft, bottomRight)
                config.calculationAlgorithm = depthai.SpatialLocationCalculatorAlgorithm.AVERAGE
                cfg = depthai.SpatialLocationCalculatorConfig()
                cfg.addROI(config)
                spatialCalcConfigInQueue.send(cfg)
                newConfig = False

    numrecords = len(inlist)
    numrecords_report  = 'the number of records is %s' %numrecords
    #Need to split the dataset into chunks for SQL due to query limit.

    n = 500 #size of chunks
    chunks = [] #list of chunks
    counter = 0

    for i in range(0, numrecords, n): 
        chunks.append(inlist[i:i + n])
    numchunks = len(chunks)
    print('the number of chunks is %s' %numchunks)

    for chunk in chunks:
        counter = counter + 1

        final = ''
        for rec in chunk: 
            query = """INSERT INTO [dbo].[bt_actual] ([color],[UID],[height],[seconds],[xcoord],[ycoord])VALUES(%s,'%s',%s,%s,%s,%s)""" %(rec[0],rec[1],rec[2],rec[3],rec[4],rec[5])
            final = final + query +';'

        cursor.execute(final)
        cnxn.commit()
            
    out_video.release()
  
    #close the database connection
    cursor.close()


