import re
import jinja2
import smtplib

import dns.resolver as dnsr
import email.mime.text as emt

import configuration

env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))


def valid_configuration():
    """
    Verifies that the configuration is correct.

    :return: true if the configuration is valid.
    """

    return configuration.email_domain is not None and configuration.email_account is not None and \
           configuration.email_user is not None and configuration.email_password is not None


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


def send_email(content, subject, destination):
    """
    Send an email.

    :param str content: the content of the email.
    :param str subject: the subject of the email.
    :param str destination: the destination address.
    """

    if valid_configuration():
        print('Invalid email configuration!')
        return

    msg = emt.MIMEText(content, 'html', 'utf-8')

    msg['Subject'] = subject
    msg['From'] = configuration.email_account
    msg['To'] = destination

    s = smtplib.SMTP(configuration.email_domain)
    s.starttls()
    s.login(configuration.email_user, configuration.email_password)
    s.sendmail(configuration.email_user, [destination], msg.as_string())
    s.quit()


def send_activation_email(username, destination):
    """
    Send an activation email.

    :param str username: the username.
    :param str destination: the destination address.
    """

    content = env.get_template('activation_email.html').render(username=username, code=None)

    print(content)

    subject = 'Activation Email'

    send_email(content, subject, destination)
