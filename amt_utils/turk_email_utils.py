from collections import defaultdict
import imaplib
import email
import email.header
import datetime
import re
import pickle

from keysTkingdom.g_app_pass import app_pass


def process_mailbox(imap_server):
    emails = []
    rv, data = imap_server.search(None, "ALL")
    if rv != 'OK':
        print("No messages found!")
        return
    for num in data[0].split():
        rv, data = imap_server.fetch(num, '(RFC822)')
        if rv != 'OK':
            print("ERROR getting message", num)
            return
        # msg = email.message_from_bytes(data[0][1])
        msg = email.message_from_string(data[0][1])
        hdr = email.header.make_header(email.header.decode_header(msg['Subject']))
        subject = str(hdr)
        print('Message %s: %s' % (num, subject))
        print('Raw Date:', msg['Date'])
        # Now convert to local date-time
        date_tuple = email.utils.parsedate_tz(msg['Date'])
        if date_tuple:
            local_date = datetime.datetime.fromtimestamp(
                email.utils.mktime_tz(date_tuple))
            print ("Local Date:", local_date.strftime("%a, %d %b %Y %H:%M:%S"))
        emails.append(msg)
    return emails


def get_turker_emails():
    app_password = app_pass
    imap_server = 'imap.gmail.com'
    email_account = "drschwenk@gmail.com"
    email_folder = '"2 lower priority/turk"'

    imap_server = imaplib.IMAP4_SSL(imap_server)
    imap_server.login(email_account, app_password)
    rv, data = imap_server.select(email_folder)
    if rv == 'OK':
        print ("Processing mailbox: ", email_folder)
        emails = process_mailbox(imap_server)
        imap_server.close()
    else:
        print ("error: Unable to open mailbox ", rv)
        emails = None
    imap_server.logout()
    return emails 


def capture_worker_ids(turker_emails):
    hits_by_worker = defaultdict(list)
    worker_id_pattern = re.compile('Customer ID:\s(\w+)')
    hit_id_pattern = re.compile('HIT\s(?:Type\s+)?(\w+)')
    for turker_email in turker_emails:
        worker_id = re.findall(worker_id_pattern, turker_email.get_payload())
        hit_id = re.findall(hit_id_pattern, turker_email['Subject'])[0]
        hits_by_worker[hit_id].extend(worker_id)
    return hits_by_worker


def get_latest_worker_communication():
    latest_email = get_turker_emails()
    workers = capture_worker_ids(latest_email)
    return workers


def pickle_emails(emails_to_pickle, file_path):
    with open(file_path, 'w') as f:
        pickle.dump(emails_to_pickle, f)
    print('writing latest emails to pickle')

if __name__ == "__main__":
    emails_from_workers = get_latest_worker_communication()
    file_path = 'latest_emails.pkl'
    pickle_emails(emails_from_workers, file_path)

