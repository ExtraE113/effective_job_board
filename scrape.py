import re

import pytz
import datetime
import snscrape.modules.twitter as sntwitter

from_handle = "POTUS"

days_to_summarize = 2

# List of tweet text
tweets_list = []
# Using TwitterSearchScraper to scrape data and append tweets to list
for i, tweet in enumerate(sntwitter.TwitterSearchScraper(f'from:@{from_handle}').get_items()):
	if tweet.date < datetime.datetime.now(pytz.timezone('US/Pacific')) - datetime.timedelta(days=days_to_summarize):
		break

	tweets_list.append(tweet)

print(tweets_list)
print(len(tweets_list))
