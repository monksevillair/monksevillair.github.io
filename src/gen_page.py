import sys
import os
import markdown
from pathlib import Path
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
from colour import Color
import colorsys
from PIL import ImageColor
import pdb
#red = Color("red")
#colors = list(red.range_to(Color("green"),10))

COLOR_DICT = OrderedDict({0: ["#111111", "#DDDDDD", "#DDDDDD"],
                          180: ["#9da1fa", "#FFFFFF", "#FFFFFF"],
                          200: ["#ffada2", "#FFFFFF", "#FFFFFF"],
                          240: ["#111111", "#DDDDDD", "#DDDDDD"]})

form_l = "<span style=\"background-color: {};\">&nbsp{}&nbsp</span>"
form_d = "<span style=\"background-color: {}; color: #000\">&nbsp{}&nbsp</span>"
REPLACE =     {"{RED}":    form_l.replace("{}","red"),
               "{ORANGE}": form_l.replace("{}","orange"),
               "{YELLOW}": form_l.replace("{}","yellow"),
               "{GREEN}":  form_l.replace("{}","green"),
               "{BLUE}":   form_l.replace("{}","blue"),
               "{INDIGO}": form_l.replace("{}","indigo"),
               "{VIOLET}": form_l.replace("{}","violet"),
               "{PURPLE}": form_l.replace("{}","purple"),
               "{WHITE}":  form_d.replace("{}","white"),
               "{BLACK}":  form_l.replace("{}","black")}
               

# sexy: 9669FE;
#60: ["#9da1fa", "#FFFFFF", "#FFFFFF"],
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

        timezone_offset = -5.0  # EST (UTC−05:00), connect to map page eventually
        tzinfo = timezone(timedelta(hours=timezone_offset))
        self.hr = datetime.now(tzinfo)
        #print(self.hr)
        color_list = self.color_dict[self.hr.hour*10]
        #print(self.hr, color_list)
        #print(color_list[0].get_hex())
        
        self.color_page = color_list[0].get_hex() #"#D0BCFE"
        self.color_text = color_list[1].get_hex() #"#9669FE"
        #self.color_link = color_list[2].get_hex() #"#9669FE"

        self.color_accent_light = self.gen_accent(self.color_page, 20)
        self.color_accent_dark = self.gen_accent(self.color_page, -35)
        self.color_accent_very_dark = self.gen_accent(self.color_page, -60)
        #self.color_link = self.gen_accent(self.color_page, -90)
        self.color_link = "#fff" #self.gen_accent(self.color_page, -60)
        #self.color_accent_dark = 

        REPLACE['{color_accent_light}'] = self.color_accent_light
        REPLACE['{color_accent_dark}'] = self.color_accent_dark
        REPLACE['{color_accent_very_dark}'] = self.color_accent_very_dark

        for page in self.pages:
            self.gen_page(page)
            #self.gen_html_from_markdown(page)

    def gen_accent(self, base_color, offset):
        #print(base_color)
        rgb = ImageColor.getrgb(base_color)
        hls = list(colorsys.rgb_to_hls( rgb[0], rgb[1], rgb[2] ))
        #print (hls)
        hls[1] = hls[1]+offset
        if hls[1] > 186: hls[1] = 186
        if hls[1] < 0: hls[1] = 0
        #print (hls)
        accent = [int(x) for x in colorsys.hls_to_rgb(hls[0],
                                                      hls[1],
                                                      hls[2])]

        final_color = '#%02x%02x%02x' % tuple(accent)
        #print(final_color)
        return final_color
            
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

        print (pages)
        return pages

    def gen_sitemap(self, cur_file):
        html = ""
        link_format = "<a href=\"{link}\">{content}</a></br>\n"

        #print(Path(cur_file).parent,self.pages)

        prefix = ""
        if str(Path(cur_file).parent) != "..":
            prefix = "../"
            
        for page in self.pages:
            my_path = str(page.parent)
            target_path = str(page).replace("md","html")
            html += link_format.format(link=prefix+target_path,
                                       content=str(page.name))
        return html
    
    # Generates sidebar html, garbage- fix this
    def gen_sidebar(self, filename):
        cur_file = (filename.split(".html")[0].split("/")[-1])
                        
        link_format = "<a href=\"{link}\">{content}</a></br>{hr}\n"

        directories = self.pages

        sorted_dirs = sorted(directories)

        sidebar_html = ""
        
        for x in sorted_dirs:
            name = x.name.split(".")[0]

            valid_dirs = [str(x.parent) for x in sorted_dirs]
            file_to_check = str(x.name.split(".md")[0])
            if file_to_check not in valid_dirs and name != "index": continue

            #print (name, filename)
            #print([x.parent for x in sorted_dirs])
            #if str(cur_file) in str(x.name): continue
            #if str(name) in str(cur_file):
            if str(name) in str(filename):
                #link_format = "<u><a href=\"{link}\">{content}</a></br>{hr}</u>\n"
                link_format = "<a style=\"background-color:{}\" href=\"{link}\">&nbsp{content}&nbsp</a></br>{hr}\n".replace("{}",self.color_accent_dark)
            else:
                link_format = "<a href=\"{link}\">&nbsp{content}&nbsp</a></br>{hr}\n"
            # Need to fix this those it works on all pages not just index
            if name == "index": name = "home"
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

    def gen_html_from_markdown(self, page):
        #print(page)
        file1 = open(page, 'r')
        Lines = file1.read()
        #print(Lines)
        output = markdown.markdown(Lines)
        #if "espanol.md" in str(page):
        #    print(output)
        
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
            if "# CSS" in line: mode = "css"
            if "# TODO" in line: mode = "todo"
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

        file1 = open(directory, 'r')
        Lines = file1.read()

        #print(html)
        
        html = markdown.markdown(html)

        # replace html {} tags
        for key in REPLACE.keys():
            if key in html:
                html = html.replace(key, REPLACE[key])
            if key in style:
                style = style.replace(key, REPLACE[key])
            
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

        text_file.write("<!-- generated from {filename} at {time} EST -->".format(
            filename=directory, time=self.hr.strftime("%m-%d-%Y %H:%M:%S")))


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
            elif "{color_accent_dark}" in line:
                content = line.format(color_accent_dark=self.color_accent_dark)
            elif "{color_accent_very_dark}" in line:
                content = line.format(color_accent_very_dark=self.color_accent_very_dark)
            elif "{color_accent_light}" in line:
                content = line.format(color_accent_light=self.color_accent_light)
            elif "{site_map}" in line:
                content = line.format(site_map=self.gen_sitemap(filename))
            else:
                content = line

                    

            text_file.write(content)
        text_file.close()


if __name__ == '__main__':
    page = genPages()

