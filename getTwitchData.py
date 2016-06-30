import mechanize
from bs4 import BeautifulSoup
import re
import pickle
import os
from multiprocessing import Pool, Manager

users = ['Lirik']
# Sample gameID 360430109
def getLog(url):
    # driver = webdriver.Firefox()
    # driver.get(url)
    # print driver.page_source

    log = ''
    br = mechanize.Browser()
    br.set_handle_equiv(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)
    br.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36')]

    log = br.open(url+".txt").read()
    # print log
    return log

# abbr det
def get_urls(user):
    br = mechanize.Browser()
    br.set_handle_equiv(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)
    br.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36')]
    # br.addheaders = [('cookie','__cfduid=d19f7772aac48c190924467e904c70a571464208750')]
    #cookie:__cfduid=d19f7772aac48c190924467e904c70a571464208750
    urls = []
    user_url = 'http://overrustlelogs.net/{}%20chatlog'.format(user)
    print user_url
    date_page = br.open(user_url).read()
    folders = re.findall('chatlog/(.+?(?="))',date_page)
    for folder in folders:
        logs_url = user_url+"/"+folder
        logs_page = br.open(logs_url).read()
        dates = re.findall(folder+'/(\d+-\d+-\d+)',logs_page)
        for date in dates:
            urls.append(logs_url+"/"+date)
    return urls

def addLogData(url,db):
    log = getLog(url)
    db[url] = log
    print len(db)


def getData():
    if os.path.isfile("chat_urls.p"):
        chat_urls = pickle.load( open( "chat_urls.p", "rb" ) )
    else:
        chat_urls = {}
        for user in users:
            chat_urls[user] = get_urls(user)
        teams_url = "http://espn.go.com/mlb/teams"
        pickle.dump( chat_urls, open( "chat_urls.p", "wb" ) )

    # for user in chat_urls:
    #     urls = chat_urls[user]
    #     for url in urls:
    #         getLog(url)
    logDB = {}
    for user in chat_urls:
        logDB[user] = {}
    p = Pool(20)
    i=0
    manager = Manager()
    db = manager.dict()
    for user in chat_urls:
        for url in chat_urls[user]:
            i+=1
            p.apply_async(addLogData, args=(url,db))
    p.close()
    p.join()
    out = db._getvalue()
    outfile = open("rawChat.txt","wb")
    for url in out:
        outfile.write(out[url]+"\n")
    # pickle.dump( out, open("logDB.p", "wb" ) )

# print getArticle('360430109')
# getGameIds("det")
def main():
    getData()

if __name__ == "__main__":
    main()
