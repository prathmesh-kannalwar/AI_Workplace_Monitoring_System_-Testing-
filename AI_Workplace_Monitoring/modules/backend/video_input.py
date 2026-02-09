import cv2

class VideoStream:
    def __init__(self, source=0):
        """
        Initialize the video source. 
        0 is usually the default webcam. 
        Alternatively, pass a string path to a video file.
        """
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            print(f"Error: Could not open video source {source}")

    def get_frame(self):
        """
        Reads a single frame from the source.
        Returns: ret (bool), frame (numpy array)
        """
        ret, frame = self.cap.read()
        return ret, frame

    def release(self):
        """Release the camera resource."""
        self.cap.release()

if __name__ == "__main__":
    # Quick test for the module
    video = VideoStream(0)
    
    while True:
        success, img = video.get_frame()
        if not success:
            break
            
        cv2.imshow("Workplace Monitor Test", img)
        
        # Press 'q' to exit the VideoStream
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    video.release()
    cv2.destroyAllWindows()
