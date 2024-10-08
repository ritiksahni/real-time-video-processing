import cv2
import subprocess as sp
import asyncio
import websockets
import threading
from concurrent.futures import ThreadPoolExecutor

class VideoStreamer:
    def __init__(self, width=1920, height=1080, fps=60, output_url='rtmp://localhost/live/stream'):
        self.width = width
        self.height = height
        self.fps = fps
        self.output_url = output_url
        self.msg = "No message yet"
        self.ws_connected = False
        self.running = True
        
        # Initialize video capture
        self.cap = cv2.VideoCapture('./test_test.mkv')  # 0 is usually the built-in webcam
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        
        # FFMPEG command to stream video
        self.command = [
            'ffmpeg',
            '-y',  # Overwrite output files
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', f'{width}x{height}',
            '-r', str(fps),
            '-i', '-',  # Input comes from pipe
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-preset', 'ultrafast',
            '-f', 'flv',
            output_url
        ]
        
        # Start FFMPEG process
        self.process = sp.Popen(self.command, stdin=sp.PIPE)

    async def websocket_client(self):
        """Handles WebSocket connection and message reception"""
        while self.running:
            try:
                async with websockets.connect('ws://127.0.0.1:8765') as websocket:
                    self.ws_connected = True
                    print("Connected to WebSocket server")
                    
                    while self.running:
                        try:
                            message = await websocket.recv()
                            self.msg = message
                            print(f"Received message: {message}")
                        except websockets.ConnectionClosed:
                            print("WebSocket connection closed")
                            break
                        except Exception as e:
                            print(f"Error receiving message: {e}")
                            break
                            
            except ConnectionRefusedError:
                print("Could not connect to WebSocket server. Retrying in 5 seconds...")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"WebSocket error: {e}")
                await asyncio.sleep(5)
            
            self.ws_connected = False

    def add_overlay(self, frame):
        # Add connection status
        status_color = (0, 255, 0) if self.ws_connected else (0, 0, 255)

        # Uncomment the following line to show the WebSocket status on the frame

        # status_text = "WebSocket: Connected" if self.ws_connected else "WebSocket: Disconnected"
        # cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
        #             1, status_color, 2, cv2.LINE_AA)
        
        # Add the current message
        cv2.putText(frame, self.msg, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 
                    1, (0, 255, 0), 2, cv2.LINE_AA)
        
        return frame

    async def run_async(self):
        """Runs the WebSocket client"""
        await self.websocket_client()

    def start_websocket(self):
        """Starts the WebSocket client in a separate thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.run_async())

    def start_streaming(self):
        # Start WebSocket client in a separate thread
        ws_thread = threading.Thread(target=self.start_websocket)
        ws_thread.daemon = True
        ws_thread.start()

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    break

                # Process frame (add overlays, effects, etc.)
                processed_frame = self.add_overlay(frame)
                
                # Show local preview (optional)
                cv2.imshow('Local Preview', processed_frame)
                
                # Write frame to FFMPEG process
                self.process.stdin.write(processed_frame.tobytes())
                
                # Break loop on 'q' press
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        finally:
            self.cleanup()

    def cleanup(self):
        # Signal the WebSocket client to stop
        self.running = False
        
        # Clean up resources
        self.cap.release()
        cv2.destroyAllWindows()
        self.process.stdin.close()
        self.process.wait()

if __name__ == "__main__":
    # Create and start streamer
    streamer = VideoStreamer(
        width=1280,
        height=720,
        fps=30,
        output_url='rtmp://localhost/live/stream'
    )
    streamer.start_streaming()