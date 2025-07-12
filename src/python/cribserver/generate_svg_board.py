from math import pi, sin, cos
import svgwrite

def inch_to_px(inches):
    return int(inches * 96.0)

# Constants (converted to pixels, 1" = 96px)
BOARD_WIDTH = inch_to_px(3.5)
BOARD_HEIGHT = inch_to_px(12)
HOLE_DIAMETER = inch_to_px(0.125)
HOLE_RADIUS = HOLE_DIAMETER / 2
# space between edges of holes
SPACE_BETWEEN_POINTS = inch_to_px(3/32)
# space between hole centers
HOLE_SPACING = SPACE_BETWEEN_POINTS + HOLE_DIAMETER
# start_x and start_y are relative to the hole center at the bottom left of board
START_X = inch_to_px(9/32) + HOLE_RADIUS
START_Y = BOARD_HEIGHT - inch_to_px(2) - HOLE_RADIUS
# vertical gap between centers between 5 point groups
GROUP_VERT_GAP = inch_to_px(5/16)
# 
GAP_BETWEEN_COLS = inch_to_px(1.25)


# Create SVG drawing
dwg = svgwrite.Drawing('static/board.svg', size=(BOARD_WIDTH, BOARD_HEIGHT), viewBox=(0, 0, BOARD_WIDTH, BOARD_HEIGHT))

# Draw board outline
dwg.add(dwg.rect((0, 0), (BOARD_WIDTH, BOARD_HEIGHT), fill='none', stroke='black', stroke_width=2))

# Function to add a group of 3 holes
def add_hole_group(dwg, x, y, angle_degrees=0.0, reverse_colors=False):
    '''
    angle_degrees is 0 horizontally (holes from left to right)
    angle_degrees progresses clockwise
    '''
    if reverse_colors:
        colors = ('blue', 'red', 'black')
    else:
        colors = ('black', 'red', 'blue')
    angle_rad = angle_degrees * 2 * pi / 360
    step_x_ratio = cos(angle_rad)
    step_y_ratio = sin(angle_rad)
    step_x = HOLE_SPACING * step_x_ratio
    step_y = HOLE_SPACING * step_y_ratio
    dwg.add(dwg.circle(center=(x, y), r=HOLE_RADIUS, fill='none', stroke=colors[0]))
    x += step_x
    y += step_y
    dwg.add(dwg.circle(center=(x, y), r=HOLE_RADIUS, fill='none', stroke=colors[1]))
    x += step_x
    y += step_y
    dwg.add(dwg.circle(center=(x, y), r=HOLE_RADIUS, fill='none', stroke=colors[2]))

# draw grid every inch
y_offset = BOARD_HEIGHT
for i in range(1, 12):
    y_offset -= inch_to_px(1)
    print(y_offset)
    dwg.add(dwg.line(start=(0, y_offset), end=(12, y_offset), stroke='black', stroke_width=1))

# Left (1-35), middle (86-120), right (46-80) side: Points 1–15 (3 groups of 5)
# draw from bottom to top
y_offset = START_Y
for group in range(7):
    # 7 groups
    for point in range(5):
        # group of 5 points (across left, right, center)
        left_x = START_X
        for col in range(3):
            # left, right, center
            add_hole_group(dwg, left_x, y_offset, reverse_colors=(col == 2))
            left_x += GAP_BETWEEN_COLS
        y_offset -= HOLE_SPACING
    # gap between groups of 5
    y_offset += HOLE_SPACING  # revert last change to y_offset
    y_offset -= GROUP_VERT_GAP

# top curve. 10 points total
center_x = BOARD_WIDTH / 2
center_y = START_Y - inch_to_px(8)
radius = inch_to_px(1 + 15/32)
for angle_deg in range(15, 180, 15):
    if angle_deg == 90:
        continue  # skip center
    angle_rad = angle_deg * 2 * pi / 360.
    pt_x = center_x - cos(angle_rad) * radius
    pt_y = center_y - sin(angle_rad) * radius
    add_hole_group(dwg, pt_x, pt_y, angle_deg)

# lower right curve. 5 points
#center_x = inch_to_px(1.75 + 0.625)
center_x = inch_to_px(1.75 + 0.7)
center_y = START_Y + inch_to_px(0.1)
radius = inch_to_px(0.375)
for angle_deg in range(30, 180, 30):
    angle_rad = angle_deg * 2 * pi / 360.
    pt_x = center_x + cos(angle_rad) * radius
    pt_y = center_y + sin(angle_rad) * radius
    add_hole_group(dwg, pt_x, pt_y, angle_deg, reverse_colors=True)

# finish hole
dwg.add(dwg.circle(center=(BOARD_WIDTH / 2, inch_to_px(1 + 13/32)), r=HOLE_RADIUS, fill='none', stroke='black'))

def draw_point_count(text, x, y):
    '''
    x and y are the center position
    '''
    point_size = 14
    point_px = inch_to_px(point_size / 72)
    text_width = len(text) * point_px / 2
    x -= text_width / 2
    y += point_px / 2
    dwg.add(dwg.text(text, insert=(x, y), fill='green', font_size=f'{point_size}px'))
    
#
TEXT = '''
START 85 80
5 90 75
10 95 70
15 100 65
20 105 60
25 110 55
30 115 50
35 120 45
'''.strip().splitlines()
text_y = START_Y + inch_to_px(0.12)
for line in TEXT:
    text_x = START_X + HOLE_SPACING
    for part in line.split():
        draw_point_count(part, text_x, text_y)
        text_x += GAP_BETWEEN_COLS
    text_y -= (5 * HOLE_DIAMETER + 4 * SPACE_BETWEEN_POINTS + inch_to_px(14/72))

        
'''
# Curved transition: Points 16–25 (approximate scatter)
curve_x = [24, 60, 96, 132, 168, 204, 240, 276, 312, 312]  # Approximate x-coordinates
curve_y = [528, 480, 432, 384, 336, 288, 240, 192, 144, 96]  # Approximate y-coordinates
for x, y in zip(curve_x, curve_y):
    add_hole_group(dwg, x, y)
'''

# Save the SVG file
dwg.save()
