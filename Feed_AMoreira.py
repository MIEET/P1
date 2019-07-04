#Ana Moreira
#27/05/2019
#project: RSS feed
#thread for each feed (URL)
#new feed-items for every x minutes

import feedparser, threading                                                    #feedparser and threading modules for threads
from pymongo import MongoClient
from multiprocessing.dummy import Pool as ThreadPool
from termcolor import colored

client = MongoClient()                                                          #MongoClient instance
rssfeed = client.rssfeed                                                        #database

feed = rssfeed.feed                                                             #collection for feeds (inside feed there are items)
act_url_dB = rssfeed.act_url                                                    #collection for RSS URL's active addresses
act_alert = rssfeed.act_alert                                                   #collection for active alerts
alert_title_desc = rssfeed.alert_title_desc                                     #collection with feed containing the alerts in title/description of the feed

act_alert_list = []                                                             #contains the list of active alerts in memory
act_url = []                                                                    #contains the list of active urls in memory
act_url_list = []                                                               #contains the list of active urls in memory

#==================================================================================================================================#

def act_list(url):
    dup_item = list(act_url_dB.find({"orig_url": url}))                         #detects duplicated url in act_url dB
    j_url = {'orig_url': url}
    if not dup_item:                                                            #if no duplicates
        act_url_dB.insert_one(j_url)                                            #export to dB
        act_url_list.append(url)                                                #export to memory

def add_feed(url):                                                              #receives RSS URL's addresses from the list
    loaded_json = feedparser.parse(url)
    new_url =[]
    for item in loaded_json.entries:                                            #construct a simplified json
        j_const = {
            'title': item['title'],
            'description': item['description'],
            'guid': item['guid'],
            'published': item['published'],
            'orig_url': url
        }

        dup_item = list(feed.find({"guid": j_const["guid"]}))                   #detect duplicated feed through guid
        if not dup_item:                                                        #append item to list in case there are no duplicates
            new_url.append(j_const)
    if new_url:                                                                 #if there are new items, export to dB
        feed.insert_many(new_url)

def load_list(txt):
    urls_list = open(txt)
    url_clean = [(line.strip().strip('\n')) for line in urls_list]              #removes spaces between urls, n creates list
    for item in url_clean:
        add_feed(item)
        act_list(item)

def remove_feed(url_rmv):
    res = list(act_url_dB.find({"orig_url": url_rmv}))                          #search for a "url" in dB
    if res:                                                                     #if the url exists
        feed.delete_many({"orig_url": url_rmv})                                 #remove all documents from feed that match a url
        act_url_dB.delete_many({"orig_url": url_rmv})                           #remove all documents from act_list_dB that match a url
        while url_rmv in act_url_list: act_url_list.remove(url_rmv)             #remove all documents from act_list mem that match a url
    else:
        print("The url was not found")

def search(word):
    results = list(feed.find({"title": {'$regex': word}}))                      #search for a "word" in the titles
    if results:                                                                 #if "word" is found, print content
        for i in range(len(results)):
            print("title: ", results[i]["title"])
            # print("description: ", results[i]["description"])
            print("guid: ", results[i]["guid"], "\n")
            # print("published: ", results[i]["published"])
            # print("orig_url: ", results[i]["orig_url"], "\n")
    else:
        print("No titles associated with choosen word")

def add_alerts(alert_word):
    j_alert = {'alert': alert_word}
    dup_alert = list(act_alert.find({"alert": alert_word}))                     #detect duplicated alerts in dB
    if not dup_alert:                                                           #if unique alert
        act_alert.insert_one(j_alert)                                           #insert alert in dB

    for doc in feed.find({'$or': [{'title': {'$regex': alert_word}}, {'description': {'$regex': alert_word}}]}):            #find data with choosen alert from "feed" and pass it to "alert_title_desc"
        dup_item = list(alert_title_desc.find({"guid": doc["guid"]}))                                                       #search for duplicates in collection through guid
        if not dup_item:                                                                                                    #se não houver guid duplicados
            print("\ntitle: ", doc["title"])
            print("guid: ", doc["guid"])
            alert_title_desc.insert_one(doc)

def rmv_alerts(alert_rmv):
    alert = list(act_alert.find({"alert": alert_rmv}))                          #search for an "alert" in the list
    if alert:                                                                   #if the alert exists
        act_alert.delete_many({"alert": alert_rmv})                             #remove all documents from alert_list_dB that match the word
        while alert_rmv in act_alert_list: act_alert_list.remove(alert_rmv)     #remove all alerts from alerts_list in memory that match the word

    else:
        print("The alert was not found")

def update_act_url():                                                           #updates active list of urls in memory
    act_url = list(act_url_dB.find({}, {"_id": 0}))                             #import urls from dB
    print("\nActive feeds: ", act_url, "\n")

    for i in range(len(act_url)):                                               #import url without json format to mem
        url_list = act_url[i]["orig_url"]
        act_url_list.append(url_list)

def thread_act_url():
    if act_url_list:                                                            #if the list of active url is not empty
        pool = ThreadPool(len(act_url_list))
        pool.map(add_feed, act_url_list)                                        #applies a given function to each element of a list, returning a list of results
        pool.close()
        pool.join()

def feed_timer():
    time_min = 0.0833                                                           #time in min - 5 sec
    time_sec = time_min*60                                                      #time in sec
    thread = threading.Timer(time_sec, thread_act_url)
    thread.start()
    thread.join()                                                               #waits for the thread to finish

def update_act_alerts():                                                        #updates list of alerts in memory
    act_alerts = list(act_alert.find({}, {"_id": 0}))
    print("Active alerts: ", act_alerts)

    for i in range(len(act_alerts)):                                            #import alerts without json format
        alert_list = act_alerts[i]["alert"]
        act_alert_list.append(alert_list)

def thread_act_alert():
    if act_alert_list:
        pool = ThreadPool(len(act_alert_list))
        pool.map(add_alerts, act_alert_list)                                    #applies a given function to each element of a list, returning a list of results
        pool.close()
        pool.join()

def alert_timer():
    while True:
        time_min = 0.0833                                                       #time in min (10 sec)
        time_sec = time_min*60                                                  #time in sec
        thread = threading.Timer(time_sec, thread_act_alert)
        thread.start()
        thread.join()                                                           #waits for the thread to finish

def menu():                                                                     #text menu
    while True:                                                                 #while loop which will keep going until loop = False
        print("\n", 40 * "-", "MENU", 40 * "-", "\n")
        print(colored('add-feed', 'magenta'), colored('<url>:', 'cyan'), colored('        Adds feeds on run time', 'green'))
        print(colored('remove-feed', 'magenta'), colored('<url>:', 'cyan'), colored('     Removes feeds on run time', 'green'))
        print(colored('load', 'magenta'), colored('<list.txt>:', 'cyan'), colored('       Loads feeds from a file containing a list of url', 'green'))
        print(colored('title-contains', 'magenta'), colored('<word>:', 'cyan'), colored(' Asks the DB for news containing given words', 'green'))
        print(colored('alert-on', 'magenta'), colored('<word>:', 'cyan'), colored('       Creates alerts every x minutes for keywords', 'green'))
        print(colored('remove-alert ', 'magenta'), colored('<word>:', 'cyan'), colored('  Removes created alert', 'green'))
        print(colored('exit:', 'magenta'), colored('                  Quits', 'green'))
        print("\n", 86 * "-","\n")

        choice = input("Enter your choice: ")
        tokens = choice.split()

        if tokens[0] == 'add-feed':
            print("Option 1 has been selected.", "\n")
            url_select = tokens[1]
            act_list(url_select)
            add_feed(url_select)

        elif tokens[0] == 'remove-feed':
            print("Option 2 has been selected.", "\n")
            url_rmv = tokens[1]
            remove_feed(url_rmv)

        elif tokens[0] == 'load':
            print("Option 3 has been selected.", "\n")
            txt = tokens[1]
            load_list(txt)

        elif tokens[0] == 'title-contains':
            print("Option 4 has been selected.", "\n")
            word = tokens[1]
            search(word)

        elif tokens[0] == 'alert-on':
            print("Option 5 has been selected.", "\n")
            alert_word = tokens[1]
            add_alerts(alert_word)                                                      #creates alerts every x minutes for keywords

        elif tokens[0] == 'remove-alert':
            print("Option 6 has been selected.", "\n")
            alert_rmv = tokens[1]
            rmv_alerts(alert_rmv)

        elif tokens[0] == 'exit':
            print("Option 7 has been selected.", "\n")
            print("Program closed.")
            quit()

        else:                                                                           #any inputs other than the available options, print an error message
            print("Wrong option selection. Please try again.", "\n")

#==================================================================================================================================#

update_act_url()                                                                        #update list of active url in memory, from dB
feed_timer()
update_act_alerts()
t_menu = threading.Thread(target=menu)
t_menu.start()
alert_timer()
t_menu.join()
