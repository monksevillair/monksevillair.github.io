import sys
import os
from pathlib import Path
from collections import OrderedDict
from datetime import datetime
from colour import Color

#red = Color("red")
#colors = list(red.range_to(Color("green"),10))

COLOR_DICT = OrderedDict({0: ["#000000", "#FFFFFF", "#FFFFFF"],
                          60: ["#9da1fa", "#FFFFFF", "#FFFFFF"],
                          120: ["#FFFFFF", "#FF0000", "#FF0000"],
                          180: ["#9da1fa", "#FFFFFF", "#FFFFFF"],
                          240: ["#000000", "#FFFFFF", "#FFFFFF"]})

#100: ["#dcfaff", "#ffada2", "#442643"],
#              160: ["#ffca6f", "#435a91", "#a1b5d6"],

class genPages():
    def __init__(self):
        directory = ''
        page_title = ''


        
        self.pages = self.find_pages()
        self.template_dir = 'templates/template.html'

        self.color_dict = {}
        self.fade_colors()

        #self.hr = int(args)
        self.hr = datetime.now().hour*10
        color_list = self.color_dict[self.hr]
        #print(self.hr, color_list)
        #print(color_list[0].get_hex())
        
        self.color_page = color_list[0].get_hex() #"#D0BCFE"
        self.color_text = color_list[1].get_hex() #"#9669FE"
        self.color_link = color_list[2].get_hex() #"#9669FE"
        
        #print(self.pages)
        for page in self.pages:
            self.gen_page(page)

    def fade_colors(self):

        last_col = 0
        for col in COLOR_DICT.keys():
            if col == 0: continue

            #print(col-last_col)

            num_colors = col-last_col


            color_group = []
            for x in range(len(COLOR_DICT[0])):
                color_group.append(list(Color(COLOR_DICT[last_col][x]).range_to(Color(COLOR_DICT[col][x]),num_colors)))

            for y in range(num_colors):
                self.color_dict[last_col+y] = (color_group[0][y], color_group[1][y], color_group[2][y])
            
            #last_cols = [Color(x).range_to(Color(col for x in COLOR_DICT[last_col]]
            #colors = list(red.range_to(Color("green"),10))
            
            last_col = col            

        #print(self.color_dict.keys())
            
            
    def find_pages(self):
        pages = []

        for path in Path('.').rglob('*.md'):
               pages.append(path)

        return pages

    # Generates sidebar html, garbage- fix this
    def gen_sidebar(self, filename):
        link_format = "<a href=\"{link}\">{content}</a></br>{hr}\n"

        directories = self.pages

        sorted_dirs = sorted(directories)

        sidebar_html = ""
        
        for x in sorted_dirs:
            name = x.name.split(".")[0]
            if name == "index": name = "home"
            # Need to fix this those it works on all pages not just index

            link_address = "../"+str(x)

            #print(str(Path(filename[3:]).parent), str(x))
            if str(Path(filename[3:]).parent) in str(x):
                link_address = (str(x))
                if str(Path(filename[3:]).parent) != ".":
                    link_address = "../"+(str(x))
                #print (x, filename, Path(filename[3:]).parent)
            #print(x, Path(filename[3:]).parent)
            #if name == "index": continue;
            sidebar_html = sidebar_html + link_format.format(
                link=link_address.replace(".md",".html"), content=name, hr="")

        return sidebar_html
        
    def gen_page(self, directory):
        file1 = open(directory, 'r')
        Lines = file1.readlines()

        title = ""
        style = ""
        html = ""

        mode = ""
        for line in Lines:
            if "# Title" in line: mode = "title"
            if "# Style" in line: mode = "style"
            if "# HTML" in line: mode = "html"
            if line != "\n":
                if mode == "title":
                    if "# Title" not in line:
                        title = line
                if mode == "style":
                    if "# Style" not in line:
                        style = style + line
                if mode == "html": 
                    if "# HTML" not in line:
                        html = html + line
            
        file1 = open(self.template_dir, 'r')
        Lines = file1.readlines()


        filename = ("../"+str(directory).replace(".md",".html"))
        #print(filename)

        if not os.path.exists(os.path.dirname(filename)):
            try:
                os.makedirs(os.path.dirname(filename))
            except OSError as exc: # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
        
        text_file = open(filename, "w")

        text_file.write("<!-- generated from {filename} at {time} -->".format(
            filename=directory, time=datetime.now().strftime("%m-%d-%Y %H:%M:%S")))

        for line in Lines:
            content = ''
            if "{page_title}" in line:
                content = line.format(page_title=title)
            elif "{additional_css}" in line:
                content = line.format(additional_css=style)
            elif "{sidebar_html}" in line:
                content = self.gen_sidebar(filename)
            elif "{page_content}" in line:
                content = line.format(page_content=html)
            elif "{color_text}" in line:
                content = line.format(color_text=self.color_text)
            elif "{color_link}" in line:
                content = line.format(color_link=self.color_link)
            elif "{color_page}" in line:
                content = line.format(color_page=self.color_page)
            else:
                content = line

            text_file.write(content)
        text_file.close()


if __name__ == '__main__':
    page = genPages()

