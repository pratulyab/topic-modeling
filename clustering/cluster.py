import collections, re
from numpy import corrcoef # Pearson's Correlation Coefficient
from PIL import Image, ImageDraw

def preprocess(result):

	# Bag of Words
	word_counts = []
	for each in result:
		bow = collections.Counter(re.findall(r'\w+', each['text']))
		word_counts.append({'url': each['url'], 'bow': bow})
	
	del result # Freeing up memory

	global_word_count = {} # In how many docs does a word occur

	for each in word_counts:
		for word, count in each['bow'].items():
			if count > 1:
				global_word_count[word] = global_word_count.setdefault(word, 0) + 1

	# Filtering words based on their probability of occurrence
	# Because 'the' is a high probability word; thus isn't worth considering
	# Similarly, low probability words particular to particular docs are also
	# not helpful.
	final_words = []
	for word,count in global_word_count.items():
		prob = count/len(word_counts)
		if prob > 0.05 and prob < 0.3:
			final_words.append(word)


	# URL Word1 Word2 Word3 ...
	# xxx  2     0     0    ...
	# yyy  22    11    9    ...
	table = [] # To store the above DS

	# TABLE:
	# # ROWS: final_words
	# # COLS: count corresponding to each doc(url)
	# # # Indices synced according to 'url' order in 'word_counts'

	table.append(final_words)

	for each in word_counts:
		url, bow = each['url'], each['bow']
		# No need to check existence because Counter object (bow)
		# returns 0 if word doesn't exist
		counts = [bow[word] for word in final_words]
		table.append(counts)

	urls = [each['url'] for each in word_counts]
	return (urls, table)


class BiCluster(object):
	def __init__(self, vec, left=None, right=None, distance=0.0, cid=None):
		self.left = left
		self.right = right
		self.vec = vec
		self.cid = cid # Cluster ID
		self.distance = distance

def hierarchical_clustering(rows, closeness=corrcoef):
	calculated_distances = {} # Caching distance calculations
	current_cluster_id = -1

	clusters = [BiCluster(rows[i], cid=i) for i in range(len(rows))]

	while len(clusters) > 1:
		closest_pair = (0,1)#(clusters[0].cid, clusters[1].cid)
		closest_dist = closeness(clusters[0].vec, clusters[1].vec)[0,1]

		# Finding smallest distance
		for i in range(len(clusters)):
			for j in range(i+1, len(clusters)):
				c1 = clusters[i]
				c2 = clusters[j]
				if (c1.cid, c2.cid) not in calculated_distances:
					calculated_distances[(c1.cid, c2.cid)] = closeness(c1.vec, c2.vec)[0,1]

				dist = calculated_distances[(c1.cid, c2.cid)]

				if dist < closest_dist:
					closest_dist = dist
					closest_pair = (i,j)#(c1.cid, c2.cid)

		c1 = clusters[closest_pair[0]]
		c2 = clusters[closest_pair[1]]
		# Calcuating average of the two clust

		avg_vec = [(c1.vec[i] + c2.vec[i])/2 for i in range(len(c1.vec))]

		# New combined cluster
		new_cluster = BiCluster(avg_vec, left=c1, right=c2, distance=closest_dist, cid=current_cluster_id)

		current_cluster_id -= 1
		del clusters[closest_pair[1]]
		del clusters[closest_pair[0]]
		clusters.append(new_cluster)

	return clusters[0]

def print_cluster(cluster, labels=None, n=0):
	for i in range(n):
		print(' ', end='')
	if cluster.cid < 0:
		print ('-')
	else:
		if labels == None:
			print(cluster.cid)
		else:
			print (labels[cluster.cid])

	if cluster.left != None:
		print_cluster(cluster.left, labels=labels, n=n+1)
	if cluster.right != None:
		print_cluster(cluster.right, labels=labels, n=n+1)


# # # # # #
def getheight(cluster):
	if cluster.left == None and cluster.right == None:
		return 1
	return getheight(cluster.left) + getheight(cluster.right)


def getdepth(cluster):
	if cluster.left == None and cluster.right == None:
		return 0
	return max(getdepth(cluster.left), getdepth(cluster.right)) + cluster.distance

def drawnode(draw, cluster, x, y, scaling, labels):
	if cluster.cid < 0:
		h1 = getheight(cluster.left) * 20
		h2 = getheight(cluster.right) * 20
		top = y - (h1+h2)/2
		bottom = y + (h1+h2)/2
		ll = cluster.distance * scaling
		draw.line((x, top+h1/2, x, bottom-h2/2), fill=(255,0,0))

		draw.line((x, top+h1/2, x+ll, top+h1/2), fill=(255,0,0))

		draw.line((x, bottom-h2/2, x+ll, bottom-h2/2), fill=(255,0,0))

		drawnode(draw, cluster.left, x+ll, top+h1/2, scaling, labels)
		drawnode(draw, cluster.right, x+ll, bottom-h2/2, scaling, labels)

	else:
		draw.text((x+5,y-7), labels[cluster.cid], (0,0,0))

def drawdendrogram(cluster, labels, jpeg='clusters.jpg'):
	h = getheight(cluster) * 20
	w = 1200
	depth = getdepth(cluster)

	scaling = float(w-150)/depth

	img = Image.new('RGB', (w,h), (255,255,255))
	draw = ImageDraw.Draw(img)

	draw.line((0, h/2, 10, h/2), fill=(255, 0, 0))

	drawnode(draw, cluster, 10, h/2, scaling, labels)
	img.save(jpeg, 'JPEG')


# # # # # #
'''
def print_table(table):
	print(len(table), len(table[0]))
	for i in range(len(table)):
		if i > 2:
			break
		for j in range(len(table[0])):
			print(table[i][j], end=" ")
		print()
'''

def run(result, rotate=True):
	# Column Clustering when rotate = True
	
	urls, table = preprocess(result)
#	print_table(table)
	if rotate:
		labels = table.pop(0) # final_words
		rotated_table = []
		for j in range(len(table[0])):
			newrow = []
			for i in range(len(table)):
				newrow.append(table[i][j])
			rotated_table.append(newrow)
#		print_table(rotated_table)
#		rotated_table.insert(0, urls)
		table = rotated_table
		rows = table[0:]
	else:
		labels = urls
		rows = table[1:]
	cluster = hierarchical_clustering(rows)
#	print_cluster(cluster, labels=labels)
	drawdendrogram(cluster, labels)
