"""
Asternic Call Static Email Script
Copyright 2016 SF/Software t/a PEBBLE
"""

try:
    import local_settings
except ImportError:
    raise RuntimeError('local_settings.py does not exist or cannot be imported')

from bs4 import BeautifulSoup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import CommonMark
import requests
import arrow


class CallStats(object):
    ARROW_FORMAT = 'YYYY-MM-DD HH:MM:ss'

    def __init__(self, extensions):
        self.stats = extensions
        self.session = requests.Session()

    def connect_smtp(self, server, username, password):
        print ">>> Connecting to SMTP"
        self.smtp = smtplib.SMTP_SSL(server, 465)
        self.smtp.login(username, password)

    def stats_markdown(self, stats):
        return u"""
<table>
<tr>
    <th style="text-align:left">Total Calls</th>
    <td>{total}</td>
</tr>
<tr>
    <th style="text-align:left">Completed Calls</th>
    <td>{completed}</td>
</tr>
<tr>
    <th style="text-align:left">Missed Calls</th>
    <td>{missed}</td>
</tr>
<tr>
    <th style="text-align:left">Missed Percentage To You</th>
    <td>{missedPercentage}</td>
</tr>
<tr>
    <th style="text-align:left">Total time on phone</th>
    <td>{duration}</td>
</tr>
<tr>
    <th style="text-align:left">Average time per call</th>
    <td>{avgDuration}</td>
</tr>
<tr>
    <th style="text-align:left">Total Ring Time</th>
    <td>{totalRingTime}</td>
</tr>
<tr>
    <th style="text-align:left">Average Ring Time</th>
    <td>{avgRingTime}</td>
</tr>
</table>
""".format(**stats)

    def generate_email(self, data, tagline):
        email = u"""
Hi {name},

{tagline}

## Outgoing Calls

{outgoing}

## Incoming Calls

{incoming}

Thanks,

The Call Stats Robot
""".format(
            name=data['name'],
            outgoing=self.stats_markdown(data['outgoing']),
            incoming=self.stats_markdown(data['incoming']),
            tagline=tagline)
        html_email = CommonMark.commonmark(email)
        # Send HTML email
        html_part = MIMEText(html_email, 'html', 'utf-8')
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Your Call Stats'
        msg['From'] = local_settings.SMTP_FROM
        msg['To'] = data['email']
        msg.attach(html_part)
        self.smtp.sendmail(
            local_settings.SMTP_FROM,
            data['email'], msg.as_string())

    def generate_emails(self, tagline):
        for extension, data in self.stats.items():
            self.generate_email(data, tagline)
        print ">>> Sent Emails"

    def fetch_stats(self):
        self.get_callstats('incoming')
        self.get_callstats('outgoing')

    def set_day(self):
        # Set to start of day
        self.start = arrow.get().replace(hour=0, minute=0, second=0)
        # Roll to end of day
        self.end = arrow.get().replace(hour=23, minute=59, second=59)

    def set_month(self):
        # Set to start of month
        self.start = arrow.get().replace(day=1, hour=0, minute=0, second=0)
        # Roll to next month's first day, then back to last second of month
        self.end = arrow.get().replace(day=1, months=+1).replace(
            days=-1, hour=23, minute=59, second=59)

    def set_times(self, start, end):
        self.start = arrow.get(start)
        self.end = arrow.get(end)

    def get_callstats(self, tab):
        print '>>> Requesting {} stats'.format(tab)

        # Asternic requires a post
        page = self.session.post(
            "{}/admin/config.php?type=tool&display=asternic_cdr&tab={}".format(
                local_settings.PBX_URL, tab),
            auth=(local_settings.PBX_USERNAME, local_settings.PBX_PASSWORD),
            data={
                'start': self.start.format(self.ARROW_FORMAT),
                'end': self.end.format(self.ARROW_FORMAT),
                'List_Extensions[]': [
                    "'{}'".format(k) for k, v in
                    self.stats.items()
                ],
                'tab': tab
            })
        # Then requesting the report
        # (idk what it's doing)
        page = self.session.get(
            "{}/admin/config.php?type=tool&display=asternic_cdr&tab={}".format(
                local_settings.PBX_URL, tab),
            auth=(local_settings.PBX_USERNAME, local_settings.PBX_PASSWORD))

        print '>>> Asternic responded with {}'.format(page.status_code)

        soup = BeautifulSoup(page.text, 'html.parser')

        for extension, data in self.stats.items():
            # Asternic produces a <tr> straight after what we want labeled
            # with an ID
            wrong_row = soup.select("#{}".format(extension))[0]
            # So we need to get the row just before it
            row = wrong_row.previous_sibling.previous_sibling

            items = row.find_all('td')
            # Now we have the partial call stats for this person
            # so we fill the array
            self.stats[extension][tab] = {
                'total': items[1].string,
                'completed': items[2].string,
                'missed': items[3].string,
                'missedPercentage': items[4].string,
                'duration': items[5].string,
                'durationPercentage': items[6].string,
                'avgDuration': items[7].string,
                'totalRingTime': items[8].string,
                'avgRingTime': items[9].string
            }
