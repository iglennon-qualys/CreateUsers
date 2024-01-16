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
  -R ROLE, --role ROLE  Default user role, defaults to "READER" ("SCANNER" | "READER" | "MANAGER")
  -d, --debug           Provide debugging output from API calls
  -x, --exit_on_error   Exit on error
```

## CSV Columns
The columns in the CSV file need to be in the following order
Firstname       (required) The first name of the user
Surname         (required) The surname of the user
Email           (required) The email address of the user
Title           (required) The title of the user
Phone           (required) The phone number of the user
Address1        (required) The first line of the user's address
Country-Code    (required) The Country Code for the user
Business Unit   (optional) The user's assigned Business Unit
Time Zone Code  (optional) The user's Time Zone Code (see time_zone_codes.json)
External ID     (optional) The External ID for the user
Roles           (optional) Semi-colon (;) separated list of roles to be assigned to the user
Scopes          (optional) Semi-colon (;) separated list of tag IDs to be assigned to the user as scope tags

### Example

```
Joe,Bloggs,joebloggs@company.com,Director of Operations,216-555-1183,22 Acacia Avenue,United Kingdom,,GB,External123,CA MANAGER;Certificate View Administrator,12345689;12345690
```