
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_update(side, price, contracts):

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
    smtp.login(sender, "finn1228")
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
    smtp.login(sender, "finn1228")
    smtp.sendmail(sender, receivers, message.as_string())

    smtp.quit()