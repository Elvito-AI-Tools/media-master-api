"""
Utility functions for creating caption files (SRT/ASS) from text with various styles.

This module provides functions for:
1. Creating SRT and ASS subtitle files from text
2. Formatting timestamps for different subtitle formats
3. Styling captions with different visual effects (highlight, karaoke, word-by-word, underline)
"""
import os
import uuid
import logging
import subprocess
from typing import Dict, List, Optional

# Configure logging
logger = logging.getLogger(__name__)

def format_srt_timestamp(seconds: float) -> str:
    """
    Format seconds as SRT timestamp (HH:MM:SS,mmm).
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"

def format_ass_timestamp(seconds: float) -> str:
    """
    Format seconds as ASS timestamp (H:MM:SS.cc).
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centiseconds = int((seconds - int(seconds)) * 100)
    
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"

def convert_color_to_ass_with_alpha(color: str, opacity: float = 1.0) -> str:
    """
    Convert a color string to ASS subtitle format with alpha channel.
    
    Args:
        color: Color string in hex (#RRGGBB), named format, or rgb()
        opacity: Opacity value from 0.0 (transparent) to 1.0 (opaque)
        
    Returns:
        Color in ASS format with alpha (&HAABBGGRR&)
    """
    # Handle hex colors
    if color.startswith('#'):
        # Remove # and ensure 6 characters
        color = color.lstrip('#')
        if len(color) == 3:  # Shorthand #RGB
            color = ''.join([c*2 for c in color])
        
        try:
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
        except ValueError:
            logger.warning(f"Invalid hex color format: {color}")
            r, g, b = 255, 255, 255  # Default to white
    
    # Handle named colors
    elif color.lower() in {
        "white", "black", "red", "green", "blue", 
        "yellow", "cyan", "magenta", "gray", "purple"
    }:
        color_map = {
            "white": (255, 255, 255),
            "black": (0, 0, 0),
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 0, 255),
            "yellow": (255, 255, 0),
            "cyan": (0, 255, 255),
            "magenta": (255, 0, 255),
            "gray": (128, 128, 128),
            "purple": (128, 0, 128)
        }
        r, g, b = color_map[color.lower()]
    
    # Handle rgb() format
    elif color.startswith('rgb(') and color.endswith(')'):
        try:
            rgb = color[4:-1].split(',')
            if len(rgb) == 3:
                r = int(rgb[0].strip())
                g = int(rgb[1].strip())
                b = int(rgb[2].strip())
            else:
                r, g, b = 255, 255, 255  # Default to white
        except ValueError:
            logger.warning(f"Invalid rgb() color format: {color}")
            r, g, b = 255, 255, 255  # Default to white
    
    # Default for unrecognized formats
    else:
        logger.warning(f"Unrecognized color format: {color}, defaulting to white")
        r, g, b = 255, 255, 255
    
    # Convert opacity to ASS alpha (inverted)
    alpha = int((1 - opacity) * 255)
    
    # Format in ASS: &HAABBGGRR& (AA=alpha, BB=blue, GG=green, RR=red)
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}&"

def prepare_subtitle_styling(caption_properties: Optional[Dict] = None) -> Dict:
    """
    Prepare subtitle styling options for FFmpeg based on caption properties.
    
    Args:
        caption_properties: Dictionary of caption styling properties
        
    Returns:
        Dictionary of FFmpeg subtitle styling options
    """

    print(f"Preparing subtitle styling with properties: {caption_properties}")
    if not caption_properties:
        return {}
    
    # Define default options
    options = {
        'FontName': 'Arial',
        'FontSize': 48,
        'PrimaryColour': '&HFFFFFF&',  # White
        'OutlineColour': '&H000000&',  # Black
        'BackColour': '&H000000&',    # Black
        'SecondaryColour': '&HFFFF00&',  # Yellow for highlighted words
        'Bold': 0,
        'Italic': 0,
        'Underline': 0,
        'StrikeOut': 0,
        'Alignment': 2,  # Center-bottom aligned
        'MarginV': 20,
        'MarginL': 20,
        'MarginR': 20,
        'Outline': 2,
        'Shadow': 1,
        'Spacing': 0,
        'Angle': 0,
        'BorderStyle': 1  # Default to outline + drop shadow
    }
    
    # Determine caption style
    style_value = caption_properties.get("style")
    style = style_value.lower() if style_value else "highlight"
    
    # Map properties to ASS style options
    if caption_properties.get("font_family"):
        requested_font = caption_properties["font_family"]
        options['FontName'] = requested_font
        logger.info(f"Font family requested: '{requested_font}'")
        
        # Check if the requested font exists on the system
        try:
            # Run fc-list to check if the font is available
            font_check_cmd = ["fc-list", requested_font]
            font_check_result = subprocess.run(
                font_check_cmd, 
                capture_output=True,
                text=True
            )
            
            if font_check_result.stdout.strip():
                logger.info(f"Font '{requested_font}' is available on the system")
            else:
                logger.warning(f"Font '{requested_font}' may not be available on the system, falling back to Arial")
                logger.info(f"Available fonts similar to '{requested_font}': {subprocess.run(['fc-list', ':', 'family', '|', 'grep', '-i', requested_font], capture_output=True, text=True).stdout.strip()}")
        except Exception as e:
            logger.warning(f"Error checking font availability: {e}")
    
    if caption_properties.get("font_size"):
        options['FontSize'] = caption_properties["font_size"]
    
    # Handle colors
    if caption_properties.get("line_color"):
        options['PrimaryColour'] = convert_color_to_ass_with_alpha(
            caption_properties["line_color"],
            caption_properties.get("line_opacity", 1.0)
        )
        logger.info(f"Setting line color to {options['PrimaryColour']} (AABBGGRR format)")
    
    if caption_properties.get("outline_color"):
        options['OutlineColour'] = convert_color_to_ass_with_alpha(
            caption_properties["outline_color"],
             1.0
        )
        logger.info(f"Setting outline color to {options['OutlineColour']} (AABBGGRR format)")
    
    # Word color is specially important for highlight style
    if caption_properties.get("word_color"):
        options['SecondaryColour'] = convert_color_to_ass_with_alpha(
            caption_properties["word_color"],
             1.0
        )
        logger.info(f"Setting word color to {options['SecondaryColour']} (AABBGGRR format)")
    
    # Handle background properties
    if caption_properties.get("background_color"):
        # Set the border style first
        options['BorderStyle'] = 4  # Opaque box
        
        options['BackColour'] = convert_color_to_ass_with_alpha(
            caption_properties["background_color"],
            caption_properties.get("background_opacity", 1.0)
        )
        logger.info(f"Setting background color to {options['BackColour']} (AABBGGRR format)")
        
        # When using background, disable outline but keep minimal shadow
        options['Outline'] = 0
        options['Shadow'] = 1
        
        # Handle padding through margins
        if caption_properties.get("background_padding") is not None:
            padding = caption_properties["background_padding"]
            options['MarginL'] = padding
            options['MarginR'] = padding
            options['MarginV'] = padding
    
    # Handle boolean properties
    for prop, option in [
        ("bold", "Bold"), 
        ("italic", "Italic"),
        ("underline", "Underline"),
        ("strikeout", "StrikeOut")
    ]:
        if prop in caption_properties and caption_properties[prop] is not None:
            options[option] = 1 if caption_properties[prop] else 0
    
    # Handle numeric properties
    for prop, option in [
        ("outline_width", "Outline"),
        ("shadow_offset", "Shadow"),
        ("spacing", "Spacing"),
        ("angle", "Angle")
    ]:
        if prop in caption_properties and caption_properties[prop] is not None:
            options[option] = caption_properties[prop]
    
    # Handle alignment
    if caption_properties.get("position"):
        # Map predefined positions to alignment values
        position_map = {
            "bottom_left": 1, "bottom_center": 2, "bottom_right": 3,
            "middle_left": 4, "middle_center": 5, "middle_right": 6,
            "top_left": 7, "top_center": 8, "top_right": 9
        }
        if caption_properties["position"] in position_map:
            options['Alignment'] = position_map[caption_properties["position"]]
    elif caption_properties.get("alignment"):
        alignment_map = {"left": 1, "center": 2, "right": 3}
        if caption_properties["alignment"] in alignment_map:
            options['Alignment'] = alignment_map[caption_properties["alignment"]]
    
    # Style-specific adjustments
    if style == "highlight":
        if not caption_properties.get("word_color"):
            options['SecondaryColour'] = "&HFFFF00&"  # Yellow for highlighted words
    elif style == "word_by_word":
        if not caption_properties.get("word_color"):
            options['PrimaryColour'] = "&HFFFF00&"  # Yellow for word-by-word
    
    # Log the final options for debugging
    logger.info(f"Final subtitle styling options: {options}")
    
    return options

async def create_standard_ass_from_timestamps(
    word_timestamps: List[Dict],
    duration: float,
    max_words_per_line: int,
    output_path: str,
    caption_properties: Optional[Dict] = None
) -> None:
    """
    Create a standard ASS subtitle file from word timestamps without special styling effects.
    
    Args:
        word_timestamps: List of word timestamps
        duration: Duration in seconds
        max_words_per_line: Maximum words per line
        output_path: Output file path
        caption_properties: Dictionary of caption styling properties
    """
    try:
        # Prepare styling options
        style_options = prepare_subtitle_styling(caption_properties)
        
        # Get style properties
        primary_color = style_options.get('PrimaryColour', '&HFFFFFF&')  # Default white
        secondary_color = style_options.get('SecondaryColour', '&HFFFF00&')  # Default yellow
        outline_color = style_options.get('OutlineColour', '&H000000&')  # Default black
        back_color = style_options.get('BackColour', '&H000000&')  # Default black
        
        # Get font properties
        font_name = style_options.get('FontName', 'Arial')
        font_size = style_options.get('FontSize', 48)
        bold = style_options.get('Bold', 0)
        italic = style_options.get('Italic', 0)
        underline = style_options.get('Underline', 0)
        strikeout = style_options.get('StrikeOut', 0)
        
        # Get other style properties
        border_style = style_options.get('BorderStyle', 1)
        outline = style_options.get('Outline', 2)
        shadow = style_options.get('Shadow', 0)
        alignment = style_options.get('Alignment', 2)
        margin_l = style_options.get('MarginL', 20)
        margin_r = style_options.get('MarginR', 20)
        margin_v = style_options.get('MarginV', 20)
        
        # Group words into lines
        lines = []
        current_line = []
        for word_data in word_timestamps:
            word = word_data.get("word", "").strip()
            if word:
                current_line.append(word_data)
                if len(current_line) >= max_words_per_line:
                    lines.append(current_line)
                    current_line = []
        
        # Add the last line if there are remaining words
        if current_line:
            lines.append(current_line)
        
        # Create ASS header
        ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
"""
        # Add the style with proper colors
        ass_content += f"Style: Default,{font_name},{font_size},{primary_color},{secondary_color},{outline_color},{back_color},{bold},{italic},{underline},{strikeout},100,100,0,0,{border_style},{outline},{shadow},{alignment},{margin_l},{margin_r},{margin_v},0\n\n"
        
        ass_content += """[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        # Add dialogue events for each line (standard text without special effects)
        for line_idx, line_words in enumerate(lines):
            # Create the text for the line
            line_text = ' '.join([word_data.get("word", "").strip() for word_data in line_words])
            line_start = line_words[0].get("start", 0)
            line_end = line_words[-1].get("end", duration)
            
            start_time_str = format_ass_timestamp(line_start)
            end_time_str = format_ass_timestamp(line_end)
            
            # Standard text line
            ass_content += f"Dialogue: 0,{start_time_str},{end_time_str},Default,,0,0,0,,{line_text}\n"
        
        # Write the ASS content to the output file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)
        
        logger.info(f"Created standard ASS file with {len(lines)} lines from word timestamps")
    
    except Exception as e:
        logger.error(f"Error creating standard ASS from timestamps: {e}")
        raise

async def create_srt_from_word_timestamps(
    word_timestamps: List[Dict],
    duration: float,
    max_words_per_line: int = 10,
    style: str = "",
    caption_properties: Optional[Dict] = None
) -> str:
    """
    Create subtitle file from word-level timestamps with precise timing.
    
    Args:
        word_timestamps: List of word timestamps from transcription
                         Each item should have 'word', 'start', and 'end' keys
        duration: Duration of the audio/video in seconds
        max_words_per_line: Maximum words per line
        style: Caption style (highlight, word_by_word)
        caption_properties: Dictionary of caption styling properties
        
    Returns:
        Path to generated subtitle file
    """
    try:
        # Create a temp subtitle file
        subtitle_path = os.path.join("temp", f"caption_{uuid.uuid4()}")
        
        # Add .ass extension for all styles
        subtitle_path += ".ass"
        
        # Process based on style
        if style == "highlight":
            await create_highlight_style_ass_from_timestamps(word_timestamps, duration, max_words_per_line, subtitle_path, caption_properties)
        elif style == "word_by_word":
            await create_word_by_word_style_ass_from_timestamps(word_timestamps, duration, max_words_per_line, subtitle_path)
        else:
            # Use standard ASS without special styling but with caption properties
            await create_standard_ass_from_timestamps(word_timestamps, duration, max_words_per_line, subtitle_path, caption_properties)
        
        logger.info(f"Created subtitle file with style {style} at {subtitle_path} using word timestamps")
        return subtitle_path
    
    except Exception as e:
        logger.error(f"Error creating subtitle file from word timestamps: {e}")
        raise

async def create_highlight_style_ass_from_timestamps(
    word_timestamps: List[Dict],
    duration: float,
    max_words_per_line: int,
    output_path: str,
    caption_properties: Optional[Dict] = None
) -> None:
    """
    Create an ASS subtitle file with highlight style from word timestamps.
    
    Args:
        word_timestamps: List of word timestamps
        duration: Duration in seconds
        max_words_per_line: Maximum words per line
        output_path: Output file path
        caption_properties: Dictionary of caption styling properties
    """
    try:
        # Prepare styling options
        style_options = prepare_subtitle_styling(caption_properties)
        
        # Get colors from style options
        primary_color = style_options.get('PrimaryColour', '&HFFFFFF&')  # Default white
        secondary_color = style_options.get('SecondaryColour', '&HFFFF00&')  # Default yellow
        outline_color = style_options.get('OutlineColour', '&H000000&')  # Default black
        back_color = style_options.get('BackColour', '&H000000&')  # Default black
        
        # Get font properties
        font_name = style_options.get('FontName', 'Arial')
        font_size = style_options.get('FontSize', 48)
        bold = style_options.get('Bold', 0)
        italic = style_options.get('Italic', 0)
        underline = style_options.get('Underline', 0)
        strikeout = style_options.get('StrikeOut', 0)
        
        # Get other style properties
        border_style = style_options.get('BorderStyle', 1)
        outline = style_options.get('Outline', 2)
        shadow = style_options.get('Shadow', 0)
        alignment = style_options.get('Alignment', 2)
        margin_l = style_options.get('MarginL', 20)
        margin_r = style_options.get('MarginR', 20)
        margin_v = style_options.get('MarginV', 20)
        
        # Group words into lines
        lines = []
        current_line = []
        for word_data in word_timestamps:
            word = word_data.get("word", "").strip()
            if word:
                current_line.append(word_data)
                if len(current_line) >= max_words_per_line:
                    lines.append(current_line)
                    current_line = []
        
        # Add the last line if there are remaining words
        if current_line:
            lines.append(current_line)
        
        # Create ASS header
        ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
"""
        # Add the style with proper colors
        ass_content += f"Style: Default,{font_name},{font_size},{primary_color},{secondary_color},{outline_color},{back_color},{bold},{italic},{underline},{strikeout},100,100,0,0,{border_style},{outline},{shadow},{alignment},{margin_l},{margin_r},{margin_v},0\n\n"
        
        ass_content += """[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        # Add dialogue events for each line (base text)
        event_counter = 0
        for line_idx, line_words in enumerate(lines):
            # Create the base text for the line
            line_text = ' '.join([word_data.get("word", "").strip() for word_data in line_words])
            line_start = line_words[0].get("start", 0)
            line_end = line_words[-1].get("end", duration)
            
            start_time_str = format_ass_timestamp(line_start)
            end_time_str = format_ass_timestamp(line_end)
            
            # Base text line - layer 0 (bottom layer)
            ass_content += f"Dialogue: 0,{start_time_str},{end_time_str},Default,,0,0,0,,{line_text}\n"
            
            # Add individual highlighting for each word in the line
            for word_idx, word_data in enumerate(line_words):
                word = word_data.get("word", "").strip()
                if not word:
                    continue
                    
                word_start = word_data.get("start", 0)
                word_end = word_data.get("end", 0)
                
                word_start_str = format_ass_timestamp(word_start)
                word_end_str = format_ass_timestamp(word_end)
                
                # Create highlighted version of this word within the line
                highlighted_words = []
                for i, w_data in enumerate(line_words):
                    w = w_data.get("word", "").strip()
                    if i == word_idx:
                        # This is the current word - highlight it using the secondary color
                        # Use the color code without the &H and & parts for the \c tag
                        secondary_color_code = secondary_color.replace('&H', '').replace('&', '')
                        primary_color_code = primary_color.replace('&H', '').replace('&', '')
                        highlighted_words.append(f"{{\\c{secondary_color_code}}}{w}{{\\c{primary_color_code}}}")
                    else:
                        # Regular word
                        highlighted_words.append(w)
                
                highlighted_text = ' '.join(highlighted_words)
                
                # Highlighted word line - layer 1 (top layer)
                ass_content += f"Dialogue: 1,{word_start_str},{word_end_str},Default,,0,0,0,,{highlighted_text}\n"
                
                event_counter += 1
        
        # Write the ASS content to the output file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)
        
        logger.info(f"Created highlight style ASS file with {event_counter} events from word timestamps")
    
    except Exception as e:
        logger.error(f"Error creating highlight style ASS from timestamps: {e}")
        raise

async def create_word_by_word_style_ass_from_timestamps(
    word_timestamps: List[Dict],
    duration: float,
    max_words_per_line: int,
    output_path: str
) -> None:
    """
    Create an ASS subtitle file with word-by-word style from word timestamps.
    
    Args:
        word_timestamps: List of word timestamps
        duration: Duration in seconds
        max_words_per_line: Maximum words per line (not used in this style)
        output_path: Output file path
    """
    try:
        # Create ASS header
        ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&HFFFF00&,&HFFFF00&,&H000000&,&H000000&,0,0,0,0,100,100,0,0,1,2,0,2,20,20,20,0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        # Add events for each word
        word_count = 0
        for word_data in word_timestamps:
            word = word_data.get("word", "").strip()
            if not word:
                continue
                
            start_time = word_data.get("start", 0)
            end_time = word_data.get("end", 0)
            
            start_time_str = format_ass_timestamp(start_time)
            end_time_str = format_ass_timestamp(end_time)
            
            # Add the word as a separate dialogue event
            ass_content += f"Dialogue: 0,{start_time_str},{end_time_str},Default,,0,0,0,,{word}\n"
            word_count += 1
        
        # Write the ASS content to the output file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)
        
        logger.info(f"Created word-by-word style ASS file with {word_count} words from word timestamps")
    
    except Exception as e:
        logger.error(f"Error creating word-by-word style ASS from timestamps: {e}")
        raise

async def create_srt_from_text(text: str, duration: float, max_words_per_line: int = 10, style: str = "highlight") -> str:
    """
    Create an SRT subtitle file from text with simple timing.
    
    Args:
        text: The caption text
        duration: Duration of the video in seconds
        max_words_per_line: Maximum words per line
        style: Caption style (highlight, word_by_word)
        
    Returns:
        Path to generated SRT file
    """
    try:
        # Create a temp subtitle file with .ass extension
        output_path = os.path.join("temp", f"caption_{uuid.uuid4()}.ass")
        
        # Split text into words
        words = text.split()
        
        # Create artificial word timestamps by distributing evenly
        word_count = len(words)
        if word_count == 0:
            raise ValueError("No words found in text")
            
        seconds_per_word = duration / word_count
        
        # Create artificial word timestamps
        word_timestamps = []
        for i, word in enumerate(words):
            start_time = i * seconds_per_word
            end_time = (i + 1) * seconds_per_word
            word_timestamps.append({
                "word": word,
                "start": start_time,
                "end": end_time
            })
        
        # Use appropriate method based on style
        if style == "highlight":
            await create_highlight_style_ass_from_timestamps(word_timestamps, duration, max_words_per_line, output_path, None)
        elif style == "word_by_word":
            await create_word_by_word_style_ass_from_timestamps(word_timestamps, duration, max_words_per_line, output_path)
        else:
            # Default to highlight style for any unsupported style
            logger.warning(f"Unsupported style '{style}', falling back to highlight style")
            await create_highlight_style_ass_from_timestamps(word_timestamps, duration, max_words_per_line, output_path, None)
            
        logger.info(f"Created subtitle file with style {style} at {output_path}")
        return output_path
    
    except Exception as e:
        logger.error(f"Error creating subtitle file: {e}")
        raise 