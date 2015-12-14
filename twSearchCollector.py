#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
twSearchCollector: Search Twitter Tweets (ja) by specified keyword
                   To use proxy, set "http_proxy" env value

usage:
    twSearchCollector.py <Keyword> [-s <since_id>]
    twSearchCollector.py -h | --help

options:
    -h, --help       # show this help message and exit
    -s <since_id>    # specify since id (retrieve tweets after specified tweet id)
"""

import sys
import os
import json
import tweepy
import requests
from http.client import IncompleteRead

# for Twitter OAuth
AUTH_FILE = 'twitter_auth.json'

# page ( 100 tweets in a page), 0 for no limit for num of pages
PAGE_SIZE = 100
PAGE_LIMIT = 0


# overwrite tweepy
# AppAuthHandler to support proxy
# (add proxy arg to init)
class AppAuthHandlerProxy(tweepy.auth.AppAuthHandler):

    def __init__(self, consumer_key, consumer_secret, proxy=''):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self._bearer_token = ''
        self.proxy = {}
        if proxy:
            self.proxy['https'] = proxy

        resp = requests.post(self._get_oauth_url('token'),
                             auth=(self.consumer_key,
                                   self.consumer_secret),
                             data={'grant_type': 'client_credentials'},
                             proxies=self.proxy)
        data = resp.json()
        if data.get('token_type') != 'bearer':
            raise tweepy.TweepError('Expected token_type to equal "bearer", '
                                    'but got %s instead' % data.get('token_type'))

        self._bearer_token = data['access_token']


class SearchTweets:

    def __init__(self, consumer_key='', consumer_secret=''):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret

        env = os.environ

        if 'http_proxy' in env:
            self.auth = AppAuthHandlerProxy(self.consumer_key, self.consumer_secret, proxy=env['http_proxy'])
            self.api = tweepy.API(self.auth, proxy=env['http_proxy'])
        else:
            self.auth = AppAuthHandlerProxy(self.consumer_key, self.consumer_secret)
            self.api = tweepy.API(self.auth)

    def get_status(self):
        rate_limit = self.api.rate_limit_status()
        rate_limit_resources = rate_limit['resources']
        search_limit = rate_limit_resources['search']

        return search_limit

    def get_tweets(self, keyword='*', since_id=0, delegate=print):

        tweet_cnt = max_id = min_id = 0

        try:

            if since_id == 0:
                tweets = tweepy.Cursor(
                    self.api.search, q=keyword, count=PAGE_SIZE, result_type='recent',
                    include_entities=True, lang='ja').items(limit=PAGE_LIMIT)
            else:
                tweets = tweepy.Cursor(
                    self.api.search, q=keyword, count=PAGE_SIZE, result_type='recent',
                    include_entities=True, lang='ja',
                    since_id=since_id).items(limit=PAGE_LIMIT)

            for tweet in tweets:
                delegate(tweet)
                sys.stdout.flush()
                tweet_cnt = tweet_cnt + 1
                max_id = tweet.id
                if min_id == 0:
                    min_id = tweet.id

        except tweepy.TweepError:
            print('ERROR: !!! Tweepy Error !!! ')
        except IncompleteRead:
            print('ERROR: !!! http IncompleteRead Error !!!')

        return tweet_cnt, min_id, max_id


def write_tweets(tweet):
    print(tweet.text)


if __name__ == '__main__':

    from docopt import docopt

    args = docopt(__doc__)
    since_id = 0
    keyword = args['<Keyword>']
    if args['-s']:
        since_id = args['-s']

    os.path.exists(AUTH_FILE)
    f = open(AUTH_FILE, 'r')
    twitter_key = json.load(f)

    search_tweets = SearchTweets(consumer_key=twitter_key['CONSUMER_KEY'],
                                 consumer_secret=twitter_key['CONSUMER_SECRET'])

    api_status = search_tweets.get_status()
    print('INFO: twitter search api limit:', api_status['/search/tweets']['limit'],
          ', remaining:', api_status['/search/tweets']['remaining'])
    print('INFO: --------------------------------------------------')

    tweet_cnt, min_id, max_id = search_tweets.get_tweets(keyword, since_id, write_tweets)
    print('INFO: --------------------------------------------------')
    print('INFO: total tweets : ', tweet_cnt)
    print('INFO: min_id: %d, max_id: %d ' % (min_id, max_id))
    print('INFO: --------------------------------------------------')
