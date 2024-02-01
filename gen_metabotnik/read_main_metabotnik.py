import cairocffi as cairo
import gspread
# from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.service_account import Credentials
import os
import sys
sys.path.append('/home/ubuntu/code/django_app')
import metabotnik.planodo as planodo
import textbase
import sqlite3
import json
import sys
sys.path.append('/home/ubuntu/code/django_app')

################################################################################################

# Fix for multiple lemmas LCI_ARTES_1_2 etc.
# Change to draw updated images from Dropbox and not the direcory on server elsewhere

################################################################################################

#LEMMAS = textbase.parse("./Images/lemmas.dmp")
IMAGES = "./Images"
SUPPIMAGES = "./Supplement"  # Note! These are in sub-directories
DEST = "./Output"

# Very subtle zero-width space
n = "\ufeff"

image_paths = {}

for dirpath, dirnames, filenames in os.walk(SUPPIMAGES):
    for filename in filenames:
        if filename.startswith(n):
            print(f"{filename} contains \ufeff removing the first character")
            filename = filename[1:]

        image_paths[filename] = os.path.join(dirpath, filename)
        
for filename in os.listdir(IMAGES):
    image_paths[filename] = os.path.join(IMAGES, filename)

def get_ss():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("./secret/client_secret.json", scopes = scope)

    client = gspread.authorize(creds)
    ss = client.open_by_url(
        "https://docs.google.com/spreadsheets/d/1teGdFWVyYPv4R1ZxqoyTt5MlkPHb_LuV1TBqWDnvBFI/edit#gid=1772022142"
    )
    ws = [ws for ws in ss.worksheets() if ws.title == "Supplemental Illustrations"][0]
    return ws.get_all_values()

def make_lemma_image(lemma_filename, lemma):
    FONT_SIZE = 50

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1)
    cr = cairo.Context(surface)
    cr.select_font_face("Brill", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(FONT_SIZE)
    x, y, width, height, dx, dy = cr.text_extents(lemma)

    HEIGHT = 1000
    WIDTH = int(width * 1.3)
    asurf = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
    cr = cairo.Context(asurf)
    cr.set_source_rgb(0.95, 0.95, 0.95)  # Fill the square with greyish
    cr.rectangle(0, 0, WIDTH, HEIGHT)
    cr.fill()
    # Draw a black border on the left
    cr.set_source_rgb(0, 0, 0)  # Fill the square with greyish
    cr.rectangle(0, 0, 2, HEIGHT)
    cr.fill()

    cr.set_source_rgb(0, 0, 0)
    cr.select_font_face("Brill", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(FONT_SIZE)
    cr.move_to(
        int((WIDTH - width) / 2) + int(width * 0.09), int(height * 1.3)
    )
    cr.show_text(lemma)

    # asurf.write_to_png(os.path.join(SUPPIMAGES, "Lemmas", lemma_filename))
    asurf.write_to_png(os.path.join(SUPPIMAGES, lemma_filename))

def make():
    data = get_ss()
    images = []
    lemma_filename = None
    for x in data[1:]:
        ID = x[0]  # Column A
        seq = x[3]  # Column D
        filenames = x[4]  # Column E
        caption = x[7] # Column H

        if ID and ID.endswith(
            "_1"
        ):  # This is the first image in the sequence for this lemma, so also output the lemma
            lemma_seq = seq[:-1] + "0"
            lemma_filename = f"{ID}.png"
            lemma = x[1]  # Column B

        for filename in filenames.split("\n"):
            if filename and filename.lower().endswith(".jpg"):
                if filename not in image_paths:
                    # print(f"{filename}\tnot in image paths")
                    continue

                if lemma_filename:
                    if lemma_filename not in image_paths:
                        make_lemma_image(lemma_filename, lemma)                       
                    images.append((lemma_seq, lemma_filename, lemma, lemma))
                    image_paths[lemma_filename] = os.path.join(SUPPIMAGES, lemma_filename)
                    # print(f"Lemma appended! {lemma_seq}, {lemma_filename}, {lemma}, {lemma}")
                    lemma_filename = None

                images.append((seq, filename, caption, lemma))
            with open ('images.txt', 'w') as f:
                f.write(str(images))
    return images


def make_mm(images):
    imagepaths = [
        image_paths[filename] for _, filename, _, _ in images if filename in image_paths
    ]
    with open ('imagepaths.txt', 'w') as f:
            f.write(str(imagepaths))

    print("ENTERING!")
    f = planodo.read_files_filepaths(imagepaths)
    print("Filepaths created!")
    d = planodo.layout(f)
    print("Layout created!")
    json_filename = os.path.join(DEST, "main.json")
    open(json_filename, "w").write(json.dumps(d, indent=2))
    print("main.json created!")
    bitmap_filename = os.path.join(DEST, "main.png")
    print("Bitmap file opened!")
    pyramid_filename = os.path.join(DEST, "main")
    print("Pyramid file opened!")
    planodo.make_bitmap(d, bitmap_filename)
    print("Bitmap created!")
    os.system("vips dzsave %s %s  --suffix=.jpg" % (bitmap_filename, pyramid_filename))
    print("DZ created!")
    os.remove(bitmap_filename)
    print("Bitmap file removed!")

# /data/sites/metabotnik.com/www/api/db.sqlite3
# /data/content/referenceworks/lci/mapping.json

def to_metabotnik(db_filename, project_name, json_filename, images):
    mapping = json.load(open(json_filename))
    width, height = mapping['width'], mapping['height']
    seqs = {}
    for seq, filename, caption, lemma in images:
        if filename not in image_paths:
            continue
        # seq looks like 3 numbers split with underscores, volume_column_seq, eg. 2_155_999
        seq = seq.split("_")
        if len(seq) != 3:
            continue
        seqs[image_paths[filename]] = ("_".join(seq), f"{seq[0]}_{seq[1]}\n{lemma}\n{caption}")
    insert_objs = []
    insert_xy = []
    insert_tags = []
    count = 1
    for obj in mapping["images"]:
        if obj["filename"] not in seqs:
            continue
        obj_caption = seqs[obj["filename"]][1]
        insert_objs.append((count, obj_caption))
        obj_seq = seqs[obj["filename"]][0]
        insert_tags.append((obj_seq, count))
        # NOTE: in rtree we do not insert x y w h, but x1 x2, y1, y2 !!!!
        insert_xy.append((count, obj["x"]/width, obj["x"]/width + obj["width"]/width, obj["y"]/height, obj["y"]/height+obj["height"]/height))
        count += 1
        if count > 999999:
            break
    db = sqlite3.connect(db_filename)
    cursor = db.cursor()
    cursor.execute("CREATE TABLE projects (name, width, height )")
    cursor.execute("INSERT INTO projects VALUES (?, ?, ?)", (project_name, width, height))
    cursor.execute(f"CREATE TABLE {project_name}_tags (tag, obj_id)")    
    cursor.execute(f"CREATE TABLE {project_name}_objs (id INTEGER PRIMARY KEY AUTOINCREMENT, obj)")
    cursor.execute(f"CREATE VIRTUAL TABLE {project_name}_index USING rtree(id, x1, x2, y1, y2)")
    cursor.executemany(f"INSERT INTO {project_name}_objs VALUES (?, ?)", insert_objs)
    cursor.executemany(f"INSERT INTO {project_name}_index VALUES (?, ?, ?, ?, ?)", insert_xy)
    cursor.executemany(f"INSERT INTO {project_name}_tags VALUES (?, ?)", insert_tags)
    db.commit()

if __name__ == '__main__':
    images = make()
    print("Lemmy zrobione")
    make_mm(images)
    print("Layout i kafle zrobione, czas na db!")
    to_metabotnik('db.sqlite3', 'lci20210601', os.path.join(DEST, 'main.json'), images)
    print('db zrobione!')

