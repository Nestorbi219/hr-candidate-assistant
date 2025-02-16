import gensim.downloader as api

word2vec_model = api.load("word2vec-ruscorpora-300")

print("sql" in word2vec_model)
print("python" in word2vec_model)