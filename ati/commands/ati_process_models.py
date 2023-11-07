
from django.core.management.base import BaseCommand
from django.conf import settings
import logging
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
import os
import pandas as pd
import pickle
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import string
import sys


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
stemmer = PorterStemmer()


def stem_tokens(tokens, stemmer):
    stemmed = []
    for item in tokens:
        stemmed.append(stemmer.stem(item))
    return stemmed


def tokenize(text):
    tokens = nltk.word_tokenize(text)
    tokens = [i for i in tokens if i not in string.punctuation]
    stems = stem_tokens(tokens, stemmer)
    return stems


class Command(BaseCommand):
    help = 'Django manage command that will import CSV data into a Solr search that created with the ' \
           'import_schema_ckan_yaml command'

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument('--csv', type=str, help='CSV filename to import', required=True)

    def handle(self, *args, **options):
        nltk.data.path.append(os.path.join(settings.NLTK_DATADIR))
        self.logger.info(f"Reading NLTK data from {settings.NLTK_DATADIR}")

        df_ati = pd.read_csv(options['csv'])

        self.logger.info("Parsing and cleaning English and French data ...")

        # drop records with NA summaries
        df_en = df_ati.dropna(subset=["summary_en"])
        df_fr = df_ati.dropna(subset=["summary_fr"])

        X_en = df_en['summary_en']
        X_fr = df_fr['summary_fr']
        y_en = df_en.owner_org_title
        y_fr = df_fr.owner_org_title

        X_train_en = X_en
        X_train_fr = X_fr
        y_train_en = y_en
        y_train_fr = y_fr

        # Tf-idf term weighting
        text_clf_en = Pipeline([
            ('tfidf',
             TfidfVectorizer(tokenizer=tokenize, stop_words=stopwords.words('english'), min_df=0.000075)),
            ('clf', LogisticRegression(penalty='l2',
                                       dual=False,
                                       tol=0.0001,
                                       C=10.0,
                                       fit_intercept=True,
                                       intercept_scaling=1,
                                       class_weight=None,
                                       random_state=None,
                                       solver='newton-cg',
                                       max_iter=100,
                                       multi_class='multinomial',
                                       verbose=0,
                                       warm_start=False,
                                       n_jobs=1))])

        # Tf-idf term weighting
        text_clf_fr = Pipeline([
            ('tfidf',
             TfidfVectorizer(tokenizer=tokenize, stop_words=stopwords.words('french'), min_df=0.000075)),
            ('clf', LogisticRegression(penalty='l2',
                                       dual=False,
                                       tol=0.0001,
                                       C=10.0,
                                       fit_intercept=True,
                                       intercept_scaling=1,
                                       class_weight=None,
                                       random_state=None,
                                       solver='newton-cg',
                                       max_iter=100,
                                       multi_class='multinomial',
                                       verbose=0,
                                       warm_start=False,
                                       n_jobs=1))])
        # English Model

        self.logger.info("fitting English model...")
        model_en = text_clf_en.fit(X_train_en, y_train_en)

        classifier_en = os.path.join(settings.NLTK_DATADIR, 'ati_en.model')
        self.logger.info(f"Saving English model to {classifier_en}")
        pickle.dump(model_en, open(classifier_en, 'wb'))

        # French Model

        self.logger.info("fitting French model...")
        model_fr = text_clf_fr.fit(X_train_fr, y_train_fr)

        classifier_fr = os.path.join(settings.NLTK_DATADIR, 'ati_fr.model')
        self.logger.info(f"Saving French model to {classifier_fr}")
        pickle.dump(model_fr, open(classifier_fr, 'wb'))

        self.logger.info("Done")
