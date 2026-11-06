import logging
import smtplib
import traceback
from email.message import EmailMessage

from config import PERSONAL_EMAIL, PROJECT_EMAIL, PROJECT_EMAIL_APP_PASSWORD


def generateMessage(exceptionMessage):
    msg = EmailMessage()
    msg["Subject"] = "Ranked Race Job Failed"
    msg["From"] = PROJECT_EMAIL
    msg["To"] = PERSONAL_EMAIL
    content = "The Ranked Race Has Failed. See Below. \n\n"
    content += exceptionMessage
    msg.set_content(content)
    return msg


def PageError(exceptionMessage):
    LOG = logging.getLogger("pager")
    msg = generateMessage(exceptionMessage)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(PROJECT_EMAIL, PROJECT_EMAIL_APP_PASSWORD)
            smtp.send_message(msg)
    except Exception:
        LOG.error(traceback.format_exc())

    return 0
