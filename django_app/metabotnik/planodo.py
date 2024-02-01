import os, sys, re
import math, random
from PIL import Image, UnidentifiedImageError
import warnings
import json
from progress.bar import Bar
import time


# Disable the warnings for giant images
Image.MAX_IMAGE_PIXELS = None
warnings.simplefilter("ignore", Image.DecompressionBombWarning)

MAX_WIDTH = 175000
MAX_HEIGHT = 100000


class Last:
    pass


class BitmapFile(object):
    def __init__(self, path, width, height):
        self.path = path
        self.width = width
        self.height = height
        self.is_break = False
        self.metadata = {}

    def __str__(self):
        return "%s %sx%s" % (self.path, self.width, self.height)

    def __lt__(self, other):
        return self.path < other.path

    __repr__ = __str__


def layout(
    project,
    frame=0,
    layout_mode="horizontal",
    background_color="#ffffff",
    onestripe=False,
):
    width = MAX_WIDTH + 1
    height = MAX_HEIGHT + 1

    iterations = 0
    scale_factor = 1
    iter_max = 10
    while (width > MAX_WIDTH) or (height > MAX_HEIGHT):
        if layout_mode == "hstrip":
            data = make_h_strip(
                project, background_color=background_color, scale_factor=scale_factor
            )
        else:
            data = horzvert_layout(
                project,
                frame=frame,
                background_color=background_color,
                scale_factor=scale_factor,
                layout_mode=layout_mode,
                onestripe=onestripe,
            )

        iterations += 1
        if iterations > iter_max:
            raise Exception(f"Layout iterations exceeds {iter_max}")
        scale_factor -= 0.1
        if scale_factor <= 0:
            raise Exception("Layout scale_fator <= 0")
        width = data.get("width", 0)
        height = data.get("height", 0)

    return data


def make_h_strip(files, background_color="#ffffff", scale_factor=1):
    stripe_height = int(max(f.height for f in files) * scale_factor)

    x, y = 0, 0
    data = {"images": [], "background_color": background_color}
    for f in files:
        ratio = f.width / f.height
        new_width = int(stripe_height * ratio)
        tmp = {
            "filename": f.path,
            "x": x,
            "y": y,
            "width": new_width,
            "height": stripe_height,
        }
        x += new_width
        data["images"].append(tmp)

    data["width"] = x
    data["height"] = stripe_height

    return data


def horzvert_layout(
    files,
    layout_mode="horizontal",
    background_color="#ffffff",
    frame=0,
    scale_factor=1,
    onestripe=False,
):
    """Do the layout and produce a usable dict output that can be persisted with the Project.
    We used to save these as attributes in the File objects.
    """
    # Allow overrriding the row_height by having a paramater passed in
    if len(files) < 1:
        return {}

    # Make a copy so we don't 'empty' the incoming files var
    files = files[:]

    if layout_mode == "horizontal":
        stripe_height = int(max(f.height for f in files) * scale_factor) + frame
        print(f"Stripe height: {stripe_height}")
        if frame == "slide":
            frame = stripe_height / 2
            stripe_height += frame * 2
    if layout_mode.startswith("vertical"):
        stripe_width = int(max(f.width for f in files) * scale_factor) + frame
        if frame == "slide":
            frame = stripe_width / 2
            stripe_width += frame * 2

    # If a frame was passed in, adjust the x,y of all items to give them that much spacing as a frame
    try:
        frame = int(frame)
    except ValueError:
        frame = 0

    # Calculate a new width/height for the files
    # based on making them all the same height
    for f in files:
        if layout_mode == "horizontal":
            f.new_height = stripe_height
            if f.height != stripe_height:
                ratio = float(f.width) / float(f.height)
                f.new_width = int(stripe_height * ratio)
                # print(f"change height and width, height: {f.height}, width: {f.new_width}")
            else:
                f.new_width = f.width
        elif layout_mode.startswith("vertical"):
            f.new_width = stripe_width
            if f.width != stripe_width:
                ratio = float(f.height) / float(f.width)
                f.new_height = int(stripe_width * ratio)
            else:
                f.new_height = f.height
        else:
            f.new_width = f.width
            f.new_height = f.height

    # Given the files, how many should there be per row
    # and how wide should a row be?
    # calc_row_width_height
    if onestripe:
        count_per_stripe = len(files) + 1
    else:
        count_per_stripe = int(round(math.sqrt(len(files))))
    average_width = sum(f.new_width for f in files) / len(files)
    print(f"Average width: {average_width}")
    average_height = sum(f.new_height for f in files) / len(files)
    print(f"Average height: {average_height}")

    if layout_mode == "horizontal":
        stripe_size = count_per_stripe * (average_width + frame * count_per_stripe)
        # But there could be a case where one of the images has a width bigger than the entire stripe!
        stripe_size = max(max(f.new_width for f in files), stripe_size)
        stripe_width = stripe_size

    elif layout_mode.startswith("vertical"):
        stripe_size = count_per_stripe * (average_height + frame * count_per_stripe)
        stripe_height = stripe_size
    else:
        stripe_size = count_per_stripe * average_height
        stripe_width = stripe_height = stripe_size

    # Make the stripes by calculating an offset for where the
    # images should be placed
    new_files = []
    stripe_idx, stripes = 0, []
    x, y = 0, 0
    thefile = None
    cur_size = 0
    if len(files) == 1:
        margin = stripe_size + 1
    else:
        margin = stripe_size * 0.965

    stripe_height += 50  # small space between stripes

    idx = 0
    while files or thefile:
        idx += 1

        if not thefile:
            thefile = files.pop(0)  # just feels wrong to name it 'file'
            new_files.append(thefile)

        if layout_mode == "horizontal":
            if (cur_size + thefile.new_width) < margin:
                thefile.x = x
                thefile.y = y
                thefile.stripe = stripe_idx
                x += thefile.new_width + 100
                cur_size += thefile.new_width + 100
                dontfit = True if thefile.is_break else False
                thefile = None
                x += frame
            else:
                dontfit = True
            if dontfit and (cur_size > 0):
                stripes.append(cur_size)
                stripe_idx += 1
                cur_size = 0
                x = 0
                y += stripe_height
                y += frame
            # could be a single giant image
            if dontfit and (cur_size == 0) and (thefile.new_width > margin):
                x = 0
                thefile.x = x
                thefile.y = y
                thefile.stripe = stripe_idx
                cur_size += thefile.new_width
                thefile = None
                y += stripe_height
                y += frame
                stripe_idx += 1
                stripes.append(cur_size)
                cur_size = 0
        elif layout_mode.startswith("vertical"):
            if (cur_size + thefile.new_height) < margin:
                thefile.x = x
                thefile.y = y
                thefile.stripe = stripe_idx
                y += thefile.new_height
                cur_size += thefile.new_height
                dontfit = True if thefile.is_break else False
                thefile = None
                y += frame
            else:
                dontfit = True
            if dontfit and (cur_size > 0):
                stripes.append(cur_size)
                stripe_idx += 1
                cur_size = 0
                y = 0
                x += stripe_width
                x += frame
        else:
            thefile.x = random.randint(0, stripe_width - thefile.width)
            thefile.y = random.randint(0, stripe_height - thefile.height)
            thefile = None

    if len(stripes) < (stripe_idx + 1):
        stripes.append(cur_size)

    if layout_mode == "horizontal":
        # In horizontal layout_mode, each stripe has an actual width that is less than the stripe_width
        # To make the layout nicely centered, adjust each x with an offset.
        for f in new_files:
            offset = (stripe_width - stripes[f.stripe]) / 2
            f.x = f.x + offset
        canvas_width = stripe_width
        canvas_height = stripe_height * len(stripes)
        print(f"Stripe height: {stripe_height}")
        print(f"Len of stripes: {len(stripes)}")
    elif layout_mode == "vertical":
        for f in new_files:
            offset = (stripe_height - stripes[f.stripe]) / 2
            f.y = f.y + offset
        canvas_width = stripe_width * len(stripes)
        canvas_height = stripe_height
    elif layout_mode == "verticaltop":
        canvas_width = stripe_width * len(stripes)
        canvas_height = stripe_height
    else:
        canvas_width = stripe_width
        canvas_height = stripe_height

    data = {
        "version": 1,
        "width": int(canvas_width),
        "height": int(canvas_height),
        "background_color": background_color,
        "images": [],
    }

    # And save all the modified attributes
    for f in new_files:
        random_colour = "%x" % random.randint(0, 180)
        tmp = {
            "filename": f.path,
            "fill_style": "#%s" % (random_colour * 3),
            "x": int(f.x),
            "y": int(f.y),
            "width": int(f.new_width),
            "height": int(f.new_height),
            "metadata": f.metadata and json.loads(f.metadata) or {},
        }
        data["images"].append(tmp)

    return data


def make_bitmap(layout_data, filepath, show_progress=False):
    "Given the layout coordinates for @project, generate a bitmap and save it under @filename"
    # Make the gigantic bitmap, if it is too large try and scale down the size using horzvert_layout iteratively
    if layout_data["width"] > MAX_WIDTH:
        raise Exception("Width %s is > %s" % (layout_data["width"], MAX_WIDTH))
    if layout_data["height"] > MAX_HEIGHT:
        raise Exception("Height %s is > %s" % (layout_data["height"], MAX_HEIGHT))

    size = len(layout_data.get("images", []))
    if size < 1:
        raise Exception("There are no images?")
    width, height = layout_data["width"], layout_data["height"]

    if show_progress:
        bar = Bar(f"Generating {filepath} of {width} x {height}", max=size)

    msgs = []
    print("Before new PIL image")
    print("size: ", (layout_data["width"], layout_data["height"]))
    large = Image.new(
        "RGBA",
        (layout_data["width"], layout_data["height"]),
        color=layout_data["background_color"],
    )
    for f in layout_data.get("images", []):
        if show_progress:
            bar.next()
        try:
            img = Image.open(f["filename"])
            i_width, i_height = img.size
            if i_width != f["width"] or i_height != f["height"]:
                print(f"Resize! width: {i_width} -> {f['width']}, height: {i_height} -> {f['height']}")
                img = img.resize((f["width"], f["height"]), Image.Resampling.LANCZOS)
        except IOError:
            msgs.append("Problem with %s" % f["filename"])
            continue
        if img.mode == "RGBA":
            large.paste(img, (f["x"], f["y"]), img)
            # img.close()
        else:
            large.paste(img, (f["x"], f["y"]))
            # img.close()

    large = large.convert("RGB")
    print("After large.convert")
    large.save(filepath)
    print("After large.save")
    if show_progress:
        bar.finish()

    return msgs


def read_files_filepaths(filepaths):
    files = []
    for filepath in filepaths:
        if not os.path.exists(filepath):
            continue
        try:
            img = Image.open(filepath)
        except UnidentifiedImageError:
            print(f"\nUnidentified error\nPath: {filepath}\n")
            continue
        # except Image.DecompressionBombError:
        #     print(f"Problem Image.DecompressionBombError with {filepath}")
        #     continue
        width, height = img.size
        last_file = BitmapFile(filepath, width, height)
        files.append(last_file)
    return files


def read_files_file(filename):
    files = []
    last_file = None
    for line in open(filename).readlines():
        tmp = line.strip()
        if not tmp and last_file:
            last_file.is_break = True
        files.append(last_file)
    return read_files_filepaths(files)


def read_files_directory(path, regex=r".*jpg"):
    files = []
    for filename in sorted(os.listdir(path)):
        if filename.startswith("."):
            continue
        if regex and not re.match(regex, filename):
            continue
        filepath = os.path.join(path, filename)
        files.append(filepath)
    return read_files_filepaths(files)


if __name__ == "__main__":
    INPUT_DIR = sys.argv[1]
    OUTPUT_DIR = sys.argv[2]
    print("IN: ", INPUT_DIR)
    print("OUT: ", OUTPUT_DIR)
    the_files = read_files_directory(INPUT_DIR)
    print(the_files)
    d = layout(the_files)
    print(f"Generating a bitmap of size {d['width']} x {d['height']}")
    open(os.path.join(OUTPUT_DIR, "layout.json"), "w").write(json.dumps(d, indent=2))
    bitmap_filename = os.path.join(OUTPUT_DIR, "big.png")
    make_bitmap(d, bitmap_filename)
    os.system("vips dzsave %s %s  --suffix=.jpg" % (bitmap_filename, "tiled"))