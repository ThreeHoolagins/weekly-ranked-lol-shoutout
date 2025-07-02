import logging
import smtplib
from email.message import EmailMessage
import traceback

from data import PROJECT_EMAIL, PERSONAL_EMAIL, PROJECT_EMAIL_APP_PASSWORD

def generateMessage(exception_message):
    msg = EmailMessage()
    msg["Subject"] = "Ranked Race Job Failed"
    msg["From"] = PROJECT_EMAIL
    msg["To"] = PERSONAL_EMAIL
    content = "The Ranked Race Has Failed. See Below. \n\n"
    content += exception_message
    msg.set_content(content)
    return msg

def PageError(exception_message):
    LOG = logging.getLogger("pager")
    msg = generateMessage(exception_message)
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(PROJECT_EMAIL, PROJECT_EMAIL_APP_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        LOG.error(traceback.format_exc())
        
    return 0