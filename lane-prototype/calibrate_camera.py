"""
Interactive camera calibration tool.
Click 4 points on the road plane and enter their real-world coordinates.
"""
import argparse
import cv2
import numpy as np
import yaml
import os

class CameraCalibrationTool:
    def __init__(self, image_path, config_path):
        self.image_path = image_path
        self.config_path = config_path
        self.image = cv2.imread(image_path)
        if self.image is None:
            raise ValueError(f"Could not read image: {image_path}")
        
        self.display_image = self.image.copy()
        self.image_points = []  # Pixel coordinates
        self.world_points = []  # Meter coordinates
        self.max_points = 4
        
        # Load existing config
        self.config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            # Load existing calibration if present
            if 'homography' in self.config and self.config['homography']:
                hom = self.config['homography']
                if 'image_points' in hom:
                    self.image_points = [tuple(p) for p in hom['image_points']]
                if 'world_points' in hom:
                    self.world_points = [tuple(p) for p in hom['world_points']]
        
        self.window_name = 'Camera Calibration - Click 4 Road Points'
        self.current_world_input = None
    
    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse clicks for selecting points."""
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(self.image_points) < self.max_points:
                # Add image point
                self.image_points.append((x, y))
                print(f"\nPoint {len(self.image_points)} clicked at pixel: ({x}, {y})")
                
                # Prompt for world coordinates
                self.prompt_world_coordinates(len(self.image_points))
                
                self.update_display()
            else:
                print(f"Already have {self.max_points} points. Press 'r' to reset.")
    
    def prompt_world_coordinates(self, point_num):
        """Prompt user to enter world coordinates for the clicked point."""
        print(f"\nEnter real-world coordinates for Point {point_num}:")
        print("  (These are the actual distances in METERS on the road)")
        
        while True:
            try:
                x_str = input(f"  X coordinate (meters, horizontal): ")
                y_str = input(f"  Y coordinate (meters, depth/forward): ")

                x_world = float(x_str)
                y_world = float(y_str)
                
                self.world_points.append((x_world, y_world))
                print(f"  Point {point_num}: Pixel({self.image_points[-1][0]}, {self.image_points[-1][1]}) = World({x_world}m, {y_world}m)")
                break
            except ValueError:
                print("  Invalid input. Please enter numbers.")
            except (KeyboardInterrupt, EOFError):
                print("\n  Skipped. You can reset with 'r'.")
                # Remove the image point we just added
                if len(self.image_points) > 0:
                    self.image_points.pop()
                break
            except Exception as e:
                print(f"  Error: {e}. Please try again.")
                if len(self.image_points) > 0:
                    self.image_points.pop()
                break
    
    def update_display(self):
        """Update the display with current points."""
        self.display_image = self.image.copy()
        
        # Draw points and labels
        for i, point in enumerate(self.image_points):
            # Draw circle
            cv2.circle(self.display_image, point, 8, (0, 255, 0), -1)
            
            # Draw point number
            cv2.putText(self.display_image, str(i + 1), 
                       (point[0] + 12, point[1] + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Draw world coordinates if available
            if i < len(self.world_points):
                world_text = f"({self.world_points[i][0]:.1f}m, {self.world_points[i][1]:.1f}m)"
                cv2.putText(self.display_image, world_text,
                           (point[0] + 12, point[1] + 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        # Draw lines connecting points
        if len(self.image_points) > 1:
            for i in range(len(self.image_points)):
                if i < len(self.image_points) - 1 or len(self.image_points) == self.max_points:
                    pt1 = self.image_points[i]
                    pt2 = self.image_points[(i + 1) % len(self.image_points)]
                    cv2.line(self.display_image, pt1, pt2, (0, 255, 0), 2)
        
        # Instructions
        points_remaining = self.max_points - len(self.image_points)
        if points_remaining > 0:
            instructions = [
                f"Click {points_remaining} more point(s) on the ROAD PLANE",
                "Then enter real-world coordinates in console",
                "Press 's' to save | 'r' to reset | 'q' to quit"
            ]
        else:
            instructions = [
                "Calibration complete! Press 's' to save",
                "Press 'r' to reset | 'q' to quit"
            ]
        
        for i, text in enumerate(instructions):
            cv2.putText(self.display_image, text, (10, 30 + i * 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow(self.window_name, self.display_image)
    
    def save_config(self):
        """Save calibration to config file."""
        if len(self.image_points) != self.max_points or len(self.world_points) != self.max_points:
            print(f"Need {self.max_points} complete points. Currently have {len(self.image_points)} image points and {len(self.world_points)} world points.")
            return False
        
        # Update config
        self.config['homography'] = {
            'image_points': [[int(p[0]), int(p[1])] for p in self.image_points],
            'world_points': [[float(p[0]), float(p[1])] for p in self.world_points]
        }
        
        # Save to file
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
        
        print(f"\nSaved camera calibration to: {self.config_path}")
        print("\nCalibration Summary:")
        for i in range(len(self.image_points)):
            print(f"  Point {i+1}: Pixel{self.image_points[i]} -> World({self.world_points[i][0]}m, {self.world_points[i][1]}m)")
        return True
    
    def reset(self):
        """Reset all points."""
        self.image_points = []
        self.world_points = []
        self.update_display()
        print("\nCalibration reset")
    
    def run(self):
        """Run the interactive calibration."""
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        
        self.update_display()
        
        print("\n" + "="*70)
        print("Camera Calibration Tool")
        print("="*70)
        print(f"Image: {self.image_path}")
        print(f"Config: {self.config_path}")
        print(f"Image size: {self.image.shape[1]}x{self.image.shape[0]}")
        print("\nInstructions:")
        print("  1. Click 4 points on the ROAD PLANE (not on walls/signs)")
        print("  2. For each point, enter its real-world coordinates in METERS")
        print("  3. Use known distances (lane width, markings, etc.)")
        print("  4. Press 's' to save, 'r' to reset, 'q' to quit")
        print("\nTips:")
        print("  - Choose points that form a rectangle or quadrilateral")
        print("  - Standard lane width: 3.5m")
        print("  - Use Google Maps to measure distances")
        print("  - All points must be on the same flat road surface")
        print("="*70 + "\n")
        
        while True:
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('s'):
                if self.save_config():
                    print("\nConfiguration saved! You can close the window or continue editing.")
            
            elif key == ord('r'):
                self.reset()
            
            elif key == ord('q'):
                print("Exiting without saving.")
                break
        
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(
        description='Interactive camera calibration tool for speed estimation'
    )
    parser.add_argument('--image', required=True,
                       help='Path to image or video (will extract first frame)')
    parser.add_argument('--config', required=True,
                       help='Path to site config YAML to update')
    
    args = parser.parse_args()
    
    # Check if input is video or image
    image_path = args.image
    
    if args.image.endswith(('.mp4', '.avi', '.mov', '.mkv')):
        # Extract first frame from video
        print(f"Extracting frame from video: {args.image}")
        cap = cv2.VideoCapture(args.image)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print(f"Error: Could not read video: {args.image}")
            return
        
        # Save temporary frame
        temp_frame = "temp_calibration_frame.jpg"
        cv2.imwrite(temp_frame, frame)
        image_path = temp_frame
        print(f"Saved temporary frame: {temp_frame}")
    
    # Run calibration tool
    tool = CameraCalibrationTool(image_path, args.config)
    tool.run()
    
    # Clean up temp file
    if image_path == "temp_calibration_frame.jpg" and os.path.exists(image_path):
        os.remove(image_path)
        print(f"Cleaned up temporary frame")


if __name__ == '__main__':
    main()
