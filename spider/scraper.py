import os, sys, time
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from datetime import timedelta
from spider.parser import PARSER_LOOKUP
from tornado import gen, httpclient, ioloop, queues, web
from urllib.parse import quote_plus, urlparse
from lda.modeling import model

SEARCH_ENGINES = {
	'google'     : {'url': 'https://google.com/search?q=%s&num=100'},
}

CONCURRENCY = 10 # Num. Of Concurrent Workers

@gen.coroutine
def get_text_from_url(url):
	''' Crawls url, scrapes the page and parses the text '''
	
	try:
		response = yield httpclient.AsyncHTTPClient().fetch(url, request_timeout=3) # Asynch network fetch call
		html = response.body #if isinstance(response.body, str) else response.body.decode()
		parser = PARSER_LOOKUP['text'](html) # Create specific parser object
		text = parser.get_text(encoding='utf-8') # Parse text
	except Exception as e:
#		print('Exception: %s %s' % (e, url))
		raise gen.Return('')
	# Tornado way of returning data from coroutines.
	raise gen.Return(text)

def get_se_parser(url):
	''' Returns particular Search Engine parser class based on domain of url if found in PARSER_LOOKUP; otherwise None '''
	subdomain = urlparse(url).netloc
	domain = subdomain.split('.')[-2].lower()
	return PARSER_LOOKUP.get(domain)

@gen.coroutine
def get_links_from_url(url):
	''' Crawls url, scrapes search result page and parses for results' links '''
	
	try:
		response = yield httpclient.AsyncHTTPClient().fetch(url, request_timeout=4)
		try:
			html = response.body if isinstance(response.body, str) else response.body.decode()
		except:
			html = response.body
		parser = get_se_parser(url)(html)
		links = parser.get_links()
	except Exception as e:
#		print('Exception: %s %s' % (e, url))
		raise gen.Return([])
	
	raise gen.Return(links)


@gen.coroutine
def boot(query, n=100):
	''' Boot spider '''
#	if not query or not n:
#		raise gen.Return([])
	query = quote_plus(query) # Quote Query
	start = time.time()
	se_queue = queues.Queue() # Queue to store search engine urls with quoted query
	links_queue = queues.Queue() # Queue to store search result links
	fetching, fetched, processed = set(), set(), set() 
	result = list()
	TOTAL_PROCESSED = list() # Hack to limit slider range, because global int variable doesn't work with coroutine	

	@gen.coroutine
	def scrape_link():
		url = yield se_queue.get()
		try:
			if url in fetching:
				return
#			print('fetching url', url)
			fetching.add(url)
			links = yield get_links_from_url(url)
			fetched.add(url)
#			print(len(links), 'links fetched from', url)
			for each in links:
				if each.startswith('http'):
					yield links_queue.put(each) # Adding to links_queue
		finally:
			se_queue.task_done() # Decrement task counter

	@gen.coroutine
	def scrape_text(n):
		url = yield links_queue.get()
		try:
			if url in processed or len(TOTAL_PROCESSED) >= n:
				raise gen.Return('')
#			print('processing url', url)
			TOTAL_PROCESSED.append(url)
			processed.add(url)
			text = yield get_text_from_url(url)
			fetched.add(url)
			if text:
				result.append({'url': url, 'text': str(text)})
#			else:
#				print('no text for', url)
		finally:
			links_queue.task_done()

	@gen.coroutine
	def create_worker(who):
		if who == 'link_scraper':
			while True:
				yield scrape_link()
		else:
			# text_scraper
			while True:
				yield scrape_text(n)

	# Enqueue search engine urls into se_queue
	for key,se in SEARCH_ENGINES.items():
		se_queue.put(str(se['url'] % query))

	for _ in range(2):
		# Create worker to send request to search engines and crawl links
		create_worker(who='link_scraper')
	
	yield se_queue.join(timeout=timedelta(seconds=120)) # Block until queue is empty or timeout is reached
	
	for _ in range(CONCURRENCY):
		# Create worker to send request to link and parse text
		create_worker(who='text_scraper')
	
	yield links_queue.join(timeout=timedelta(seconds=300))

	print('Scraped %d URLs in %d seconds.' % (len(fetched), time.time() - start))

	lda_model, results = model(result)
	topics = [str(topic[1]) for topic in lda_model.show_topics(num_words=7)]
	raise gen.Return({'topics': topics, 'results': results})
