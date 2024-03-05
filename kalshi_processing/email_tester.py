import base64
from pathlib import Path

import mailtrap as mt

import mailtrap as mt

# create mail object
mail = mt.Mail(
    sender=mt.Address(email="mailtrap@example.com", name="Mailtrap Test"),
    to=[mt.Address(email="finner14@gmail.com")],
    subject="You are awesome!",
    text="Congrats for sending test email with Mailtrap!",
)

# create client and send
client = mt.MailtrapClient(token="your-api-key")
client.send(mail)



# welcome_image = Path(__file__).parent.joinpath("welcome.png").read_bytes()

# mail = mt.Mail(
#     sender=mt.Address(email="mailtrap@example.com", name="Mailtrap Test"),
#     to=[mt.Address(email="your@email.com", name="Your name")],
#     cc=[mt.Address(email="cc@email.com", name="Copy to")],
#     bcc=[mt.Address(email="bcc@email.com", name="Hidden Recipient")],
#     subject="You are awesome!",
#     text="Congrats for sending test email with Mailtrap!",
#     html="""
#     <!doctype html>
#     <html>
#       <head>
#         <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
#       </head>
#       <body style="font-family: sans-serif;">
#         <div style="display: block; margin: auto; max-width: 600px;" class="main">
#           <h1 style="font-size: 18px; font-weight: bold; margin-top: 20px">
#             Congrats for sending test email with Mailtrap!
#           </h1>
#           <p>Inspect it using the tabs you see above and learn how this email can be improved.</p>
#           <img alt="Inspect with Tabs" src="cid:welcome.png" style="width: 100%;">
#           <p>Now send your email using our fake SMTP server and integration of your choice!</p>
#           <p>Good luck! Hope it works.</p>
#         </div>
#         <!-- Example of invalid for email html/css, will be detected by Mailtrap: -->
#         <style>
#           .main { background-color: white; }
#           a:hover { border-left-width: 1em; min-height: 2em; }
#         </style>
#       </body>
#     </html>
#     """,
#     category="Test",
#     attachments=[
#         mt.Attachment(
#             content=base64.b64encode(welcome_image),
#             filename="welcome.png",
#             disposition=mt.Disposition.INLINE,
#             mimetype="image/png",
#             content_id="welcome.png",
#         )
#     ],
#     headers={"X-MT-Header": "Custom header"},
#     custom_variables={"year": 2023},
# )

# client = mt.MailtrapClient(token="your-api-key")
# client.send(mail)




# import smtplib
# from smtplib import SMTPException

# sender = 'jmpjones14@gmail.com'
# receivers = ['finner14@gmail.com']
# message = """From: Jake Jones <jmpjones14@gmail.com>
# To: Jake Jones <finner14@gmail.edu>
# Subject: SMTP email example


# This is a test message.
# """

# server = smtplib.SMTP('localhost', 1025)
# server.sendmail(sender, receivers, message)
# server.quit()
