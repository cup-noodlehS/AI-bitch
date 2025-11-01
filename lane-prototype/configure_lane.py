"""
Interactive lane polygon configuration tool.
Click 4 corners to define the truck/bus lane polygon.
Press 's' to save, 'r' to reset, 'q' to quit.
"""
import argparse
import os

import cv2
import numpy as np
import yaml


class LaneConfigurator:
    def __init__(self, image_path, config_path):
        self.image_path = image_path
        self.config_path = config_path
        self.image = cv2.imread(image_path)
        if self.image is None:
            raise ValueError(f"Could not read image: {image_path}")
        
        self.display_image = self.image.copy()
        self.points = []  # List of (x, y) tuples for polygon corners
        self.max_points = 4
        
        # Load existing config if available
        self.config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            # Load existing polygon if present (new format)
            if 'truck_bus_lane_polygon' in self.config:
                self.points = [tuple(p) for p in self.config['truck_bus_lane_polygon']]
            # Load existing rectangle and convert to polygon (backward compatibility)
            elif 'truck_bus_lane_rect' in self.config:
                rect = self.config['truck_bus_lane_rect']
                x, y, w, h = rect['x'], rect['y'], rect['w'], rect['h']
                # Convert rectangle to 4-point polygon
                self.points = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        
        self.window_name = 'Lane Configuration - Click 4 Corners'
        
    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse events for clicking polygon corners."""
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(self.points) < self.max_points:
                # Add new point
                self.points.append((x, y))
                print(f"Point {len(self.points)}: ({x}, {y})")
                self.update_display()
            else:
                print(f"Already have {self.max_points} points. Press 'r' to reset.")
    
    def update_display(self):
        """Update the display with current polygon."""
        self.display_image = self.image.copy()
        
        # Draw polygon if we have points
        if len(self.points) > 0:
            # Draw points with numbers
            for i, point in enumerate(self.points):
                # Draw circle for each point
                cv2.circle(self.display_image, point, 8, (0, 255, 0), -1)
                # Draw point number
                cv2.putText(self.display_image, str(i + 1), 
                           (point[0] + 12, point[1] + 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Draw lines connecting points
            if len(self.points) > 1:
                for i in range(len(self.points)):
                    pt1 = self.points[i]
                    pt2 = self.points[(i + 1) % len(self.points)]
                    # Only draw line to next point if it exists, or close polygon if complete
                    if i < len(self.points) - 1 or len(self.points) == self.max_points:
                        cv2.line(self.display_image, pt1, pt2, (0, 255, 0), 2)
            
            # Fill polygon with semi-transparent overlay if complete
            if len(self.points) == self.max_points:
                overlay = self.display_image.copy()
                pts = np.array(self.points, np.int32)
                cv2.fillPoly(overlay, [pts], (0, 255, 0))
                cv2.addWeighted(overlay, 0.2, self.display_image, 0.8, 0, self.display_image)
                
                # Add label
                centroid_x = int(sum(p[0] for p in self.points) / len(self.points))
                centroid_y = int(sum(p[1] for p in self.points) / len(self.points))
                cv2.putText(self.display_image, "TRUCK/BUS LANE", 
                           (centroid_x - 80, centroid_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Instructions
        points_remaining = self.max_points - len(self.points)
        if points_remaining > 0:
            instructions = [
                f"Click {points_remaining} more corner(s) to define lane polygon",
                "Press 's' to save | 'r' to reset | 'q' to quit"
            ]
        else:
            instructions = [
                "Polygon complete! Press 's' to save",
                "Press 'r' to reset | 'q' to quit"
            ]
        
        for i, text in enumerate(instructions):
            cv2.putText(self.display_image, text, (10, 30 + i * 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow(self.window_name, self.display_image)
    
    def save_config(self):
        """Save the polygon to config file."""
        if len(self.points) != self.max_points:
            print(f"Need {self.max_points} points. Currently have {len(self.points)}.")
            return False
        
        # Update config with polygon format
        self.config['truck_bus_lane_polygon'] = [[int(p[0]), int(p[1])] for p in self.points]
        
        # Remove old rectangle format if present
        if 'truck_bus_lane_rect' in self.config:
            del self.config['truck_bus_lane_rect']
        
        # Save to file
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
        
        print(f"\nSaved lane polygon to: {self.config_path}")
        for i, p in enumerate(self.points):
            print(f"  Point {i+1}: ({p[0]}, {p[1]})")
        return True
    
    def reset(self):
        """Reset the polygon."""
        self.points = []
        self.update_display()
        print("Polygon reset")
    
    def run(self):
        """Run the interactive configuration."""
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        
        self.update_display()
        
        print("\n" + "="*60)
        print("Lane Polygon Configuration Tool")
        print("="*60)
        print(f"Image: {self.image_path}")
        print(f"Config: {self.config_path}")
        print(f"Image size: {self.image.shape[1]}x{self.image.shape[0]}")
        print("\nInstructions:")
        print("  - Click 4 corners to define the truck/bus lane polygon")
        print("  - Points will be numbered 1, 2, 3, 4")
        print("  - Press 's' to save the configuration")
        print("  - Press 'r' to reset and start over")
        print("  - Press 'q' to quit without saving")
        print("="*60 + "\n")
        
        while True:
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('s'):
                if self.save_config():
                    print("Configuration saved! You can now close the window or continue editing.")
            
            elif key == ord('r'):
                self.reset()
            
            elif key == ord('q'):
                print("Exiting without saving.")
                break
        
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(
        description='Interactive lane polygon configuration tool (4 corners)'
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
        temp_frame = "temp_config_frame.jpg"
        cv2.imwrite(temp_frame, frame)
        image_path = temp_frame
        print(f"Saved temporary frame: {temp_frame}")
    
    # Run configurator
    configurator = LaneConfigurator(image_path, args.config)
    configurator.run()
    
    # Clean up temp file
    if image_path == "temp_config_frame.jpg" and os.path.exists(image_path):
        os.remove(image_path)
        print(f"Cleaned up temporary frame")


if __name__ == '__main__':
    main()

