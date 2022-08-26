import time
from datetime import datetime, timedelta
from urllib.parse import urlparse

from tqdm import tqdm
import unicodedata
import re









import requests
import tweepy
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import bleach

SLEEP_TIME = 5

load_dotenv()

# load from env
bearer_token = os.getenv('BEARER_TOKEN')


# filter for top level tweets
def is_top_level(tweet):
	return tweet.referenced_tweets is None or len(tweet.referenced_tweets) == 0


# filter for quote tweets
def is_quote(tweet):
	if len(tweet.referenced_tweets) == 0:
		return False
	for ref in tweet.referenced_tweets:
		if ref.type != 'retweeted':
			return False
	return True


def extract_urls(conversation, ref_tweet, client):
	urls = []

	if ref_tweet.entities is not None:
		for url in ref_tweet.entities.get('urls', []):
			urls.append({'url': url, 'tweet': ref_tweet, 'basetweet': ref_tweet})

	if conversation is not None:
		for reply in conversation:
			# check if `reply` is by the same author as `ref_tweet` and is replying to a tweet by that author
			if reply.author_id == ref_tweet.author_id:
				for ref in reply.referenced_tweets:
					if ref.type == 'replied_to':
						# fech ref
						ref = client.get_tweet(ref.id, tweet_fields=['created_at', 'referenced_tweets', 'text',
																	 'author_id', 'entities']).data

						if ref.author_id == reply.author_id and reply.entities is not None:
							for url in reply.entities.get('urls', []):
								urls.append({'url': url, 'tweet': reply, 'basetweet': ref_tweet})
	return urls


def get_job_urls(tweets, client):
	if tweets is None or len(tweets) == 0:
		return None
	print('There are tweets, proceding to extract urls')
	true_urls = []
	for tweet in tqdm(tweets):
		if is_top_level(tweet) or is_quote(tweet):
			# get the first referenced tweet's text from the api, if it exists
			if tweet.referenced_tweets is not None and len(tweet.referenced_tweets) > 0:
				ref_tweet = tweet.referenced_tweets[0]
				ref_tweet = client.get_tweet(ref_tweet.id,
											 tweet_fields=['created_at', 'referenced_tweets', 'text',
														   'conversation_id', 'author_id', 'entities']).data

				conversation_id = ref_tweet.conversation_id
				# get all tweets in that conversation by that user
				conversation = client.search_recent_tweets(query='conversation_id:' + str(conversation_id),
														   tweet_fields=['created_at', 'referenced_tweets', 'text',
																		 'author_id', 'in_reply_to_user_id', 'entities']
														   ).data

				urls = extract_urls(conversation, ref_tweet, client)
				has_found_url = False
				for url in urls:
					# parse domain from url
					domain = urlparse(url['url']['expanded_url']).netloc
					if domain != 'twitter.com':
						url['url'] = url['url']['expanded_url']
						true_urls.append(url)
						has_found_url = True

				if not has_found_url:
					true_urls.append(
						{'url': f'https://twitter.com/effective_jobs/status/{ref_tweet.id}', 'tweet': ref_tweet})
	return true_urls


def slugify(value, allow_unicode=False):
	"""
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
	value = str(value)
	if allow_unicode:
		value = unicodedata.normalize('NFKC', value)
	else:
		value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
	value = re.sub(r'[^\w\s-]', '', value.lower())
	return re.sub(r'[-\s]+', '-', value).strip('-_')


def main():
	client = tweepy.Client(
		bearer_token,
		# access_token=access_token, access_token_secret=access_token_secret,
		# consumer_key=consumer_key, consumer_secret=consumer_secret,
		wait_on_rate_limit=True,
	)

	user_id = client.get_user(username='Effective_Jobs').data['id']

	tweets = client.get_users_tweets(
		user_id, tweet_fields=['created_at', 'referenced_tweets', 'text'], max_results=100,
		start_time=datetime.now() - timedelta(days=45)
	).data

	print('executing')
	jobs = get_job_urls(tweets, client)
	if jobs is None:
		return None
	for job in tqdm(jobs):
		title_text = ""

		try:
			job_html = requests.get(job['url'])
			# use bs4 to extract the 'title' tag
			job_html.raise_for_status()
			job_soup = BeautifulSoup(job_html.text, 'html.parser')
			title = job_soup.find('title')
			if title is not None:
				title_text = title.text

			# check for "real" titles
			if len(title_text.split()) < 2:
				title_text = job['basetweet'].text[0:100].replace('\n', ' ') + '...'
		except Exception as e:
			print(e)
			title_text = job['basetweet'].text[0:100].replace('\n', ' ') + '...'
		# print(job['tweet'])

		description = job['tweet'].text
		# todo lots of injection opportunities here

		safe_url = bleach.clean(job['url'])

		post = f"""---
layout: post
title:  "{title_text}"
date:   {job['tweet'].created_at}
categories: jobs
---
{description}


"""
		post = bleach.clean(post)
		post += f"""<meta http-equiv="refresh" content="0; URL={safe_url}" />"""

		post = post.replace("{", "&#123;").replace("}", "&#125;")

		# strip title_text to be a valid filename
		date_string = job['tweet'].created_at.strftime('%Y-%m-%d')
		fn = slugify(f'{date_string}-{title_text}') + '.markdown'

		# write post to effective_jobs/_posts/{title_text}{date}.markdown
		with open(f'./remote/effective_jobs/_posts/{fn}', 'w', encoding="utf-8") as f:
			f.write(post)


if __name__ == '__main__':
	main()
