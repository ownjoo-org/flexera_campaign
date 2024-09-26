# flexera_campaign
Create campaign (for software retirement)

# SECURITY NOTE:
I wrote the .py files.  You have my word that they don't do anything nefarious.  Even so, I recommend that you perform
your own static analysis and supply chain testing before use.  Many libraries are imported that are not in my own control.

# usage
```
$ python flexera_campaign.py -h
usage: flexera_campaign.py [-h] --domain DOMAIN --username USERNAME --password PASSWORD --flexera_id FLEXERA_ID [--proxies PROXIES] [--log_level LOG_LEVEL]

options:
  -h, --help                    show this help message and exit
  --proxies PROXIES             JSON structure specifying 'http' and 'https' proxy URLs
  --domain DOMAIN               The URL for your Flexera server
  --username USERNAME           The user name for your Flexera account
  --password PASSWORD           The password for your Flexera account
  --flexera_id FLEXERA_ID       The Flexera ID for the software package
  --group_id GROUP ID           The AD Group ID for the software campaign policy
  --log_level LOG_LEVEL         Log level: default is 50. Greater than 0 enables some logging. 10 or more is DEBUG.
```

# example
```
$ python flexera_campaign.py --domain 'https://my_flexera.domain.com/' --username USERNAME --password PASSWORD --flexera_id 'arl://SOME_ID'  --group_id SOME_GROUP_ID
```