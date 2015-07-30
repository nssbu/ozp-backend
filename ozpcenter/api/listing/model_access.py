"""
Model access
"""
import logging

from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist

import ozpcenter.models as models
import ozpcenter.utils as utils
import ozpcenter.model_access as generic_model_access

# Get an instance of a logger
logger = logging.getLogger('ozp-center')

def filter_listings(username, filter_params):
    """
    Filter Listings

    Respects private apps (only from user's agency) and user's
    max_classification_level

    filter_params can contain:
        * list of category names (OR logic)
        * list of agencies (OR logic)
        * list of listing types (OR logic)
        * offset (for pagination)

    Too many variations to cache
    """
    objects = models.Listing.objects.for_user(username).all()
    if 'categories' in filter_params:
        # TODO: this is OR logic not AND
        objects = objects.filter(
            categories__title__in=filter_params['categories'])
    if 'agencies' in filter_params:
        objects = objects.filter(
            agency__short_name__in=filter_params['agencies'])
    if 'listing_types' in filter_params:
        objects = objects.filter(
            app_type__title__in=filter_params['listing_types'])

    # enforce any pagination params
    if 'offset' in filter_params:
        offset = int(filter_params['offset'])
        objects = objects[offset:]

    if 'limit' in filter_params:
        limit = int(filter_params['limit'])
        objects = objects[0:limit]

    return objects

def get_self_listings(username):
    """
    Get the Listings that belong to this user

    Key: self_listings:<username>
    """
    username = utils.make_keysafe(username)
    key = 'self_listings:%s' % username
    data = cache.get(key)
    if data is None:
        try:
            user = generic_model_access.get_profile(username)
            data = models.Listing.objects.for_user(username).filter(
                owners__in=[user.id])
            cache.set(key, data)
            return data
        except ObjectDoesNotExist:
            return None
    else:
        return data

def get_listings(username):
    """
    Get Listings this user can see

    Key: listings:<username>
    """
    username = utils.make_keysafe(username)
    key = 'listings:%s' % username
    data = cache.get(key)
    if data is None:
        try:
            data = models.Listing.objects.for_user(username).all()
            cache.set(key, data)
            return data
        except ObjectDoesNotExist:
            return None
    else:
        return data

def get_item_comments(username):
    """
    Get ItemComments this user can see

    Key: item_comments:<username>
    """
    username = utils.make_keysafe(username)
    key = 'item_comments:%s' % username
    data = cache.get(key)
    if data is None:
        try:
            data = models.ItemComment.objects.for_user(username).all()
            cache.set(key, data)
            return data
        except ObjectDoesNotExist:
            return None
    else:
        return data

def update_rating(username, listing_id):
    """
    Invoked each time a review is created, deleted, or updated
    """
    listing = models.Listing.objects.for_user(username).get(id=listing_id)
    reviews = models.ItemComment.objects.filter(listing__id=listing_id)
    rate1 = reviews.filter(rate=1).count()
    rate2 = reviews.filter(rate=2).count()
    rate3 = reviews.filter(rate=3).count()
    rate4 = reviews.filter(rate=4).count()
    rate5 = reviews.filter(rate=5).count()
    total_votes = reviews.count()
    total_comments = total_votes - reviews.filter(text=None).count()

    # calculate weighted average
    avg_rate = (5*rate5 + 4*rate4 + 3*rate3 + 2*rate2 + rate1)/total_votes

    # update listing
    listing.total_rate1 = rate1
    listing.total_rate2 = rate2
    listing.total_rate3 = rate3
    listing.total_rate4 = rate4
    listing.total_rate5 = rate5
    listing.total_votes = total_votes
    listing.total_comments = total_comments
    listing.avg_rate = avg_rate
    listing.save()







