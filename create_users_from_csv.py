import csv
import xmltodict
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
        role_payload = {'roleList': {
            'add': {'RoleData': []}
        }
        }
        for role in self.portal_role:
            role_payload['roleList']['add']['RoleData'].append({'name': {'#text': role}})
        return role_payload

    def __scope_tags_url(self):
        scope_payload = {'scopeTags': {
            'add': {'TagData': []}
        }
        }
        for tag in self.scope_tags:
            scope_payload['scopeTags']['add']['TagData'].append({'id': {'#text': tag}})
        return scope_payload

    def set_role_and_scope_url(self, baseurl: str):
        url = '%s/qps/rest/2.0/update/am/user/%s' % (baseurl, self.id)
        dict_payload = {'ServiceRequest': {'data': {'User': {}}}}
        dict_payload['ServiceRequest']['data']['User'].update(self.__scope_tags_url())
        dict_payload['ServiceRequest']['data']['User'].update(self.__role_url())

        return url, xmltodict.unparse(dict_payload)


def get_portal_users(api: QualysAPI.QualysAPI):
    portal_user_dict = {'ServiceRequest': {
        'filters': {
            'Criteria': {
                '@field': 'id',
                '@operator': 'GREATER',
                '#text': '0'
            }
        }
    }}
    payload = xmltodict.unparse(portal_user_dict)
    response = api.makeCall(url='%s/qps/rest/2.0/search/am/user' % api.server, payload=payload)
    error_code, error_message = validate_api_response(response=response)
    if error_code > 0:
        my_quit(exitcode=error_code, errormsg='Could not get Portal users: Reason (%s)' % error_message)
    return response


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
            if row[0].find('#') == 0:
                continue
            user = QualysUser()
            user.forename = row[0]
            user.surname = row[1]
            user.email = row[2]
            user.title = row[3]
            user.portal_role = row[4].split(';')
            user.scope_tags = row[5].split(';')
            user.phone = '1234'
            user.address1 = '22 Acacia Avenue'
            user.city = 'Acaciaville'
            user.country = 'United Kingdom'
            user.business_unit = 'Unassigned'
            user.time_zone_code = ''
            user.external_id = None
            user.id = None

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
                    print('\t%s (%s %s)' % (user.username, user.forename, user.surname))

            else:
                # We're running with the "-n" or "--no_call" options, so don't run the API call, just output
                # what we would have sent and the URL we would have sent it to
                print('NO_CALL: Output URL and Payload\nURL: %s\nPAYLOAD: %s' % (url, payload))

            user_list.append(user)

        # Check to make sure there we actually created users
        if len(user_list) == 0:
            print('No users created, exiting')
            my_quit(0, '')

        # Now that we have the users created, we need to wait while the platform syncs between QWEB and Portal
        print('Waiting for Portal Sync (120 seconds)')
        sleep(120)

        # Now get the Portal User IDs, so first we have to get all users
        response = get_portal_users(api=api)

        # With all users in the response, filter out the cruft at the beginning of the output and store the actual
        # users in users_dict (converting on the fly to a dictionary format with xmltodict.parse()
        users_dict = xmltodict.parse(ET.tostring(response))['ServiceResponse']['data']['User']

        # For each user that we created, find that user in the list of Portal users and set the ID to match
        for user in user_list:
            while user.id is None:
                portal_user = list(filter(lambda x: x["username"] == user.username, users_dict))
                if len(portal_user) > 0:
                    print('Found ID %s for user %s' % (portal_user[0]["id"], user.username))
                    user.id = portal_user[0]["id"]
                else:
                    print('\tERROR: USER ID NOT FOUND!')
                    if args.exit_on_error:
                        my_quit(4, 'USER ID NOT FOUND FOR USER %s' % user.username)
                    else:
                        print('User ID not found for user %s - waiting 20 seconds for Portal sync' % user.username)
                        sleep(20)
                        response = get_portal_users(api=api)
                        users_dict = xmltodict.parse(ET.tostring(response))['ServiceResponse']['data']['User']
                        continue

        # Now we have the complete data in the user objects it's time to set the scope and tags
        print('Setting scopes and roles:')
        if args.debug:
            print('%d users in user_list' % len(user_list))
        for user in user_list:
            print('\t%s ... ' % user.username, end='')
            url, payload = user.set_role_and_scope_url(baseurl=api.server)
            response = api.makeCall(url=url, payload=payload)
            error_code, error_message = validate_api_response(response)
            if error_code > 0:
                if args.exit_on_error:
                    print('ERROR')
                    my_quit(exitcode=error_code, errormsg=error_message)
                else:
                    print('\nERROR: %s (%s)' % (error_message, error_code))
            else:
                print('DONE')

        # Finally write the usernames and passwords to the output file
        for user in user_list:
            with open(args.output_file, 'w') as f:
                f.write('%s,%s' % (user.username, user.password))
