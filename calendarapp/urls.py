from django.urls import path

from . import views
from .views import  other_views
#from django.conf.urls.static import static
#from django.conf import settings
app_name = 'calendarapp'


urlpatterns = [
    path('calender/', views.CalendarViewNew.as_view(), name='calendar'),
    #path('', other_views.SubirArchivos(), name='archivos'),
    path('calenders/', views.CalendarView.as_view(), name='calendars'),
    path('event/new/', views.create_event, name='event_new'),
    path(
        'event/edit/<int:pk>/', views.EventEdit.as_view(), name='event_edit'
    ),
    path(
        'event/<int:event_id>/details/', views.event_details,
        name='event-detail'
    ),

    path(
        'add_eventmember/<int:event_id>', views.add_eventmember,
        name='add_eventmember'
    ),
    path(
        'event/<int:pk>/remove', views.EventMemberDeleteView.as_view(),
        name="remove_event"
    ),
    path(
        'all-event-list/', views.AllEventsListView.as_view(),
        name="all_events"
    ),
    path(
        'running-event-list/', views.RunningEventsListView.as_view(),
        name="running_events"
    ),
    path('excel/', other_views.sub_excel, name='excel'),
path(
        'event/aprobacion/<int:event_id>', other_views.agregar_aprobacion,
        name='event-aprobacion'
    ),
]
#if settings.DEBUG:
 #   urlpatterns += static(
  #      settings.MEDIA_URL,
   #     document_root = settings.MEDIA_ROOT
   # )