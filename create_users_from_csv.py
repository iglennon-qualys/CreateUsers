import json
import csv
from xml.etree import ElementTree as ET
import QualysAPI
import argparse
import sys
import getpass
import os.path
from time import sleep


def validate_api_response(response: ET.ElementTree):
    if response.find('.//RETURN') is not None:
        if response.find('.//RETURN').attrib['status'] == 'SUCCESS':
            return 0, ''
        else:
            return 2, response.find('.//MESSAGE').text

    elif response.find('.//responseCode') is not None:
        if response.find('.//responseCode').text == 'SUCCESS':
            return 0, ''
        else:
            return 2, response.find('.//errorMessage').text
    else:
        return 3, 'Unknown error'


def validate_json_response(response: dict):
    if response['ServiceResponse']['responseCode'] == 'SUCCESS':
        return 0, ''
    else:
        return 2, f'{response['ServiceResponse']['responseErrorDetails']['errorMessage']}'


def my_quit(exitcode: int, errormsg: str = None):
    if exitcode != 0:
        print('ERROR', end='')
        if errormsg is None:
            print('')
        else:
            print(' %s' % errormsg)
    sys.exit(exitcode)


class QualysUser:
    forename: str
    surname: str
    email: str
    title: str
    phone: str
    address1: str
    city: str
    country: str
    external_id: str
    asset_groups: list
    business_unit: str
    time_zone_code: str
    id: str
    portal_role: list
    scope_tags: list
    username: str
    password: str
    synced: bool

    def __init__(self, forename: str = '', surname: str = '', title: str = '', phone: str = '', email: str = '',
                 address1: str = '', city: str = '', country: str = '', external_id: str = '', asset_groups=None,
                 business_unit: str = '', time_zone_code: str = '', id: str = '', portal_role=None, scope_tags=None,
                 username: str = '', user_password: str = '', synced: bool = False):
        self.forename = forename
        self.surname = surname
        self.title = title
        self.phone = phone
        self.email = email
        self.address1 = address1
        self.city = city
        self.country = country
        self.external_id = external_id
        if asset_groups is None:
            asset_groups = []
        else:
            self.asset_groups = asset_groups
        self.business_unit = business_unit
        self.time_zone_code = time_zone_code
        self.id = id
        if portal_role is None:
            self.portal_role = []
        else:
            self.portal_role = portal_role
        if scope_tags is None:
            self.scope_tags = []
        else:
            self.scope_tags = scope_tags
        self.username = username
        self.password = user_password
        self.synced = synced

    def create_url(self, baseurl: str, send_email: bool = False, user_role: str = 'reader'):
        url = '%s/msp/user.php' % baseurl
        payload = {
            'action': 'add',
            'first_name': self.forename,
            'last_name': self.surname,
            'title': self.title,
            'phone': self.phone,
            'email': self.email,
            'address1': self.address1,
            'city': self.city,
            'country': self.country,
            'user_role': user_role,
            'business_unit': self.business_unit,
            'time_zone_code': self.time_zone_code
        }
        if self.external_id is not None:
            payload['external_id'] = self.external_id

        if send_email:
            payload['send_email'] = '1'
        else:
            payload['send_email'] = '0'

        return url, payload

    def __role_url(self):
        role_payload = {'roleList': {'add': {'RoleData': []}}}
        for role in self.portal_role:
            # role_payload['roleList']['add']['RoleData'].append({'name': {'#text': role}})
            role_payload['roleList']['add']['RoleData'].append({'name': role})
        return role_payload

    def __scope_tags_url(self):
        scope_payload = {'scopeTags': {'add': {'TagData': []}}}
        for tag in self.scope_tags:
            # scope_payload['scopeTags']['add']['TagData'].append({'id': {'#text': tag}})
            scope_payload['scopeTags']['add']['TagData'].append({'id': tag})
        return scope_payload

    def set_role_and_scope_url(self, baseurl: str):
        url = '%s/qps/rest/2.0/update/am/user/%s' % (baseurl, self.id)
        dict_payload = {'ServiceRequest': {'data': {'User': {}}}}
        dict_payload['ServiceRequest']['data']['User'].update(self.__scope_tags_url())
        dict_payload['ServiceRequest']['data']['User'].update(self.__role_url())

        return url, dict_payload


def get_portal_users(api: QualysAPI.QualysAPI) -> list[dict]:
    all_users = []
    limit_results = 50
    offset = 0

    service_request = {
        'ServiceRequest': {
            'filters': {
                'Criteria': [{
                    'field': 'id',
                    'operator': 'GREATER',
                    'value': '0'
                }]
            },
            'preferences': {
                'limitResults': str(limit_results),
            }
        }
    }
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    more_data = True
    while more_data:
        response = api.makeCall(url='%s/qps/rest/2.0/search/am/user' % (api.server),
                                payload=json.dumps(service_request),
                                headers=headers,
                                method='POST',
                                returnwith='json')
        service_response = response['ServiceResponse']
        if service_response['responseCode'] != 'SUCCESS':
            pass
        if 'hasMoreRecords' in service_response and service_response['hasMoreRecords'] == 'true':
            more_data = True
            offset += limit_results
            service_request['ServiceRequest']['preferences']['startFromOffset'] = str(offset)
        else:
            more_data = False
        all_users += service_response['data']

    return all_users


if __name__ == '__main__':

    # Add arguments to be collected from the command line
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--filename', help='Input CSV file containing user information')
    parser.add_argument('-o', '--output_file', help='Output file (usernames & passwords')
    parser.add_argument('-u', '--username', help='Qualys Username')
    parser.add_argument('-p', '--password', help='Qualys Password (use - for interactive input')
    parser.add_argument('-P', '--proxy_enable', action='store_true', help='Enable HTTPS proxy')
    parser.add_argument('-U', '--proxy_url', help='HTTPS proxy address')
    parser.add_argument('-a', '--apiurl', help='Qualys API URL (e.g. https://qualysapi.qualys.com)')
    parser.add_argument('-n', '--no_call', action='store_true', help='Do not make API calls, write URLs to console')
    parser.add_argument('-d', '--debug', action='store_true', help='Provide debugging output from API calls')
    parser.add_argument('-x', '--exit_on_error', action='store_true', help='Exit on error')

    # Process the passed arguments
    args = parser.parse_args()

    # Validate the configuration file
    # Validate the critical arguments
    if args.filename is None or args.filename == '':
        my_quit(1, 'CSV File Not Specified')

    if not os.path.exists(args.filename):
        my_quit(1, 'CSV File %s does not exist' % args.filename)

    if not os.path.isfile(args.filename):
        my_quit(1, '%s is not a file' % args.filename)

    if args.username is None or args.username == '':
        my_quit(1, 'Username not specified')

    if args.password is None or args.password == '':
        my_quit(1, 'Password not specified or - not used in password option')

    if args.proxy_enable and (args.proxy_url is None or args.proxy_url == ''):
        my_quit(1, 'Proxy enabled but proxy URL not specified')

    if args.apiurl is None or args.apiurl == '':
        my_quit(1, 'API URL not specified')

    if args.output_file is None or args.output_file == '':
        my_quit(1, 'Output file not specified')

    # Get the Password interactively if '-' is used in that argument
    if args.password == '-':
        password = getpass.getpass(prompt='Enter password : ')
    else:
        password = args.password

    # Process the configuration file

    if args.proxy_enable:
        api = QualysAPI.QualysAPI(svr=args.apiurl, usr=args.username, passwd=password, enableProxy=args.proxy_enable,
                                  proxy=args.proxy_url, debug=args.debug)
    else:
        api = QualysAPI.QualysAPI(svr=args.apiurl, usr=args.username, passwd=password, debug=args.debug)

    user_list = []

    # Open the CSV input file and start processing the contents into QualysUser objects, adding each to the list
    # user_list
    with open(args.filename, 'r') as inputfile:
        csvreader = csv.reader(inputfile, delimiter=',', quotechar='"')
        print('Creating users:')
        for row in csvreader:
            if row[0].find('#') > -1:
                continue
            user = QualysUser(forename=row[0],
                              surname=row[1],
                              email=row[2],
                              title=row[3],
                              portal_role=row[4].split(';'),
                              scope_tags=row[5].split(';'),
                              phone='1234',
                              address1='22 Acacia Avenue',
                              city='Acaciaville',
                              country='United Kingdom',
                              business_unit='Unassigned',
                              time_zone_code='',
                              external_id='',
                              id='',
                              synced=False)

            # Generate the URL and payload from the user object
            url, payload = user.create_url(baseurl=api.server, send_email=False, user_role='reader')

            # If we are not running with the "-n" or "--no-call" option, run the API call to create the user
            if not args.no_call:
                response = api.makeCall(url=url, payload=payload)
                error_code, error_message = validate_api_response(response=response)
                # If the validated error code is not 0, there's an error
                if error_code > 0 and args.exit_on_error:
                    # If we are running with "-x" or "--exit_on_error" then quit out with a sensible message
                    my_quit(exitcode=error_code, errormsg='Could not create user %s %s (%s) : Reason (%s)' %
                                                          (user.forename,
                                                           user.surname,
                                                           user.email,
                                                           error_message))
                # Otherwise if there was an error, just report the error and continue
                elif error_code > 0:
                    print('ERROR: Could not create user %s %s (%s) : Reason (%s)' % (user.forename, user.surname,
                                                                                     user.email, error_message))
                # Otherwise it was successful, so we record the username and password in the user object
                else:
                    user.username = response.find('.//USER_LOGIN').text
                    user.password = response.find('.//PASSWORD').text
                    print(f'\t{user.username} - {user.forename} {user.surname}')

            else:
                # We're running with the "-n" or "--no_call" options, so don't run the API call, just output
                # what we would have sent and the URL we would have sent it to
                print('NO_CALL: Output URL and Payload\nURL: %s\nPAYLOAD: %s' % (url, payload))

            user_list.append(user)

        # Check to make sure there we actually created users
        if len(user_list) == 0:
            print('No users created, exiting')
            my_quit(0, '')

        # Now we need to start a cycle validating user synchronization
        sleep_time = 15
        while len([u for u in user_list if not u.synced]) > 0:
            print(f'{len([u for u in user_list if not u.synced])} users not synced')
            print(f'Waiting {sleep_time} seconds for sync')
            sleep(sleep_time)
            print('Getting Portal Users')
            portal_users = get_portal_users(api=api)
            users_to_sync = [u for u in user_list if u.username in [pu['User']['username'] for pu in portal_users] and not u.synced]

            for user in users_to_sync:
                print(f'Processing {user.username}')
                user.id = [u['User']['id'] for u in portal_users if u['User']['username'] == user.username][0]
                print(f'\t\tSetting roles & scopes', end='')
                url, payload = user.set_role_and_scope_url(baseurl=api.server)
                headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
                response = api.makeCall(url=url, payload=json.dumps(payload), method='POST', returnwith='json',
                                        headers=headers)
                error_code, error_message = validate_json_response(response)
                if error_code > 0:
                    print(f'\nERROR: Could not update roles and scopes for {user.username}')
                    if args.exit_on_error:
                        my_quit(exitcode=error_code, errormsg=error_message)
                else:
                    user.synced = True
                    with open(args.output_file, 'a') as f:
                        f.writelines([f'{user.username}, {user.password}\n'])
                    f.close()
                    print('DONE')

