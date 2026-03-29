import numpy as np
import svgwrite
import cairosvg

from autowrite.handwriting_synthesis import drawing


def _draw(strokes, lines, filename, stroke_colors=None, stroke_widths=None, page=None):
    stroke_colors = stroke_colors or ["black"] * len(lines)
    stroke_widths = stroke_widths or [2] * len(lines)

    if isinstance(page, dict):
        line_height = page.get("line_height", 32)
        total_lines_per_page = page.get("total_lines", 24)
        view_height = page.get("view_height", 896)
        view_width = page.get("view_width", 632)
        margin_left = page.get("margin_left", -64)
        margin_top = page.get("margin_top", -96)
        page_color = page.get("page_color", "white")
        margin_color = page.get("margin_color", "red")
        line_color = page.get("line_color", "lightgray")
    else:
        (
            line_height,
            total_lines_per_page,
            view_height,
            view_width,
            margin_left,
            margin_top,
            page_color,
            margin_color,
            line_color,
        ) = page or [32, 24, 896, 632, -64, -96, "white", "red", "lightgray"]

    # Initialize G-code variables
    gcode_lines = [
        "$X",
        "G21 ; Set units to millimeters",
        "G90 ; Set to absolute positioning",
        "G1 F2000 ; Set feed rate for move speed",
        "G1 Z0 F800 ; PEN UP",
        "G0 X0 Y0 ; Move to start position (0,0)"
    ]
    px_to_mm = 25.4 / 96.0
    pen_is_down = False

    def add_gcode(cmd):
        gcode_lines.append(cmd)

    def pen_up():
        nonlocal pen_is_down
        if pen_is_down:
            add_gcode("G1 Z0 F800 ; PEN UP")
            pen_is_down = False

    def pen_down():
        nonlocal pen_is_down
        if not pen_is_down:
            add_gcode("G1 Z10 F800 ; PEN DOWN")
            pen_is_down = True

    def move_to_gcode(x, y):
        pen_up()
        add_gcode(f"G0 X{x * px_to_mm:.3f} Y{y * px_to_mm:.3f}")

    def line_to_gcode(x, y):
        pen_down()
        add_gcode(f"G1 X{x * px_to_mm:.3f} Y{y * px_to_mm:.3f} F2000")

    # Initialize the SVG drawing
    dwg = svgwrite.Drawing(
        filename=filename, size=(f"{view_width}px", f"{view_height}px")
    )
    dwg.viewbox(width=view_width, height=view_height)

    from autowrite.handwriting_synthesis.config import background

    if background:
        dwg.add(
            dwg.rect(insert=(0, 0), size=(view_width, view_height), fill=page_color)
        )

        # Draw fixed number of ruled lines
        for i in range(total_lines_per_page):
            y_position = (
                line_height * (i + 1) - margin_top
            )  # Adjust as needed to align with text
            dwg.add(
                dwg.line(
                    start=(0, y_position),
                    end=(view_width, y_position),
                    stroke=line_color,
                    stroke_width=1,
                )
            )
            move_to_gcode(0, y_position)
            line_to_gcode(view_width, y_position)

        dwg.add(
            dwg.line(
                start=(-margin_left + line_height / 2, 0),
                end=(-margin_left + line_height / 2, view_height),
                stroke=margin_color,
                stroke_width=1,
            )
        )
        move_to_gcode(-margin_left + line_height / 2, 0)
        line_to_gcode(-margin_left + line_height / 2, view_height)

        dwg.add(
            dwg.line(
                start=(-margin_left + line_height / 2 - 5, 0),
                end=(-margin_left + line_height / 2 - 5, view_height),
                stroke=margin_color,
                stroke_width=1,
            )
        )
        move_to_gcode(-margin_left + line_height / 2 - 5, 0)
        line_to_gcode(-margin_left + line_height / 2 - 5, view_height)

        dwg.add(
            dwg.line(
                start=(0, -margin_top),
                end=(view_width, -margin_top),
                stroke=margin_color,
                stroke_width=1,
            )
        )
        move_to_gcode(0, -margin_top)
        line_to_gcode(view_width, -margin_top)

        dwg.add(
            dwg.line(
                start=(0, -margin_top - 5),
                end=(view_width, -margin_top - 5),
                stroke=margin_color,
                stroke_width=1,
            )
        )
        move_to_gcode(0, -margin_top - 5)
        line_to_gcode(view_width, -margin_top - 5)

    initial_coord = np.array([margin_left, margin_top - line_height / 2])

    for i, (offsets, line, color, width) in enumerate(
        zip(strokes, lines, stroke_colors, stroke_widths)
    ):
        # Stop drawing text if lines exceed the fixed page limit
        if i >= total_lines_per_page:
            break

        if not line:
            initial_coord[1] -= line_height
            continue

        # Convert offsets to coordinates and adjust them
        offsets[:, :2] *= 1
        strokes = drawing.offsets_to_coords(offsets)
        strokes = drawing.denoise(strokes)
        strokes[:, :2] = drawing.align(strokes[:, :2])
        strokes[:, 1] *= -1
        strokes[:, :2] -= strokes[:, :2].min() + initial_coord

        # Create the path for handwriting strokes
        p = ""
        prev_eos = 1.0
        for x, y, eos in zip(*strokes.T):
            p += "{}{},{} ".format("M" if prev_eos == 1.0 else "L", x, y)
            if prev_eos == 1.0:
                move_to_gcode(x, y)
            else:
                line_to_gcode(x, y)
            prev_eos = eos
        path = svgwrite.path.Path(p)
        path = path.stroke(color=color, width="1px", linecap="round", linejoin="round").fill("none")
        dwg.add(path)

        initial_coord[1] -= line_height

    # Save the SVG file and convert to PNG
    dwg.save()
    cairosvg.svg2png(url=filename, write_to=filename + ".png")

    # Save the G-code file
    pen_up()
    add_gcode("G90 ; absolute")
    add_gcode("G0 X0 Y0 Z0 ; Move back to home")

    numbered_gcode = []
    for idx, line in enumerate(gcode_lines):
        numbered_gcode.append(f"N{(idx + 1) * 10} {line}")
    
    gcode_content = "\n".join(numbered_gcode) + "\n"
    gcode_filename = filename.replace(".svg", ".gcode") if filename.endswith(".svg") else filename + ".gcode"
    
    with open(gcode_filename, "w") as f:
        f.write(gcode_content)
