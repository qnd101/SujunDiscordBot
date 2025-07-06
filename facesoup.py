import cv2
import dlib
import numpy as np

soup_total = cv2.imread("soup.jpg")
soupcorner = (85, 204)
soupsize = (210, 185)
soup = soup_total[soupcorner[1]:soupcorner[1]+soupsize[1], soupcorner[0]:soupcorner[0]+soupsize[0]]

# Create a circular mask for blending
mask = np.zeros((soupsize[1], soupsize[0]), dtype=np.float32)
halfsz = (soupsize[0]//2, soupsize[1]//2)
cv2.ellipse(mask, halfsz, halfsz, 0, 0, 360, 1, -1)  # Fill the ellipse with 1

def load_image_from_buffer(buffer):
    np_data = np.frombuffer(buffer, np.uint8)
    return cv2.imdecode(np_data, cv2.IMREAD_COLOR)

def encode_array_into_jpg(img):
    success, encoded_image = cv2.imencode(".jpg", img)
    if not success:
        raise ValueError("Failed to encode image.")
    return encoded_image.tobytes()

def resize_image(image, target_size = 800):
    """
    Resize the image to the target size while maintaining aspect ratio.
    """
    h, w = image.shape[:2]
    if h > w and h > target_size:
        new_h = target_size
        new_w = int(w * (target_size / h))
    elif w > h and w > target_size:
        new_w = target_size
        new_h = int(h * (target_size / w))
    else:
        return image
    
    return cv2.resize(image, (new_w, new_h))

def find_face(img):
    cnn_detector = dlib.cnn_face_detection_model_v1("mmod_human_face_detector.dat")
    faces = cnn_detector(img, 0)

    print(f"Number of faces detected: {len(faces)}")

    if len(faces) > 0:
        face = faces[0]  # Get the first detected face
        # Get the bounding box
        x1 = max(face.rect.left(), 0)
        y1 = max(face.rect.top(), 0)
        x2 = min(face.rect.right(), img.shape[1])
        y2 = min(face.rect.bottom(), img.shape[0])

        sqlen = min(x2 - x1, y2 - y1)

        x1 = x1 + (x2-x1)//2 - sqlen // 2
        y1 = y1 + (y2-y1)//2 - sqlen // 2

        # Show the image with detected faces
        return img[y1:y1+sqlen, x1:x1+sqlen]
        #cv2.imwrite("facesoup.jpg", face)
    else:
        raise ValueError("No face detected in the image.")
    
def blend_soup(img):
    face = cv2.resize(img, soupsize)
    mask = np.zeros((soupsize[1], soupsize[0]), dtype=np.uint8)
    halfsz = (soupsize[0]//2, soupsize[1]//2)
    cv2.ellipse(mask, halfsz, (int(halfsz[0]*0.8), int(halfsz[1]*0.8)), 0, 0, 360, 255, -1)  # Fill the ellipse with 1
    blended = cv2.seamlessClone(face, soup, mask, (halfsz[0], halfsz[1]), cv2.NORMAL_CLONE)
    result = soup_total.copy()
    result[soupcorner[1]:soupcorner[1]+soupsize[1], soupcorner[0]:soupcorner[0]+soupsize[0]] = blended
    return result
# innerratio = 0.4
# innermask = np.zeros((soupsize[1], soupsize[0]), dtype=np.float32)
# cv2.ellipse(innermask, halfsz, (int(halfsz[0] * innerratio), int(halfsz[1] * innerratio)), 0, 0, 360, 1, -1)  # Fill the ellipse with 1

# temp = (1-((np.arange(soupsize[0]) - halfsz[0])/ halfsz[0])**2 - ((np.arange(soupsize[1])[:, None] - halfsz[1])/ halfsz[1])**2)/(1- innerratio**2)

# interp = temp**2*(3-2*temp)
# mask = (mask - innermask) * interp + innermask

# mask = cv2.merge([mask, mask, mask])

# blended = soup * (1 - mask) + face * mask
# blended = blended.astype(np.uint8)

# soup_total[soupcorner[1]:soupcorner[1]+soupsize[1], soupcorner[0]:soupcorner[0]+soupsize[0]] = blended

# cv2.imwrite("facesoup1.jpg", soup_total)

