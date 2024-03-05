import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def main():
  """Shows basic usage of the Gmail API.
  Lists the user's Gmail labels.
  """
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "kalshi_processing/credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    # Call the Gmail API
    service = build("gmail", "v1", credentials=creds)
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])

    if not labels:
      print("No labels found.")
      return
    print("Labels:")
    for label in labels:
      print(label["name"])

  except HttpError as error:
    # TODO(developer) - Handle errors from gmail API.
    print(f"An error occurred: {error}")


if __name__ == "__main__":
    import yagmail
    # yagmail.register('kalshitrading', 'BigBucks29!')
    # yag = yagmail.SMTP('mygmailusername')
    
    yag = yagmail.SMTP('kalshitrading@gmail.com', oauth2_file='kalshi_processing/credentials.json')
    yag.send(subject="Great!")
    
    # main()
    
    # import smtplib, ssl

    # port = 465  # For SSL
    # password = 'BigBucks29!'

    # # Create a secure SSL context
    # context = ssl.create_default_context()

    # with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
    #     server.login("kalshitrading@gmail.com", password)
    #     # TODO: Send email here
        
    #     sender_email = "kalshitrading@gmail.com"
    #     receiver_email = "kalshitrading@gmail.com"
    #     message = """\
    #     Subject: Hi there

    #     This message is sent from Python."""

    #     server.sendmail(sender_email, receiver_email, message)