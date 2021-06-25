import json
import subprocess
from subprocess import PIPE, run
from ast import literal_eval

# Parse python dicts in notes with ag, gen map, and other things in the future

class genMap():
    def __init__(self):
        command = ["ag", "\"type\": \"GPS\""]
        result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        res = result.stdout.split("\n")
        clean_res = []
        for x in res:
            try:
                the_dict = literal_eval("{"+x.split(":{")[1])
                the_dict["directory"] = x.split(":{")[0].split(":")[0]
                the_dict["line_num"] = x.split(":{")[0].split(":")[1]

                clean_res.append(the_dict)
            except:
                print("unclean")

        #t_dict = [literal_eval(x) for x in clean_res]
        print(clean_res)
        

        
if __name__ == "__main__":
    map = genMap()
