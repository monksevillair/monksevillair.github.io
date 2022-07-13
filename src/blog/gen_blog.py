#sudo apt install python3-dateutil

import glob
import dateutil.parser as dparser

class blogGen:
    def __init__(self):
        blogs = glob.glob("./*/main.md")

        lines = ''
        base = "\"https://monksevillair.com/src/blog"
        
        for b in sorted(blogs)[::-1]:
            with open(b) as f:
                date = dparser.parse(b,fuzzy=True)
                title = b.split(str(date.strftime("%Y-%m-%d")))[-1].strip("/main.md").strip("/")[1::].replace("-", " ")
                lines += "## "+ title + "  \r\n"
                lines += "### "+ str(date.strftime("%A, %B %d %Y")) + "  \r\n"


                for lll in f.readlines():
                    ll = lll.replace("\"./",base+b.strip("main.md"))
                    l = ll.replace("\"~/","https://monksevillair.com/")
                    lines += l.strip("\r").strip("\n") + "  \r\n"

                lines += "\r\n"+ "---  "+ "\r\n\r\n"
                
        #print(lines)
        f = open("blog.md", "a")
        f.write(lines)
        f.close()
        
if __name__ == '__main__':
    b = blogGen()
