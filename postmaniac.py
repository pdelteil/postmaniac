import json
import re
from colorama import Fore, Back, Style
import requests
import argparse
import random
from stringcolor import *
import sys
from tabulate import tabulate

VERSION = "0.1.1"

def get_unique_dicts(list):
    # Ensure each dictionary is converted to a frozenset of its items, which is hashable and can be used in a set.
    unique_dicts = set(frozenset(d.items()) for d in list)

    # Convert frozensets back to dictionaries and store them in authlistnodoublon.
    output = [dict(d) for d in unique_dicts]

    return output

def main():

    baseUrl          = 'https://www.postman.com/'
    urlProxy         = baseUrl+'_api/ws/proxy'
    urlenvapi        = baseUrl+'_api/environment/'
    urlrequest       = baseUrl+'_api/request/'
    urlApiCollection = baseUrl+'_api/collection/'
    urlApiFolder     = baseUrl+'_api/folder/'

    urlsWorkspaces = []
    urlsteam = []

    parser = argparse.ArgumentParser(
        description=(
            "Tool to find sensitive information from Postman Public Workspaces\n"
            "\nExamples of use:\n\n"
            "  Searching for term google.com\n"
            "  python3 postmaniac.py google.com\n"
            "  Searching for term google.com showing max 50 results\n"            
            "  python3 postmaniac.py google.com 50\n"
        ),
    formatter_class=argparse.RawTextHelpFormatter   
    )
    parser.add_argument('query', type=str, help='Query string (example: api.target.com)')
    parser.add_argument('maxresults', type=int, help='Max number of results\n example',default=10, nargs='?')
    parser.add_argument("--debug", action="store_true", help="Enable debug mode.\nThis will print additional debug information.")

    #scan only a given workspace url 

    #only search for requests

    args = parser.parse_args()
    # Show help if no arguments are provided
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    print("\nScan report for " + f"{args.query}")

    # List of user agents
    with open('useragents.txt', 'r') as file:
        user_agents = [line.strip() for line in file]
    # Choose a random user agent
    random_user_agent = random.choice(user_agents)
    
    headers = {
        'User-Agent': random_user_agent,
        'Content-Type': 'application/json',
    }
    size=100
    pages=1
    if args.maxresults > 100:
        pages=(args.maxresults // 100) + (1 if args.maxresults % 100 != 0 else 0)
    if args.maxresults < 100:
        size=args.maxresults
    data_raw = {
        "service": "search",
        "method": "POST",
        "path": "/search-all",
        "body": {
            "queryIndices": ["collaboration.workspace", 
                             "runtime.collection", 
                             "runtime.request", 
                             "adp.api", 
                             "flow.flow",
                             "apinetwork.team"],
            "queryText": f"{args.query}",
            "size": size,
            "from": 0,
            "requestOrigin": "srp",
            "mergeEntities": True,
            "nonNestedRequests": True
        }
    }
    
    for i in range(pages):
        try:
            remaining_results = args.maxresults - (i * 100)
            data_raw["body"]["size"] = min(remaining_results,100)
            # run query
            response = requests.post(urlProxy, headers=headers, json=data_raw)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
            data = response.json()  # Parse JSON response if needed
            if args.debug:
                print(f'POST Response searching for {args.query} \n {data}')
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            sys.exit(1)
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Connection error occurred: {conn_err}")
            sys.exit(1)
        except requests.exceptions.Timeout as timeout_err:
            print(f"Timeout error occurred: {timeout_err}")
            sys.exit(1)

        data_raw["body"]["from"] += 100

        for item in data['data']:
            if item['document']['documentType'] == 'request':
                if 'publisherHandle' in item['document'] and item['document']['publisherHandle']:
                    if 'slug' in item['document']['workspaces'][0]:
                        urlworkspace = baseUrl + item['document']['publisherHandle'] + '/workspace/' + item['document']['workspaces'][0]['slug']
                        urlsWorkspaces.append(urlworkspace)
                    else:
                        chelou = 'https://go.postman.co/workspace/' + item['document']['workspaces'][0]['id'] + '/request/' + item['document']['id']
                        print("Weird request" + chelou)
                        continue
                else:
                    continue
            #teams
            if item['document']['documentType'] == 'team':
                urlteam = baseUrl + item['document']['publicHandle']
                urlsteam.append(urlteam)
            #workspaces
            if item['document']['documentType'] == 'workspace':
                urlworkspace2 = baseUrl + item['document']['publisherHandle']+'/workspace/' + item['document']['slug']
                urlsWorkspaces.append(urlworkspace2)

    urlsWorkspaces = list(set(urlsWorkspaces))
    urlsWorkspaces = urlsWorkspaces[:args.maxresults]

    urlsteam = list(set(urlsteam))
    
    print("\n"+Fore.RED + str(len(urlsWorkspaces)) +" Workspaces found" + Style.RESET_ALL)
    # Print each URL with line numbers
    for i, workspaceUrl in enumerate(urlsWorkspaces, start=1):
        print(f"{i}. {workspaceUrl}")

    print(Fore.BLUE + str(len(urlsteam)) + " Teams found" + Style.RESET_ALL)

    for i, teamUrls in enumerate(urlsteam, start=1):
        print(f"{i}. {teamUrls}")

    nombrecollection = 0
    nombreenv = 0

    listeallcollec = []

    for o, workspace in enumerate(urlsWorkspaces, start=1):
        if baseUrl+"/" in workspace:
            continue
        print(Fore.YELLOW + f'\nScanning {workspace} [{o}/{len(urlsWorkspaces)}]'+ Style.RESET_ALL+"\n")
        workurlcompl = workspace + "overview"
        match_workspace = re.search(r'https://www.postman.com/([^/]+)/', workspace)
        match_workspacename = re.search(r'/workspace/([^/]+)/?$', workspace)

        worksp = match_workspace.group(1)
        workspnam = match_workspacename.group(1)

        data_rawid = {
            "service": "workspaces",
            "method": "GET",
            "path": f"/workspaces?handle={worksp}&slug={workspnam}"
        }
        # get Details of workspaces
        responseid = requests.post(urlProxy, headers=headers, json=data_rawid)
        iddiv = responseid.json()
        if args.debug:
	        print(f'POST Response getting details for workspace {workspace} \n {iddiv}')

        workspaceId  	 = iddiv['data'][0]['id']
        workspaceName    = iddiv['data'][0]['name']
        workspaceDesc    = iddiv['data'][0]['description']
        workspaceCreated = iddiv['data'][0]['createdAt']

        print(f'Name: {workspaceName}')
        print(f'Description: {workspaceDesc}')
        print(f'Created at: {workspaceCreated}\n')
        if 'error' in iddiv:
            continue

        data_raw = {
            "service": "workspaces",
            "method": "GET",
            "path": f"/workspaces/{workspaceId}?include=elements"
        }
        #get Collection
        response = requests.post(urlProxy, headers=headers, json=data_raw)
        all_uuid = response.json()
        if args.debug:
            print(f'POST Response getting Colletions for workspace {workspace} \n {all_uuid}')

        urlcollec = all_uuid['data']['elements'].get('collections', [])
        listeallcollec.extend(urlcollec)

        print(Fore.GREEN + str(len(listeallcollec)) +" Collections found" + Style.RESET_ALL)
        # Print each Collection with line numbers
        for i, urlc in enumerate(listeallcollec, start=1):
            print(f"{i}. {workspace}/collection/{urlc}")

        urlenv = all_uuid['data']['elements'].get('environments', [])

        env_list = [] 
        env_names = [] 

        for urle in urlenv:
           # urlenvfinal = workspace + "environment/" + urle
            apienvurl = urlenvapi + urle
            response = requests.get(apienvurl, headers=headers)
            environment = response.json()
            # Check if 'data' key exists in the JSON response
            envName = environment.get('data', {}).get('name')
            #print(envName)
            if envName:
                env_names.append(envName)   
            envValues = environment.get('data', {}).get('values')
            if envValues:
                env_list.append(envValues)
        print(Fore.GREEN + str(len(env_list)) +" Environment found" + Style.RESET_ALL)
        #for i, envValue in enumerate(env_list, start=1):
            #print(f"{i}. {envValue}")
        for j, item in enumerate(env_names,start=1):
            print(f"{j}. {item}")
            for i, item in enumerate(env_list, start=1):
                env_dict = item[0]  # Extract the dictionary from the list
                # Convert dictionary to a list of tuples for tabulate
                table_data = [(key, value) for key, value in list(env_dict.items())[:2]]

                # Print as table with aligned columns
                print(f"{i} .")
                for key, value in table_data:
                   print(f" {key}: {value}")
    print('\nDone!\n')
    #done scanning for collections and enviroments vars

    reqtrouv = 0
    authlist = []
    headerlist = []
    bodylist = []

    #scanning every collection
    for p, coll in enumerate(listeallcollec, start=1):
        print(f'\nScan of collection {coll} [{p}/{len(listeallcollec)}]\n')
        segments = coll.split('/')
        idseg = segments[-1]
        urltrueapi = urlApiCollection + idseg

        #getRequest
        responsecoll = requests.get(urltrueapi, headers=headers)
        collection = responsecoll.json()
        #print(collection)
    
        #Folders
        owner = collection['data']['owner']
        order = collection['data']['order']
        folderName = collection['data']['name']
        folderDesc = collection['data']['description']
        print(f"\t{folderName}, {folderDesc}")

        #subfolders of a collection
        folders_order = collection['data']['folders_order']        

        for subfolder in folders_order:
            urlsubord = urlApiFolder + owner + "-" + subfolder
            responsesub = requests.get(urlsubord, headers=headers)
            subcollection = responsesub.json()
            print(subcollection)
            if 'error' in subcollection:
                continue
            suborder = subcollection['data']['order']
            folderName = subcollection['data']['name']
            folderDesc = subcollection['data']['description']
            folderVars = subcollection['data']['variables']
            folderAuth = subcollection['data']['auth']
            folderCreated = subcollection['data']['createdAt']
            folderUpdated = subcollection['data']['updatedAt']
            print(f"\t{folderName},{folderDesc}")

            #finding subfolders (recursive)
            subsubfolders = subcollection['data']['folders_order']
            if len(subsubfolders) != 0:
                for subsubfolder in subsubfolders:
                    urlsubsubord = urlApiFolder + owner + "-" + subsubfolder
                    responsesubsub = requests.get(urlsubsubord, headers=headers)
                    print(responsesubsub)
                    subsubcollection = responsesubsub.json()
                    subsuborder = subsubcollection['data']['order']
                    order.extend(subsuborder)
            else:
                pass
            order.extend(suborder)
        reqtrouv = len(order)
        print(Fore.GREEN + f"\t{str(reqtrouv)}"+ " Requests found" + Style.RESET_ALL+"\n")
        pattern = re.compile(r'^\{\{.*\}\}$')
        #Requests per folder
        for request in order:
            urlrequestfull = urlrequest + owner + "-" + request
            print(urlrequestfull)

            requestresponse = requests.get(urlrequestfull, headers=headers)

            requestresp = requestresponse.json()
            urlreq = requestresp['data']['url']
            method = requestresp['data']['method']
            data = requestresp['data']['data']
            description = requestresp['data']['description']
            preRequestScript = requestresp['data']['preRequestScript']
            #how to get pre and post scripts?

            #Header 
            header = requestresp['data']['headerData']
            pattern = re.compile(r'^\{\{.*\}\}$')
            #removing values like {{..}}
            filtered_header_data = [item for item in header if
                                    item['key'] not in ['Content-Type', 'Accept', 'x-api-error-detail','x-api-appid'] and not pattern.match(item['value']) and item['value']]
            if filtered_header_data:
                headerlist.append(filtered_header_data)
            headerlistUnique = []
            headerlistUnique= get_unique_dicts(headerlist)
            print(Fore.RED + str(len(headerlistUnique)) + " Intersting values in headers" + Style.RESET_ALL)

            #Auth
            auth = requestresp['data']['auth']

            if auth is not None:
                authlist.append(auth)

            authlistUnique = []
            authlistUnique = get_unique_dicts(authlist)
            print(Fore.RED + str(len(authlistUnique)) + " Auth token ​​found" + Style.RESET_ALL)

            #body params
            datamode = requestresp['data']['dataMode']

            if datamode == "raw":
                body1 = requestresp['data']['rawModeData']
                #checking for keys in body
                try:
                    if body1 is not None and body1.strip():
                        parsed_data = json.loads(body1)
                    else:
                        pass
                except json.JSONDecodeError as e:
                    continue
            bodylistUnique = []
            bodylistUnique = get_unique_dicts(bodylist)    
            print(Fore.RED + str(len(bodylistUnique)) + " Intersting values in bodies" + Style.RESET_ALL)

            #more modes for body (form-data, x-www-form-urlencoded, raw, binary)
            #datamode params
            if datamode == "params" and requestresp['data']['data'] is not None and len(requestresp['data']["data"]) > 0:
                datas = requestresp['data']["data"]
                print(datas)

if __name__ == '__main__':
    main()
