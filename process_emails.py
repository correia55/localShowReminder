import email.mime.text as emt
import re
import smtplib

import dns.resolver as dnsr
import jinja2

import configuration
import models
import gettext

pt = gettext.translation('main', localedir='locales', languages=['pt'])
en = gettext.translation('main', localedir='locales', languages=['en'])

extensions = ['jinja2.ext.i18n']
env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'), extensions=extensions)

current = pt
env.install_gettext_callables(gettext=current.gettext, ngettext=current.ngettext, newstyle=True)


def valid_configuration():
    """
    Verifies that the configuration is correct.

    :return: true if the configuration is valid.
    """

    return configuration.email_domain is not None and configuration.email_account is not None and \
           configuration.email_user is not None and configuration.email_password is not None


def set_language(language: str):
    """
    Set the language for the emails.

    :param language: the language string.
    """
    global current, pt, en

    if language == 'pt':
        current = pt
    else:
        current = en

    env.install_gettext_callables(gettext=current.gettext, ngettext=current.ngettext, newstyle=True)


def verify_email(email):
    """
    Verify if the email is valid.

    :param email: the proposed email.
    :return: True if the email is valid.
    """

    # Verify if it has the syntax of an email
    match = re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', email)

    if match is None:
        return False

    # Verify if the domain exists
    domain_name = email.split('@')[1]

    try:
        dnsr.query(domain_name, 'MX')
    except (dnsr.NoAnswer, dnsr.NXDOMAIN):
        return False

    return True


def send_email(content: str, subject: str, destination: str):
    """
    Send an email.

    :param str content: the content of the email.
    :param str subject: the subject of the email.
    :param str destination: the destination address.
    """

    if not valid_configuration():
        print('Invalid email configuration!')
        return

    msg = emt.MIMEText(content, 'html', 'utf-8')

    msg['Subject'] = subject
    msg['From'] = configuration.email_account
    msg['To'] = destination

    s = smtplib.SMTP(configuration.email_domain)
    s.starttls()
    s.login(configuration.email_user, configuration.email_password)
    s.sendmail(configuration.email_account, [destination], msg.as_string())
    s.quit()


def send_verification_email(destination: str, verification_token: str):
    """
    Send a verification email.

    :param str destination: the destination address.
    :param str verification_token: the verification token.
    """

    subject = current.gettext('verification_email')

    content = env.get_template('verification_email.html').render(application_name=configuration.application_name,
                                                                 application_link=configuration.application_link,
                                                                 username=destination,
                                                                 verification_token=verification_token,
                                                                 validity_hours=configuration.VERIFICATION_TOKEN_VALIDITY_DAYS * 24,
                                                                 title=subject)

    send_email(content, subject, destination)


def send_deletion_email(destination: str, deletion_token: str):
    """
    Send a deletion email.

    :param str destination: the destination address.
    :param str deletion_token: the deletion token.
    """

    subject = current.gettext('deletion_email')

    content = env.get_template('deletion_email.html').render(application_name=configuration.application_name,
                                                           application_link=configuration.application_link,
                                                           username=destination,
                                                           deletion_token=deletion_token,
                                                           validity_hours=configuration.DELETION_TOKEN_VALIDITY_DAYS * 24,
                                                           title=subject)

    send_email(content, subject, destination)


def send_reminders_email(destination: str, reminder: models.DBReminder, results: [models.Show]):
    """
    Send an email with the results found for the reminders created.

    :param str destination: the destination address.
    :param DBReminder reminder: the corresponding reminder.
    :param list results: the list of results.
    """

    subject = current.gettext('reminder_results')

    content = env.get_template('reminders_email.html').render(application_name=configuration.application_name,
                                                              application_link=configuration.application_link,
                                                              username=destination, reminder=reminder, results=results,
                                                              title=subject)

    send_email(content, subject, destination)
