# CreateUsers

## Synopsis
The CreateUsers script will create users from a list of people in CSV format.  It includes assignment of scope tags and 
roles via the Administration API

## Usage
```
create_users_from_csv.py [-h] [-f FILENAME] [-o OUTPUT_FILE] 
                         [-u USERNAME] [-p PASSWORD] 
                         [-P] [-U PROXY_URL] 
                         [-a APIURL] [-n] [-d] [-x]

options:
  -h, --help            show this help message and exit
  -f FILENAME, --filename FILENAME
                        Input CSV file containing user information
  -o OUTPUT_FILE, --output_file OUTPUT_FILE
                        Output file (usernames & passwords
  -u USERNAME, --username USERNAME
                        Qualys Username
  -p PASSWORD, --password PASSWORD
                        Qualys Password (use - for interactive input
  -P, --proxy_enable    Enable HTTPS proxy
  -U PROXY_URL, --proxy_url PROXY_URL
                        HTTPS proxy address
  -a APIURL, --apiurl APIURL
                        Qualys API URL (e.g. https://qualysapi.qualys.com)
  -n, --no_call         Do not make API calls, write URLs to console
  -d, --debug           Provide debugging output from API calls
  -x, --exit_on_error   Exit on error
```

## CSV Columns
The columns in the CSV file need to be in the following order
Firstname   The first name of the user
Surname     The surname of the user
Email       The email address of the user
Title       The title of the user
Roles       Semi-colon (;) delimited list of roles to be assigned to the user
Scopes      Semi-colon (;) delimited list of tag IDs to be assigned to the user as scope tags

### Example

```
Joe,Bloggs,joebloggs@company.com,Director of Operations,CA MANAGER;Certificate View Administrator,12345689;12345690
```