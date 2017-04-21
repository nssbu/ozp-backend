"""
Storefront and Metadata Model Access
"""
import logging

from django.db.models.functions import Lower
from django.db import connection
import msgpack


import ozpcenter.api.listing.serializers as listing_serializers
from ozpcenter import models
from ozpcenter.pipe import pipes
from ozpcenter.pipe import pipeline
from ozpcenter.recommend import recommend_utils
# Get an instance of a logger
logger = logging.getLogger('ozp-center.' + str(__name__))


def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]

# SELECT
#   ozpcenter_profile.id profile_id,
#   ozpcenter_profile.display_name profile_display_name,
#   auth_user.username profile_username,
#   auth_group.name profile_group_name,
#   CASE auth_group.name
#     WHEN 'APPS_MALL_STEWARD' THEN 1
#     WHEN 'ORG_STEWARD' THEN 2
#     WHEN 'USER' THEN 3
#   END role_priority,
#   agency.title agency_title,
#   steward_agency.title steward_agency
#
# FROM ozpcenter_profile
#   JOIN auth_user ON (ozpcenter_profile.user_id = auth_user.id)
#   JOIN auth_user_groups ON (auth_user_groups.user_id = auth_user.id)
#   JOIN auth_group ON (auth_user_groups.group_id = auth_group.id)
#
#   LEFT JOIN agency_profile ON (ozpcenter_profile.id = agency_profile.profile_id)
#   LEFT JOIN ozpcenter_agency agency ON (agency_profile.agency_id = agency.id)
#
#   LEFT JOIN stewarded_agency_profile ON (ozpcenter_profile.id = stewarded_agency_profile.profile_id)
#   LEFT JOIN ozpcenter_agency steward_agency ON (stewarded_agency_profile.agency_id = steward_agency.id)
# ORDER BY role_priority


def get_sql_statement():
    schema_class_str = str(connection.SchemaEditorClass)
    is_deleted = None
    is_enabled = None

    if 'sqlite' in schema_class_str:
        is_deleted = '0'
        is_enabled = '1'
    elif 'postgres' in schema_class_str:
        is_deleted = 'False'
        is_enabled = 'True'
    else:
        raise Exception('Get SQL Statment ENGINE Error')

    sql_statement = '''
SELECT DISTINCT
  ozpcenter_listing.id,
  ozpcenter_listing.title,
  ozpcenter_listing.approved_date,
  ozpcenter_listing.edited_date,
  ozpcenter_listing.description,
  ozpcenter_listing.launch_url,
  ozpcenter_listing.version_name,
  ozpcenter_listing.unique_name,
  ozpcenter_listing.what_is_new,
  ozpcenter_listing.requirements,
  ozpcenter_listing.description_short,
  ozpcenter_listing.approval_status,
  ozpcenter_listing.is_enabled,
  ozpcenter_listing.is_featured,
  ozpcenter_listing.avg_rate,
  ozpcenter_listing.total_votes,
  ozpcenter_listing.total_rate4,
  ozpcenter_listing.total_rate5,
  ozpcenter_listing.total_rate3,
  ozpcenter_listing.total_rate2,
  ozpcenter_listing.total_rate1,
  ozpcenter_listing.total_reviews,
  ozpcenter_listing.iframe_compatible,
  ozpcenter_listing.security_marking,
  ozpcenter_listing.is_private,
  ozpcenter_listing.current_rejection_id,
  ozpcenter_listing.last_activity_id,
  ozpcenter_listing.listing_type_id,
  ozpcenter_listing.required_listings_id,
  ozpcenter_listing.is_deleted,

  /* One to Many */
  ozpcenter_listing.listing_type_id,
  ozpcenter_listingtype.title listing_type_title,

  /* One to Many Images*/
  ozpcenter_listing.agency_id agency_id,
  ozpcenter_agency.title agency_title,
  ozpcenter_agency.short_name agency_short_name,

  ozpcenter_listing.small_icon_id,
  small_icon.security_marking small_icon_security_marking,

  ozpcenter_listing.large_icon_id,
  large_icon.security_marking large_icon_security_marking,

  ozpcenter_listing.banner_icon_id,
  banner_icon.security_marking banner_icon_security_marking,

  ozpcenter_listing.large_banner_icon_id,
  large_banner_icon.security_marking large_banner_icon_security_marking,

  /* Many to Many */
  /* Category */
  category_listing.category_id,
  ozpcenter_category.title category_title,
  ozpcenter_category.description category_description,

  /* Contact */
  contact_listing.contact_id contact_id,
  ozpcenter_contact.contact_type_id contact_type_id, /* Check to see if contact_id and contact_type_id is correct*/
  ozpcenter_contacttype.name contact_type_name,
  ozpcenter_contact.secure_phone contact_secure_phone,
  ozpcenter_contact.unsecure_phone contact_unsecure_phone,
  ozpcenter_contact.email contact_email,
  ozpcenter_contact.name contact_name,
  ozpcenter_contact.organization contact_organization,

  /* Tags */
  tag_listing.tag_id,
  ozpcenter_tag.name tag_name,

  /* Owners */
  owners.profile_id,
  owner_profile.display_name owner_display_name,
  owner_profile.user_id owner_user_id,
  owner_user.username owner_username,

  /* Intents */
  intent_listing.intent_id,
  ozpcenter_intent.action intent_action,

  /* Bookmarks */
  lib_entries.count bookmark_count
FROM
  ozpcenter_listing
/* One to Many Joins */
JOIN ozpcenter_agency ON (ozpcenter_listing.agency_id = ozpcenter_agency.id)
JOIN ozpcenter_listingtype ON (ozpcenter_listingtype.id = ozpcenter_listing.listing_type_id)
JOIN ozpcenter_image small_icon ON (small_icon.id = ozpcenter_listing.small_icon_id)
JOIN ozpcenter_image large_icon ON (large_icon.id = ozpcenter_listing.small_icon_id)
JOIN ozpcenter_image banner_icon ON (banner_icon.id = ozpcenter_listing.small_icon_id)
JOIN ozpcenter_image large_banner_icon ON (large_banner_icon.id = ozpcenter_listing.small_icon_id)
/* Many to Many Joins */

/* Categories */
LEFT JOIN category_listing ON (category_listing.listing_id = ozpcenter_listing.id)
LEFT JOIN ozpcenter_category on (category_listing.category_id = ozpcenter_category.id)

/* Contacts */
LEFT JOIN contact_listing ON (contact_listing.listing_id = ozpcenter_listing.id)
LEFT JOIN ozpcenter_contact on (contact_listing.contact_id = ozpcenter_contact.id)
LEFT JOIN ozpcenter_contacttype on (ozpcenter_contact.contact_type_id = ozpcenter_contacttype.id)

/* Tags */
LEFT JOIN tag_listing ON (tag_listing.listing_id = ozpcenter_listing.id)
LEFT JOIN ozpcenter_tag ON (tag_listing.tag_id = ozpcenter_tag.id)

/* Owners */
LEFT JOIN profile_listing owners ON (owners.listing_id = ozpcenter_listing.id)
LEFT JOIN ozpcenter_profile owner_profile ON (owners.profile_id = owner_profile.id)
LEFT JOIN auth_user owner_user ON (owner_profile.user_id = owner_user.id)

/* Intent */
LEFT JOIN intent_listing ON (intent_listing.listing_id = ozpcenter_listing.id)
LEFT JOIN ozpcenter_intent ON (intent_listing.intent_id = ozpcenter_intent.id)

/* Bookmarks */
LEFT JOIN (SELECT ozpcenter_applicationlibraryentry.listing_id, count(ozpcenter_applicationlibraryentry.listing_id)
           FROM ozpcenter_applicationlibraryentry
           GROUP BY ozpcenter_applicationlibraryentry.listing_id) lib_entries ON (lib_entries.listing_id = ozpcenter_listing.id)
/*
Get Listings that are enabled, not deleted, and approved
*/
WHERE ozpcenter_listing.is_enabled = {} AND
      ozpcenter_listing.is_deleted = {} AND
      ozpcenter_listing.approval_status = 'APPROVED'
ORDER BY ozpcenter_listing.approved_date DESC;
    '''.format(is_enabled, is_deleted)
    return sql_statement


def get_user_listings(username):
    """
    Get User listings

    Returns:
        Python object of listings
    """
    mapping_dict = {}

    cursor = connection.cursor()

    cursor.execute(get_sql_statement())
    rows = dictfetchall(cursor)

    categories_set = set()
    tags_set = set()
    contacts_set = set()
    profile_set = set()
    intents_set = set()

    for row in rows:
        if row['id'] not in mapping_dict:
            mapping_dict[row['id']] = {
                "is_enabled": row['is_enabled'],
                "required_listings_id": row['required_listings_id'],
                "is_private": row['is_private'],
                "total_rate2": row['total_rate2'],
                "id": row['id'],
                "avg_rate": row['avg_rate'],
                "unique_name": row['unique_name'],

                "approved_date": row['approved_date'],
                "total_rate5": row['total_rate5'],
                "requirements": row['requirements'],
                "iframe_compatible": row['iframe_compatible'],
                "last_activity_id": row['last_activity_id'],
                "total_rate4": row['total_rate4'],
                "total_rate3": row['total_rate3'],
                "what_is_new": row['what_is_new'],
                "total_rate1": row['total_rate1'],
                "is_deleted": row['is_deleted'],
                "security_marking": row['security_marking'],
                "version_name": row['version_name'],
                "approval_status": row['approval_status'],
                "current_rejection_id": row['current_rejection_id'],
                "is_featured": row['is_featured'],
                "title": row['title'],
                "description_short": row['description_short'],
                "total_reviews": row['total_reviews'],
                "listing_type_id": row['listing_type_id'],
                "launch_url": row['launch_url'],
                "edited_date": row['edited_date'],
                "description": row['description'],
                "total_votes": row['total_votes'],
                # One to One
                "agency": {'title': row['agency_title'],
                           'short_name': row['agency_short_name']},
                "small_icon": {"id": row['small_icon_id'],
                               'url': None,
                               "security_marking": row['small_icon_security_marking']},
                "large_icon": {"id": row['large_icon_id'],
                               'url': None,
                               "security_marking": row['large_icon_security_marking']},
                "banner_icon": {"id": row['banner_icon_id'],
                                'url': None,
                                "security_marking": row['banner_icon_security_marking']},
                "large_banner_icon": {"id": row['large_banner_icon_id'],
                                      'url': None,
                                      "security_marking": row['large_banner_icon_security_marking']}
            }

            # Many to Many
            if row['category_id']:
                mapping_dict[row['id']]['categories'] = {row['category_id']:
                                                         {'title': row['category_title'],
                                                          'description': row['category_description']}}
                categories_set.add(row['category_id'])
            else:
                mapping_dict[row['id']]['categories'] = {}

            if row['tag_id']:
                mapping_dict[row['id']]['tags'] = {row['tag_id']: {'name': row['tag_name']}}
                tags_set.add(row['tag_id'])
            else:
                mapping_dict[row['id']]['tags'] = {}

            if row['contact_id']:
                mapping_dict[row['id']]['contacts'] = {row['contact_id']: {'id': row['contact_id'],
                                                     'secure_phone': row['contact_secure_phone'],
                                                     'unsecure_phone': row['contact_unsecure_phone'],
                                                     'email': row['contact_email'],
                                                     'name': row['contact_name'],
                                                     'organization': row['contact_organization'],
                                                     'contact_type': {'name': row['contact_type_name']}
                    }}
                contacts_set.add(row['contact_id'])
            else:
                mapping_dict[row['id']]['contacts'] = {}

            if row['profile_id']:
                mapping_dict[row['id']]['owners'] = {row['profile_id']: {'display_name': row['owner_display_name'],
                    'user': {'username': row['owner_username']}}}
                profile_set.add(row['profile_id'])
            else:
                mapping_dict[row['id']]['owners'] = {}

            if row['intent_id']:
                mapping_dict[row['id']]['intents'] = {row['intent_id']: None}
                intents_set.add(row['intent_id'])
            else:
                mapping_dict[row['id']]['intents'] = {}

        else:
            if row['category_id']:
                if row['category_id'] not in mapping_dict[row['id']]['categories']:
                    mapping_dict[row['id']]['categories'][row['category_id']] = {'title': row['category_title'],
                                                                                 'description': row['category_description']}
                    categories_set.add(row['category_id'])

            if row['tag_id']:
                if row['tag_id'] not in mapping_dict[row['id']]['tags']:
                    mapping_dict[row['id']]['tags'][row['tag_id']] = {'name': row['tag_name']}
                    tags_set.add(row['tag_id'])

            if row['contact_id']:
                if row['contact_id'] not in mapping_dict[row['id']]['contacts']:
                    mapping_dict[row['id']]['contacts'][row['contact_id']] = {'id': row['contact_id'],
                                                         'secure_phone': row['contact_secure_phone'],
                                                         'unsecure_phone': row['contact_unsecure_phone'],
                                                         'email': row['contact_email'],
                                                         'name': row['contact_name'],
                                                         'organization': row['contact_organization'],
                                                         'contact_type': {'name': row['contact_type_name']}
                        }
                    contacts_set.add(row['contact_id'])

            if row['profile_id']:
                if row['profile_id'] not in mapping_dict[row['id']]['owners']:
                    mapping_dict[row['id']]['owners'][row['profile_id']] = {'display_name': row['owner_display_name'],
                        'user': {'username': row['owner_username']}}
                    profile_set.add(row['profile_id'])

            if row['intent_id']:
                if row['intent_id'] not in mapping_dict[row['id']]['intents']:
                    mapping_dict[row['id']]['intents'][row['intent_id']] = None
                    intents_set.add(row['intent_id'])

    for profile_key in mapping_dict:
        profile_map = mapping_dict[profile_key]
        profile_map['owners'] = [profile_map['owners'][p_key] for p_key in profile_map['owners']]
        profile_map['tags'] = [profile_map['tags'][p_key] for p_key in profile_map['tags']]
        profile_map['categories'] = [profile_map['categories'][p_key] for p_key in profile_map['categories']]
        profile_map['contacts'] = [profile_map['contacts'][p_key] for p_key in profile_map['contacts']]
        profile_map['intents'] = [profile_map['intents'][p_key] for p_key in profile_map['intents']]

    return list(mapping_dict.values())


def get_storefront(username, pre_fetch=False):
    """
    Returns data for /storefront api invocation including:
        * recommended listings (max=10)
        * featured listings (max=12)
        * recent (new) listings (max=24)
        * most popular listings (max=36)

    NOTE: think about adding Bookmark status to this later on

    Args:
        username

    Returns:
        {
            'recommended': [Listing],
            'featured': [Listing],
            'recent': [Listing],
            'most_popular': [Listing]
        }
    """
    profile = models.Profile.objects.get(user__username=username)
    try:
        # Get Recommended Listings for owner
        target_profile_recommended_entry = models.RecommendationsEntry.objects.filter(target_profile=profile).first()  # Get

        recommended_entry_data = {}
        if target_profile_recommended_entry:
            recommendation_data = target_profile_recommended_entry.recommendation_data
            if recommendation_data:
                recommended_entry_data = msgpack.unpackb(recommendation_data)

        recommendation_combined_dict = {'profile': {}}

        for recommender_friendly_name in recommended_entry_data:
            recommender_name_data = recommended_entry_data[recommender_friendly_name]
            # print(recommender_name_data)
            recommender_name_weight = recommender_name_data[b'weight']
            recommender_name_recommendations = recommender_name_data[b'recommendations']

            for recommendation_tuple in recommender_name_recommendations:
                current_listing_id = recommendation_tuple[0]
                current_listing_score = recommendation_tuple[1]

                if current_listing_id in recommendation_combined_dict['profile']:
                    recommendation_combined_dict['profile'][current_listing_id] = recommendation_combined_dict['profile'][current_listing_id] + (current_listing_score * recommender_name_weight)
                else:
                    recommendation_combined_dict['profile'][current_listing_id] = current_listing_score * recommender_name_weight

        sorted_recommendations_combined_dict = recommend_utils.get_top_n_score(recommendation_combined_dict, 40)
        listing_ids_list = [entry[0] for entry in sorted_recommendations_combined_dict['profile']]

        recommended_listings_queryset = models.Listing.objects.for_user_organization_minus_security_markings(username).filter(pk__in=listing_ids_list,
                                                                                                                              approval_status=models.Listing.APPROVED,
                                                                                                                              is_enabled=True,
                                                                                                                              is_deleted=False).all()

        recommended_listings_raw = listing_serializers.ListingSerializer.setup_eager_loading(recommended_listings_queryset)

        if pre_fetch:
            recommended_listings_raw = [recommendations_listing for recommendations_listing in recommended_listings_raw]

        # Post security_marking check - lazy loading
        recommended_listings = pipeline.Pipeline(recommend_utils.ListIterator([recommendations_listing for recommendations_listing in recommended_listings_raw]),
                                          [pipes.ListingPostSecurityMarkingCheckPipe(username),
                                           pipes.LimitPipe(10)]).to_list()

        # Get Featured Listings
        featured_listings_raw = models.Listing.objects.for_user_organization_minus_security_markings(
            username).filter(
                is_featured=True,
                approval_status=models.Listing.APPROVED,
                is_enabled=True,
                is_deleted=False)

        if pre_fetch:
            featured_listings_raw = listing_serializers.ListingSerializer.setup_eager_loading(featured_listings_raw)

        featured_listings = pipeline.Pipeline(recommend_utils.ListIterator([listing for listing in featured_listings_raw]),
                                          [pipes.ListingPostSecurityMarkingCheckPipe(username),
                                           pipes.LimitPipe(12)]).to_list()

        # Get Recent Listings
        recent_listings_raw = models.Listing.objects.for_user_organization_minus_security_markings(
            username).order_by('-approved_date').filter(
            approval_status=models.Listing.APPROVED,
            is_enabled=True,
            is_deleted=False)

        if pre_fetch:
            recent_listings_raw = listing_serializers.ListingSerializer.setup_eager_loading(recent_listings_raw)

        recent_listings = pipeline.Pipeline(recommend_utils.ListIterator([listing for listing in recent_listings_raw]),
                                          [pipes.ListingPostSecurityMarkingCheckPipe(username),
                                           pipes.LimitPipe(24)]).to_list()

        # Get most popular listings via a weighted average
        most_popular_listings_raw = models.Listing.objects.for_user_organization_minus_security_markings(
            username).filter(
                approval_status=models.Listing.APPROVED,
                is_enabled=True,
                is_deleted=False).order_by('-avg_rate', '-total_reviews')

        if pre_fetch:
            most_popular_listings_raw = listing_serializers.ListingSerializer.setup_eager_loading(most_popular_listings_raw)

        most_popular_listings = pipeline.Pipeline(recommend_utils.ListIterator([listing for listing in most_popular_listings_raw]),
                                          [pipes.ListingPostSecurityMarkingCheckPipe(username),
                                           pipes.LimitPipe(36)]).to_list()

        data = {
            'recommended': recommended_listings,
            'featured': featured_listings,
            'recent': recent_listings,
            'most_popular': most_popular_listings
        }
    except Exception:
        # raise Exception({'error': True, 'msg': 'Error getting storefront: {0!s}'.format(str(e))})
        raise  # Should be catch in the django framwork
    return data


def values_query_set_to_dict(vqs):
    return [item for item in vqs]


def get_metadata(username):
    """
    Returns metadata including:
        * categories
        * organizations (agencies)
        * listing types
        * intents
        * contact types

    Key: metadata
    """
    try:
        data = {}
        data['categories'] = values_query_set_to_dict(models.Category.objects.all().values(
            'id', 'title', 'description').order_by(Lower('title')))

        data['listing_types'] = values_query_set_to_dict(models.ListingType.objects.all().values(
            'title', 'description'))

        data['agencies'] = values_query_set_to_dict(models.Agency.objects.all().values(
            'title', 'short_name', 'icon', 'id'))

        data['contact_types'] = values_query_set_to_dict(models.ContactType.objects.all().values(
            'name', 'required'))

        data['intents'] = values_query_set_to_dict(models.Intent.objects.all().values(
            'action', 'media_type', 'label', 'icon', 'id'))

        # return icon/image urls instead of the id and get listing counts
        for i in data['agencies']:
            # i['icon'] = models.Image.objects.get(id=i['icon']).image_url()
            # i['icon'] = '/TODO'
            i['listing_count'] = models.Listing.objects.for_user(
                username).filter(agency__title=i['title'],
                approval_status=models.Listing.APPROVED).count()

        for i in data['intents']:
            # i['icon'] = models.Image.objects.get(id=i['icon']).image_url()
            i['icon'] = '/TODO'

        return data
    except Exception as e:
        return {'error': True, 'msg': 'Error getting metadata: {0!s}'.format(str(e))}
