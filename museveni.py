"""
Created by Elizabeth Gin.
Copyright (c) 2012 __MyCompanyName__. All rights reserved.
Licensed under the Affero 3 GPL License
http://www.gnu.org/licenses/agpl.txt

"""

import datetime
from copy import deepcopy
from flask import Flask
from flask import request, url_for, render_template
from flaskext.mongoalchemy import MongoAlchemy
import shelve
import feedparser
import plivo
import sys
import re
import twitter
from HTMLParser import HTMLParser
app = Flask(__name__)
app.config.from_object('config')
app.config['MONGOALCHEMY_DATABASE'] = 'watchTest'
db = MongoAlchemy(app)

c_key = app.config('CONSUMER_KEY')
c_secret = app.config('CONSUMER_SECRET')
a_t_key = app.config('ACCESS_TOKEN_KEY')
a_t_secret = app.config('ACCESS_TOKEN_SECRET')

api = twitter.Api(consumer_key=c_key, 
consumer_secret=c_secret, 
access_token_key=a_t_key, 
access_token_secret=a_t_secret)

auth_id = app.config('AUTH_ID')
auth_token = app.config('AUTH_TOKEN')
    
class Input(db.Document):
    text = db.StringField()
    date = db.StringField()
    source = db.StringField()
    headline = db.StringField()
    tags = db.ListField(db.StringField())
    rating = db.IntField()
    speaker = db.StringField()
    createdAt = db.DateTimeField(required=True)
        
class SMS(db.Document):
    timeAnswered = db.DateTimeField()
    direction = db.StringField()
    smsTo = db.StringField()
    smsType = db.StringField()
    smsMessageUUID = db.StringField()
    smsFrom = db.StringField()
    smsText = db.StringField()
    
class User(db.Document):
    number = db.StringField()
    rss = db.ListField(db.StringField(required=False))
    sms = db.ListField(db.StringField(required=False))
    quote = db.ListField(db.StringField(required=False))
    interacting = db.StringField()
    createdAt = db.DateTimeField(required=True)
    age = db.IntField(required=False)
    gender = db.StringField(required=False)
    country = db.StringField(required=False)
    town = db.StringField(required=False)
    district = db.StringField(required=False)
    
class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self,d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

@app.route('/', methods=['POST','GET'])
def enter():
    return render_template('enter.html')
    
@app.route('/multiply', methods=['POST','GET'])
def multiply():
    return render_template('multiply.html')
    
@app.route('/comment', methods=['POST','GET'])
def comment():
    return render_template('comment.html')
    
@app.route('/login', methods=['POST','GET'])
def login():
    return render_template('login.html')

@app.route('/dashboard', methods=['POST','GET'])
def dashboard():
    global figure
    figure = ""
    if request.method == 'POST': #do this if the form is submitted
        figure = str(request.form['figure'])
    global twitterHandle
    twitterHandle = ""
    global rssSearch
    rssSearch = ""
    global new_feed
    new_feed = []
    if figure == 'Yoweri Museveni':
        twitterHandle = '@KagutaMuseveni'
        rssSearch = 'Yoweri'
        rssLink = 'http://allafrica.com/tools/headlines/rdf/uganda/headlines.rdf'
        feed = feedparser.parse(rssLink)
        for entry in feed['entries']:
            if entry.summary.find('Museveni') != -1:
                new_entry = entry
                new_feed.append(new_entry)
            if entry.summary.find(rssSearch) != -1:
                new_entry = entry
                new_feed.append(new_entry)
    else:
        twitterHandle = figure
        try: 
            full_feed = []
            new_entry = {}
            rssSearch = figure.replace(' ','')
            link1 = 'http://news.google.com/news?gl=us&pz=1&cf=all&ned=us&hl=en&q='
            link2 = '&output=rss'
            rssLink = link1 + rssSearch + link2
            feed = feedparser.parse(rssLink)
            for entry in feed['entries']:
                sumHTML = entry.summary
                summary = strip_tags(sumHTML)
                title = entry.title
                url = entry.link
                published = entry.published
                new_entry = {'title':title,'link':url,'summary':summary,'published':published}
                full_feed.append(new_entry)
                new_feed = full_feed[0:2]
        except:
            print >> sys.stderr, str(sys.exc_info()[0]) # These write the nature of the error
            print >> sys.stderr, str(sys.exc_info()[1])
    input_list = Input.query.all()
    return render_template('index.html', input_list=input_list, new_feed=new_feed, figure=figure, twitterHandle=twitterHandle, rssSearch=rssSearch, rssLink=rssLink)

@app.route('/text', methods=['POST','GET'])
def text():
    if request.method == 'POST': #do this if the form is submitted
        print >> sys.stderr, 'Received POST request to /text'
        try:
            tagsAll = str(request.form['tags'])
            tags_list = tagsAll.split(' ')
            new_input = Input(text=str(request.form['text']), date=str(request.form['date']), source=str(request.form['source']), headline=str(request.form['headline']), tags=tags_list, rating=int(request.form['rating']), speaker=figure, createdAt=datetime.datetime.now())
            new_input.save()
            input_list = Input.query.all()
        except:
            print >> sys.stderr, str(sys.exc_info()[0]) # These write the nature of the error
            print >> sys.stderr, str(sys.exc_info()[1])
    return render_template('index.html', input_list=input_list, figure=figure, new_feed=new_feed, twitterHandle=twitterHandle, rssSearch=rssSearch)
    
@app.route("/plivo/sms/", methods=['GET', 'POST'])
def sms():
    if request.method == 'POST':
        print >> sys.stderr, "Received POST request to /plivo/sms/" # this is how you write messages to yourself in the Apache /var/log/apache2/error.log
        try:
            s = SMS(timeAnswered = datetime.datetime.now(),
                                direction = 'incoming',
                                smsTo = request.form['To'],
                                smsType = request.form['Type'],
                                smsMessageUUID = request.form['MessageUUID'],
                                smsFrom = request.form['From'],
                                smsText = request.form['Text'],
                                )
            print >> sys.stderr, s
            s.save()
            caller = request.form['From']
            watchText = str(request.form['Text']).lower()
            rssU = ''
            twitterU = ''
            quotesU = ''
            watchingR = ''
            watchingT = ''
            watchingQ = ''
            if User.query.filter(User.number == caller).first():
                regisUser = User.query.filter(User.number == caller).first()
                if watchText[0:6] == '#watch':
                    if regisUser.interacting == 'start':
                        regisUser.interacting = 'pending'
                        regisUser.save()
                        message = 'Reply with #watch and the name of the person, place, or issue you would like to watch. Ex: #watch Obama'
                        send_txt(caller,message)
                    elif regisUser.interacting == 'pending':
                        victim = str(request.form['Text'])[7:]
                        regisUser.interacting = victim
                        regisUser.save()
                        message = 'You are watching ' + victim + '. Which updates to receive? \n 1: rss \n 2: twitter \n 3: quotes \n A: start again \n E: exit'
                        send_txt(caller,message)
                    elif regisUser.interacting == 'check':
                        lengthR = len(regisUser.rss)
                        lengthT = len(regisUser.sms)
                        lengthQ = len(regisUser.quote)
                        regisUser.interacting = 'start'
                        regisUser.save()
                        message = str(lengthR) + ' rss watches. \n' + str(lengthT) + ' twitter watches. \n' + str(lengthQ) + ' quote watches. \n Commands: \n #watch \n #check \n #stop'
                        send_txt(caller,message)
                    else:
                        toWatch = regisUser.interacting
                        tempStr = str(request.form['Text']).upper()
                        choiceStr = tempStr[7:]
                        a = re.compile('[1-3]')
                        if a.search(choiceStr):
                            if choiceStr.find('1') != -1:
                                regisUser.rss.append(toWatch)
                                regisUser.interacting = 'start'
                                rssU = 'rss: ' + toWatch + ' \n'
                            if choiceStr.find('2') != -1:
                                regisUser.sms.append(toWatch)
                                regisUser.interacting = 'start'
                                twitterU = 'twitter: ' + toWatch + ' \n'
                            if choiceStr.find('3') != -1:
                                regisUser.quote.append(toWatch)
                                regisUser.interacting = 'start'
                                quotesU = 'quotes: ' + toWatch + ' \n'
                            regisUser.save()
                            message = 'You will receive the following updates: \n' + rssU + twitterU + quotesU + '\n Thank you!'
                            send_txt(caller,message)
                        elif choiceStr.find('A') != -1:
                            regisUser.interacting = 'pending'
                            regisUser.save()
                            message = 'Who or what would you like to watch?'
                            send_txt(caller,message)
                        elif choiceStr.find('E') != -1:
                            regisUser.interacting = 'check'
                            regisUser.save()
                            message = 'Have a great day!'
                            send_txt(caller,message)
                        else:
                            regisUser.interacting = 'pending'
                            regisUser.save()
                            message = 'Sorry, we did not understand your text. Who or what would you like to watch?'
                            send_txt(caller,message)
                elif watchText == '#check':
                    if (len(regisUser.rss) > 0) and (len(regisUser.rss) < 3):
                        watch_list = regisUser.rss
                        watchingR = str(watch_list)
                    elif len(regisUser.rss) == 0:
                        watchingR = '0'
                    else:
                        watchingR = 'alot'
                    if (len(regisUser.sms) > 0) and (len(regisUser.sms) < 3):
                        watch_list = regisUser.sms
                        watchingT = str(watch_list)
                    elif len(regisUser.sms) == 0:
                        watchingT = '0'
                    else:
                        watchingT = 'alot'
                    if (len(regisUser.quote) > 0) and (len(regisUser.quote) < 3):
                        watch_list = regisUser.quote
                        watchingQ = str(watch_list)
                    elif len(regisUser.quote) == 0:
                        watchingQ = '0'
                    else:
                        watchingQ = 'alot'
                    message = 'rss: ' + watchingR + '\n twitter: ' + watchingT + '\n quotes: ' + watchingQ
                    send_txt(caller,message)
                elif watchText == '#stop':
                    regisUser.interacting = "start"
                    regisUser.rss = []
                    regisUser.sms = []
                    regisUser.quote =[]
                    regisUser.save()
                    message = 'You are no longer watching. We hope you watch again soon!'
                    send_txt(caller,message)
                else:
                    message = 'Sorry, please try again. #watch: new watch \n #check: check your watches \n #stop: stop all watches'
                    send_txt(caller,message)
            else:
                message = 'Welcome! Reply with #watch and the name of the person, place, or issue you would like to watch. Ex: #watch Obama'
                rss_list = []
                twitter_list = []
                quote_list = []
                newUser = User(number=caller, rss=rss_list, sms=twitter_list, quote=quote_list, interacting='pending', createdAt=datetime.datetime.now())
                newUser.save()
                send_txt(caller,message)
        except:
            print >> sys.stderr, str(sys.exc_info()[0]) # These write the nature of the error
            print >> sys.stderr, str(sys.exc_info()[1])
    else:
        return "These aren't the droids you're looking for. Move along, move along."
        
@app.route('/sms')
def list_sms():
    sms_list = SMS.query.all()
    user_list = User.query.all()
    return render_template('test.html', sms_list=sms_list, user_list=user_list)
    
@app.route('/send/<password>')
def send(password):
    if password == 'museven1':
        user_list = User.query.all()
        for user in user_list:
            if len(user.rss) > 0:
                rss_list = user.rss
                for rss in rss_list:
                    try: 
                        full_feed = []
                        new_entry = {}
                        rssSearch = rss.replace(' ','')
                        link1 = 'http://news.google.com/news?gl=us&pz=1&cf=all&ned=us&hl=en&q='
                        link2 = '&output=rss'
                        rssLink = link1 + rssSearch + link2
                        feed = feedparser.parse(rssLink)
                        for entry in feed['entries']:
                            title = entry.title
                            url = entry.link
                            published = entry.published
                            new_entry = {'title':title,'link':url,'published':published}
                            full_feed.append(new_entry)
                        new_feed = full_feed[0]
                        title = str(new_feed['title'])
                        date = str(new_feed['published'])[5:16]
                        message = title + ' ' + date
                        send_txt(user.number,message)
                    except:
                        print >> sys.stderr, str(sys.exc_info()[0]) # These write the nature of the error
                        print >> sys.stderr, str(sys.exc_info()[1])
            if len(user.quote) > 0:
                quote_list = user.quote
                print >> sys.stderr, quote_list
                for quote in quote_list:
                    try:
                        input_list = Input.query.filter(Input.speaker == quote).first()
                        print >> sys.stderr, input_list
                        text = str(input_list.text)[0:90]
                        print >> sys.stderr, text
                        date = input_list.date
                        print >> sys.stderr, date
                        message = 'Quote: ' + text + '... \n Date: ' + date
                        print >> sys.stderr, message
                        send_txt(user.number,message)  
                    except:
                        print >> sys.stderr, str(sys.exc_info()[0]) # These write the nature of the error
                        print >> sys.stderr, str(sys.exc_info()[1])
            if len(user.sms) > 0:
                print >> sys.stderr, 'FREAKING WORK YOU SUCKER!'
                twitter_list = user.sms
                print >> sys.stderr, twitter_list
                for twitter in twitter_list:
                    try:
                        result = api.GetSearch(twitter,show_user='true',per_page=1,page=1)
                        dictTweets = result[0].AsDict()
                        screen_name = dictTweets['user']['screen_name']
                        tweet = dictTweets['text']
                        date = str(dictTweets['created_at'])[5:16]
                        message = 'User: ' + screen_name + ' \n Tweet: ' + tweet + ' \n Date: ' + date
                        print >> sys.stderr, message
                        send_txt(user.number,message)
                    except:
                        print >> sys.stderr, str(sys.exc_info()[0]) # These write the nature of the error
                        print >> sys.stderr, str(sys.exc_info()[1])
        return 'Success?'
    else:
        print >> sys.stderr, 'crontabbing it up, yo'
        return 'Wrong! Try again.'
                
                

def send_txt(destination, text, src='16262190621'):
    p = plivo.RestAPI(auth_id, auth_token) # Create a Plivo API object, used when you want to write to their service
    params = { 'text':text,
              'src':src,
              'dst':destination,
              }
    p.send_message(params) # A method in the object for sending sms

if __name__ == '__main__':
    app.run(debug=True)
