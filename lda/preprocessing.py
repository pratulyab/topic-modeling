from nltk.corpus import stopwords
from nltk.stem.wordnet import WordNetLemmatizer
import string

def process(docs):
	stop_words = set(stopwords.words('english'))
	punctuation_marks = set(string.punctuation)

	lemmatizer = WordNetLemmatizer()

	def clean(doc):
		stopwords_cleaned = " ".join([w for w in doc.lower().split() if w not in stop_words])
		punctuation_cleaned = ''.join(p for p in stopwords_cleaned if p not in punctuation_marks)
		lemmatized = " ".join(lemmatizer.lemmatize(word) for word in punctuation_cleaned.split())
		return lemmatized

	cleaned_docs = [clean(doc).split() for doc in docs]
	return cleaned_docs
