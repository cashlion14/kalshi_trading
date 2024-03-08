import smtplib
from email import encoders
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from os import listdir
from os.path import isfile, join

def send_log():
    
    #get log filename
    onlyfiles = [f for f in listdir('logs') if isfile(join('logs', f))]
    onlyfiles.sort()
    filename = 'logs/' + onlyfiles[-1]
    
    text = """\
    """
    subject = f"[TEST] Today's Kalshi Trading Log"
    
    sender = "kalshitrading@outlook.com"
    receivers = "nkakarla@mit.edu"

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = receivers

    part1 = MIMEText(text, "plain")
    message.attach(part1)

    f = open(filename, 'r')
    attachment = MIMEText(f.read())
    attachment.add_header('Content-Disposition', 'attachment', filename=filename)           
    message.attach(attachment)

    smtp = smtplib.SMTP("smtp-mail.outlook.com", port=587)
    smtp.starttls()
    smtp.login(sender, "traderemail123")
    smtp.sendmail(sender, receivers, message.as_string())
    
    sender = "kalshitrading@outlook.com"
    receivers = "jmpjones@mit.edu"

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = receivers

    part1 = MIMEText(text, "plain")
    message.attach(part1)
    
    attachment.add_header('Content-Disposition', 'attachment', filename=filename)           
    message.attach(attachment)

    smtp = smtplib.SMTP("smtp-mail.outlook.com", port=587)
    smtp.starttls()
    smtp.login(sender, "traderemail123")
    smtp.sendmail(sender, receivers, message.as_string())

    smtp.quit()

send_log()


def send_trade_update(side, price, contracts):

    text = """\
    """
    subject = f'Kalshi Trade: {side} @ {price} for {contracts}'
    
    sender = "kalshitrading@outlook.com"
    receivers = "nkakarla@mit.edu"

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = receivers

    part1 = MIMEText(text, "plain")
    message.attach(part1)
    
    smtp = smtplib.SMTP("smtp-mail.outlook.com", port=587)
    smtp.starttls()
    smtp.login(sender, "traderemail123")
    smtp.sendmail(sender, receivers, message.as_string())

    sender = "kalshitrading@outlook.com"
    receivers = "jmpjones@mit.edu"


    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = receivers

    part1 = MIMEText(text, "plain")
    message.attach(part1)

    smtp = smtplib.SMTP("smtp-mail.outlook.com", port=587)
    smtp.starttls()
    smtp.login(sender, "traderemail123")
    smtp.sendmail(sender, receivers, message.as_string())

    smtp.quit()