import gensim
from gensim import corpora
from lda.preprocessing import process
from math import ceil

def model(documents_dict):
	docs = [doc['text'] for doc in documents_dict]
	docs = process(docs)
	dictionary = corpora.Dictionary(docs)
	doc_term_matrix = [dictionary.doc2bow(doc) for doc in docs]
	
	lda_model = gensim.models.ldamodel.LdaModel(doc_term_matrix, num_topics=ceil(len(docs) * .2), id2word = dictionary, passes=50)

	results = [] # [{'url': '',  'topicID': ''}]

	for i,bow in enumerate(doc_term_matrix):
		doc_topics = lda_model.get_document_topics(bow)
		doc_topics = sorted(doc_topics, key=lambda d: d[1], reverse=True)
		dominant_topicID = doc_topics[0][0]
		results.append({'url': documents_dict[i]['url'], 'topicID': dominant_topicID})
	
#	from pprint import pprint
#	pprint(results)
	return (lda_model, results)
