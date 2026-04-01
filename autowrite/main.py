import os
import uuid
import tempfile
from typing import List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from autowrite.handwriting_synthesis import Hand
import autowrite.handwriting_synthesis.config

app = FastAPI(title="AutoWrite API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    text: str
    max_line_length: int = 50
    lines_per_page: int = 30
    handwriting_consistency: float = 0.98
    styles: int = 1
    ink_color: str = "Blue"
    pen_thickness: float = 0.5
    line_height: int = 32
    total_lines_per_page: int = 30
    view_height: float = 210.0
    view_width: float = 148.0
    margin_left: int = 10
    margin_right: int = 10
    margin_top: int = 10
    margin_bottom: int = 10
    page_color: str = "white"
    margin_color: str = "red"
    line_color: str = "lightgray"

class PageResult(BaseModel):
    page_num: int
    svg_content: str
    gcode_content: str

class GenerateResponse(BaseModel):
    pages: List[PageResult]

# Global Hand instance
hand_instance = None

def get_hand_instance():
    global hand_instance
    if hand_instance is None:
        hand_instance = Hand()
    return hand_instance

def process_text_to_pages(text: str, max_line_length: int, lines_per_page: int, alphabet: list):
    lines = [line.strip() if line.strip() else "." for line in text.split("\n")]
    
    sanitized_lines = []
    for line in lines:
        sanitized_char_list = []
        for char in line:
            if char in alphabet:
                sanitized_char_list.append(char)
            elif char.lower() in alphabet:
                sanitized_char_list.append(char.lower())
            else:
                sanitized_char_list.append(" ")
        sanitized_lines.append("".join(sanitized_char_list))

    wrapped_lines = []
    for line in sanitized_lines:
        words = line.split()
        if not words:
            wrapped_lines.append("")
        else:
            current_line = ""
            for word in words:
                if current_line:
                    if len(current_line) + len(word) + 1 > max_line_length:
                        wrapped_lines.append(current_line.strip())
                        current_line = word
                    else:
                        current_line += " " + word
                else:
                    current_line = word
            if current_line:
                wrapped_lines.append(current_line.strip())

    pages = [
        wrapped_lines[i : i + lines_per_page]
        for i in range(0, len(wrapped_lines), lines_per_page)
    ]
    return pages

@app.post("/api/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    try:
        hand = get_hand_instance()
        
        alphabet = [
            "\x00", " ", "!", '"', "#", "'", "(", ")", ",", "-", ".", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", ":", ";", "?", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "R", "S", "T", "U", "V", "W", "Y", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"
        ]

        stroke_colors_map = {
            "Black": "#000000",
            "Blue": "#0000FF",
            "Red": "#FF0000",
            "Green": "#008000",
        }
        color_hex = stroke_colors_map.get(req.ink_color, "#0000FF")

        pages_lines = process_text_to_pages(req.text, req.max_line_length, req.lines_per_page, alphabet)

        page_config = {
            "page_color": req.page_color,
            "margin_color": req.margin_color,
            "line_color": req.line_color,
            "view_height": req.view_height,
            "view_width": req.view_width,
            "margin_left": -req.margin_left,
            "margin_right": -req.margin_right,
            "margin_top": -req.margin_top,
            "margin_bottom": -req.margin_bottom,
            "line_height": req.line_height,
            "total_lines": req.total_lines_per_page,
        }

        autowrite.handwriting_synthesis.config.background = False

        results = []
        with tempfile.TemporaryDirectory() as tmpdir:
            for page_num, page_lines in enumerate(pages_lines):
                base_filename = os.path.join(tmpdir, f"page_{page_num}.svg")
                
                hand.write(
                    filename=base_filename,
                    lines=page_lines,
                    biases=[req.handwriting_consistency] * len(page_lines),
                    styles=[req.styles] * len(page_lines),
                    stroke_colors=[color_hex] * len(page_lines),
                    stroke_widths=[req.pen_thickness] * len(page_lines),
                    page=page_config,
                )
                
                with open(base_filename, "r") as f:
                    svg_content = f.read()
                
                gcode_filename = base_filename.replace(".svg", ".gcode")
                with open(gcode_filename, "r") as f:
                    gcode_content = f.read()
                    
                results.append(PageResult(
                    page_num=page_num + 1,
                    svg_content=svg_content,
                    gcode_content=gcode_content
                ))
                
        return GenerateResponse(pages=results)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
