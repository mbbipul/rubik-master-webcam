from picamera.array import PiRGBArray
from picamera import PiCamera
import time
import cv2
import math 
import imutils
from rubik_solver import utils
import time

STICKER_CONTOUR_COLOR = (36, 255, 12)


def getROI_croped_image(contour):
	(x,y,w,h) = contour
	ROI = image[y:y+h, x:x+w]
	return ROI

def detect_color(img):
    rgb_pixel = img.mean(axis=0).mean(axis=0)
    rgb_pixel = rgb_pixel[::-1]

    colors = {
         'red'   : ( 255,0,0),
            'orange': (255,165, 0),
            'blue'  : (0, 0, 255),
            'green' : (0, 255, 0),
            'white' : (255, 255, 255),
            'yellow': (255, 255, 0)
    }
    score = {"green": 0, "blue": 0, "red": 0, "yellow": 0, "white": 0, "orange": 0}
    
    for k, v in colors.items():
        color_score = 0
        
        for i in range(3):
            color_score += abs(v[i] - rgb_pixel[i])**2
        score[k] = math.sqrt(color_score)
    
    return min(score, key=score.get)

def find_contours( dilatedFrame):
	contours, hierarchy = cv2.findContours(dilatedFrame, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[-2:]
	final_contours = []
	
	for contour in contours:
		perimeter = cv2.arcLength(contour, True)
		approx = cv2.approxPolyDP(contour, 0.1 * perimeter, True)

		if len (approx) == 4:
			area = cv2.contourArea(contour)
			(x, y, w, h) = cv2.boundingRect(approx)

			ratio = w / float(h)

			# Check square
			if ratio >= 0.8 and ratio <= 1.2 and w >= 30 and w <= 60 and area / (w * h) > 0.4:
				final_contours.append((x, y, w, h))
	
	found = False
	contour_neighbors = {}
	for index, contour in enumerate(final_contours):
		(x, y, w, h) = contour
		contour_neighbors[index] = []
		center_x = x + w / 2
		center_y = y + h / 2
		radius = 1.5

		neighbor_positions = [
			# top left
			[(center_x - w * radius), (center_y - h * radius)],

			# top middle
			[center_x, (center_y - h * radius)],

			# top right
			[(center_x + w * radius), (center_y - h * radius)],

			# middle left
			[(center_x - w * radius), center_y],

			# center
			[center_x, center_y],

			# middle right
			[(center_x + w * radius), center_y],

			# bottom left
			[(center_x - w * radius), (center_y + h * radius)],

			# bottom middle
			[center_x, (center_y + h * radius)],

			# bottom right
			[(center_x + w * radius), (center_y + h * radius)],
		]
	
		

		for neighbor in final_contours:
			(x2, y2, w2, h2) = neighbor
			for (x3, y3) in neighbor_positions:
				
				if (x2 < x3 and y2 < y3) and (x2 + w2 > x3 and y2 + h2 > y3):
					contour_neighbors[index].append(neighbor)


	for (contour, neighbors) in contour_neighbors.items():
		if len(neighbors) == 5:
			found = True
			final_contours = neighbors
			break


	if not found:
		return []

	y_sorted = sorted(final_contours, key=lambda item: item[1])

	top_row = sorted(y_sorted[0:3], key=lambda item: item[0])
	middle_row = sorted(y_sorted[3:6], key=lambda item: item[0])
	bottom_row = sorted(y_sorted[6:9], key=lambda item: item[0])

	sorted_contours = top_row + middle_row + bottom_row
	return sorted_contours

def draw_contours( frame, contours):

	for index, (x, y, w, h) in enumerate(contours):
		
		cv2.rectangle(frame, (x, y), (x + w, y + h), STICKER_CONTOUR_COLOR, 2)


def verify_cube_string_is_valid(cube_string):
    count = {"G": 0, "B": 0, "R": 0, "Y": 0, "W": 0, "O": 0}

    for c in cube_string:
        count[c] += 1

    for k in count:
        if count[k] != 9:
            print("Uploaded values are wrong!! Terminating the program!")
            time.sleep(2)
            return False

    return True


def generate_cube_string(faces):
    cube_string = ''

    face = faces['up']
    for i in range(3):
        for j in range(3):
            cube_string += face[i][j][0].capitalize()

    order = ['left', 'front', 'right', 'back']
    for o in order:
        face = faces[o]
        for i in range(3):
                for j in range(3):
                    cube_string += face[i][j][0].capitalize()

    face = faces['down']
    for i in range(3):
        for j in range(3):
            cube_string += face[i][j][0].capitalize()

    return cube_string


def solve_cube(faces):
    cube = generate_cube_string(faces)
    return utils.solve(cube.lower(), 'Kociemba')

# initialize picamera
camera = PiCamera()
camera.resolution = (640, 480)
camera.framerate = 32
rawCapture = PiRGBArray(camera)

# wait for camera open
time.sleep(0.1)
	

faces = {	'up' : None,
				'left' : None, 
				'front' : None, 
				'right' : None, 
				'back' :  None,
				'down' :  None
	}

for face in faces:
	face_info = []

	# capture frames from the camera
	for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
		
		image = frame.array
		image = cv2.flip(image,-1)
		


		grayFrame = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
		blurredFrame = cv2.blur(grayFrame, (3, 3))
		cannyFrame = cv2.Canny(blurredFrame, 30, 60, 3)
		kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
		dilatedFrame = cv2.dilate(cannyFrame, kernel)

		contours = find_contours(dilatedFrame)

		if len(contours) == 9:
			# draw contour 
			draw_contours(image, contours)

			cv2.imshow("Frame contoru", image)
			key = cv2.waitKey(1) & 0xFF
			
			row1 = [
				detect_color(getROI_croped_image(contours[0])),
				detect_color(getROI_croped_image(contours[1])),
				detect_color(getROI_croped_image(contours[2]))
			]
			face_info.append(row1)

			row2 = [
				detect_color(getROI_croped_image(contours[3])),
				detect_color(getROI_croped_image(contours[4])),
				detect_color(getROI_croped_image(contours[5]))
			]
			face_info.append(row2)

			row3 = [
				detect_color(getROI_croped_image(contours[6])),
				detect_color(getROI_croped_image(contours[7])),
				detect_color(getROI_croped_image(contours[8]))
			]
			
			face_info.append(row3)
			faces[face] = face_info
		

		key = cv2.waitKey(1) & 0xFF
		rawCapture.truncate(0)

		# if the `q` key was pressed, break from the loop
		if key == ord("q"):
			break

print(solve_cube(faces))




