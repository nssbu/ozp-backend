"""
"""
import logging

from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework import permissions
from rest_framework import generics, status
from rest_framework.response import Response

import ozpcenter.api.intent.model_access as intent_model_access
import ozpcenter.api.intent.serializers as intent_serializers
import ozpcenter.model_access as model_access
import ozpiwc.hal as hal

# Get an instance of a logger
logger = logging.getLogger('ozp-iwc')

@api_view(['GET'])
@permission_classes((permissions.IsAuthenticated, ))
def IntentListView(request):
    """
    List of intents
    """
    root_url = hal.get_abs_url_for_iwc(request)
    profile = model_access.get_profile(request.user.username)
    data = hal.create_base_structure(request)
    intents = intent_model_access.get_all_intents()
    items = []
    for i in intents:
        item = {"href": '%sintent/%s/' % (root_url, i.id)}
        items.append(item)
    data['_links']['item'] = items

    return Response(data)

@api_view(['GET'])
@permission_classes((permissions.IsAuthenticated, ))
def IntentView(request, id='0'):
    """
    Single intent
    """
    root_url = hal.get_abs_url_for_iwc(request)
    profile = model_access.get_profile(request.user.username)

    queryset = intent_model_access.get_intent_by_id(id)
    if not queryset:
        return Response(status=status.HTTP_404_NOT_FOUND)
    serializer = intent_serializers.IntentSerializer(queryset,
            context={'request': request})
    data = serializer.data
    data = hal.add_hal_structure(data, request)

    return Response(data)