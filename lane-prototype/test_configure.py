"""
Quick test of the lane configuration tool with existing test frame.
This demonstrates the tool without requiring user interaction.
"""
import cv2
import yaml

# Load test frame
image = cv2.imread("footage/siteA/test_frame.jpg")
if image is None:
    print("Test frame not found. Run test_image.py first.")
    exit(1)

# Draw example rectangle
x, y, w, h = 820, 300, 220, 380
cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
cv2.putText(image, "TRUCK/BUS LANE", (x + 5, y - 10),
           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
cv2.putText(image, f"x:{x} y:{y} w:{w} h:{h}", (x + 5, y + h + 25),
           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

# Add instructions
instructions = [
    "Example: Lane Rectangle Configuration",
    "Use configure_lane.py to draw your own rectangle"
]
for i, text in enumerate(instructions):
    cv2.putText(image, text, (10, 30 + i * 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

# Save example
cv2.imwrite("runs/images/lane_config_example.jpg", image)
print("Saved example to: runs/images/lane_config_example.jpg")
print(f"  Rectangle: x={x}, y={y}, w={w}, h={h}")
print("\nTo configure your own lane rectangle, run:")
print("  python configure_lane.py --image footage/siteA/video.mp4 --config footage/siteA/config.yaml")

