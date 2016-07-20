from asternic_email import CallStats
import local_settings

stats = CallStats(local_settings.EXTENSIONS)

stats.set_week()

stats.connect_smtp(
    local_settings.SMTP_SERVER,
    local_settings.SMTP_USER,
    local_settings.SMTP_PASSWORD)
stats.fetch_stats()

print stats.stats

stats.generate_emails('Your monthly call stats are as follows:')

print ">>> DONE!"
