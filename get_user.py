
from ldap3 import Server, Connection, ALL, NTLM, SUBTREE
import csv
import boto3
import os


def lambda_handler(event, context):

    server = Server('YOUR SERVER', use_ssl=True, get_info=ALL)                # AD Server address

    conn = Connection(server, "CN OF YOUR USER", "USER PASSWORD", auto_bind=True, auto_referrals=False) # Authenticated User to make the query

    # Connection settings to use for the query. Specify OU, that you are looking for a group and that you're looking for its members

    conn.search(
        search_base='BASE CN',
        search_filter='(objectClass=group)',
        search_scope='SUBTREE',
        attributes = ['member']
    )


    all_users = []
    your_groups = ["GROUPA","GROUPB","GROUPC"]
    user_without_groups = []
    user_with_groups = []

    # For all users from the search above, use their names to look them up in the AD and get their Names, Usernames, distinguishedNames and Email addresses.
    # Outmatically create a csv file and store the data as a dictionary on it to use with Quicksight afterwards.

    for entry in conn.entries:
        for member in entry.member.values:

            conn.search(
                search_base='BASE CN',
                search_filter=f'(distinguishedName={member})',
                search_scope='SUBTREE',
                attributes=[
                    'mail',
                    'sAMAccountName',
                    "displayName",
                    "distinguishedName"
                ]
            )

            if len(conn.entries) >= 1:
                all_users.append(str(conn.entries[0].distinguishedName.value) + ";" + str(conn.entries[0].displayName.value) + "," + str(conn.entries[0].sAMAccountName.value) + "," + str(conn.entries[0].mail.value))

    # Use the list with all user to query each of them and check wether or not they're in a specific group

    for entry in all_users:

        dn = entry.split(";")[0]

        conn.search(
            search_base='BASE CN',
            search_filter=f'(|(&(objectClass=*)(member={dn})))',
            search_scope='SUBTREE',
            attributes=[
                'sAMAccountName',
                'displayName',
                'mail',
            ]
        )

        is_in_group = False

        for item in conn.entries:
            if item.sAMAccountName in your_groups:
                user_with_groups.append(str(item.sAMAccountName.value) + ',' + str(entry.split(";")[1]))
                is_in_group = True

        if not is_in_group:
            user_without_groups.append(str(entry.split(";")[1]))


    # Create a csv file and add all users from the user_without_group list into it

    os.chdir('/tmp')

    with open(r'user_without_dashboard.csv', 'a', newline='') as no_dashboard:
        fieldnames = ['Name', 'CWID', 'Email']

        writer = csv.DictWriter(no_dashboard, fieldnames=fieldnames)

        writer.writeheader()

        for entry in user_without_groups:

            writer.writerow({'Name': entry.split(",")[0], 'CWID': entry.split(",")[1], 'Email': entry.split(",")[2]})
            all_users.append(conn.entries[0].sAMAccountName.value)

    # Create a csv file and add all users from the user_wit_group list into it

    with open(r'user_with_dashboard.csv', 'a', newline='') as with_dashboard:
        fieldnames = ['Group','Name', 'CWID', 'Email']

        writer = csv.DictWriter(with_dashboard, fieldnames=fieldnames)

        writer.writeheader()

        for entry in user_with_groups:

            writer.writerow({'Group': entry.split(",")[0], 'Name': entry.split(",")[1], 'CWID': entry.split(",")[2], 'Email': entry.split(",")[3]})
            all_users.append(conn.entries[0].sAMAccountName.value)




    # Upload both files to s3


    s3_client = boto3.client('s3')
    s3_client.upload_file("user_with_dashboard.csv", "YOUR S3 BUCKET", "user_with_dashboard.csv")
    s3_client.upload_file("user_without_dashboard.csv", "YOUR S3 BUCKET", "user_without_dashboard.csv")



