#sudo apt install python3-dateutil

import glob
import dateutil.parser as dparser

class yuyanGen:
    def __init__(self):
        yuyans = glob.glob("./*/main.md")

        lines = '''
# Title
Yuyan
        
# Style
img {
padding: 10px;
margin: 5px;
background-color: {color_accent_light}; 
}

.img_div {
padding: 10px;
margin: 5px;
background-color: {color_accent_light}; 
}
        

.scroll {
font-size: medium; 
line-height: 1.6;
}

# HTML
'''

        #id_tag = '''# {title} {{#{tag}}}  \r\n'''
        id_tag = '''## {title} \r\n'''
        base = "\"https://monksevillair.com/src/yuyan"
        base2 = "https://monksevillair.com/yuyan"
        
        for b in sorted(yuyans)[::-1]:
            with open(b) as f:
                date = dparser.parse(b,fuzzy=True)
                title = b.split(str(date.strftime("%Y-%m-%d")))[-1].strip("/main.md").strip("/")[1::].replace("-", " ")
                #lines += "[## {title}]({link})  \r\n".format(link=base2+b[1::].replace("md","html"), title=title)

                #lines += id_tag.format(title=title, tag=b.split("/")[1].lower())
                lines += id_tag.format(title=title)
                lines += "### "+ str(date.strftime("%A, %B %d %Y")) + "  \r\n"

                for lll in f.readlines():
                    ll = lll.replace("\"./",base+b.strip("main.md"))
                    l = ll.replace("\"~/","https://monksevillair.com/")
                    lines += l.strip("\r").strip("\n") + "  \r\n"
                    
                lines += "\r\n"+ "---  "+ "\r\n\r\n"
                
        print(lines)
        f = open("yuyan.md", "w")
        f.write(lines)
        f.close()
        
if __name__ == '__main__':
    b = yuyanGen()
