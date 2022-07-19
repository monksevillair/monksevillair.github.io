'''
sudo apt install python3-pip
pip3 install imap_tools
pip3 install genanki
'''

from imap_tools import MailBox, AND
import random
import time
import sys
from datetime import date
today = date.today()

import os
import smtplib
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from email import encoders

DIR = "./decks/"

class parseMessage:
    def __init__(self):
        self.email = sys.argv[1]
        self.password = sys.argv[2]
    
        mailbox = MailBox('imap.gmail.com')
        mailbox.login(self.email, self.password, initial_folder='INBOX')  # or mailbox.folder.set instead 3d arg
        msgs = [msg for msg in mailbox.fetch(AND(seen=False))]

        for msg in msgs:
            if "`" in msg.subject:
                topic = msg.subject.split("`")[1]
                topic_dir = topic+'/'+today.strftime("%Y-%m-%d")+"-"+msg.subject.strip(topic).strip("`").replace(" ","-")
                if not(os.path.exists(topic_dir) and os.path.isdir(topic_dir)):
                    os.mkdir(topic_dir,exist_ok=True)
                with open(topic_dir+'/main.md', 'w') as f:
                    f.write(msg.text)

                for att in msg.attachments:
                    with open(topic_dir+'/{}'.format(att.filename), 'wb') as f:
                        f.write(att.payload)
                    
                '''import json
                with open('study_list.json', 'r') as f:
                    json_data = json.load(f)
                    json_data[msg.subject.strip("`youtube`")] = {'date':today.strftime("%m-%d-%y"), 't':msg.text.strip("\r\n")}

                with open('study_list.json', 'w') as f:
                    f.write(json.dumps(json_data))'''

        mailbox.logout()

    def send_mail(self, send_from, send_to, subject, message, username, password, files=[],server="smtp.gmail.com", port=587,  use_tls=True):
        """Compose and send email with provided info and attachments.
   
        Args:
            send_from (str): from name
            send_to (list[str]): to name(s)
            subject (str): message title
            message (str): message body
            files (list[str]): list of file paths to be attached to email
            server (str): mail server host name
            port (int): port number
            username (str): server auth username
            password (str): server auth password
            use_tls (bool): use TLS mode
        """
        msg = MIMEMultipart()
        msg['From'] = send_from
        msg['To'] = send_to #COMMASPACE.join(send_to)
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = subject
   
        msg.attach(MIMEText(message))
   
        for path in files:
            part = MIMEBase('application', "octet-stream")
            print(path)
            with open(path, 'rb') as file:
                part.set_payload(file.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition',
                            'attachment; filename={}'.format(Path(path).name))
            msg.attach(part)
   
        smtp = smtplib.SMTP(server, port)
        if use_tls:
            smtp.starttls()
        smtp.login(username, password)
        smtp.sendmail(send_from, send_to, msg.as_string())
        smtp.quit()


if __name__ == '__main__':
    #while True:
    p = parseMessage()
    #time.sleep(20)
