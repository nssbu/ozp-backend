"""
Recommendation Engine Runner

settings.py/or this file?
-----
recommendation_engines = ['ElasticsearchUserBaseRecommender', 'ElasticsearchContentBaseRecommender', 'CrabUserBaseRecommender']
----

obj = ElasticsearchUserBaseRecommender()
obj.recommend()

obj.merge(CrabUserBaseRecommender().recommend())

obj.save_to_db()
************************************WARNING************************************
Running this script will delete existing Recommendations in database
************************************WARNING************************************
"""
import sys
import os

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '../../')))

from ozpcenter.recommend.recommend import RecommenderDirectory

RECOMMENDATION_ENGINE = os.getenv('RECOMMENDATION_ENGINE', 'sample_data')

def run():
    """
    Run the Recommendation Engine
    """
    print('RECOMMENDATION_ENGINE: {}'.format(RECOMMENDATION_ENGINE))

    recommender_wrapper_obj = RecommenderDirectory()
    recommender_wrapper_obj.recommend(RECOMMENDATION_ENGINE)
